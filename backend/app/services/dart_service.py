import io
import zipfile
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import settings


class DARTService:
    """DART OpenAPI 연동 서비스"""

    def __init__(self):
        self.base_url = settings.dart_base_url
        self.api_key = settings.dart_api_key

    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """DART API 요청 헬퍼 함수"""
        params["crtfc_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()

    async def get_company_info(self, corp_code: str) -> Dict:
        """
        기업 기본 정보 조회

        Args:
            corp_code: 기업 고유번호

        Returns:
            기업 정보 딕셔너리 (출처 포함)
        """
        data = await self._request("company.json", {"corp_code": corp_code})

        # 출처 정보 추가
        data["_source"] = {
            "provider": "DART (금융감독원 전자공시시스템)",
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={corp_code}",
            "retrieved_at": datetime.now().isoformat()
        }

        return data

    async def get_disclosure_list(
        self,
        corp_code: str,
        bgn_de: str,
        end_de: str,
        page_no: int = 1,
        page_count: int = 10
    ) -> Dict:
        """
        공시 목록 조회

        Args:
            corp_code: 기업 고유번호
            bgn_de: 시작일 (YYYYMMDD)
            end_de: 종료일 (YYYYMMDD)
            page_no: 페이지 번호
            page_count: 페이지당 건수

        Returns:
            공시 목록 (출처 포함)
        """
        params = {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": page_no,
            "page_count": page_count
        }

        data = await self._request("list.json", params)

        # 각 공시에 출처 URL 추가
        if "list" in data:
            for item in data["list"]:
                item["_source_url"] = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}"

        # 전체 출처 정보
        data["_source"] = {
            "provider": "DART 공시 검색",
            "api_endpoint": f"{self.base_url}/list.json",
            "retrieved_at": datetime.now().isoformat()
        }

        return data

    async def get_financial_statement(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011"
    ) -> Dict:
        """
        재무제표 조회

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)

        Returns:
            재무제표 데이터 (출처 포함)
        """
        params = {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code
        }

        data = await self._request("fnlttSinglAcntAll.json", params)

        # 출처 정보 추가
        data["_source"] = {
            "provider": "DART 재무제표",
            "report_type": self._get_report_type_name(reprt_code),
            "business_year": bsns_year,
            "url": f"https://dart.fss.or.kr",
            "retrieved_at": datetime.now().isoformat()
        }

        return data

    async def search_company(self, company_name: str) -> List[Dict]:
        """
        기업명으로 기업 검색

        DART corpCode.xml은 ZIP 압축 파일로 제공됩니다.
        압축 해제 후 XML을 파싱하여 기업명 기반으로 필터링합니다.

        Args:
            company_name: 기업명 (부분 일치 검색)

        Returns:
            검색된 기업 목록 (상장사 우선)
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/corpCode.xml",
                params={"crtfc_key": self.api_key}
            )
            response.raise_for_status()

        # ZIP 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_filename = next(
                (name for name in zf.namelist() if name.endswith(".xml")),
                None
            )
            if not xml_filename:
                return []
            xml_content = zf.read(xml_filename)

        # XML 파싱
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(xml_content, "xml")

        companies = []
        for corp in soup.find_all("list"):
            corp_name_tag = corp.find("corp_name")
            if not corp_name_tag:
                continue
            corp_name = corp_name_tag.text

            if company_name.lower() not in corp_name.lower():
                continue

            stock_code_tag = corp.find("stock_code")
            stock_code = stock_code_tag.text.strip() if stock_code_tag else ""

            companies.append({
                "corp_code": corp.find("corp_code").text,
                "corp_name": corp_name,
                "stock_code": stock_code if stock_code else None,
                "modify_date": corp.find("modify_date").text if corp.find("modify_date") else None,
                "_source": {
                    "provider": "DART 기업 목록",
                    "retrieved_at": datetime.now().isoformat()
                }
            })

        # 상장사(stock_code 있음) 우선 정렬, 최대 20개
        companies.sort(key=lambda x: (x["stock_code"] is None, x["corp_name"]))
        return companies[:20]

    async def get_major_shareholders(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011",
    ) -> Dict:
        """
        최대주주 현황 조회 (DART majorstock.json)

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드

        Returns:
            최대주주 및 특수관계인 지분 목록
        """
        data = await self._request(
            "majorstock.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )
        data["_source"] = {
            "provider": "DART 최대주주 현황",
            "business_year": bsns_year,
            "retrieved_at": datetime.now().isoformat(),
        }
        return data

    async def get_executives(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011",
    ) -> Dict:
        """
        임원 현황 조회 (DART exctvSttus.json)

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드

        Returns:
            임원 명단 및 직위 정보
        """
        data = await self._request(
            "exctvSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )
        data["_source"] = {
            "provider": "DART 임원 현황",
            "business_year": bsns_year,
            "retrieved_at": datetime.now().isoformat(),
        }
        return data

    async def get_affiliated_companies(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011",
    ) -> Dict:
        """
        계열회사 현황 조회 (DART affilCo.json)

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드

        Returns:
            계열회사 목록
        """
        data = await self._request(
            "affilCo.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )
        data["_source"] = {
            "provider": "DART 계열회사 현황",
            "business_year": bsns_year,
            "retrieved_at": datetime.now().isoformat(),
        }
        return data

    async def get_key_indicators(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011",
    ) -> Dict:
        """
        단일회사 주요 재무지표 조회 (DART fnlttCmpnyIndctr.json)
        — ROE, ROA, EPS, BPS, PER, PBR 등 이미 계산된 지표 제공

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드

        Returns:
            주요 재무지표 목록
        """
        data = await self._request(
            "fnlttCmpnyIndctr.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )
        data["_source"] = {
            "provider": "DART 주요 재무지표",
            "business_year": bsns_year,
            "retrieved_at": datetime.now().isoformat(),
        }
        return data

    def _get_report_type_name(self, reprt_code: str) -> str:
        """보고서 코드를 이름으로 변환"""
        report_types = {
            "11011": "사업보고서",
            "11012": "반기보고서",
            "11013": "1분기보고서",
            "11014": "3분기보고서"
        }
        return report_types.get(reprt_code, "알 수 없음")


# 싱글톤 인스턴스
dart_service = DARTService()
