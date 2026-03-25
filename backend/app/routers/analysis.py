import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel

from app.services.dart_service import dart_service
from app.services.krx_service import krx_service
from app.services.dart_parser import create_parser, analyzer as section_analyzer
from app.services.financial_parser import structure_financial_data
from app.services.claude_service import claude_service
from app.services.module_service import module_service, MODULES, MODULE_ID_ALIAS
from app.services.usage_tracker import usage_tracker
from app.services import job_service, cache_service
from config import settings

logger = logging.getLogger("pathway.analysis")


# ══════════════════════════════════════════════════════════════════════
# 주요 재무지표 자체 계산 폴백
# DART fnlttCmpnyIndctr API가 데이터를 제공하지 않을 때
# 재무제표(structure_financial_data 결과) + 시장 데이터로 직접 계산
# ══════════════════════════════════════════════════════════════════════

def _parse_market_num(s: Any) -> Optional[float]:
    """시장 데이터 숫자 문자열 파싱 (쉼표 제거, None/N/A 처리)"""
    if s is None or s == "N/A" or s == "":
        return None
    try:
        return float(str(s).replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _calc_key_indicators_fallback(
    financials: Dict,
    market_data: Dict,
    year: str,
) -> Optional[Dict]:
    """
    DART 주요 재무지표 API 실패 시 자체 계산 (fnlttCmpnyIndctr 동일 구조 반환)

    계산 항목:
      - EPS  = 당기순이익(원) ÷ 발행주식수
      - BPS  = 자본총계(원) ÷ 발행주식수
      - PER  = 현재주가 ÷ EPS
      - PBR  = 현재주가 ÷ BPS
      - ROE  = 당기순이익 ÷ 자본총계 × 100
      - ROA  = 당기순이익 ÷ 자산총계 × 100

    발행주식수 = 네이버 시가총액 ÷ 현재주가 역산 (FDR/Yahoo 폴백 시 생략)
    금액 단위: financial_parser 출력은 백만원 → 원 환산 시 × 1,000,000
    """
    try:
        is_curr = financials.get("income_statement", {}).get("current", {})
        bs_curr = financials.get("balance_sheet",    {}).get("current", {})

        net_income_m   = is_curr.get("net_income")    # 백만원
        total_equity_m = bs_curr.get("total_equity")  # 백만원
        total_assets_m = bs_curr.get("total_assets")  # 백만원

        # 최소한 순이익 + 자본총계는 있어야 ROE 계산 가능
        if net_income_m is None or total_equity_m is None:
            return None

        items: List[Dict] = []

        # ── 주식수 역산 (시가총액 ÷ 현재주가) ───────────────────────────
        current_price = _parse_market_num(market_data.get("current_price"))
        market_cap    = _parse_market_num(market_data.get("market_cap"))

        shares: Optional[float] = None
        if market_cap and current_price and current_price > 0:
            shares = market_cap / current_price

        # ── 주당 지표 (주식수 있을 때만) ───────────────────────────────
        if shares and shares > 0:
            net_income_won   = net_income_m   * 1_000_000
            total_equity_won = total_equity_m * 1_000_000

            eps = net_income_won   / shares
            bps = total_equity_won / shares

            items.append({"idx_nm": "EPS", "idx_val": f"{eps:,.0f}", "idx_unit": "원",
                          "_calc": True, "_note": "당기순이익÷발행주식수(시가총액역산)"})
            items.append({"idx_nm": "BPS", "idx_val": f"{bps:,.0f}", "idx_unit": "원",
                          "_calc": True, "_note": "자본총계÷발행주식수"})

            if current_price and eps != 0:
                per = current_price / eps
                items.append({"idx_nm": "PER", "idx_val": f"{per:.1f}", "idx_unit": "배",
                              "_calc": True, "_note": "현재주가÷EPS"})

            if bps > 0:
                pbr = current_price / bps if current_price else None
                if pbr:
                    items.append({"idx_nm": "PBR", "idx_val": f"{pbr:.2f}", "idx_unit": "배",
                                  "_calc": True, "_note": "현재주가÷BPS"})

        # ── 수익성 비율 (주식수 불필요) ─────────────────────────────────
        if total_equity_m and total_equity_m != 0:
            roe = net_income_m / total_equity_m * 100
            items.append({"idx_nm": "ROE", "idx_val": f"{roe:.1f}", "idx_unit": "%",
                          "_calc": True, "_note": "당기순이익÷자본총계"})

        if total_assets_m and total_assets_m != 0:
            roa = net_income_m / total_assets_m * 100
            items.append({"idx_nm": "ROA", "idx_val": f"{roa:.1f}", "idx_unit": "%",
                          "_calc": True, "_note": "당기순이익÷자산총계"})

        if not items:
            return None

        return {
            "status": "000",
            "list":   items,
            "_calculated": True,   # 자체 계산 플래그 (DART API 원본과 구별)
            "_source": {
                "provider":     "자체 계산 (DART 재무제표 + 네이버/FDR 시장 데이터)",
                "business_year": year,
                "note":         "DART fnlttCmpnyIndctr API 미제공 → 직접 계산값",
                "retrieved_at": datetime.now().isoformat(),
            },
        }
    except Exception as exc:
        logger.debug("key_indicators 자체 계산 실패: %s", exc, exc_info=True)
        return None


# ─── 요청 바디 모델 ──────────────────────────────────────────────────
class IncrementalModuleRequest(BaseModel):
    end_year:    str = ""
    prev_result: Optional[Dict[str, Any]] = None

router = APIRouter()


@router.get("/usage")
async def get_api_usage():
    """오늘 Gemini API 사용량 통계 반환"""
    return usage_tracker.get_stats()


@router.get("/config")
async def get_config():
    """현재 설정된 Gemini 모델 반환 (배포 진단용)"""
    import os
    return {
        "gemini_model": settings.gemini_model,
        "gemini_model_meta": settings.gemini_model_meta,
        "railway_service": os.environ.get("RAILWAY_SERVICE_NAME", "unknown"),
        "railway_public_domain": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "unknown"),
        "railway_deployment_id": os.environ.get("RAILWAY_DEPLOYMENT_ID", "unknown")[:12],
    }


@router.get("/{corp_code}/comprehensive")
async def get_comprehensive_analysis(
    corp_code: str,
    include_financial: bool = Query(True,  description="재무제표 포함 여부"),
    include_disclosures: bool = Query(True, description="최근 공시 포함 여부"),
    include_market_data: bool = Query(True, description="시장 데이터 포함 여부"),
    bsns_year: str = Query("", description="기준 사업연도 (YYYY, 기본값: 전년도)"),
) -> Dict[str, Any]:
    """
    종합 기업 분석 리포트

    - **corp_code**: 기업 고유번호
    - **반환**: 종합 분석 리포트 (모든 데이터에 출처 포함)
    """
    try:
        company_info = await dart_service.get_company_info(corp_code)
        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        result: Dict[str, Any] = {
            "company_info": company_info,
            "analysis_metadata": {
                "generated_at": datetime.now().isoformat(),
                "corp_code": corp_code,
                "included_sections": {
                    "financial": include_financial,
                    "disclosures": include_disclosures,
                    "market_data": include_market_data,
                },
            },
        }

        # 재무제표 (XBRL → 구조화) — 지정 연도 우선, 없으면 전년도 fallback
        if include_financial:
            target_year = bsns_year if bsns_year else str(datetime.now().year - 1)
            fallback_year = str(int(target_year) - 1)

            async def _fetch_financial(year: str):
                raw = await dart_service.get_financial_statement(
                    corp_code=corp_code, bsns_year=year, reprt_code="11011"
                )
                # DART가 데이터 없음 반환 시 status 013 또는 list 비어있음
                if raw.get("status") == "013" or not raw.get("list"):
                    return None, year
                return raw, year

            try:
                raw, used_year = await _fetch_financial(target_year)
                if raw is None:
                    # fallback
                    raw, used_year = await _fetch_financial(fallback_year)
                if raw:
                    result["financial_statement"] = structure_financial_data(raw)
                    result["financial_year"] = used_year
                else:
                    result["financial_statement"] = {"error": f"{target_year}·{fallback_year}년 재무데이터 없음"}
            except Exception as e:
                result["financial_statement"] = {"error": str(e)}

        # 최근 공시 목록
        if include_disclosures:
            try:
                end = datetime.now()
                disclosures = await dart_service.get_disclosure_list(
                    corp_code=corp_code,
                    bgn_de=(end - timedelta(days=90)).strftime("%Y%m%d"),
                    end_de=end.strftime("%Y%m%d"),
                    page_no=1,
                    page_count=20,
                )
                result["recent_disclosures"] = disclosures
            except Exception as e:
                result["recent_disclosures"] = {"error": str(e)}

        # 시장 데이터
        if include_market_data and company_info.get("stock_code"):
            try:
                result["market_data"] = await krx_service.get_stock_price(
                    company_info["stock_code"]
                )
            except Exception as e:
                result["market_data"] = {"error": str(e)}

        result["sources_summary"] = _build_sources_summary()
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 리포트 생성 중 오류: {str(e)}")


@router.get("/{corp_code}/sections")
async def get_sectioned_report(
    corp_code: str = Path(..., description="기업 고유번호"),
    rcept_no: str = Query(..., description="분석할 공시 접수번호 (DART 공시 목록에서 확인)"),
) -> Dict[str, Any]:
    """
    공시 문서 섹션별 분석 리포트

    DART 공시 HTML을 금융감독원 고시 표준 목차 기준으로 분해하여
    각 섹션별 구조화된 분석 결과를 반환합니다.

    - **corp_code**: 기업 고유번호
    - **rcept_no**: 공시 접수번호 (예: 20240315000123)

    ### 분해되는 섹션 (사업보고서 표준 목차)
    - 회사의 개요
    - 사업의 내용 (리스크 키워드 추출)
    - 재무에 관한 사항 (핵심 수치)
    - 이사의 경영진단 및 분석의견 MD&A (경영진 어조 분석)
    - 감사인의 감사의견 (적정/한정/부적정/의견거절)
    - 이사회 및 지배구조
    - 주주, 임원, 계열회사 등

    ### 출처
    모든 내용은 DART 공시 원문 HTML에서 추출되며,
    각 섹션에 출처 URL이 포함됩니다.
    """
    try:
        company_info = await dart_service.get_company_info(corp_code)
        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        # 공시 HTML 다운로드 및 섹션 분해
        parser = create_parser(settings.dart_api_key)
        doc_files = await parser.fetch_report_index(rcept_no)

        if not doc_files:
            raise HTTPException(status_code=404, detail="공시 문서를 찾을 수 없습니다.")

        file_url = doc_files[0].get("url", "")
        html = await parser.fetch_document_html(rcept_no, file_url)

        corp_context = {
            "corp_code": corp_code,
            "corp_name": company_info.get("corp_name", ""),
            "report_type": "사업보고서",
            "report_date": datetime.now().strftime("%Y"),
        }
        parsed = parser.parse_sections(html, rcept_no, corp_context)

        # 각 섹션 분석 수행
        analyzed_sections: Dict[str, Any] = {}
        for code, section in parsed.sections.items():
            analyzed_sections[code] = {
                **section_analyzer.analyze_section(section),
                # 텍스트 미리보기 (처음 500자)
                "content_preview": section.content[:500] + ("…" if len(section.content) > 500 else ""),
                "table_count": len(section.tables),
                # 표 헤더만 요약 (상세 데이터 과부하 방지)
                "table_headers": [t["headers"] for t in section.tables[:5]],
            }

        return {
            "corp_name":   company_info.get("corp_name"),
            "corp_code":   corp_code,
            "rcept_no":    rcept_no,
            "parsed_at":   parsed.parsed_at,
            "section_count": len(analyzed_sections),
            "sections":    analyzed_sections,
            "_source": {
                "provider":    "DART 공시 원문 (섹션별 분해 분석)",
                "document_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                "methodology": "금융감독원 고시 표준 목차 기준으로 섹션 경계 자동 감지 후 분해",
                "retrieved_at": datetime.now().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"섹션 분석 중 오류: {str(e)}"
        )


@router.get("/{corp_code}/financial-structured")
async def get_structured_financial(
    corp_code: str = Path(..., description="기업 고유번호"),
    bsns_year: str = Query(..., description="사업연도 (예: 2023)", pattern=r"^\d{4}$"),
    reprt_code: str = Query("11011", description="11011:사업보고서 / 11012:반기 / 11013:1분기 / 11014:3분기"),
) -> Dict[str, Any]:
    """
    구조화된 재무제표 (XBRL 파싱)

    DART XBRL 계정과목 코드 기반으로 재무 데이터를 구조화하여
    손익계산서 / 재무상태표 / 현금흐름표 / 재무비율을 반환합니다.

    ### 계산되는 재무비율
    - 매출총이익률, 영업이익률, 순이익률
    - 부채비율, 유동비율
    - ROA, ROE
    - 전년 대비 성장률 (매출, 영업이익, 순이익)

    ### 출처
    DART API `fnlttSinglAcntAll` 엔드포인트 (XBRL 표준 계정코드 기반)
    """
    try:
        raw = await dart_service.get_financial_statement(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
        )
        if raw.get("status") == "013":
            raise HTTPException(status_code=404, detail="재무제표를 찾을 수 없습니다.")

        structured = structure_financial_data(raw)
        company_info = await dart_service.get_company_info(corp_code)

        return {
            "corp_name":  company_info.get("corp_name"),
            "corp_code":  corp_code,
            "bsns_year":  bsns_year,
            "report_type": _reprt_code_to_name(reprt_code),
            **structured,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재무제표 파싱 중 오류: {str(e)}")


@router.get("/{corp_code}/summary")
async def get_analysis_summary(corp_code: str) -> Dict[str, Any]:
    """기업 분석 요약 (핵심 지표)"""
    try:
        company_info = await dart_service.get_company_info(corp_code)
        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        end = datetime.now()
        disclosures = await dart_service.get_disclosure_list(
            corp_code=corp_code,
            bgn_de=(end - timedelta(days=30)).strftime("%Y%m%d"),
            end_de=end.strftime("%Y%m%d"),
            page_no=1,
            page_count=100,
        )

        return {
            "corp_name":  company_info.get("corp_name"),
            "stock_code": company_info.get("stock_code"),
            "ceo":        company_info.get("ceo_nm"),
            "established": company_info.get("est_dt"),
            "recent_disclosure_count": len(disclosures.get("list", [])),
            "generated_at": datetime.now().isoformat(),
            "_source": {
                "provider": "DART·KRX 기업분석 플랫폼",
                "data_sources": ["DART", "KRX"],
                "retrieved_at": datetime.now().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 생성 중 오류: {str(e)}")


# ─── 내부 헬퍼 ──────────────────────────────────────────────────────

def _build_sources_summary() -> Dict:
    return {
        "description": "본 리포트의 모든 데이터는 공식 출처에서 수집되었으며, 각 섹션에 출처 정보가 포함됩니다.",
        "primary_sources": [
            {
                "name": "DART (금융감독원 전자공시시스템)",
                "url": "https://dart.fss.or.kr",
                "description": "기업 정보, 재무제표 (XBRL), 공시 원문 HTML",
            },
            {
                "name": "KRX (한국거래소)",
                "url": "http://data.krx.co.kr",
                "description": "시장 데이터, 주가 정보",
            },
        ],
        "data_reliability": "모든 데이터는 금융감독원·한국거래소 공식 API 및 공시 원문에서 수집됩니다.",
        "last_updated": datetime.now().isoformat(),
    }


@router.get("/{corp_code}/ai-report")
async def get_ai_report(
    corp_code: str = Path(..., description="기업 고유번호"),
    start_year: int = Query(default=0, description="분석 시작 연도 (예: 2021, 기본값: 종료연도-2)"),
    start_qtr: int  = Query(default=1, ge=1, le=4, description="시작 분기 (1=Q1, 2=Q2/반기, 3=Q3, 4=연간)"),
    end_year: int   = Query(default=0, description="분석 종료 연도 (예: 2024, 기본값: 전년도)"),
    end_qtr: int    = Query(default=4, ge=1, le=4, description="종료 분기 (1=Q1, 2=Q2/반기, 3=Q3, 4=연간)"),
) -> Dict[str, Any]:
    """
    Gemini AI 종합 기업분석 리포트

    사용자가 지정한 연-분기 범위의 재무제표 + 지배구조 + 공시 원문을 Gemini AI가 분석합니다.

    - **start_year / start_qtr**: 분석 시작 연도·분기
    - **end_year   / end_qtr**  : 분석 종료 연도·분기
    - 기본값: 최근 3개년(end_year=전년도, start_year=end_year-2), Q1~Q4 전체
    """
    # ── 기간 계산 ────────────────────────────────────────────────────────
    now = datetime.now()
    _end_year   = end_year   if end_year   else now.year - 1
    _start_year = start_year if start_year else _end_year - 2

    if _start_year > _end_year:
        raise HTTPException(400, "start_year는 end_year보다 작거나 같아야 합니다.")
    if _start_year == _end_year and start_qtr > end_qtr:
        raise HTTPException(400, "같은 연도에서 start_qtr는 end_qtr보다 작거나 같아야 합니다.")

    # 연도 목록 (오름차순) — 최대 10년으로 제한
    year_range = list(range(_start_year, min(_end_year, _start_year + 9) + 1))
    years = [str(y) for y in year_range]              # ["2021","2022","2023","2024"]
    latest_year = years[-1]                            # 지배구조 등 최신 기준

    # 분기별 DART reprt_code  (Q4/연간 = 11011은 annual_tasks에서 처리)
    QTR_CODES  = {1: "11013", 2: "11012", 3: "11014"}
    QTR_LABELS = {1: "Q1",   2: "H1",   3: "Q3"}

    # 분기 태스크 목록 & 레이블 동적 생성
    quarterly_tasks_list: list = []
    quarterly_labels_list: list = []
    for yr in year_range:
        yr_min_q = start_qtr if yr == _start_year else 1
        yr_max_q = end_qtr   if yr == _end_year   else 4
        for q in [1, 2, 3]:           # Q1/H1/Q3 만 (연간=4는 annual_tasks 처리)
            if yr_min_q <= q <= yr_max_q:
                quarterly_tasks_list.append(
                    dart_service.get_financial_statement(corp_code, str(yr), QTR_CODES[q])
                )
                quarterly_labels_list.append(f"{yr}_{QTR_LABELS[q]}")

    try:
        # ── 1단계: 기업 기본정보 먼저 확인 ──────────────────────────────
        company_info = await dart_service.get_company_info(corp_code)
        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        # ── 2단계: 병렬 데이터 수집 ──────────────────────────────────────
        # 연간 재무제표 (범위 내 전 연도)
        annual_tasks = [
            dart_service.get_financial_statement(corp_code, y, "11011")
            for y in years
        ]

        # 지배구조 & 주요지표 (최신 연도 기준)
        governance_tasks = [
            dart_service.get_major_shareholders(corp_code, latest_year, "11011"),
            dart_service.get_executives(corp_code, latest_year, "11011"),
            dart_service.get_affiliated_companies(corp_code, latest_year, "11011"),
            dart_service.get_key_indicators(corp_code, latest_year, "11011"),
        ]

        # 공시 목록 (분석 기간 전체 + 6개월 여유)
        bgn_de = f"{_start_year}0101"
        end_de = now.strftime("%Y%m%d")
        disclosure_task = dart_service.get_disclosure_list(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
            page_no=1,
            page_count=30,
        )

        # 전부 병렬 실행
        n_annual = len(annual_tasks)
        n_qtr    = len(quarterly_tasks_list)
        results = await asyncio.gather(
            *annual_tasks,
            *quarterly_tasks_list,
            *governance_tasks,
            disclosure_task,
            return_exceptions=True,
        )

        # ── 3단계: 결과 분류 ──────────────────────────────────────────────
        annual_raws    = results[0          : n_annual]
        quarterly_raws = results[n_annual   : n_annual + n_qtr]
        gov_offset     = n_annual + n_qtr
        shareholders_raw, executives_raw, affiliates_raw, indicators_raw = results[gov_offset : gov_offset + 4]
        disclosures    = results[gov_offset + 4]

        # 연간 재무 구조화 (실패 시 빈 dict)
        financials_by_year: Dict[str, Any] = {}
        for i, year in enumerate(years):
            raw = annual_raws[i]
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_by_year[year] = structure_financial_data(raw)
            else:
                financials_by_year[year] = {}

        # 분기 재무 구조화
        financials_quarterly: Dict[str, Any] = {}
        for label, raw in zip(quarterly_labels_list, quarterly_raws):
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_quarterly[label] = structure_financial_data(raw)

        # 지배구조 데이터 (실패 시 None)
        def safe(r):
            return r if not isinstance(r, Exception) and r.get("status") not in ("013", "020") else None

        governance_data = {
            "major_shareholders":   safe(shareholders_raw),
            "executives":           safe(executives_raw),
            "affiliated_companies": safe(affiliates_raw),
            "key_indicators":       safe(indicators_raw),
        }

        # ── 4단계: 시장 데이터 ───────────────────────────────────────────
        market_data: Dict = {}
        stock_code = company_info.get("stock_code")
        if stock_code:
            try:
                market_data = await krx_service.get_stock_price(stock_code)
            except Exception:
                logger.debug("시장 데이터 조회 실패 (stock_code=%s)", stock_code, exc_info=True)

        # ── 4.1단계: key_indicators 자체 계산 폴백 ──────────────────────
        # DART fnlttCmpnyIndctr가 데이터 없을 때 재무제표 + 시장 데이터로 계산
        ki = governance_data.get("key_indicators")
        if not ki or not ki.get("list"):
            fin_latest = financials_by_year.get(latest_year, {})
            if fin_latest and not fin_latest.get("error") and market_data and not market_data.get("error"):
                calc_ki = _calc_key_indicators_fallback(fin_latest, market_data, latest_year)
                if calc_ki:
                    governance_data["key_indicators"] = calc_ki
                    logger.info(
                        "key_indicators 자체 계산 적용 (corp=%s, year=%s, items=%d)",
                        corp_code, latest_year, len(calc_ki["list"]),
                    )

        # ── 4.5단계: 사업보고서 원문 섹션 분해 ─────────────────────────────
        # DART에서 사업보고서를 직접 검색(최대 3년 소급)한 뒤 HTML 다운로드 → 섹션 분해
        # 6개월 공시 목록에 의존하지 않으므로 시기에 관계없이 항상 원문을 읽음
        report_sections: Dict[str, Any] = {}
        try:
            parser = create_parser(settings.dart_api_key)

            # 사업보고서 접수번호 직접 탐색 (종료연도 포함 최대 3년 소급)
            annual_meta = await asyncio.wait_for(
                dart_service.get_annual_report_rcept_no(corp_code, _end_year),
                timeout=15.0,
            )

            if annual_meta and annual_meta.get("rcept_no"):
                rcept_no_ar = annual_meta["rcept_no"]
                rcept_dt_ar = annual_meta["rcept_dt"]

                # 문서 인덱스 → 본문 HTML 취득 (각 30초 타임아웃)
                doc_files = await asyncio.wait_for(
                    parser.fetch_report_index(rcept_no_ar), timeout=30.0
                )
                if doc_files:
                    file_url = doc_files[0].get("url", "")
                    html = await asyncio.wait_for(
                        parser.fetch_document_html(rcept_no_ar, file_url),
                        timeout=30.0,
                    )
                    corp_ctx = {
                        "corp_code": corp_code,
                        "corp_name": company_info.get("corp_name", ""),
                        "report_type": "사업보고서",
                        "report_date": rcept_dt_ar,
                    }
                    parsed = parser.parse_sections(html, rcept_no_ar, corp_ctx)

                    # Gemini 컨텍스트에 포함할 핵심 4개 섹션
                    # (각 섹션 원문 최대 8,000자 → 총 ~32K자 추가)
                    KEY_SECTIONS = [
                        "company_overview",   # Ⅰ. 회사의 개요
                        "business_content",   # Ⅱ. 사업의 내용 (핵심)
                        "mda",                # Ⅳ. 경영진단 및 분석의견
                        "audit_opinion",      # Ⅴ. 감사인의 감사의견
                    ]
                    for code in KEY_SECTIONS:
                        if code in parsed.sections:
                            sec = parsed.sections[code]
                            report_sections[code] = {
                                "title":      sec.title,
                                "content":    sec.content[:8000],
                                "char_count": sec.char_count,
                                "rcept_no":   rcept_no_ar,
                                "rcept_dt":   rcept_dt_ar,
                            }
        except Exception:
            # 원문 파싱 실패 시 경고 후 진행 — 재무/AI 분석은 계속
            logger.warning("사업보고서 원문 파싱 실패 (corp_code=%s)", corp_code, exc_info=True)

        # ── 5단계: Gemini AI 분석 ─────────────────────────────────────────
        corp_name = company_info.get("corp_name", corp_code)
        report = claude_service.generate_comprehensive_report(
            corp_name=corp_name,
            company_info=company_info,
            financials_by_year=financials_by_year,
            financials_quarterly=financials_quarterly,
            governance_data=governance_data,
            disclosures=disclosures if not isinstance(disclosures, Exception) else {},
            report_sections=report_sections,
            market_data=market_data,
            base_year=latest_year,
            years=years,
        )

        QTR_NAME = {1: "Q1", 2: "Q2(반기)", 3: "Q3", 4: "Q4(연간)"}
        return {
            "corp_code":     corp_code,
            "corp_name":     corp_name,
            "base_year":     latest_year,
            "years_covered": years,
            "period": {
                "start_year": _start_year,
                "start_qtr":  start_qtr,
                "end_year":   _end_year,
                "end_qtr":    end_qtr,
                "label": f"{_start_year} {QTR_NAME[start_qtr]} ~ {_end_year} {QTR_NAME[end_qtr]}",
            },
            **report,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 리포트 생성 중 오류: {str(e)}")


@router.get("/{corp_code}/stock-history")
async def get_stock_history(
    corp_code: str = Path(..., description="기업 고유번호"),
    start_date: str = Query("", description="시작일 (YYYYMMDD 또는 YYYY-MM-DD, 기본값: 1년 전)"),
    end_date:   str = Query("", description="종료일 (YYYYMMDD 또는 YYYY-MM-DD, 기본값: 오늘)"),
) -> Dict[str, Any]:
    """
    일자별 주가 이력 (OHLCV)

    FinanceDataReader → Yahoo Finance 폴백 체인으로
    일자별 시가·고가·저가·종가·거래량을 반환합니다.

    - **start_date** / **end_date**: 조회 기간 (미입력 시 최근 1년)
    - 장중 조회 시 당일 Close 컬럼에 실시간 종가가 포함됩니다.
    """
    try:
        company_info = await dart_service.get_company_info(corp_code)
        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        stock_code = company_info.get("stock_code")
        if not stock_code:
            raise HTTPException(status_code=422, detail="상장 종목코드가 없는 기업입니다.")

        history = await krx_service.get_stock_history(
            stock_code,
            start_date or None,
            end_date   or None,
        )
        return {
            "corp_name":  company_info.get("corp_name"),
            "corp_code":  corp_code,
            "stock_code": stock_code,
            **history,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주가 이력 조회 중 오류: {str(e)}")


@router.get("/modules/list")
async def list_modules():
    """분석 모듈 목록 반환 (VC/PE 강화형 v2)"""
    return {
        "modules":       list(MODULES.values()),
        "total":         len(MODULES),
        "prompt_pack":   "darty_vcpe_investment_analysis_modules v2.0",
        "output_format": "strict JSON (module_output_json_skeleton)",
    }


@router.post("/{corp_code}/module/{module_id}")
async def run_module_analysis(
    corp_code: str = Path(..., description="기업 고유번호"),
    module_id: str = Path(..., description="분석 모듈 ID"),
    end_year:  str = Query("", description="종료 연도 (YYYY)"),
):
    """
    단일 분석 모듈 실행 (VC/PE 프롬프트 팩 v2)

    담당 섹션(S1~S11)만 읽어 strict JSON 결과를 반환합니다.
    구 모듈 ID(예: comprehensive, key_financials)도 자동 변환되어 호환됩니다.

    **출력 형식**: `module_output_json_skeleton` 기준 JSON
    - `one_line_summary`: 한 줄 요약
    - `scorecard`: 성장성/수익성/현금창출/자본효율/거버넌스 점수
    - `positive_signals` / `negative_signals`: 투자 판단 시사점
    - `vc_view` / `pe_view`: VC·PE 관점 분리 해석
    - `recommended_action`: 즉시검토·보류 등 액션
    """
    # 구 ID → 신 ID 자동 변환
    real_id = MODULE_ID_ALIAS.get(module_id, module_id)
    if real_id not in MODULES:
        all_ids = list(MODULES.keys()) + list(MODULE_ID_ALIAS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"알 수 없는 모듈: {module_id}. 가능한 모듈: {list(MODULES.keys())}",
        )

    base_year  = int(end_year) if end_year.isdigit() else datetime.now().year - 1
    years      = [str(base_year), str(base_year - 1), str(base_year - 2)]

    try:
        # ── 병렬 데이터 수집 ─────────────────────────────────────────
        from datetime import date
        disc_start = (date.today() - timedelta(days=365 * 4)).strftime("%Y%m%d")
        disc_end   = date.today().strftime("%Y%m%d")

        # 분기 재무 태스크 (개선 7: base_year Q1/H1/Q3)
        QTR_CODES = {"Q1": "11013", "H1": "11012", "Q3": "11014"}
        qtr_tasks  = [
            dart_service.get_financial_statement(corp_code, years[0], code)
            for code in QTR_CODES.values()
        ]
        qtr_labels = [f"{years[0]}_{lbl}" for lbl in QTR_CODES.keys()]

        results = await asyncio.gather(
            dart_service.get_company_info(corp_code),
            dart_service.get_financial_statement(corp_code, years[0], "11011"),
            dart_service.get_financial_statement(corp_code, years[1], "11011"),
            dart_service.get_financial_statement(corp_code, years[2], "11011"),
            dart_service.get_major_shareholders(corp_code, str(base_year)),
            dart_service.get_executives(corp_code, str(base_year)),
            dart_service.get_disclosure_list(corp_code, bgn_de=disc_start, end_de=disc_end, page_count=50),
            *qtr_tasks,
            return_exceptions=True,
        )

        company_info        = results[0] if not isinstance(results[0], Exception) else {}
        financials_by_year  = {}
        for i, year in enumerate(years):
            raw = results[1 + i]
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_by_year[year] = structure_financial_data(raw)

        def safe(r):
            return r if not isinstance(r, Exception) and r.get("status") not in ("013", "020") else None

        governance_data = {
            "major_shareholders": safe(results[4]),
            "executives":         safe(results[5]),
        }
        disc_raw  = results[6]
        disc_list = disc_raw.get("list", []) if not isinstance(disc_raw, Exception) else []

        # 분기 재무 구조화 (개선 7)
        financials_quarterly: Dict = {}
        for lbl, raw in zip(qtr_labels, results[7:]):
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_quarterly[lbl] = structure_financial_data(raw)

        # 주가 데이터
        market_data: Dict = {}
        stock_code = company_info.get("stock_code", "")
        if stock_code:
            try:
                market_data = await krx_service.get_stock_price(stock_code)
            except Exception:
                logger.debug("모듈 분석용 시장 데이터 조회 실패 (stock_code=%s)", stock_code)

        # 일자별 주가 이력 — S11 포함 모듈 전체에 제공 (FDR/Yahoo)
        stock_history: Dict = {}
        s11_modules = {
            "stock_price_movement_analysis", "stock_movement",
            "comprehensive_corporate_analysis", "comprehensive",
            "paid_in_capital_increase", "capital_increase",
            "preliminary_results", "preliminary",
        }
        if stock_code and (real_id in s11_modules or module_id in s11_modules):
            try:
                hist_start = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
                hist_end   = date.today().strftime("%Y-%m-%d")
                stock_history = await krx_service.get_stock_history(
                    stock_code, hist_start, hist_end
                )
            except Exception:
                logger.debug("주가 이력 조회 실패 (stock_code=%s)", stock_code)

        # ── 모듈 분석 실행 ───────────────────────────────────────────
        result = await module_service.run_module(
            module_id=module_id,
            corp_code=corp_code,
            company_info=company_info,
            end_year=str(base_year),
            years=years,
            financials_by_year=financials_by_year,
            financials_quarterly=financials_quarterly,
            governance_data=governance_data,
            disc_list=disc_list,
            market_data=market_data,
            stock_history=stock_history,
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모듈 분석 오류: {str(e)}")


@router.post("/{corp_code}/meta-analysis")
async def run_meta_analysis(
    corp_code: str = Path(..., description="기업 고유번호"),
    end_year:  str = Query("", description="종료 연도 (YYYY, 기본값: 전년도)"),
) -> Dict[str, Any]:
    """
    VC/PE 심층 종합 기업분석 (메타 분석)

    9개 분석 모듈을 병렬 실행 후 메타 AI(deep_composite_investment_analysis)가
    모듈 간 충돌 신호를 포함한 투자위원회 수준의 종합 판단을 생성합니다.

    **처리 시간**: 3~8분 소요 (9 모듈 + 1 메타 = 10 LLM 호출)

    **출력 형식**: `meta_output_json_skeleton` 기준 JSON
    - `core_investment_thesis`: 핵심 투자 논지
    - `company_type_assessment`: 성장형/운영개선형/관찰/회피 판단
    - `cross_module_conflicts`: 모듈 간 충돌 신호
    - `vc_conclusion` / `pe_conclusion`: VC·PE 분리 결론
    - `recommended_action`: 최종 액션
    """
    from datetime import date as _date

    base_year = int(end_year) if end_year.isdigit() else datetime.now().year - 1
    years     = [str(base_year), str(base_year - 1), str(base_year - 2)]

    # ── 1. 데이터 수집 ──────────────────────────────────────────────
    try:
        disc_start = (_date.today() - timedelta(days=365 * 4)).strftime("%Y%m%d")
        disc_end   = _date.today().strftime("%Y%m%d")

        gather_results = await asyncio.gather(
            dart_service.get_company_info(corp_code),
            dart_service.get_financial_statement(corp_code, years[0], "11011"),
            dart_service.get_financial_statement(corp_code, years[1], "11011"),
            dart_service.get_financial_statement(corp_code, years[2], "11011"),
            dart_service.get_major_shareholders(corp_code, str(base_year)),
            dart_service.get_executives(corp_code, str(base_year)),
            dart_service.get_disclosure_list(
                corp_code, bgn_de=disc_start, end_de=disc_end, page_count=50
            ),
            return_exceptions=True,
        )

        company_info = gather_results[0] if not isinstance(gather_results[0], Exception) else {}
        financials_by_year: Dict = {}
        for i, year in enumerate(years):
            raw = gather_results[1 + i]
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_by_year[year] = structure_financial_data(raw)

        def _safe(r):
            return r if not isinstance(r, Exception) and r.get("status") not in ("013", "020") else None

        governance_data = {
            "major_shareholders": _safe(gather_results[4]),
            "executives":         _safe(gather_results[5]),
        }
        disc_raw  = gather_results[6]
        disc_list = disc_raw.get("list", []) if not isinstance(disc_raw, Exception) else []

        # 주가 데이터
        market_data: Dict = {}
        stock_history: Dict = {}
        stock_code = company_info.get("stock_code", "")
        if stock_code:
            try:
                market_data = await krx_service.get_stock_price(stock_code)
            except Exception:
                logger.debug("메타 분석용 시장 데이터 조회 실패 (stock_code=%s)", stock_code)
            try:
                hist_start = (_date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
                hist_end   = _date.today().strftime("%Y-%m-%d")
                stock_history = await krx_service.get_stock_history(
                    stock_code, hist_start, hist_end
                )
            except Exception:
                logger.debug("메타 분석용 주가 이력 조회 실패 (stock_code=%s)", stock_code)

        # ── 2. 9개 모듈 병렬 실행 ──────────────────────────────────
        ALL_MODULE_IDS = [
            "comprehensive_corporate_analysis",
            "key_financial_indicators",
            "complete_financial_statements",
            "business_segment_performance",
            "shareholder_structure",
            "board_executive_analysis",
            "stock_price_movement_analysis",
            "paid_in_capital_increase",
            "preliminary_results",
        ]
        # S11(시장데이터) 사용 모듈에만 stock_history 전달
        _S11_MODULES = {
            "comprehensive_corporate_analysis",
            "stock_price_movement_analysis",
            "paid_in_capital_increase",
            "preliminary_results",
        }

        module_tasks = [
            module_service.run_module(
                module_id=mid,
                corp_code=corp_code,
                company_info=company_info,
                end_year=str(base_year),
                years=years,
                financials_by_year=financials_by_year,
                financials_quarterly={},
                governance_data=governance_data,
                disc_list=disc_list,
                market_data=market_data,
                stock_history=stock_history if mid in _S11_MODULES else None,
            )
            for mid in ALL_MODULE_IDS
        ]

        module_raw_results = await asyncio.gather(*module_tasks, return_exceptions=True)

        # ── 3. 모듈 결과 정리 ──────────────────────────────────────
        module_outputs: Dict[str, Any]  = {}
        module_summaries: Dict[str, Any] = {}
        for mid, res in zip(ALL_MODULE_IDS, module_raw_results):
            if not isinstance(res, Exception) and "result" in res:
                module_outputs[mid] = res["result"]
                module_summaries[mid] = {
                    "module_name":        res.get("module_name"),
                    "status":             "success",
                    "one_line_summary":   res["result"].get("one_line_summary", ""),
                    "recommended_action": res["result"].get("recommended_action", ""),
                    "confidence":         res["result"].get("confidence"),
                }
            else:
                module_outputs[mid] = {}
                module_summaries[mid] = {
                    "status": "failed",
                    "error":  str(res) if isinstance(res, Exception) else "분석 실패",
                }

        # ── 4. 메타 종합 분석 ───────────────────────────────────────
        meta_result = await module_service.run_meta_analysis(
            corp_code=corp_code,
            company_info=company_info,
            end_year=str(base_year),
            years=years,
            module_outputs=module_outputs,
        )

        return {
            "corp_code":        corp_code,
            "corp_name":        company_info.get("corp_name"),
            "base_year":        str(base_year),
            "years_covered":    years,
            "module_summaries": module_summaries,
            "module_outputs":   module_outputs,
            **meta_result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메타 분석 오류: {str(e)}")


# ─── 개선 9: 증분 분석 (PATCH) ───────────────────────────────────────

@router.patch("/{corp_code}/module/{module_id}")
async def run_incremental_module_analysis(
    corp_code: str = Path(..., description="기업 고유번호"),
    module_id: str = Path(..., description="분석 모듈 ID"),
    body: IncrementalModuleRequest = None,
):
    """
    증분 모듈 분석 (이전 결과 기반 업데이트)

    이전 분석 결과(`prev_result`)를 컨텍스트로 제공하면
    변경된 부분만 재분석하여 효율적으로 업데이트합니다.

    - **prev_result**: 이전 `run_module` 반환값의 `result` 필드
    - 변경 없으면 이전 결과 그대로 반환, 변경 시 업데이트된 필드만 교체
    """
    if body is None:
        body = IncrementalModuleRequest()

    real_id = MODULE_ID_ALIAS.get(module_id, module_id)
    if real_id not in MODULES:
        raise HTTPException(
            status_code=400,
            detail=f"알 수 없는 모듈: {module_id}. 가능한 모듈: {list(MODULES.keys())}",
        )

    end_year   = body.end_year
    base_year  = int(end_year) if end_year.isdigit() else datetime.now().year - 1
    years      = [str(base_year), str(base_year - 1), str(base_year - 2)]

    try:
        from datetime import date
        disc_start = (date.today() - timedelta(days=365 * 4)).strftime("%Y%m%d")
        disc_end   = date.today().strftime("%Y%m%d")

        QTR_CODES = {"Q1": "11013", "H1": "11012", "Q3": "11014"}
        qtr_tasks  = [
            dart_service.get_financial_statement(corp_code, years[0], code)
            for code in QTR_CODES.values()
        ]
        qtr_labels = [f"{years[0]}_{lbl}" for lbl in QTR_CODES.keys()]

        results = await asyncio.gather(
            dart_service.get_company_info(corp_code),
            dart_service.get_financial_statement(corp_code, years[0], "11011"),
            dart_service.get_financial_statement(corp_code, years[1], "11011"),
            dart_service.get_financial_statement(corp_code, years[2], "11011"),
            dart_service.get_major_shareholders(corp_code, str(base_year)),
            dart_service.get_executives(corp_code, str(base_year)),
            dart_service.get_disclosure_list(corp_code, bgn_de=disc_start, end_de=disc_end, page_count=50),
            *qtr_tasks,
            return_exceptions=True,
        )

        company_info = results[0] if not isinstance(results[0], Exception) else {}
        financials_by_year: Dict = {}
        for i, year in enumerate(years):
            raw = results[1 + i]
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_by_year[year] = structure_financial_data(raw)

        def _safe(r):
            return r if not isinstance(r, Exception) and r.get("status") not in ("013", "020") else None

        governance_data = {
            "major_shareholders": _safe(results[4]),
            "executives":         _safe(results[5]),
        }
        disc_raw  = results[6]
        disc_list = disc_raw.get("list", []) if not isinstance(disc_raw, Exception) else []

        financials_quarterly: Dict = {}
        for lbl, raw in zip(qtr_labels, results[7:]):
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_quarterly[lbl] = structure_financial_data(raw)

        market_data: Dict = {}
        stock_code = company_info.get("stock_code", "")
        if stock_code:
            try:
                market_data = await krx_service.get_stock_price(stock_code)
            except Exception:
                logger.debug("증분 분석용 시장 데이터 조회 실패 (stock_code=%s)", stock_code)

        # 증분: 캐시 무효화 후 prev_result 주입
        cache_service.invalidate(corp_code, real_id, str(base_year))

        result = await module_service.run_module(
            module_id=module_id,
            corp_code=corp_code,
            company_info=company_info,
            end_year=str(base_year),
            years=years,
            financials_by_year=financials_by_year,
            financials_quarterly=financials_quarterly,
            governance_data=governance_data,
            disc_list=disc_list,
            market_data=market_data,
            stock_history={},
            prev_result=body.prev_result,
            use_cache=False,        # 강제 재분석
        )
        result["incremental"] = True
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"증분 분석 오류: {str(e)}")


# ─── 개선 2: 비동기 메타 분석 + 폴링 ─────────────────────────────────

async def _run_meta_analysis_background(
    job_id: str,
    corp_code: str,
    base_year: int,
) -> None:
    """백그라운드 메타 분석 실행기"""
    from datetime import date as _date

    try:
        job_service.update_job(job_id, "running", progress=5)
        years = [str(base_year), str(base_year - 1), str(base_year - 2)]

        disc_start = (_date.today() - timedelta(days=365 * 4)).strftime("%Y%m%d")
        disc_end   = _date.today().strftime("%Y%m%d")

        gather_results = await asyncio.gather(
            dart_service.get_company_info(corp_code),
            dart_service.get_financial_statement(corp_code, years[0], "11011"),
            dart_service.get_financial_statement(corp_code, years[1], "11011"),
            dart_service.get_financial_statement(corp_code, years[2], "11011"),
            dart_service.get_major_shareholders(corp_code, str(base_year)),
            dart_service.get_executives(corp_code, str(base_year)),
            dart_service.get_disclosure_list(
                corp_code, bgn_de=disc_start, end_de=disc_end, page_count=50
            ),
            return_exceptions=True,
        )

        company_info = gather_results[0] if not isinstance(gather_results[0], Exception) else {}
        financials_by_year: Dict = {}
        for i, year in enumerate(years):
            raw = gather_results[1 + i]
            if not isinstance(raw, Exception) and raw.get("status") != "013":
                financials_by_year[year] = structure_financial_data(raw)

        def _safe(r):
            return r if not isinstance(r, Exception) and r.get("status") not in ("013", "020") else None

        governance_data = {
            "major_shareholders": _safe(gather_results[4]),
            "executives":         _safe(gather_results[5]),
        }
        disc_raw  = gather_results[6]
        disc_list = disc_raw.get("list", []) if not isinstance(disc_raw, Exception) else []

        market_data: Dict = {}
        stock_history: Dict = {}
        stock_code = company_info.get("stock_code", "")
        if stock_code:
            try:
                market_data = await krx_service.get_stock_price(stock_code)
            except Exception:
                logger.debug("비동기 메타 분석 시장 데이터 조회 실패 (stock_code=%s)", stock_code)
            try:
                hist_start = (_date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
                hist_end   = _date.today().strftime("%Y-%m-%d")
                stock_history = await krx_service.get_stock_history(
                    stock_code, hist_start, hist_end
                )
            except Exception:
                logger.debug("비동기 메타 분석 주가 이력 조회 실패 (stock_code=%s)", stock_code)

        job_service.update_job(job_id, "running", progress=15)

        ALL_MODULE_IDS = [
            "comprehensive_corporate_analysis",
            "key_financial_indicators",
            "complete_financial_statements",
            "business_segment_performance",
            "shareholder_structure",
            "board_executive_analysis",
            "stock_price_movement_analysis",
            "paid_in_capital_increase",
            "preliminary_results",
        ]
        _S11_MODULES = {
            "comprehensive_corporate_analysis",
            "stock_price_movement_analysis",
            "paid_in_capital_increase",
            "preliminary_results",
        }

        # 9개 모듈 병렬 실행
        module_tasks = [
            module_service.run_module(
                module_id=mid,
                corp_code=corp_code,
                company_info=company_info,
                end_year=str(base_year),
                years=years,
                financials_by_year=financials_by_year,
                financials_quarterly={},
                governance_data=governance_data,
                disc_list=disc_list,
                market_data=market_data,
                stock_history=stock_history if mid in _S11_MODULES else None,
            )
            for mid in ALL_MODULE_IDS
        ]
        module_raw_results = await asyncio.gather(*module_tasks, return_exceptions=True)

        job_service.update_job(job_id, "running", progress=80)

        module_outputs: Dict[str, Any]   = {}
        module_summaries: Dict[str, Any] = {}
        for mid, res in zip(ALL_MODULE_IDS, module_raw_results):
            if not isinstance(res, Exception) and "result" in res:
                module_outputs[mid]   = res["result"]
                module_summaries[mid] = {
                    "module_name":        res.get("module_name"),
                    "status":             "success",
                    "one_line_summary":   res["result"].get("one_line_summary", ""),
                    "recommended_action": res["result"].get("recommended_action", ""),
                    "confidence":         res["result"].get("confidence"),
                }
            else:
                module_outputs[mid]   = {}
                module_summaries[mid] = {
                    "status": "failed",
                    "error":  str(res) if isinstance(res, Exception) else "분석 실패",
                }

        meta_result = await module_service.run_meta_analysis(
            corp_code=corp_code,
            company_info=company_info,
            end_year=str(base_year),
            years=years,
            module_outputs=module_outputs,
        )

        final = {
            "corp_code":        corp_code,
            "corp_name":        company_info.get("corp_name"),
            "base_year":        str(base_year),
            "years_covered":    years,
            "module_summaries": module_summaries,
            "module_outputs":   module_outputs,
            **meta_result,
        }
        job_service.update_job(job_id, "completed", result=final, progress=100)

    except Exception as e:
        job_service.update_job(job_id, "failed", error=str(e))


@router.post("/{corp_code}/meta-analysis/async")
async def start_meta_analysis_async(
    corp_code: str = Path(..., description="기업 고유번호"),
    end_year:  str = Query("", description="종료 연도 (YYYY, 기본값: 전년도)"),
) -> Dict[str, Any]:
    """
    비동기 메타 분석 시작 (job_id 반환)

    9개 모듈 + 메타 분석을 백그라운드에서 실행합니다.
    반환된 `job_id`로 `GET /jobs/{job_id}`를 폴링하여 진행률·결과를 확인하세요.

    **예상 소요 시간**: 3~8분
    """
    base_year = int(end_year) if end_year.isdigit() else datetime.now().year - 1

    job_id = job_service.create_job(
        corp_code=corp_code,
        task_type="meta_analysis",
        meta={"base_year": str(base_year)},
    )

    # FastAPI 이벤트 루프에서 비동기 백그라운드 태스크 실행
    asyncio.create_task(
        _run_meta_analysis_background(job_id, corp_code, base_year)
    )

    return {
        "job_id":    job_id,
        "status":    "pending",
        "corp_code": corp_code,
        "base_year": str(base_year),
        "poll_url":  f"/api/analysis/jobs/{job_id}",
        "message":   "메타 분석이 시작되었습니다. job_id로 진행 상황을 확인하세요.",
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str = Path(..., description="작업 ID"),
) -> Dict[str, Any]:
    """
    백그라운드 작업 상태 폴링

    - **status**: pending → running → completed | failed
    - **progress**: 0~100 진행률
    - **result**: 완료 시 메타 분석 결과 포함
    - **error**: 실패 시 오류 메시지
    """
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"작업을 찾을 수 없습니다: {job_id}")
    return job


@router.get("/jobs")
async def list_jobs(
    corp_code: str = Query("", description="기업 고유번호 필터 (미입력 시 전체)"),
    limit: int = Query(20, ge=1, le=100, description="최대 반환 수"),
) -> Dict[str, Any]:
    """백그라운드 작업 목록 (최신순)"""
    jobs = job_service.list_jobs(corp_code=corp_code or None, limit=limit)
    return {"jobs": jobs, "total": len(jobs)}


def _reprt_code_to_name(code: str) -> str:
    return {
        "11011": "사업보고서",
        "11012": "반기보고서",
        "11013": "1분기보고서",
        "11014": "3분기보고서",
    }.get(code, code)
