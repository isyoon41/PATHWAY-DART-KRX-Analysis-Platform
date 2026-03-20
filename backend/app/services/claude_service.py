"""
Claude API 분석 서비스

DART/KRX 데이터를 Claude에게 전달하여
투자/기업 분석 리포트를 생성합니다.

DARTY와 동일한 접근법:
  - 섹션별 데이터를 컨텍스트로 제공
  - 사전 정의된 프롬프트 템플릿으로 일관된 리포트 생성
  - 스트리밍 응답 지원
"""
import anthropic
from typing import Dict, Any, AsyncIterator
from datetime import datetime
from config import settings


# ──────────────────────────────────────────────────────────
# 분석 프롬프트 템플릿 (DARTY의 prompts_generated에 해당)
# ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 한국 주식시장 전문 기업분석 AI입니다.
DART 전자공시시스템과 KRX 한국거래소의 공식 데이터를 기반으로 분석합니다.

분석 원칙:
1. 모든 수치는 원본 데이터 기준으로 정확하게 인용
2. 투자 판단은 사용자 몫 — 사실 기반 분석만 제공
3. 불확실한 정보는 명시적으로 표기
4. 한국어로 작성, 전문 용어는 간결하게 설명
5. 출처(DART/KRX)를 항상 명시"""

COMPREHENSIVE_REPORT_PROMPT = """다음 데이터를 바탕으로 {corp_name}의 종합 기업분석 리포트를 작성하세요.

## 제공 데이터
{data_context}

## 리포트 구성 (아래 순서로 작성)

### 1. 기업 개요
- 회사명, 업종, 설립일, 대표이사, 상장시장
- 주요 사업 영역 요약

### 2. 재무 현황 ({bsns_year}년 기준)
- 매출액, 영업이익, 당기순이익 (전년 대비 증감률 포함)
- 핵심 재무비율: 영업이익률, ROE, 부채비율
- 재무 안정성 평가

### 3. 공시 동향
- 최근 3개월 주요 공시 요약
- 투자자 관심 사항 (IR, 유상증자, M&A 등)

### 4. 리스크 요인
- 사업 리스크 (경쟁, 규제, 시장)
- 재무 리스크

### 5. 종합 의견
- 핵심 투자 포인트 (3가지)
- 주목할 사항

**데이터 출처: DART 전자공시시스템 / KRX 한국거래소**
**분석 기준일: {analysis_date}**
"""

FINANCIAL_ANALYSIS_PROMPT = """다음 재무제표 데이터로 {corp_name}의 재무 분석을 작성하세요.

## 재무 데이터
{financial_data}

## 분석 항목
1. **수익성 분석**: 매출/이익 추이, 마진율 변화
2. **안정성 분석**: 부채비율, 유동비율, 재무 건전성
3. **성장성 분석**: YoY 성장률, 성장 모멘텀
4. **종합 재무 평가**: 강점/약점 요약

수치는 정확하게 인용하고, 단위(억원/%)를 명시하세요.
"""

DISCLOSURE_SUMMARY_PROMPT = """다음 공시 목록을 분석하여 {corp_name}의 최근 동향을 요약하세요.

## 공시 데이터
{disclosure_data}

## 분석 요청
1. **중요 공시 분류**: 경영/재무/M&A/IR 등 유형별 분류
2. **주요 이슈**: 투자자가 주목할 상위 3개 공시
3. **트렌드**: 최근 공시 패턴에서 읽히는 경영 방향성
"""

SECTION_SUMMARY_PROMPT = """다음은 {corp_name} 사업보고서의 '{section_title}' 섹션입니다.

## 원문 내용 (최대 30,000자)
{section_content}

## 분석 요청
이 섹션의 핵심 내용을 다음 형식으로 요약하세요:
- **핵심 포인트** (3~5개 bullet)
- **주목할 수치/사실**
- **리스크 또는 기회 요인**

간결하고 투자자에게 유용한 인사이트를 제공하세요.
"""


class ClaudeAnalysisService:
    """Claude API를 활용한 기업분석 서비스"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    def _call(self, prompt: str, max_tokens: int = 4096) -> str:
        """동기 Claude API 호출"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def generate_comprehensive_report(
        self,
        corp_name: str,
        company_info: Dict,
        financial_data: Dict,
        disclosures: Dict,
        market_data: Dict,
        bsns_year: str,
    ) -> Dict[str, Any]:
        """
        종합 기업분석 리포트 생성 (DARTY의 comprehensive_corporate_analysis에 해당)
        """
        # 데이터 컨텍스트 구성
        context_parts = []

        # 기업 기본 정보
        context_parts.append(f"""[기업 기본 정보]
기업명: {company_info.get('corp_name', corp_name)}
종목코드: {company_info.get('stock_code', 'N/A')}
업종: {company_info.get('induty_code', 'N/A')}
대표이사: {company_info.get('ceo_nm', 'N/A')}
설립일: {company_info.get('est_dt', 'N/A')}
상장일: {company_info.get('listing_dt', 'N/A')}
홈페이지: {company_info.get('hm_url', 'N/A')}""")

        # 재무 데이터
        if financial_data and "error" not in financial_data:
            is_curr = financial_data.get("income_statement", {}).get("current", {})
            bs_curr = financial_data.get("balance_sheet", {}).get("current", {})
            ratios  = financial_data.get("ratios", {})
            growth  = financial_data.get("growth", {})

            def fmt(v):
                if v is None: return "N/A"
                return f"{v:,}백만원"

            def pct(v):
                if v is None: return "N/A"
                return f"{v:.1f}%"

            context_parts.append(f"""[{bsns_year}년 재무제표 요약]
매출액: {fmt(is_curr.get('revenue'))}
영업이익: {fmt(is_curr.get('operating_profit'))}
당기순이익: {fmt(is_curr.get('net_income'))}
자산총계: {fmt(bs_curr.get('total_assets'))}
부채총계: {fmt(bs_curr.get('total_liabilities'))}
자본총계: {fmt(bs_curr.get('total_equity'))}

[재무비율]
영업이익률: {pct(ratios.get('operating_margin_pct'))}
순이익률: {pct(ratios.get('net_margin_pct'))}
ROE: {pct(ratios.get('roe_pct'))}
ROA: {pct(ratios.get('roa_pct'))}
부채비율: {pct(ratios.get('debt_ratio_pct'))}
유동비율: {ratios.get('current_ratio', 'N/A')}

[전년 대비 성장률]
매출 YoY: {pct(growth.get('revenue_yoy_pct'))}
영업이익 YoY: {pct(growth.get('operating_profit_yoy_pct'))}
순이익 YoY: {pct(growth.get('net_income_yoy_pct'))}""")

        # 최근 공시
        if disclosures and "error" not in disclosures:
            disc_list = disclosures.get("list", [])[:10]
            if disc_list:
                disc_text = "\n".join([
                    f"- [{d.get('rcept_dt', '')}] {d.get('report_nm', '')} ({d.get('flr_nm', '')})"
                    for d in disc_list
                ])
                context_parts.append(f"[최근 공시 목록]\n{disc_text}")

        # 시장 데이터
        if market_data and "error" not in market_data:
            context_parts.append(f"[시장 데이터]\n{market_data}")

        data_context = "\n\n".join(context_parts)

        prompt = COMPREHENSIVE_REPORT_PROMPT.format(
            corp_name=corp_name,
            data_context=data_context,
            bsns_year=bsns_year,
            analysis_date=datetime.now().strftime("%Y년 %m월 %d일"),
        )

        report_text = self._call(prompt, max_tokens=4096)

        return {
            "corp_name": corp_name,
            "report": report_text,
            "generated_at": datetime.now().isoformat(),
            "model": self.model,
            "_source": {
                "provider": "Claude AI 분석 (DART·KRX 데이터 기반)",
                "model": self.model,
                "data_sources": ["DART 전자공시시스템", "KRX 한국거래소"],
                "generated_at": datetime.now().isoformat(),
            }
        }

    def analyze_financial(self, corp_name: str, financial_data: Dict) -> str:
        """재무제표 심층 분석"""
        import json
        prompt = FINANCIAL_ANALYSIS_PROMPT.format(
            corp_name=corp_name,
            financial_data=json.dumps(financial_data, ensure_ascii=False, indent=2)
        )
        return self._call(prompt, max_tokens=2048)

    def summarize_disclosures(self, corp_name: str, disclosures: Dict) -> str:
        """공시 목록 요약 분석"""
        import json
        disc_list = disclosures.get("list", [])[:20]
        prompt = DISCLOSURE_SUMMARY_PROMPT.format(
            corp_name=corp_name,
            disclosure_data=json.dumps(disc_list, ensure_ascii=False, indent=2)
        )
        return self._call(prompt, max_tokens=1024)

    def summarize_section(self, corp_name: str, section_title: str, section_content: str) -> str:
        """사업보고서 섹션 AI 요약"""
        prompt = SECTION_SUMMARY_PROMPT.format(
            corp_name=corp_name,
            section_title=section_title,
            section_content=section_content[:8000],  # 토큰 절약
        )
        return self._call(prompt, max_tokens=1024)


# 싱글톤 인스턴스
claude_service = ClaudeAnalysisService()
