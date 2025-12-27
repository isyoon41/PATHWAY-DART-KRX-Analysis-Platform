from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from datetime import datetime, timedelta
from app.services.dart_service import dart_service
from app.services.krx_service import krx_service

router = APIRouter()


@router.get("/{corp_code}/comprehensive")
async def get_comprehensive_analysis(
    corp_code: str,
    include_financial: bool = Query(True, description="재무제표 포함 여부"),
    include_disclosures: bool = Query(True, description="최근 공시 포함 여부"),
    include_market_data: bool = Query(True, description="시장 데이터 포함 여부")
) -> Dict[str, Any]:
    """
    종합 기업 분석 리포트

    - **corp_code**: 기업 고유번호
    - **include_financial**: 재무제표 포함 여부
    - **include_disclosures**: 최근 공시 포함 여부
    - **include_market_data**: 시장 데이터 포함 여부
    - **반환**: 종합 분석 리포트 (모든 데이터에 출처 포함)
    """
    try:
        # 기업 기본 정보 조회
        company_info = await dart_service.get_company_info(corp_code)

        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        analysis_result = {
            "company_info": company_info,
            "analysis_metadata": {
                "generated_at": datetime.now().isoformat(),
                "corp_code": corp_code,
                "included_sections": {
                    "financial": include_financial,
                    "disclosures": include_disclosures,
                    "market_data": include_market_data
                }
            }
        }

        # 재무제표 포함
        if include_financial:
            try:
                current_year = datetime.now().year - 1  # 전년도 데이터
                financial_data = await dart_service.get_financial_statement(
                    corp_code=corp_code,
                    bsns_year=str(current_year),
                    reprt_code="11011"  # 사업보고서
                )
                analysis_result["financial_statement"] = financial_data
            except Exception as e:
                analysis_result["financial_statement"] = {
                    "error": str(e),
                    "message": "재무제표를 가져올 수 없습니다."
                }

        # 최근 공시 포함 (최근 3개월)
        if include_disclosures:
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)

                disclosures = await dart_service.get_disclosure_list(
                    corp_code=corp_code,
                    bgn_de=start_date.strftime("%Y%m%d"),
                    end_de=end_date.strftime("%Y%m%d"),
                    page_no=1,
                    page_count=20
                )
                analysis_result["recent_disclosures"] = disclosures
            except Exception as e:
                analysis_result["recent_disclosures"] = {
                    "error": str(e),
                    "message": "공시 정보를 가져올 수 없습니다."
                }

        # 시장 데이터 포함
        if include_market_data and company_info.get("stock_code"):
            try:
                stock_code = company_info.get("stock_code")
                market_data = await krx_service.get_stock_info(stock_code)
                analysis_result["market_data"] = market_data
            except Exception as e:
                analysis_result["market_data"] = {
                    "error": str(e),
                    "message": "시장 데이터를 가져올 수 없습니다."
                }

        # 출처 요약
        analysis_result["sources_summary"] = {
            "description": "본 리포트의 모든 데이터는 공식 출처에서 수집되었으며, 각 섹션에 출처 정보가 포함되어 있습니다.",
            "primary_sources": [
                {
                    "name": "DART (금융감독원 전자공시시스템)",
                    "url": "https://dart.fss.or.kr",
                    "description": "기업 정보, 재무제표, 공시 데이터"
                },
                {
                    "name": "KRX (한국거래소)",
                    "url": "http://data.krx.co.kr",
                    "description": "시장 데이터, 주가 정보"
                }
            ],
            "data_reliability": "모든 데이터는 공식 금융 기관에서 제공하는 정보를 기반으로 합니다.",
            "last_updated": datetime.now().isoformat()
        }

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 리포트 생성 중 오류 발생: {str(e)}")


@router.get("/{corp_code}/summary")
async def get_analysis_summary(corp_code: str) -> Dict[str, Any]:
    """
    기업 분석 요약

    - **corp_code**: 기업 고유번호
    - **반환**: 핵심 지표 및 요약 정보
    """
    try:
        # 기업 기본 정보
        company_info = await dart_service.get_company_info(corp_code)

        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

        # 최근 공시 개수 (최근 1개월)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        recent_disclosures = await dart_service.get_disclosure_list(
            corp_code=corp_code,
            bgn_de=start_date.strftime("%Y%m%d"),
            end_de=end_date.strftime("%Y%m%d"),
            page_no=1,
            page_count=100
        )

        summary = {
            "corp_name": company_info.get("corp_name"),
            "stock_code": company_info.get("stock_code"),
            "ceo": company_info.get("ceo_nm"),
            "established": company_info.get("est_dt"),
            "industry": company_info.get("induty_code"),
            "recent_disclosure_count": len(recent_disclosures.get("list", [])),
            "summary_generated_at": datetime.now().isoformat(),
            "_source": {
                "provider": "DART·KRX 기업분석 플랫폼",
                "data_sources": ["DART", "KRX"],
                "retrieved_at": datetime.now().isoformat()
            }
        }

        return summary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 정보 생성 중 오류 발생: {str(e)}")
