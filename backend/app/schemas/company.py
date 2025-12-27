from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class SourceInfo(BaseModel):
    """데이터 출처 정보"""
    provider: str = Field(..., description="데이터 제공자")
    url: str = Field(..., description="출처 URL")
    retrieved_at: str = Field(..., description="데이터 조회 시각")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="추가 정보")


class CompanySearchResult(BaseModel):
    """기업 검색 결과"""
    corp_code: str = Field(..., description="기업 고유번호")
    corp_name: str = Field(..., description="기업명")
    stock_code: Optional[str] = Field(None, description="종목코드")
    modify_date: Optional[str] = Field(None, description="수정일자")
    source: SourceInfo = Field(..., description="출처 정보", alias="_source")

    class Config:
        populate_by_name = True


class CompanyInfo(BaseModel):
    """기업 기본 정보"""
    corp_code: str = Field(..., description="기업 고유번호")
    corp_name: str = Field(..., description="정식 기업명")
    corp_name_eng: Optional[str] = Field(None, description="영문 기업명")
    stock_name: Optional[str] = Field(None, description="종목명")
    stock_code: Optional[str] = Field(None, description="종목코드")
    ceo_nm: Optional[str] = Field(None, description="대표이사명")
    corp_cls: Optional[str] = Field(None, description="법인 구분")
    jurir_no: Optional[str] = Field(None, description="법인등록번호")
    bizr_no: Optional[str] = Field(None, description="사업자등록번호")
    adres: Optional[str] = Field(None, description="주소")
    hm_url: Optional[str] = Field(None, description="홈페이지")
    ir_url: Optional[str] = Field(None, description="IR 홈페이지")
    phn_no: Optional[str] = Field(None, description="전화번호")
    fax_no: Optional[str] = Field(None, description="팩스번호")
    induty_code: Optional[str] = Field(None, description="업종코드")
    est_dt: Optional[str] = Field(None, description="설립일")
    acc_mt: Optional[str] = Field(None, description="결산월")
    source: SourceInfo = Field(..., description="출처 정보", alias="_source")

    class Config:
        populate_by_name = True


class DisclosureItem(BaseModel):
    """공시 항목"""
    rcept_no: str = Field(..., description="접수번호")
    corp_cls: str = Field(..., description="법인 구분")
    corp_code: str = Field(..., description="기업 고유번호")
    corp_name: str = Field(..., description="기업명")
    report_nm: str = Field(..., description="보고서명")
    rcept_dt: str = Field(..., description="접수일자")
    flr_nm: str = Field(..., description="공시 제출인")
    rm: Optional[str] = Field(None, description="비고")
    source_url: str = Field(..., description="공시 원문 URL", alias="_source_url")

    class Config:
        populate_by_name = True


class DisclosureList(BaseModel):
    """공시 목록 응답"""
    status: str = Field(..., description="응답 상태")
    message: str = Field(..., description="응답 메시지")
    list: list[DisclosureItem] = Field(..., description="공시 목록")
    page_no: int = Field(..., description="페이지 번호")
    page_count: int = Field(..., description="페이지당 건수")
    total_count: int = Field(..., description="전체 건수")
    total_page: int = Field(..., description="전체 페이지 수")
    source: SourceInfo = Field(..., description="출처 정보", alias="_source")

    class Config:
        populate_by_name = True
