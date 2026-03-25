"""
AI 분석 서비스 (Google Gemini 기반)

DART/KRX 데이터를 Gemini에게 전달하여
투자자 관점의 심층 기업분석 리포트를 생성합니다.

데이터 수준:
  - 연간 재무제표: 3개년 (IS / BS / CF)
  - 분기 재무제표: 최근 2개년 × 3분기 (Q1 / 반기 / Q3)
  - 지배구조: 최대주주·임원현황·계열회사
  - 주요 재무지표: DART fnlttCmpnyIndctr (ROE, EPS, PER 등)
  - 최근 공시: 6개월
  - 시장 데이터: KRX 시세
"""
import json
from google import genai
from google.genai import types as genai_types
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import settings


# ──────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
당신은 한국 자본시장 전문 기업분석 AI입니다.
DART(금융감독원 전자공시시스템)와 KRX(한국거래소) 공식 데이터만을 기반으로 분석합니다.

## 분석 원칙
1. **정확성**: 모든 수치는 원본 데이터를 그대로 인용하고, 단위(억원/%, 배)를 명시
2. **객관성**: 투자 권고는 하지 않음 — 사실 기반 분석과 인사이트만 제공
3. **명확성**: 불확실하거나 데이터가 없는 항목은 "데이터 없음"으로 명시
4. **출처 준수**: 분석 근거가 되는 데이터 출처(DART/KRX)를 항상 명시
5. **일관성**: 비교 기간·기준은 일관되게 유지 (연결재무제표 우선, 없으면 별도)
6. **언어**: 한국어로 작성, 전문용어는 간결하게 풀어 설명
"""


# ──────────────────────────────────────────────────────────────────────
# 종합 기업분석 프롬프트 (DARTY comprehensive_corporate_analysis 수준)
# ──────────────────────────────────────────────────────────────────────

COMPREHENSIVE_REPORT_PROMPT = """\
다음 데이터를 바탕으로 **{corp_name}** 종합 기업분석 리포트를 작성하세요.

## 제공 데이터
{data_context}

---

## 리포트 구성 (아래 6개 섹션 순서로 작성)

### 1. 기업 개요
- 회사명 / 업종 / 설립일 / 대표이사 / 상장시장 / 홈페이지
- 주요 사업 영역 요약 (제공 정보 기준)

### 2. 지배구조 및 소유구조
- **최대주주 현황**: 최대주주명, 보유 지분율, 특수관계인 포함 합산 지분
- **경영진 구성**: 주요 임원 직위·성명 (5명 이내 요약)
- **계열회사**: 종속·관계회사 수 및 주요 계열사명

### 3. 재무성과 분석 ({years_label} 기준)

#### 3-1. 연간 실적 추이 (표 형식)
| 구분 | {year3}년 | {year2}년 | {year1}년 | YoY증감 |
|------|-----------|-----------|-----------|---------|
| 매출액 | | | | |
| 영업이익 | | | | |
| 당기순이익 | | | | |
| 영업이익률 | | | | |
| 순이익률 | | | | |

#### 3-2. 재무상태 (최신연도)
- 자산총계 / 부채총계 / 자본총계
- 부채비율 / 유동비율
- ROE / ROA

#### 3-3. 분기 실적 추이
제공된 분기 데이터를 활용하여 최근 6개 분기 매출·영업이익 추이를 분석하고,
계절성이나 특이 변동이 있으면 언급하세요.

#### 3-4. 주요 재무지표 (DART 공시 기준)
EPS, BPS, PER, PBR 등 제공된 지표를 표로 정리하세요.

### 4. 공시 동향 (최근 6개월)
- 중요 공시 유형별 분류 (경영/재무/M&A/IR 등)
- 투자자가 주목할 상위 3개 공시 요약
- 최근 공시 패턴에서 읽히는 경영 방향성

### 5. 리스크 요인
- **사업 리스크**: 경쟁환경, 규제, 시장 변화
- **재무 리스크**: 부채 수준, 현금흐름, 이자보상 능력
- **지배구조 리스크**: 대주주 지배력, 계열사 의존도 등

### 6. 종합 인사이트
- 핵심 투자 포인트 3가지 (Bullet)
- 주목할 리스크 또는 기회
- 추가 분석이 필요한 항목

---
**데이터 출처**: DART 전자공시시스템 / KRX 한국거래소
**분석 기준일**: {analysis_date}
**수집 데이터 연도**: {years_label}
"""


# ──────────────────────────────────────────────────────────────────────
# 개별 분석 프롬프트
# ──────────────────────────────────────────────────────────────────────

FINANCIAL_ANALYSIS_PROMPT = """\
다음 재무제표 데이터로 {corp_name}의 재무 심층 분석을 작성하세요.

## 재무 데이터 (3개년)
{financial_data}

## 분석 항목
1. **수익성 분석**: 매출·이익 추이, 마진율 변화, 수익 구조의 안정성
2. **안정성 분석**: 부채비율 추이, 유동성, 재무 건전성 평가
3. **성장성 분석**: YoY 성장률, 성장 모멘텀의 지속 가능성
4. **현금흐름 분석**: 영업·투자·재무 현금흐름 패턴
5. **종합 재무 평가**: 강점·약점 요약, 동종업계 평균 대비 코멘트

수치는 정확하게 인용하고, 단위(억원/%)를 명시하세요.
"""

DISCLOSURE_SUMMARY_PROMPT = """\
다음 공시 목록을 분석하여 {corp_name}의 최근 동향을 요약하세요.

## 공시 데이터
{disclosure_data}

## 분석 요청
1. **중요 공시 분류**: 경영/재무/M&A/IR/감사 등 유형별 분류
2. **주요 이슈**: 투자자가 주목할 상위 3개 공시 요약
3. **트렌드**: 최근 공시 패턴에서 읽히는 경영 방향성
4. **주의 사항**: 잠재적 리스크를 시사하는 공시 여부
"""

GOVERNANCE_ANALYSIS_PROMPT = """\
다음 지배구조 데이터를 분석하여 {corp_name}의 소유·경영 구조를 설명하세요.

## 지배구조 데이터
{governance_data}

## 분석 요청
1. **소유 집중도**: 최대주주 지분율, 특수관계인 합산 지분, 소액주주 비중
2. **경영진 안정성**: 주요 임원 구성, 임기, 내·외부 이사 균형
3. **계열사 현황**: 지배구조 내 종속·관계회사 수와 핵심 계열사
4. **지배구조 리스크**: 과도한 지배주주 집중, 순환출자 가능성 등
"""

SECTION_SUMMARY_PROMPT = """\
다음은 {corp_name} 사업보고서의 '{section_title}' 섹션입니다.

## 원문 내용
{section_content}

## 분석 요청
- **핵심 포인트** (3~5개 bullet)
- **주목할 수치·사실**
- **리스크 또는 기회 요인**

간결하고 투자자에게 유용한 인사이트를 제공하세요.
"""


# ──────────────────────────────────────────────────────────────────────
# 데이터 포맷 헬퍼
# ──────────────────────────────────────────────────────────────────────

def _fmt(v: Optional[float], unit: str = "백만원") -> str:
    if v is None:
        return "N/A"
    return f"{v:,.0f}{unit}"


def _pct(v: Optional[float]) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1f}%"


def _build_annual_context(financials_by_year: Dict[str, Any], years: List[str]) -> str:
    lines = []
    for year in years:
        fd = financials_by_year.get(year, {})
        if not fd:
            lines.append(f"[{year}년 재무데이터 없음]")
            continue

        is_c = fd.get("income_statement", {}).get("current", {})
        bs_c = fd.get("balance_sheet", {}).get("current", {})
        cf_c = fd.get("cash_flow", {}).get("current", {})
        ratios = fd.get("ratios", {})
        growth = fd.get("growth", {})

        lines.append(f"""[{year}년 연간 재무제표]
▶ 손익계산서
  매출액: {_fmt(is_c.get('revenue'))}
  영업이익: {_fmt(is_c.get('operating_profit'))}  (영업이익률: {_pct(ratios.get('operating_margin_pct'))})
  당기순이익: {_fmt(is_c.get('net_income'))}  (순이익률: {_pct(ratios.get('net_margin_pct'))})
▶ 재무상태표
  자산총계: {_fmt(bs_c.get('total_assets'))}
  부채총계: {_fmt(bs_c.get('total_liabilities'))}  (부채비율: {_pct(ratios.get('debt_ratio_pct'))})
  자본총계: {_fmt(bs_c.get('total_equity'))}
▶ 현금흐름표
  영업활동: {_fmt(cf_c.get('operating'))}
  투자활동: {_fmt(cf_c.get('investing'))}
  재무활동: {_fmt(cf_c.get('financing'))}
▶ 수익성 지표
  ROE: {_pct(ratios.get('roe_pct'))}  ROA: {_pct(ratios.get('roa_pct'))}
  유동비율: {ratios.get('current_ratio', 'N/A')}
▶ 전년 대비 성장률
  매출 YoY: {_pct(growth.get('revenue_yoy_pct'))}
  영업이익 YoY: {_pct(growth.get('operating_profit_yoy_pct'))}
  순이익 YoY: {_pct(growth.get('net_income_yoy_pct'))}""")

    return "\n\n".join(lines)


def _build_quarterly_context(financials_quarterly: Dict[str, Any]) -> str:
    if not financials_quarterly:
        return "[분기 데이터 없음]"

    lines = []
    label_map = {
        "_Q1": "1분기", "_H1": "반기(1-2Q)", "_Q3": "3분기누적(1-3Q)"
    }
    for label, fd in financials_quarterly.items():
        if not fd:
            continue
        suffix = next((s for s in label_map if label.endswith(s)), "")
        period_name = label_map.get(suffix, label)
        year_part = label.replace(suffix, "")
        is_c = fd.get("income_statement", {}).get("current", {})
        lines.append(
            f"  {year_part}년 {period_name}: "
            f"매출 {_fmt(is_c.get('revenue'))} / "
            f"영업이익 {_fmt(is_c.get('operating_profit'))}"
        )

    return "[분기별 실적 요약]\n" + "\n".join(lines) if lines else "[분기 데이터 없음]"


def _build_governance_context(governance_data: Dict[str, Any]) -> str:
    parts = []

    # 최대주주
    sh = governance_data.get("major_shareholders")
    if sh and sh.get("list"):
        rows = sh["list"][:10]
        sh_lines = "\n".join([
            f"  - {r.get('nm', 'N/A')} ({r.get('relate', '')}): "
            f"{r.get('stock_qy', 'N/A')}주 ({r.get('bsis_posesn_stock_co', 'N/A')}%)"
            for r in rows
        ])
        parts.append(f"[최대주주 현황]\n{sh_lines}")

    # 임원
    ex = governance_data.get("executives")
    if ex and ex.get("list"):
        rows = ex["list"][:8]
        ex_lines = "\n".join([
            f"  - {r.get('nm', 'N/A')} / {r.get('ofcps', 'N/A')} / {r.get('rgist_exctv_at', 'N/A')}"
            for r in rows
        ])
        parts.append(f"[임원 현황 (상위 8인)]\n{ex_lines}")

    # 계열회사
    af = governance_data.get("affiliated_companies")
    if af and af.get("list"):
        rows = af["list"]
        af_names = ", ".join([r.get("affi_corp_nm", "") for r in rows[:15]])
        parts.append(f"[계열회사 현황]\n  총 {len(rows)}개사: {af_names}")

    # 주요 재무지표 (DART 사전계산)
    ki = governance_data.get("key_indicators")
    if ki and ki.get("list"):
        rows = ki["list"][:10]
        ki_lines = "\n".join([
            f"  - {r.get('idx_nm', 'N/A')}: {r.get('idx_val', 'N/A')}"
            for r in rows
        ])
        parts.append(f"[DART 주요 재무지표]\n{ki_lines}")

    return "\n\n".join(parts) if parts else "[지배구조 데이터 없음]"


def _build_disclosure_context(disclosures: Any) -> str:
    if not disclosures or isinstance(disclosures, Exception):
        return "[공시 데이터 없음]"
    disc_list = disclosures.get("list", [])[:20]
    if not disc_list:
        return "[최근 공시 없음]"
    lines = [
        f"  [{d.get('rcept_dt', '')}] {d.get('report_nm', '')} (제출: {d.get('flr_nm', '')})"
        for d in disc_list
    ]
    return f"[최근 공시 목록 ({len(disc_list)}건)]\n" + "\n".join(lines)


def _build_report_sections_context(sections: Dict[str, Any]) -> str:
    """
    dart_parser.py가 분해한 사업보고서 원문 섹션을 Gemini 컨텍스트로 변환.

    각 섹션의 실제 텍스트를 포함하므로 Gemini가 공시 원문을 기반으로
    사업 내용·경영 전략·감사 의견을 직접 분석할 수 있다.
    """
    if not sections:
        return "[사업보고서 원문: 수집 불가 — 공시 목록에 사업보고서 없거나 HTML 파싱 실패]"

    SECTION_LABELS = {
        "company_overview": "Ⅰ. 회사의 개요",
        "business_content": "Ⅱ. 사업의 내용",
        "mda":              "Ⅳ. 이사의 경영진단 및 분석의견 (MD&A)",
        "audit_opinion":    "Ⅴ. 감사인의 감사의견",
    }

    parts = []
    rcept_info = ""
    for code, data in sections.items():
        label    = SECTION_LABELS.get(code, code)
        rcept_dt = data.get("rcept_dt", "")
        rcept_no = data.get("rcept_no", "")
        if not rcept_info and rcept_dt:
            rcept_info = f"접수일: {rcept_dt} / 접수번호: {rcept_no}"

        content    = data.get("content", "").strip()
        char_count = data.get("char_count", 0)
        excerpt_len = len(content)

        header = (
            f"[사업보고서 원문 — {label}]\n"
            f"({rcept_info} / 원문 {char_count:,}자 중 {excerpt_len:,}자 발췌)\n"
            f"{'─' * 60}\n"
        )
        parts.append(header + content)

    return (
        "\n\n[★ 사업보고서 원문 발췌 — 아래 내용은 DART 공시 원문 직접 인용입니다]\n\n"
        + "\n\n".join(parts)
    )


# ──────────────────────────────────────────────────────────────────────
# 서비스 클래스
# ──────────────────────────────────────────────────────────────────────

class ClaudeAnalysisService:
    """Google Gemini API를 활용한 기업분석 서비스"""

    def __init__(self):
        if settings.google_api_key:
            self.client = genai.Client(
                api_key=settings.google_api_key,
                http_options={"api_version": "v1"},
            )
        else:
            self.client = None
        self.model_name = settings.gemini_model

    def _call(self, prompt: str, max_tokens: int = 8192) -> str:
        """Gemini API 호출"""
        if self.client is None:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. AI 분석을 사용하려면 환경변수를 설정해주세요.")
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        return response.text

    def generate_comprehensive_report(
        self,
        corp_name: str,
        company_info: Dict,
        financials_by_year: Dict[str, Any],
        financials_quarterly: Dict[str, Any],
        governance_data: Dict[str, Any],
        disclosures: Any,
        report_sections: Dict[str, Any],   # ← 사업보고서 원문 섹션 (NEW)
        market_data: Dict,
        base_year: str,
        years: List[str],
    ) -> Dict[str, Any]:
        """
        종합 기업분석 리포트 생성

        수집된 3개년 + 분기 + 지배구조 + 사업보고서 원문 섹션 데이터를 컨텍스트로
        구성하여 Gemini에게 전달하고 투자자용 심층 리포트를 생성합니다.
        """
        # ── 컨텍스트 조립 ────────────────────────────────────────────
        context_parts = []

        # corp_cls → 상장시장 변환 (Y=KOSPI, K=KOSDAQ, N=KONEX, E=비상장)
        # companies.py에서 네이버 금융으로 보강된 값이 우선 사용됨
        corp_cls_map = {
            'Y': 'KOSPI (유가증권시장)',
            'K': 'KOSDAQ (코스닥시장)',
            'N': 'KONEX (코넥스시장)',
            'E': '비상장',
        }
        corp_cls    = company_info.get('corp_cls', '')
        stock_code  = company_info.get('stock_code', '')
        listing_dt  = company_info.get('listing_dt', '') or ''
        market_name = company_info.get('market_name', '')  # 네이버에서 보강된 값

        if market_name:
            # 네이버/Yahoo 금융에서 직접 확인된 시장명 (가장 신뢰)
            market_type = market_name
        elif corp_cls in corp_cls_map:
            market_type = corp_cls_map[corp_cls]
        elif stock_code:
            # 종목코드 있음 → 상장사이나 시장 구분 미제공
            market_type = '상장 (시장구분 확인 필요)'
        elif listing_dt:
            # 상장일이 있으면 상장 이력은 있음
            market_type = f'상장 이력 있음 (상장일: {listing_dt})'
        else:
            market_type = '비상장'

        # 상장일: DART listing_dt가 None인 경우 보완값 또는 안내문구 사용
        listing_dt_raw  = company_info.get('listing_dt') or ''
        listing_dt_note = company_info.get('_listing_dt_source', '')
        if listing_dt_raw:
            listing_dt_display = (
                f"{listing_dt_raw} ({'DART 직접 제공' if not listing_dt_note else listing_dt_note})"
            )
        elif market_type == '비상장':
            listing_dt_display = '해당 없음 (비상장)'
        else:
            listing_dt_display = 'DART 미제공 (상장사이나 DART 기업정보에 상장일 누락)'

        # 기업 기본정보
        context_parts.append(f"""[기업 기본정보]
기업명: {company_info.get('corp_name', corp_name)}
종목코드: {stock_code if stock_code else '없음 (비상장)'}
상장시장: {market_type}
업종코드: {company_info.get('induty_code', 'N/A')}
대표이사: {company_info.get('ceo_nm', 'N/A')}
설립일: {company_info.get('est_dt', 'N/A')}
상장일: {listing_dt_display}
홈페이지: {company_info.get('hm_url', 'N/A')}
결산월: {company_info.get('acc_mt', 'N/A')}""")

        # 3개년 연간 재무
        context_parts.append(_build_annual_context(financials_by_year, years))

        # 분기 실적
        context_parts.append(_build_quarterly_context(financials_quarterly))

        # 지배구조
        context_parts.append(_build_governance_context(governance_data))

        # 최근 공시 목록 (제목/날짜 메타데이터)
        context_parts.append(_build_disclosure_context(disclosures))

        # 사업보고서 원문 섹션 (실제 공시 텍스트 — 핵심 컨텍스트)
        context_parts.append(_build_report_sections_context(report_sections))

        # 시장 데이터
        if market_data and "error" not in market_data:
            context_parts.append(f"[KRX 시장 데이터]\n{json.dumps(market_data, ensure_ascii=False, indent=2)}")

        data_context = "\n\n" + "\n\n".join(context_parts)

        # ── 프롬프트 포맷 ────────────────────────────────────────────
        year1, year2, year3 = years[0], years[1], years[2]
        years_label = f"{year3}~{year1}"

        prompt = COMPREHENSIVE_REPORT_PROMPT.format(
            corp_name=corp_name,
            data_context=data_context,
            year1=year1,
            year2=year2,
            year3=year3,
            years_label=years_label,
            analysis_date=datetime.now().strftime("%Y년 %m월 %d일"),
        )

        report_text = self._call(prompt, max_tokens=32768)

        return {
            "report": report_text,
            "generated_at": datetime.now().isoformat(),
            "model": self.model_name,
            "data_coverage": {
                "annual_years": years,
                "quarterly_periods": list(financials_quarterly.keys()),
                "has_governance": any(v is not None for v in governance_data.values()),
                "disclosure_count": len(disclosures.get("list", [])) if isinstance(disclosures, dict) else 0,
                "report_sections_parsed": list(report_sections.keys()),   # 분해된 섹션 목록
                "annual_report_read": bool(report_sections),              # 원문 읽었는지 여부
            },
            "_source": {
                "provider": "Gemini AI 분석 (DART·KRX 데이터 기반)",
                "model": self.model_name,
                "data_sources": ["DART 전자공시시스템", "KRX 한국거래소"],
                "generated_at": datetime.now().isoformat(),
            },
        }

    def analyze_financial(
        self,
        corp_name: str,
        financials_by_year: Dict[str, Any],
        years: List[str],
    ) -> str:
        """재무제표 3개년 심층 분석"""
        financial_context = _build_annual_context(financials_by_year, years)
        prompt = FINANCIAL_ANALYSIS_PROMPT.format(
            corp_name=corp_name,
            financial_data=financial_context,
        )
        return self._call(prompt, max_tokens=2048)

    def summarize_disclosures(self, corp_name: str, disclosures: Dict) -> str:
        """공시 목록 요약 분석"""
        disc_list = disclosures.get("list", [])[:20]
        prompt = DISCLOSURE_SUMMARY_PROMPT.format(
            corp_name=corp_name,
            disclosure_data=json.dumps(disc_list, ensure_ascii=False, indent=2),
        )
        return self._call(prompt, max_tokens=1024)

    def analyze_governance(self, corp_name: str, governance_data: Dict) -> str:
        """지배구조 분석"""
        gov_context = _build_governance_context(governance_data)
        prompt = GOVERNANCE_ANALYSIS_PROMPT.format(
            corp_name=corp_name,
            governance_data=gov_context,
        )
        return self._call(prompt, max_tokens=1024)

    def summarize_section(self, corp_name: str, section_title: str, section_content: str) -> str:
        """사업보고서 섹션 AI 요약"""
        prompt = SECTION_SUMMARY_PROMPT.format(
            corp_name=corp_name,
            section_title=section_title,
            section_content=section_content[:8000],
        )
        return self._call(prompt, max_tokens=1024)


# 싱글톤 인스턴스
claude_service = ClaudeAnalysisService()
