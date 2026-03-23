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
        # 기업 목록 인메모리 캐시 (1시간 유효)
        self._corp_list_cache: Optional[List[Dict]] = None
        self._corp_list_cache_time: Optional[datetime] = None

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

        DART company.json API를 기본으로 하되, 아래 필드는 데이터 품질 이슈가 있어
        corp list(XML)의 값으로 보완합니다:
          - listing_dt: 많은 기업에서 None으로 반환됨 → corp list modify_date로 대체
          - corp_cls:   신규 상장사는 일시적으로 빈값일 수 있음 → corp list stock_code 기반 판단
        """
        data = await self._request("company.json", {"corp_code": corp_code})

        # ── listing_dt / corp_cls 보완 (DART 데이터 품질 이슈 대응) ──────
        listing_dt = data.get("listing_dt") or ""
        corp_cls   = data.get("corp_cls")   or ""
        stock_code = data.get("stock_code") or ""

        if not listing_dt or not corp_cls:
            # corp list에서 해당 기업 항목 찾기 (캐시 활용)
            try:
                corp_list = await self._get_corp_list()
                matched = next(
                    (c for c in corp_list if c.get("corp_code") == corp_code), None
                )
                if matched:
                    # listing_dt가 비어 있고 corp list에 stock_code가 있으면
                    # modify_date를 상장 관련 날짜로 사용 (IPO 후 DART 업데이트 일자)
                    if not listing_dt and matched.get("stock_code"):
                        data["listing_dt"] = matched.get("modify_date", "")
                        data["_listing_dt_source"] = "DART corp list modify_date (보완)"
                    # corp_cls도 비어 있으면 stock_code 유무로 판단
                    if not corp_cls and matched.get("stock_code"):
                        # stock_code 있지만 corp_cls 없음 → 시장 미분류 상장사
                        data["_corp_cls_note"] = "corp_cls 미제공 (상장사로 확인)"
            except Exception:
                pass  # 보완 실패 시 원본 유지

        # 출처 정보 추가
        data["_source"] = {
            "provider": "DART (금융감독원 전자공시시스템)",
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={corp_code}",
            "retrieved_at": datetime.now().isoformat(),
            "note": "listing_dt는 DART에서 미제공 시 corp list modify_date로 보완"
        }

        return data

    async def get_annual_report_rcept_no(
        self,
        corp_code: str,
        base_year: int,
    ) -> Optional[Dict]:
        """
        가장 최근 사업보고서 접수번호(rcept_no) 조회.

        base_year 포함 최대 3년 소급하여 사업보고서를 탐색합니다.
        사업보고서는 매년 3월 제출되므로, 6개월 공시 목록 대신
        충분한 기간(3년)을 검색해야 누락 없이 찾을 수 있습니다.

        Returns:
            {"rcept_no": ..., "rcept_dt": ..., "report_nm": ...} 또는 None
        """
        end_de   = f"{base_year}1231"
        bgn_de   = f"{base_year - 2}0101"   # 최대 3년 소급

        params = {
            "corp_code":  corp_code,
            "bgn_de":     bgn_de,
            "end_de":     end_de,
            "pblntf_ty":  "A",       # 정기공시 (사업보고서·분기·반기 포함)
            "page_no":    1,
            "page_count": 20,
        }
        data = await self._request("list.json", params)
        disc_list = data.get("list", [])

        # 사업보고서만 필터 (기재정정·첨부정정 제외), 날짜 내림차순으로 가장 최신 선택
        annual = [
            d for d in disc_list
            if d.get("report_nm", "").strip() == "사업보고서"
        ]
        if not annual:
            # 정확히 일치하지 않으면 포함 관계로 재시도
            annual = [
                d for d in disc_list
                if "사업보고서" in d.get("report_nm", "")
                and "정정" not in d.get("report_nm", "")
            ]
        if not annual:
            return None

        # 접수일 기준 최신 순 정렬
        annual.sort(key=lambda d: d.get("rcept_dt", ""), reverse=True)
        best = annual[0]
        return {
            "rcept_no":  best.get("rcept_no", ""),
            "rcept_dt":  best.get("rcept_dt", ""),
            "report_nm": best.get("report_nm", ""),
        }

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
        reprt_code: str = "11011",
        fs_div: str = "CFS"  # CFS: 연결재무제표, OFS: 별도재무제표
    ) -> Dict:
        """
        재무제표 조회

        Args:
            corp_code: 기업 고유번호
            bsns_year: 사업연도 (YYYY)
            reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
            fs_div: 재무제표 구분 (CFS: 연결, OFS: 별도)

        Returns:
            재무제표 데이터 (출처 포함)
        """
        params = {
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        }

        data = await self._request("fnlttSinglAcntAll.json", params)

        # 연결재무제표 데이터가 없으면 별도재무제표로 fallback
        if (data.get("status") == "013" or not data.get("list")) and fs_div == "CFS":
            params["fs_div"] = "OFS"
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

    async def _get_corp_list(self) -> List[Dict]:
        """
        DART 기업 목록 전체를 로드 (인메모리 캐시, 1시간 유효)
        """
        from datetime import timedelta
        now = datetime.now()

        # 캐시 유효 시 반환
        if (self._corp_list_cache is not None and
                self._corp_list_cache_time is not None and
                now - self._corp_list_cache_time < timedelta(hours=1)):
            return self._corp_list_cache

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/corpCode.xml",
                params={"crtfc_key": self.api_key}
            )
            response.raise_for_status()

        # ZIP 파일 여부 사전 검증 (ZIP magic bytes: PK\x03\x04)
        content = response.content
        if not content[:2] == b'PK':
            try:
                err_data = response.json()
                raise ValueError(f"DART API 오류 응답: status={err_data.get('status')}, message={err_data.get('message')}")
            except (ValueError, Exception) as e:
                if "DART API 오류 응답" in str(e):
                    raise
                raise ValueError(f"DART corpCode.xml이 ZIP이 아닙니다. 응답 앞부분: {content[:200]}")

        # ZIP 압축 해제 및 XML 파싱을 스레드에서 실행 (이벤트 루프 블로킹 방지)
        import asyncio
        import xml.etree.ElementTree as ET

        def _parse_zip_xml(content: bytes) -> List[Dict]:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_filename = next(
                    (name for name in zf.namelist() if name.endswith(".xml")), None
                )
                if not xml_filename:
                    return []
                xml_content = zf.read(xml_filename)

            root = ET.fromstring(xml_content)
            result = []
            for corp in root.findall("list"):
                corp_code = corp.findtext("corp_code", "").strip()
                corp_name = corp.findtext("corp_name", "").strip()
                if not corp_code or not corp_name:
                    continue
                stock_code = (corp.findtext("stock_code") or "").strip()
                modify_date = corp.findtext("modify_date")
                result.append({
                    "corp_code": corp_code,
                    "corp_name": corp_name,
                    "stock_code": stock_code if stock_code else None,
                    "modify_date": modify_date,
                })
            return result

        corps = await asyncio.to_thread(_parse_zip_xml, content)

        self._corp_list_cache = corps
        self._corp_list_cache_time = now
        return corps

    async def search_company(self, company_name: str) -> List[Dict]:
        """
        기업명으로 기업 검색 (캐시된 목록에서 필터링)

        Args:
            company_name: 기업명 또는 종목코드 (부분 일치)

        Returns:
            검색된 기업 목록 (상장사 우선, 최대 20개)
        """
        all_corps = await self._get_corp_list()
        query = company_name.lower().strip()

        matched = []
        for corp in all_corps:
            name_match = query in corp["corp_name"].lower()
            code_match = corp["stock_code"] and query in corp["stock_code"]
            if name_match or code_match:
                matched.append({
                    **corp,
                    "_source": {
                        "provider": "DART 기업 목록",
                        "url": "https://dart.fss.or.kr",
                        "retrieved_at": datetime.now().isoformat()
                    }
                })

        matched.sort(key=lambda x: (x["stock_code"] is None, x["corp_name"]))
        return matched[:20]

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
