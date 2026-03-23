"""
분석 모듈 서비스 v2 — VC/PE 강화형 프롬프트 팩

prompt_pack: darty_vcpe_investment_analysis_modules v2.0

아키텍처:
  1단계: 9개 모듈이 각자 담당 섹션(S1~S11)만 읽어 strict JSON 출력
  2단계: 메타 분석이 9개 JSON을 통합해 투자위원회 수준 판단 생성

섹션 정의 (S1~S11):
  S1  — 기업 개요 (DART 원문)
  S2  — 사업의 내용 (DART 원문)
  S3  — 사업부문 정보 (S2와 동일 소스)
  S4  — 위험요인 (DART 원문, fallback: S2)
  S5  — 주주구조 (DART API)
  S6  — 이사회·임원 (DART 원문 + API)
  S7  — 재무제표 (DART XBRL 구조화)
  S8  — 재무주석 (DART 원문 financial_info 섹션)
  S9  — 자본조달 이벤트 (공시 필터링)
  S10 — 잠정·이벤트 공시 (공시 목록)
  S11 — 시장 데이터 (KRX/네이버/FDR)

9개 분석 모듈:
  comprehensive_corporate_analysis  — 종합 기업분석
  key_financial_indicators          — 핵심 재무지표
  complete_financial_statements     — 전체 재무제표 심층
  business_segment_performance      — 사업부문별 실적
  shareholder_structure             — 주주구조
  board_executive_analysis          — 이사회·경영진
  stock_price_movement_analysis     — 주가 변동
  paid_in_capital_increase          — 유상증자·자본조달
  preliminary_results               — 잠정실적·속보
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
# S1-S11 섹션 정의
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
    "S8":  {"dart_code": "financial_info",   "name": "재무주석",          "char_limit": 15000},
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

# 구 ID → 신 ID 하위 호환 매핑
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
        "max_tokens":        8192,
    }


# ══════════════════════════════════════════════════════════════════════
# DART HTML 섹션 수집 헬퍼
# ══════════════════════════════════════════════════════════════════════

async def _fetch_sections_from_report(
    corp_code: str,
    disc_list: List[Dict],
    section_ids: List[str],
) -> Dict[str, Dict]:
    """
    공시 목록에서 사업보고서 HTML → 지정 섹션 추출
    Returns: { "S1": {"title":..., "content":..., ...}, ... }
    """
    dart_codes_needed: List[str] = []
    for sid in section_ids:
        sdef = SECTION_DEFINITIONS.get(sid, {})
        dc = sdef.get("dart_code")
        if dc and dc not in dart_codes_needed:
            dart_codes_needed.append(dc)
        also = sdef.get("also")
        if also and also not in dart_codes_needed:
            dart_codes_needed.append(also)
        fb = sdef.get("fallback")
        if fb and fb not in dart_codes_needed:
            dart_codes_needed.append(fb)

    if not dart_codes_needed:
        return {}

    annual = [
        d for d in disc_list
        if "사업보고서" in d.get("report_nm", "")
        and "정정" not in d.get("report_nm", "")
    ]
    if not annual:
        return {}

    rcept_no = annual[0].get("rcept_no", "")
    rcept_dt = annual[0].get("rcept_dt", "")
    if not rcept_no:
        return {}

    try:
        parser = create_parser(settings.dart_api_key)
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
            sdef      = SECTION_DEFINITIONS.get(sid, {})
            dc        = sdef.get("dart_code")
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
                data["title"] += " (위험요인 섹션 없음 — 사업의 내용에서 발췌)"
                result[sid] = data

        # S6: executives 내용 추가
        if "S6" in section_ids and "executives" in dart_map and "S6" in result:
            exec_content = dart_map["executives"].get("content", "")[:4000]
            result["S6"]["content"] += f"\n\n[임원 현황]\n{exec_content}"

        return result

    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════
# 재무 데이터 포맷 헬퍼
# ══════════════════════════════════════════════════════════════════════

def _fmt_financials(financials: Dict[str, Any], years: List[str]) -> str:
    lines = []
    for yr in years:
        f = financials.get(yr, {})
        if not f:
            continue
        inc   = f.get("income_statement", {})
        bal   = f.get("balance_sheet", {})
        rat   = f.get("ratios", {})
        cur_i = inc.get("current", {})
        cur_b = bal.get("current", {})
        prev_i = inc.get("previous", {})
        lines.append(
            f"[{yr}년 재무 — DART XBRL]\n"
            f"  매출액:        {cur_i.get('revenue','N/A'):>15,} 천원"
            f"  (전기: {prev_i.get('revenue','N/A')})\n"
            f"  영업이익:      {cur_i.get('operating_profit','N/A'):>15,} 천원\n"
            f"  당기순이익:    {cur_i.get('net_income','N/A'):>15,} 천원\n"
            f"  총자산:        {cur_b.get('total_assets','N/A'):>15,} 천원\n"
            f"  자기자본:      {cur_b.get('total_equity','N/A'):>15,} 천원\n"
            f"  부채총계:      {cur_b.get('total_liabilities','N/A'):>15,} 천원\n"
            f"  영업이익률:    {rat.get('operating_margin_pct','N/A'):>8}%\n"
            f"  순이익률:      {rat.get('net_margin_pct','N/A'):>8}%\n"
            f"  ROE:           {rat.get('roe_pct','N/A'):>8}%  |  "
            f"ROA: {rat.get('roa_pct','N/A'):>8}%\n"
            f"  부채비율:      {rat.get('debt_ratio_pct','N/A'):>8}%  |  "
            f"유동비율: {rat.get('current_ratio_pct','N/A'):>8}%"
        )
    return "\n\n".join(lines) if lines else "[XBRL 재무 데이터 없음]"


def _fmt_disc_list(disc_list: List[Dict], limit: int = 40) -> str:
    lines = [
        f"  [{d.get('rcept_dt','')}] {d.get('report_nm','')} (제출: {d.get('flr_nm','')})"
        for d in disc_list[:limit]
    ]
    return "\n".join(lines) if lines else "[공시 없음]"


# ══════════════════════════════════════════════════════════════════════
# S1~S11 섹션 문자열 조립
# ══════════════════════════════════════════════════════════════════════

def _assemble_section_strings(
    fetched_sections: Dict[str, Dict],
    financials_by_year: Dict[str, Any],
    years: List[str],
    governance_data: Dict[str, Any],
    disc_list: List[Dict],
    market_data: Dict,
    stock_history: Optional[Dict] = None,
) -> Dict[str, str]:
    """S1~S11 각 섹션을 LLM이 읽을 수 있는 텍스트 문자열로 변환"""
    s: Dict[str, str] = {}

    # S1 기업 개요
    s["S1"] = fetched_sections.get("S1", {}).get("content") or "[기업 개요 없음]"

    # S2 사업의 내용
    s["S2"] = fetched_sections.get("S2", {}).get("content") or "[사업내용 없음]"

    # S3 사업부문 정보 (S2와 동일 소스)
    s["S3"] = s["S2"]

    # S4 위험요인
    s["S4"] = fetched_sections.get("S4", {}).get("content") or "[위험요인 없음]"

    # S5 주주구조 (DART API JSON)
    sh = governance_data.get("major_shareholders")
    s["S5"] = (
        json.dumps(sh, ensure_ascii=False, indent=2)[:5000]
        if sh else "[주주구조 데이터 없음]"
    )

    # S6 이사회·임원 (DART 원문 + API)
    s["S6"] = fetched_sections.get("S6", {}).get("content") or ""
    ex = governance_data.get("executives")
    if ex:
        s["S6"] += "\n\n[임원 현황 (DART API)]\n" + json.dumps(ex, ensure_ascii=False, indent=2)[:3000]
    if not s["S6"].strip():
        s["S6"] = "[이사회·임원 데이터 없음]"

    # S7 재무제표 (XBRL 구조화)
    s["S7"] = _fmt_financials(financials_by_year, years)

    # S8 재무주석 (DART 원문 financial_info)
    s["S8"] = fetched_sections.get("S7", {}).get("content") or "[재무주석 없음]"

    # S9 자본조달 이벤트 (키워드 필터링)
    capital_discs = [
        d for d in disc_list
        if any(kw in d.get("report_nm", "") for kw in _CAPITAL_KEYWORDS)
    ]
    s["S9"] = (
        _fmt_disc_list(capital_discs, 30)
        if capital_discs else "[자본조달 관련 공시 없음]"
    )

    # S10 잠정·이벤트 공시
    s["S10"] = _fmt_disc_list(disc_list, 40)

    # S11 시장 데이터 (현재가 + 일자별 주가)
    s11_parts = []
    if market_data and "error" not in market_data:
        s11_parts.append(
            "[현재가 데이터 (KRX/네이버 금융)]\n"
            + json.dumps(market_data, ensure_ascii=False, indent=2)[:1500]
        )
    if stock_history and "error" not in stock_history:
        records = stock_history.get("records", [])
        if records:
            sample = records[-90:]
            provider = stock_history.get("_source", {}).get("provider", "FDR")
            s11_parts.append(
                f"[일자별 주가 ({provider}) | "
                f"{stock_history.get('start_date','')} ~ {stock_history.get('end_date','')}]\n"
                f"총 {len(records)}거래일, 최근 {len(sample)}거래일 표시:\n"
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
    """{{company.X}}, {{time.X}}, {{sections.SX}} 치환"""
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
) -> str:
    """메타 프롬프트 {{module_outputs.X}} 치환"""
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
    """LLM 응답 텍스트에서 JSON 추출 및 파싱"""
    # 코드펜스 제거
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$",         "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 첫 번째 { ... } 블록 추출 시도
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # 파싱 실패 시 원문 보존
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
        self.model = settings.gemini_model

    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
    ) -> str:
        if self.client is None:
            raise ValueError(
                "GOOGLE_API_KEY가 설정되지 않았습니다. AI 분석을 사용하려면 환경변수를 설정해주세요."
            )
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
        return response.text

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
    ) -> Dict[str, Any]:
        """
        단일 모듈 분석 실행 — VC/PE 프롬프트 팩 v2

        출력: strict JSON 객체 (module_output_json_skeleton 기준)
        """
        # 구 ID → 신 ID 변환
        real_id    = MODULE_ID_ALIAS.get(module_id, module_id)
        module_def = _PACK.get("modules", {}).get(real_id)
        module_meta = MODULES.get(real_id)

        if not module_def or not module_meta:
            return {"error": f"알 수 없는 모듈: {module_id}"}

        # ── 1. DART HTML 섹션 수집 ────────────────────────────────────
        all_s_ids = list(dict.fromkeys(
            module_def.get("required_sections", [])
            + module_def.get("optional_sections", [])
        ))
        parser_s_ids = [
            s for s in all_s_ids
            if SECTION_DEFINITIONS.get(s, {}).get("dart_code") is not None
        ]

        fetched: Dict[str, Dict] = {}
        if parser_s_ids and disc_list:
            fetched = await _fetch_sections_from_report(corp_code, disc_list, parser_s_ids)

        # ── 2. S1~S11 섹션 문자열 조립 ───────────────────────────────
        section_strings = _assemble_section_strings(
            fetched_sections=fetched,
            financials_by_year=financials_by_year,
            years=years,
            governance_data=governance_data,
            disc_list=disc_list,
            market_data=market_data,
            stock_history=stock_history,
        )

        # ── 3. 시간 정보 구성 ─────────────────────────────────────────
        today      = datetime.now().strftime("%Y-%m-%d")
        start_year = years[-1] if years else end_year
        time_info  = {
            "as_of_date":   today,
            "start_date":   f"{start_year}-01-01",
            "end_date":     f"{end_year}-12-31",
            "compare_mode": "yoy",
        }

        # ── 4. 프롬프트 조립 ─────────────────────────────────────────
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

        # ── 5. Gemini 호출 (동기 → thread 실행) ──────────────────────
        loop = asyncio.get_event_loop()
        raw_text = await loop.run_in_executor(
            None,
            lambda: self._call_gemini(system_prompt, user_prompt, max_tokens=8192),
        )

        # ── 6. JSON 파싱 ──────────────────────────────────────────────
        result_json = _parse_json_response(raw_text)

        corp_name  = company_info.get("corp_name", corp_code)
        period_str = f"{start_year}~{end_year}년"
        return {
            "module_id":    real_id,
            "module_name":  module_meta["name"],
            "report":       json.dumps(result_json, ensure_ascii=False, indent=2),
            "result":       result_json,
            "generated_at": datetime.now().isoformat(),
            "model":        self.model,
            "corp_name":    corp_name,
            "period":       period_str,
        }

    async def run_meta_analysis(
        self,
        corp_code: str,
        company_info: Dict,
        end_year: str,
        years: List[str],
        module_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        메타 종합 분석 — 9개 모듈 JSON → 투자위원회 심층 판단

        prompt: deep_composite_investment_analysis
        출력: meta_output_json_skeleton 기준 strict JSON
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

        loop = asyncio.get_event_loop()
        raw_text = await loop.run_in_executor(
            None,
            lambda: self._call_gemini(system_prompt, user_prompt, max_tokens=16384),
        )

        result_json = _parse_json_response(raw_text)
        corp_name   = company_info.get("corp_name", corp_code)

        return {
            "analysis_type": "deep_composite_investment_analysis",
            "corp_name":     corp_name,
            "corp_code":     corp_code,
            "report":        json.dumps(result_json, ensure_ascii=False, indent=2),
            "result":        result_json,
            "generated_at":  datetime.now().isoformat(),
            "model":         self.model,
            "period":        f"{start_year}~{end_year}년",
            "modules_used":  list(module_outputs.keys()),
        }


# 싱글톤
module_service = ModuleAnalysisService()
