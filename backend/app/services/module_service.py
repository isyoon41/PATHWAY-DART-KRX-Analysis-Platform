"""
분석 모듈 서비스 v2.1 — VC/PE 강화형 프롬프트 팩

개선 사항:
  1. DART 사업보고서 탐색: disc_list fallback + get_annual_report_rcept_no()
  3. S8 재무주석: audit_opinion 섹션 전용 사용
  5. 파일 기반 캐시 통합 (24h TTL)
  6. Gemini 세마포어(동시 3개) + 지수 백오프 재시도
  7. 분기 재무 데이터 S7에 통합
  8. 모듈별 max_tokens 최적화
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path

from config import settings
from app.services.dart_parser import create_parser
from app.services.dart_service import dart_service
from app.services.financial_parser import structure_financial_data
from app.services.krx_service import krx_service
from app.services.cache_service import get_cached, set_cached
from google import genai
from google.genai import types as genai_types


# ══════════════════════════════════════════════════════════════════════
# 프롬프트 팩 로드
# ══════════════════════════════════════════════════════════════════════

_PACK_PATH = Path(__file__).parent.parent / "prompt_packs" / "vcpe_v2.json"


def _load_pack() -> Dict:
    with open(_PACK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


try:
    _PACK: Dict = _load_pack()
except Exception as _e:
    raise RuntimeError(f"프롬프트 팩 로드 실패 ({_PACK_PATH}): {_e}")


# ══════════════════════════════════════════════════════════════════════
# 개선 6: Gemini 동시 호출 세마포어 (최대 3개 병렬)
# ══════════════════════════════════════════════════════════════════════

_GEMINI_SEMAPHORE = asyncio.Semaphore(3)


# ══════════════════════════════════════════════════════════════════════
# 개선 8: 모듈별 max_tokens 최적화
# ══════════════════════════════════════════════════════════════════════

MODULE_TOKENS: Dict[str, int] = {
    "comprehensive_corporate_analysis":  16384,  # 최대 → 전체 분석
    "key_financial_indicators":           8192,
    "complete_financial_statements":      8192,
    "business_segment_performance":       8192,
    "shareholder_structure":              4096,  # 단순 구조 분석
    "board_executive_analysis":           4096,
    "stock_price_movement_analysis":      8192,
    "paid_in_capital_increase":           8192,
    "preliminary_results":                8192,
    "_meta":                             32768,  # 메타 분석 최대
}


# ══════════════════════════════════════════════════════════════════════
# S1-S11 섹션 정의 (개선 3: S8 → audit_opinion)
# ══════════════════════════════════════════════════════════════════════

SECTION_DEFINITIONS: Dict[str, Dict] = {
    "S1":  {"dart_code": "company_overview",  "name": "기업 개요",       "char_limit": 8000},
    "S2":  {"dart_code": "business_content",  "name": "사업의 내용",     "char_limit": 20000},
    "S3":  {"dart_code": "business_content",  "name": "사업부문 정보",   "char_limit": 20000},
    "S4":  {"dart_code": "risk_factors",      "name": "위험요인",         "char_limit": 15000,
             "fallback": "business_content"},
    "S5":  {"dart_code": None,               "name": "주주구조",          "char_limit": 0},
    "S6":  {"dart_code": "board_governance", "name": "이사회·임원",      "char_limit": 8000,
             "also": "executives"},
    "S7":  {"dart_code": "financial_info",   "name": "재무제표",          "char_limit": 15000,
             "also": "audit_opinion"},
    # 개선 3: S8은 audit_opinion 전용 (감사인 의견 + 핵심감사사항 = 실질 재무주석)
    "S8":  {"dart_code": "audit_opinion",    "name": "감사의견·재무주석", "char_limit": 12000,
             "fallback": "financial_info"},
    "S9":  {"dart_code": None,               "name": "자본조달 이벤트",  "char_limit": 0},
    "S10": {"dart_code": None,               "name": "잠정·이벤트 공시", "char_limit": 0},
    "S11": {"dart_code": None,               "name": "시장 데이터",       "char_limit": 0},
}

_CAPITAL_KEYWORDS = [
    "유상증자", "전환사채", "신주인수권부사채", "교환사채",
    "주주배정", "일반공모", "제3자배정",
]


# ══════════════════════════════════════════════════════════════════════
# MODULES 딕셔너리 (프롬프트 팩에서 동적 생성)
# ══════════════════════════════════════════════════════════════════════

MODULE_ID_ALIAS: Dict[str, str] = {
    "comprehensive":     "comprehensive_corporate_analysis",
    "key_financials":    "key_financial_indicators",
    "full_financials":   "complete_financial_statements",
    "business_segments": "business_segment_performance",
    "shareholders":      "shareholder_structure",
    "board_executives":  "board_executive_analysis",
    "stock_movement":    "stock_price_movement_analysis",
    "capital_increase":  "paid_in_capital_increase",
    "preliminary":       "preliminary_results",
}

MODULES: Dict[str, Dict] = {}
for _mid, _mdef in _PACK.get("modules", {}).items():
    MODULES[_mid] = {
        "id":                _mid,
        "name":              _mdef.get("label_ko", _mid),
        "badge":             "VCPE",
        "is_core":           True,
        "desc":              _mdef.get("purpose", ""),
        "required_sections": _mdef.get("required_sections", []),
        "optional_sections": _mdef.get("optional_sections", []),
        "uses_financials":   any(s in ["S7", "S8"] for s in _mdef.get("required_sections", [])),
        "uses_governance":   any(s in ["S5", "S6"] for s in _mdef.get("required_sections", [])),
        "uses_disclosures":  any(s in ["S9", "S10"] for s in _mdef.get("required_sections", [])),
        "uses_market_data":  "S11" in _mdef.get("required_sections", []),
        "max_tokens":        MODULE_TOKENS.get(_mid, 8192),
    }


# ══════════════════════════════════════════════════════════════════════
# 개선 1: DART HTML 섹션 수집 (disc_list + get_annual_report_rcept_no 폴백)
# ══════════════════════════════════════════════════════════════════════

async def _fetch_sections_from_report(
    corp_code: str,
    disc_list: List[Dict],
    section_ids: List[str],
    end_year: Optional[int] = None,   # ← 개선 1: 폴백용 연도 추가
) -> Dict[str, Dict]:
    """
    사업보고서 HTML → 지정 섹션 추출

    탐색 우선순위:
      1) disc_list에서 사업보고서 접수번호 추출
      2) 없으면 dart_service.get_annual_report_rcept_no() 직접 호출 (개선 1)
    """
    dart_codes_needed: List[str] = []
    for sid in section_ids:
        sdef = SECTION_DEFINITIONS.get(sid, {})
        for key in ("dart_code", "also", "fallback"):
            code = sdef.get(key)
            if code and code not in dart_codes_needed:
                dart_codes_needed.append(code)

    if not dart_codes_needed:
        return {}

    # ── 1차: disc_list에서 사업보고서 검색 ──────────────────────────
    rcept_no = ""
    rcept_dt = ""
    annual = [
        d for d in disc_list
        if "사업보고서" in d.get("report_nm", "")
        and "정정" not in d.get("report_nm", "")
    ]
    if annual:
        rcept_no = annual[0].get("rcept_no", "")
        rcept_dt = annual[0].get("rcept_dt", "")

    # ── 2차: 개선 1 — get_annual_report_rcept_no() 폴백 ────────────
    if not rcept_no and end_year:
        try:
            annual_meta = await asyncio.wait_for(
                dart_service.get_annual_report_rcept_no(corp_code, end_year),
                timeout=15.0,
            )
            if annual_meta and annual_meta.get("rcept_no"):
                rcept_no = annual_meta["rcept_no"]
                rcept_dt = annual_meta.get("rcept_dt", "")
        except Exception:
            pass

    if not rcept_no:
        return {}

    # ── 사업보고서 HTML 다운로드 & 섹션 분해 ─────────────────────────
    try:
        parser   = create_parser(settings.dart_api_key)
        doc_files = await asyncio.wait_for(
            parser.fetch_report_index(rcept_no), timeout=25.0
        )
        if not doc_files:
            return {}

        html = await asyncio.wait_for(
            parser.fetch_document_html(rcept_no, doc_files[0].get("url", "")),
            timeout=30.0,
        )
        parsed = parser.parse_sections(html, rcept_no, {
            "corp_code":   corp_code,
            "report_type": "사업보고서",
            "report_date": rcept_dt,
        })

        dart_map: Dict[str, Dict] = {}
        for dc in dart_codes_needed:
            if dc in parsed.sections:
                sec = parsed.sections[dc]
                dart_map[dc] = {
                    "title":      sec.title,
                    "content":    sec.content,
                    "char_count": sec.char_count,
                    "rcept_no":   rcept_no,
                    "rcept_dt":   rcept_dt,
                }

        result: Dict[str, Dict] = {}
        for sid in section_ids:
            sdef       = SECTION_DEFINITIONS.get(sid, {})
            dc         = sdef.get("dart_code")
            char_limit = sdef.get("char_limit", 10000)
            if dc and dc in dart_map:
                data = dict(dart_map[dc])
                data["content"] = data["content"][:char_limit]
                result[sid] = data
                continue
            fb = sdef.get("fallback")
            if fb and fb in dart_map:
                data = dict(dart_map[fb])
                data["content"] = data["content"][:char_limit]
                data["title"] += " (해당 섹션 없음 — fallback)"
                result[sid] = data

        # S6: executives 추가
        if "S6" in section_ids and "executives" in dart_map and "S6" in result:
            result["S6"]["content"] += "\n\n[임원 현황]\n" + dart_map["executives"].get("content", "")[:4000]

        return result

    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════
# 재무 포맷 헬퍼
# ══════════════════════════════════════════════════════════════════════

def _fmt_financials(
    financials_by_year: Dict[str, Any],
    years: List[str],
    financials_quarterly: Optional[Dict[str, Any]] = None,   # 개선 7
) -> str:
    """연간 XBRL 재무 + 분기 실적 통합 텍스트"""
    lines = []
    for yr in years:
        f = financials_by_year.get(yr, {})
        if not f:
            continue
        inc    = f.get("income_statement", {})
        bal    = f.get("balance_sheet", {})
        rat    = f.get("ratios", {})
        cur_i  = inc.get("current", {})
        cur_b  = bal.get("current", {})
        prev_i = inc.get("previous", {})
        lines.append(
            f"[{yr}년 연간 재무 — DART XBRL]\n"
            f"  매출액:      {cur_i.get('revenue','N/A'):>15,} 천원"
            f"  (전기: {prev_i.get('revenue','N/A')})\n"
            f"  영업이익:    {cur_i.get('operating_profit','N/A'):>15,} 천원\n"
            f"  당기순이익:  {cur_i.get('net_income','N/A'):>15,} 천원\n"
            f"  총자산:      {cur_b.get('total_assets','N/A'):>15,} 천원\n"
            f"  자기자본:    {cur_b.get('total_equity','N/A'):>15,} 천원\n"
            f"  영업이익률:  {rat.get('operating_margin_pct','N/A'):>8}%  "
            f"순이익률: {rat.get('net_margin_pct','N/A'):>8}%\n"
            f"  ROE: {rat.get('roe_pct','N/A'):>8}%  "
            f"ROA: {rat.get('roa_pct','N/A'):>8}%  "
            f"부채비율: {rat.get('debt_ratio_pct','N/A'):>8}%"
        )

    # 개선 7: 분기 데이터 추가
    if financials_quarterly:
        qtr_lines = []
        for qtr_key in sorted(financials_quarterly.keys(), reverse=True)[:8]:
            qf = financials_quarterly.get(qtr_key, {})
            if not qf:
                continue
            inc_q = qf.get("income_statement", {}).get("current", {})
            rat_q = qf.get("ratios", {})
            rev   = inc_q.get("revenue", "N/A")
            op    = inc_q.get("operating_profit", "N/A")
            ni    = inc_q.get("net_income", "N/A")
            opm   = rat_q.get("operating_margin_pct", "N/A")
            qtr_lines.append(
                f"  [{qtr_key}] 매출:{rev:>12,}  영업:{op:>12,}  순익:{ni:>12,}  OPM:{opm}%"
                if isinstance(rev, (int, float)) else
                f"  [{qtr_key}] 데이터 없음"
            )
        if qtr_lines:
            lines.append("[분기별 실적 추이 — DART XBRL]\n" + "\n".join(qtr_lines))

    return "\n\n".join(lines) if lines else "[XBRL 재무 데이터 없음]"


def _fmt_disc_list(disc_list: List[Dict], limit: int = 40) -> str:
    lines = [
        f"  [{d.get('rcept_dt','')}] {d.get('report_nm','')} (제출: {d.get('flr_nm','')})"
        for d in disc_list[:limit]
    ]
    return "\n".join(lines) if lines else "[공시 없음]"


# ══════════════════════════════════════════════════════════════════════
# S1~S11 섹션 문자열 조립 (개선 7: 분기 데이터 통합)
# ══════════════════════════════════════════════════════════════════════

def _assemble_section_strings(
    fetched_sections: Dict[str, Dict],
    financials_by_year: Dict[str, Any],
    years: List[str],
    governance_data: Dict[str, Any],
    disc_list: List[Dict],
    market_data: Dict,
    stock_history: Optional[Dict] = None,
    financials_quarterly: Optional[Dict[str, Any]] = None,  # 개선 7
) -> Dict[str, str]:
    """S1~S11 각 섹션을 LLM용 텍스트로 변환"""
    s: Dict[str, str] = {}

    s["S1"] = fetched_sections.get("S1", {}).get("content") or "[기업 개요 없음]"
    s["S2"] = fetched_sections.get("S2", {}).get("content") or "[사업내용 없음]"
    s["S3"] = s["S2"]
    s["S4"] = fetched_sections.get("S4", {}).get("content") or "[위험요인 없음]"

    sh = governance_data.get("major_shareholders")
    s["S5"] = (
        json.dumps(sh, ensure_ascii=False, indent=2)[:5000]
        if sh else "[주주구조 데이터 없음]"
    )

    s["S6"] = fetched_sections.get("S6", {}).get("content") or ""
    ex = governance_data.get("executives")
    if ex:
        s["S6"] += "\n\n[임원 현황 (DART API)]\n" + json.dumps(ex, ensure_ascii=False, indent=2)[:3000]
    if not s["S6"].strip():
        s["S6"] = "[이사회·임원 데이터 없음]"

    # 개선 7: S7에 분기 데이터 포함
    s["S7"] = _fmt_financials(financials_by_year, years, financials_quarterly)

    # 개선 3: S8은 audit_opinion (감사의견 섹션)
    s["S8"] = fetched_sections.get("S8", {}).get("content") or "[감사의견 없음]"

    capital_discs = [
        d for d in disc_list
        if any(kw in d.get("report_nm", "") for kw in _CAPITAL_KEYWORDS)
    ]
    s["S9"] = _fmt_disc_list(capital_discs, 30) if capital_discs else "[자본조달 관련 공시 없음]"
    s["S10"] = _fmt_disc_list(disc_list, 40)

    s11_parts = []
    if market_data and "error" not in market_data:
        s11_parts.append(
            "[현재가 (KRX/네이버 금융)]\n"
            + json.dumps(market_data, ensure_ascii=False, indent=2)[:1500]
        )
    if stock_history and "error" not in stock_history:
        records = stock_history.get("records", [])
        if records:
            sample   = records[-90:]
            provider = stock_history.get("_source", {}).get("provider", "FDR")
            s11_parts.append(
                f"[일자별 주가 ({provider}) | "
                f"{stock_history.get('start_date','')} ~ {stock_history.get('end_date','')}]\n"
                f"총 {len(records)}거래일, 최근 {len(sample)}거래일:\n"
                + "\n".join(
                    f"  {r['date']}  종가:{r['close']:>10,.0f}  "
                    f"고가:{r['high']:>10,.0f}  저가:{r['low']:>10,.0f}  거래량:{r['volume']:>12,}"
                    for r in sample
                )
            )
    s["S11"] = "\n\n".join(s11_parts) if s11_parts else "[시장 데이터 없음]"

    return s


# ══════════════════════════════════════════════════════════════════════
# 템플릿 변수 치환
# ══════════════════════════════════════════════════════════════════════

def _fill_template(
    template: str,
    company: Dict,
    time_info: Dict,
    sections: Dict[str, str],
) -> str:
    r = template
    r = r.replace("{{company.corp_name}}",  company.get("corp_name", ""))
    r = r.replace("{{company.corp_code}}",  company.get("corp_code", ""))
    r = r.replace("{{company.stock_code}}", company.get("stock_code", "") or "")
    r = r.replace("{{time.as_of_date}}",    time_info.get("as_of_date", ""))
    r = r.replace("{{time.start_date}}",    time_info.get("start_date", ""))
    r = r.replace("{{time.end_date}}",      time_info.get("end_date", ""))
    r = r.replace("{{time.compare_mode}}",  time_info.get("compare_mode", "yoy"))
    for sid in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11"]:
        r = r.replace(f"{{{{sections.{sid}}}}}", sections.get(sid, f"[{sid} 없음]"))
    return r


def _fill_meta_template(
    template: str,
    company: Dict,
    time_info: Dict,
    module_outputs: Dict[str, Any],
    prev_result: Optional[Dict] = None,   # 개선 9: 증분 분석용
) -> str:
    r = template
    r = r.replace("{{company.corp_name}}",  company.get("corp_name", ""))
    r = r.replace("{{company.corp_code}}",  company.get("corp_code", ""))
    r = r.replace("{{company.stock_code}}", company.get("stock_code", "") or "")
    r = r.replace("{{time.as_of_date}}",    time_info.get("as_of_date", ""))
    r = r.replace("{{time.start_date}}",    time_info.get("start_date", ""))
    r = r.replace("{{time.end_date}}",      time_info.get("end_date", ""))
    r = r.replace("{{time.compare_mode}}",  time_info.get("compare_mode", "yoy"))
    for mod_name in _PACK.get("input_schema", {}).get("module_outputs", {}).keys():
        mod_json = json.dumps(
            module_outputs.get(mod_name, {}), ensure_ascii=False, indent=2
        )
        r = r.replace(f"{{{{module_outputs.{mod_name}}}}}", mod_json)
    return r


def _parse_json_response(text: str) -> Dict:
    """LLM 응답에서 JSON 추출 파싱 (다단계 폴백)"""
    import logging
    _log = logging.getLogger("pathway.module_service")

    if not text or not text.strip():
        return {"raw_response": "", "_parse_error": "빈 응답"}

    # 1단계: 마크다운 코드 펜스 제거
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text).strip()
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    # 2단계: 직접 파싱 시도
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3단계: 첫 번째 '{' ~ 마지막 '}' 추출 (greedy)
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 4단계: trailing comma 제거 후 재시도
        fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 5단계: 제어 문자 제거 후 재시도
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', fixed)
        try:
            return json.loads(sanitized)
        except json.JSONDecodeError as e:
            _log.warning("JSON 파싱 최종 실패: %s (처음 200자: %s)", e, candidate[:200])

    return {"raw_response": text, "_parse_error": "JSON 파싱 실패"}


# ══════════════════════════════════════════════════════════════════════
# 모듈 분석 서비스
# ══════════════════════════════════════════════════════════════════════

class ModuleAnalysisService:
    def __init__(self):
        if settings.google_api_key:
            self.client = genai.Client(api_key=settings.google_api_key)
        else:
            self.client = None
        # 일반 모듈: gemini-2.0-flash (안정, 무료 1,500 RPD)
        self.model      = settings.gemini_model
        # 투자심화 분석: gemini-2.5-flash-preview (고품질, 무료 500 RPD)
        self.model_meta = settings.gemini_model_meta

    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        model: Optional[str] = None,
    ) -> str:
        if self.client is None:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        response = self.client.models.generate_content(
            model=model or self.model,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
        return response.text

    async def _call_gemini_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        max_retries: int = 3,
        model: Optional[str] = None,
    ) -> str:
        """세마포어(최대 3 병렬) + 지수 백오프 재시도 / 모델 선택 지원"""
        loop = asyncio.get_event_loop()
        last_exc: Exception = RuntimeError("Gemini 호출 실패")
        _model = model or self.model

        for attempt in range(max_retries):
            try:
                async with _GEMINI_SEMAPHORE:
                    return await loop.run_in_executor(
                        None,
                        lambda: self._call_gemini(system_prompt, user_prompt, max_tokens, _model),
                    )
            except Exception as exc:
                last_exc = exc
                err_str  = str(exc)

                is_rate_limit  = any(kw in err_str for kw in ("429", "RESOURCE_EXHAUSTED"))
                is_server_err  = any(kw in err_str for kw in ("503", "500"))
                is_daily_limit = any(kw in err_str.lower() for kw in ("per day", "daily", "per_day"))

                if attempt < max_retries - 1 and (is_rate_limit or is_server_err):
                    if is_rate_limit and not is_daily_limit:
                        # RPM(분당) 초과 — 재시도해도 대부분 실패하므로 즉시 raise
                        # (HTTP 연결 유지 한계로 62s 대기 불가 → 프론트에서 수동 재시도 유도)
                        raise exc
                    else:
                        # 서버 오류(503/500) → 지수 백오프
                        wait_secs = (2 ** attempt) * 5  # 5s, 10s
                        await asyncio.sleep(wait_secs)
                else:
                    raise exc

        raise last_exc

    async def run_module(
        self,
        module_id: str,
        corp_code: str,
        company_info: Dict,
        end_year: str,
        years: List[str],
        financials_by_year: Dict[str, Any],
        financials_quarterly: Dict[str, Any],
        governance_data: Dict[str, Any],
        disc_list: List[Dict],
        market_data: Dict,
        stock_history: Optional[Dict] = None,
        prev_result: Optional[Dict] = None,   # 개선 9: 증분 분석용
        use_cache: bool = True,               # 개선 5: 캐시 활성화 여부
    ) -> Dict[str, Any]:
        """
        단일 모듈 분석 — VC/PE 프롬프트 팩 v2.1
        출력: strict JSON (module_output_json_skeleton 기준)
        """
        real_id     = MODULE_ID_ALIAS.get(module_id, module_id)
        module_def  = _PACK.get("modules", {}).get(real_id)
        module_meta = MODULES.get(real_id)

        if not module_def or not module_meta:
            return {"error": f"알 수 없는 모듈: {module_id}"}

        # ── 개선 5: 캐시 확인 (증분·강제 재실행 제외) ─────────────────
        if use_cache and not prev_result:
            cached = get_cached(corp_code, real_id, years[0])
            if cached:
                cached["_from_cache"] = True
                return cached

        # ── 1. DART HTML 섹션 수집 (개선 1 적용) ─────────────────────
        all_s_ids = list(dict.fromkeys(
            module_def.get("required_sections", [])
            + module_def.get("optional_sections", [])
        ))
        parser_s_ids = [
            s for s in all_s_ids
            if SECTION_DEFINITIONS.get(s, {}).get("dart_code") is not None
        ]

        fetched: Dict[str, Dict] = {}
        if parser_s_ids:
            end_year_int = int(end_year) if end_year and end_year.isdigit() else None
            fetched = await _fetch_sections_from_report(
                corp_code, disc_list, parser_s_ids, end_year=end_year_int
            )

        # ── 2. S1~S11 문자열 조립 (개선 7 포함) ─────────────────────
        section_strings = _assemble_section_strings(
            fetched_sections=fetched,
            financials_by_year=financials_by_year,
            years=years,
            governance_data=governance_data,
            disc_list=disc_list,
            market_data=market_data,
            stock_history=stock_history,
            financials_quarterly=financials_quarterly,
        )

        # ── 3. 시간 정보 ────────────────────────────────────────────────
        today      = datetime.now().strftime("%Y-%m-%d")
        start_year = years[-1] if years else end_year
        time_info  = {
            "as_of_date":   today,
            "start_date":   f"{start_year}-01-01",
            "end_date":     f"{end_year}-12-31",
            "compare_mode": "yoy",
        }

        # ── 4. 프롬프트 조립 ────────────────────────────────────────────
        system_prompt = (
            _PACK["shared_system_prompt"]
            + "\n\n"
            + _PACK["shared_module_output_contract"]
        )
        user_prompt = _fill_template(
            template=module_def["user_prompt_template"],
            company=company_info,
            time_info=time_info,
            sections=section_strings,
        )

        # 개선 9: 증분 분석 — 이전 결과를 컨텍스트에 추가
        if prev_result:
            prev_summary = json.dumps(
                {k: prev_result.get(k) for k in (
                    "one_line_summary", "recommended_action",
                    "positive_signals", "negative_signals",
                    "structural_risks", "fatal_risks", "confidence"
                )},
                ensure_ascii=False, indent=2,
            )
            user_prompt = (
                f"[이전 분석 결과 (증분 업데이트 기준)]\n{prev_summary}\n\n"
                "[지침] 위 이전 결과를 참고하되, 아래 최신 데이터로 변경된 항목만 업데이트하라.\n\n"
                + user_prompt
            )

        # ── 5. Gemini 호출 — 일반 모듈: gemini-2.0-flash ───────────────
        max_tokens = module_meta.get("max_tokens", 8192)
        raw_text   = await self._call_gemini_with_retry(
            system_prompt, user_prompt, max_tokens,
            model=self.model,
        )

        # ── 6. JSON 파싱 ────────────────────────────────────────────────
        result_json = _parse_json_response(raw_text)

        corp_name  = company_info.get("corp_name", corp_code)
        period_str = f"{start_year}~{end_year}년"
        output = {
            "module_id":    real_id,
            "module_name":  module_meta["name"],
            "report":       json.dumps(result_json, ensure_ascii=False, indent=2),
            "result":       result_json,
            "generated_at": datetime.now().isoformat(),
            "model":        self.model,
            "corp_name":    corp_name,
            "period":       period_str,
            "is_incremental": bool(prev_result),
        }

        # 개선 5: 캐시 저장 (증분 분석은 캐시하지 않음)
        if use_cache and not prev_result and "_parse_error" not in result_json:
            set_cached(corp_code, real_id, years[0], output)

        return output

    async def run_meta_analysis(
        self,
        corp_code: str,
        company_info: Dict,
        end_year: str,
        years: List[str],
        module_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        메타 종합 분석 — deep_composite_investment_analysis
        9개 모듈 JSON → 투자위원회 종합 판단 (strict JSON)
        """
        meta_def = _PACK.get("meta_prompts", {}).get(
            "deep_composite_investment_analysis", {}
        )
        if not meta_def:
            return {"error": "메타 프롬프트 정의를 찾을 수 없습니다."}

        today      = datetime.now().strftime("%Y-%m-%d")
        start_year = years[-1] if years else end_year
        time_info  = {
            "as_of_date":   today,
            "start_date":   f"{start_year}-01-01",
            "end_date":     f"{end_year}-12-31",
            "compare_mode": "yoy",
        }

        system_prompt = (
            _PACK["shared_system_prompt"]
            + "\n\n"
            + _PACK["shared_meta_output_contract"]
        )
        user_prompt = _fill_meta_template(
            template=meta_def["user_prompt_template"],
            company=company_info,
            time_info=time_info,
            module_outputs=module_outputs,
        )

        # 투자심화 분석: gemini-2.5-flash-preview (고품질 추론 필요)
        raw_text    = await self._call_gemini_with_retry(
            system_prompt, user_prompt,
            max_tokens=MODULE_TOKENS["_meta"],
            model=self.model_meta,
        )
        result_json = _parse_json_response(raw_text)

        corp_name = company_info.get("corp_name", corp_code)
        return {
            "analysis_type": "deep_composite_investment_analysis",
            "corp_name":     corp_name,
            "corp_code":     corp_code,
            "report":        json.dumps(result_json, ensure_ascii=False, indent=2),
            "result":        result_json,
            "generated_at":  datetime.now().isoformat(),
            "model":         self.model_meta,
            "period":        f"{start_year}~{end_year}년",
            "modules_used":  list(module_outputs.keys()),
        }


# 싱글톤
module_service = ModuleAnalysisService()
