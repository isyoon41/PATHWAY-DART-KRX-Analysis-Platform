from fastapi import APIRouter, HTTPException, Query, Path
from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.dart_service import dart_service
from app.services.krx_service import krx_service
from app.services.dart_parser import create_parser, analyzer as section_analyzer
from app.services.financial_parser import structure_financial_data
from config import settings

router = APIRouter()


@router.get("/{corp_code}/comprehensive")
async def get_comprehensive_analysis(
    corp_code: str,
    include_financial: bool = Query(True,  description="재무제표 포함 여부"),
    include_disclosures: bool = Query(True, description="최근 공시 포함 여부"),
    include_market_data: bool = Query(True, description="시장 데이터 포함 여부"),
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

        # 재무제표 (XBRL → 구조화)
        if include_financial:
            try:
                raw = await dart_service.get_financial_statement(
                    corp_code=corp_code,
                    bsns_year=str(datetime.now().year - 1),
                    reprt_code="11011",
                )
                result["financial_statement"] = structure_financial_data(raw)
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
                result["market_data"] = await krx_service.get_stock_info(
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
    bsns_year: str = Query(..., description="사업연도 (예: 2023)", regex=r"^\d{4}$"),
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


def _reprt_code_to_name(code: str) -> str:
    return {
        "11011": "사업보고서",
        "11012": "반기보고서",
        "11013": "1분기보고서",
        "11014": "3분기보고서",
    }.get(code, code)
