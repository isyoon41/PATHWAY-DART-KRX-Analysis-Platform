"""
KRX (한국거래소) Open API 연동 서비스

KRX Open API는 2단계 인증 방식을 사용합니다:
  1단계: OTP 발급 (GenerateOTP) → auth 토큰 획득
  2단계: 데이터 조회 (GetJSONData) → auth 토큰으로 실제 데이터 요청
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from config import settings


KRX_OTP_URL  = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"
KRX_DATA_URL = "https://openapi.krx.co.kr/contents/SBT/GetJSONData.jspx"


class KRXService:
    """KRX Open API 연동 서비스"""

    def __init__(self):
        self.api_key = settings.krx_api_key

    async def _get_otp(self, bld: str, params: Dict) -> str:
        """OTP 토큰 발급"""
        payload = {"bld": bld, "name": "otp", **params}
        headers = {"AUTH_KEY": self.api_key}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(KRX_OTP_URL, data=payload, headers=headers)
            resp.raise_for_status()
            return resp.text.strip()

    async def _fetch(self, bld: str, params: Dict) -> Dict:
        """OTP 발급 후 데이터 조회"""
        otp = await self._get_otp(bld, params)

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(KRX_DATA_URL, data={"code": otp})
            resp.raise_for_status()
            return resp.json()

    async def get_stock_price(self, stock_code: str, date: Optional[str] = None) -> Dict:
        """
        주식 현재가 및 기본 시장 정보 조회

        Args:
            stock_code: 종목코드 (예: 005930)
            date: 조회 기준일 (YYYYMMDD, 없으면 최근 영업일)
        """
        if not self.api_key:
            return {"error": "KRX API 키가 설정되지 않았습니다.", "stock_code": stock_code}

        query_date = date or datetime.now().strftime("%Y%m%d")

        try:
            data = await self._fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT01501",
                params={"isuCd": stock_code, "trdDd": query_date}
            )

            data["_source"] = {
                "provider": "KRX (한국거래소) Open API",
                "stock_code": stock_code,
                "query_date": query_date,
                "url": "https://openapi.krx.co.kr",
                "retrieved_at": datetime.now().isoformat(),
            }
            return data

        except Exception as e:
            return {
                "error": str(e),
                "stock_code": stock_code,
                "_source": {"provider": "KRX Open API", "retrieved_at": datetime.now().isoformat()}
            }

    async def get_stock_price_list(
        self,
        market: str = "ALL",
        date: Optional[str] = None
    ) -> Dict:
        """
        시장 전체 주가 목록 조회

        Args:
            market: STK(코스피) / KSQ(코스닥) / KNX(코넥스) / ALL(전체)
            date: 조회 기준일 (YYYYMMDD)
        """
        if not self.api_key:
            return {"error": "KRX API 키가 설정되지 않았습니다."}

        query_date = date or datetime.now().strftime("%Y%m%d")

        market_map = {"ALL": "", "KOSPI": "STK", "KOSDAQ": "KSQ", "KONEX": "KNX"}
        mkt_id = market_map.get(market, "")

        try:
            data = await self._fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT01501",
                params={"mktId": mkt_id, "trdDd": query_date}
            )

            data["_source"] = {
                "provider": "KRX Open API - 주가 목록",
                "market": market,
                "query_date": query_date,
                "retrieved_at": datetime.now().isoformat(),
            }
            return data

        except Exception as e:
            return {"error": str(e)}

    async def get_stock_code(self, company_name: str) -> List[Dict]:
        """
        기업명으로 종목코드 검색

        Args:
            company_name: 기업명 (부분 일치)
        """
        if not self.api_key:
            return []

        try:
            data = await self._fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT01901",
                params={}
            )

            results = []
            items = data.get("OutBlock_1", []) if isinstance(data, dict) else []
            for item in items:
                name = item.get("ISU_ABBRV", "") or item.get("ISU_NM", "")
                if company_name in name:
                    results.append({
                        "stock_code": item.get("ISU_SRT_CD", ""),
                        "company_name": name,
                        "market": item.get("MKT_NM", ""),
                        "_source": {
                            "provider": "KRX Open API",
                            "retrieved_at": datetime.now().isoformat()
                        }
                    })
            return results

        except Exception as e:
            return []

    async def get_holidays(self, year: Optional[str] = None) -> Dict:
        """휴장일 조회"""
        if not self.api_key:
            return {"error": "KRX API 키가 설정되지 않았습니다."}

        target_year = year or datetime.now().strftime("%Y")

        try:
            data = await self._fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT03901",
                params={"calnd_dd": target_year}
            )
            data["_source"] = {
                "provider": "KRX Open API - 휴장일",
                "year": target_year,
                "retrieved_at": datetime.now().isoformat(),
            }
            return data
        except Exception as e:
            return {"error": str(e)}


# 싱글톤 인스턴스
krx_service = KRXService()
