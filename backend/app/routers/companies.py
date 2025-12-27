from fastapi import APIRouter, HTTPException, Query, Path
from typing import List
from app.services.dart_service import dart_service
from app.services.krx_service import krx_service
from app.schemas.company import CompanySearchResult, CompanyInfo, DisclosureList

router = APIRouter()


@router.get("/search", response_model=List[CompanySearchResult])
async def search_companies(
    query: str = Query(..., description="검색할 기업명", min_length=1)
):
    """
    기업명으로 기업 검색

    - **query**: 검색할 기업명 (예: 삼성전자, SK하이닉스)
    - **반환**: 검색된 기업 목록 (출처 정보 포함)
    """
    try:
        companies = await dart_service.search_company(query)

        if not companies:
            raise HTTPException(status_code=404, detail=f"'{query}'에 해당하는 기업을 찾을 수 없습니다.")

        return companies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기업 검색 중 오류 발생: {str(e)}")


@router.get("/{corp_code}", response_model=CompanyInfo)
async def get_company_info(
    corp_code: str = Path(..., description="기업 고유번호")
):
    """
    기업 기본 정보 조회

    - **corp_code**: 기업 고유번호
    - **반환**: 기업 상세 정보 (출처 정보 포함)
    """
    try:
        company_info = await dart_service.get_company_info(corp_code)

        if company_info.get("status") == "013":
            raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

        return company_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기업 정보 조회 중 오류 발생: {str(e)}")


@router.get("/{corp_code}/disclosures")
async def get_disclosures(
    corp_code: str,
    bgn_de: str = Query(..., description="시작일 (YYYYMMDD)", regex=r"^\d{8}$"),
    end_de: str = Query(..., description="종료일 (YYYYMMDD)", regex=r"^\d{8}$"),
    page_no: int = Query(1, description="페이지 번호", ge=1),
    page_count: int = Query(10, description="페이지당 건수", ge=1, le=100)
):
    """
    기업 공시 목록 조회

    - **corp_code**: 기업 고유번호
    - **bgn_de**: 조회 시작일 (예: 20240101)
    - **end_de**: 조회 종료일 (예: 20241231)
    - **page_no**: 페이지 번호 (기본값: 1)
    - **page_count**: 페이지당 건수 (기본값: 10, 최대: 100)
    - **반환**: 공시 목록 (각 공시에 출처 URL 포함)
    """
    try:
        disclosures = await dart_service.get_disclosure_list(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
            page_no=page_no,
            page_count=page_count
        )

        if disclosures.get("status") == "013":
            raise HTTPException(status_code=404, detail="공시 정보를 찾을 수 없습니다.")

        return disclosures
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공시 목록 조회 중 오류 발생: {str(e)}")


@router.get("/{corp_code}/financial")
async def get_financial_statement(
    corp_code: str,
    bsns_year: str = Query(..., description="사업연도 (YYYY)", regex=r"^\d{4}$"),
    reprt_code: str = Query("11011", description="보고서 코드 (11011: 사업보고서, 11012: 반기, 11013: 1분기, 11014: 3분기)")
):
    """
    재무제표 조회

    - **corp_code**: 기업 고유번호
    - **bsns_year**: 사업연도 (예: 2023)
    - **reprt_code**: 보고서 코드
      - 11011: 사업보고서
      - 11012: 반기보고서
      - 11013: 1분기보고서
      - 11014: 3분기보고서
    - **반환**: 재무제표 데이터 (출처 정보 포함)
    """
    try:
        financial_data = await dart_service.get_financial_statement(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code
        )

        if financial_data.get("status") == "013":
            raise HTTPException(status_code=404, detail="재무제표를 찾을 수 없습니다.")

        return financial_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재무제표 조회 중 오류 발생: {str(e)}")


@router.get("/krx/{stock_code}")
async def get_krx_stock_info(
    stock_code: str = Path(..., description="종목코드")
):
    """
    KRX 주식 정보 조회

    - **stock_code**: 종목코드 (예: 005930)
    - **반환**: 주식 정보 (출처 정보 포함)
    """
    try:
        stock_info = await krx_service.get_stock_info(stock_code)
        return stock_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 정보 조회 중 오류 발생: {str(e)}")
