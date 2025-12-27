import httpx
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup


class KRXService:
    """KRX (한국거래소) 데이터 연동 서비스"""

    def __init__(self):
        self.base_url = "http://data.krx.co.kr"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd"
        }

    async def get_stock_info(self, stock_code: str) -> Dict:
        """
        주식 기본 정보 조회

        Args:
            stock_code: 종목코드

        Returns:
            주식 정보 (출처 포함)
        """
        # KRX API 엔드포인트 (실제 API는 확인 필요)
        url = f"{self.base_url}/comm/bldAttendant/getJsonData.cmd"

        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
            "locale": "ko_KR",
            "isuCd": stock_code
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            # 출처 정보 추가
            data["_source"] = {
                "provider": "KRX (한국거래소)",
                "url": f"http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
                "stock_code": stock_code,
                "retrieved_at": datetime.now().isoformat()
            }

            return data

    async def get_market_data(self, stock_code: str, date: str) -> Dict:
        """
        시장 데이터 조회 (시가, 종가, 거래량 등)

        Args:
            stock_code: 종목코드
            date: 조회 날짜 (YYYYMMDD)

        Returns:
            시장 데이터 (출처 포함)
        """
        url = f"{self.base_url}/comm/bldAttendant/getJsonData.cmd"

        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
            "locale": "ko_KR",
            "trdDd": date,
            "isuCd": stock_code
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            # 출처 정보 추가
            data["_source"] = {
                "provider": "KRX 시장 데이터",
                "date": date,
                "stock_code": stock_code,
                "url": "http://data.krx.co.kr",
                "retrieved_at": datetime.now().isoformat()
            }

            return data

    async def get_listed_companies(self, market: str = "ALL") -> List[Dict]:
        """
        상장 기업 목록 조회

        Args:
            market: 시장 구분 (ALL, KOSPI, KOSDAQ, KONEX)

        Returns:
            상장 기업 목록 (출처 포함)
        """
        url = f"{self.base_url}/comm/bldAttendant/getJsonData.cmd"

        market_code = {
            "ALL": "",
            "KOSPI": "STK",
            "KOSDAQ": "KSQ",
            "KONEX": "KNX"
        }

        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT01901",
            "locale": "ko_KR",
            "mktId": market_code.get(market, "")
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            # 출처 정보 추가
            if isinstance(data, dict) and "OutBlock_1" in data:
                for company in data["OutBlock_1"]:
                    company["_source_url"] = f"http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101"

            return {
                "companies": data.get("OutBlock_1", []) if isinstance(data, dict) else [],
                "_source": {
                    "provider": "KRX 상장 기업 목록",
                    "market": market,
                    "url": "http://data.krx.co.kr",
                    "retrieved_at": datetime.now().isoformat()
                }
            }


# 싱글톤 인스턴스
krx_service = KRXService()
