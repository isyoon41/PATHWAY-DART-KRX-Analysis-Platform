"""
주가/시장 데이터 서비스 — 4단계 폴백 체인

현재가 우선순위:
  1️⃣  KRX Open API         (공식, 2단계 OTP 인증 — IP 화이트리스트 등록 후 활성화)
  2️⃣  네이버 금융 API      (비공식, 현재 주 사용 중 — KOSPI/KOSDAQ 구분 포함)
  3️⃣  FinanceDataReader    (한국 주식 특화 패키지 — 네이버 실패 시 폴백)
  4️⃣  Yahoo Finance        (yfinance — 최종 폴백)

일자별 OHLCV 우선순위:
  1️⃣  FinanceDataReader    (주력 — 한국 주식 특화, OHLCV 정확)
  2️⃣  Yahoo Finance        (yfinance — FDR 실패 시 폴백)

상장시장 구분(KOSPI/KOSDAQ)은 네이버 API의 stockExchangeType.name 필드를 사용.
KRX API IP 등록 완료 후에는 1️⃣ 이 자동으로 우선 사용됩니다.
"""
import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from config import settings


# ── KRX Open API 엔드포인트 ───────────────────────────────────────────────
KRX_OTP_URL  = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"
KRX_DATA_URL = "https://openapi.krx.co.kr/contents/SBT/GetJSONData.jspx"

# ── 네이버 금융 비공식 API ────────────────────────────────────────────────
NAVER_STOCK_BASIC_URL = "https://m.stock.naver.com/api/stock/{code}/basic"
NAVER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 네이버 exchange code → 한국어 시장명 변환
NAVER_EXCHANGE_MAP = {
    "KS":  "KOSPI (유가증권시장)",
    "KQ":  "KOSDAQ (코스닥시장)",
    "KN":  "KONEX (코넥스시장)",
    "NX":  "KONEX (코넥스시장)",
}


class KRXService:
    """주가·시장 데이터 서비스 (KRX → 네이버 → Yahoo 폴백)"""

    def __init__(self):
        self.api_key = settings.krx_api_key

    # ────────────────────────────────────────────────────────────────────
    # 1️⃣  KRX Open API (공식)
    # ────────────────────────────────────────────────────────────────────
    async def _krx_get_otp(self, bld: str, params: Dict) -> str:
        payload = {"bld": bld, "name": "otp", **params}
        headers = {"AUTH_KEY": self.api_key}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(KRX_OTP_URL, data=payload, headers=headers)
            resp.raise_for_status()
            return resp.text.strip()

    async def _krx_fetch(self, bld: str, params: Dict) -> Dict:
        otp = await self._krx_get_otp(bld, params)
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(KRX_DATA_URL, data={"code": otp})
            resp.raise_for_status()
            return resp.json()

    # ────────────────────────────────────────────────────────────────────
    # 2️⃣  네이버 금융 비공식 API (현재 주 사용)
    # ────────────────────────────────────────────────────────────────────
    async def _fetch_naver_stock(self, stock_code: str) -> Dict:
        """
        네이버 모바일 증권 API로 종목 기본 정보 조회.
        KOSPI/KOSDAQ 시장 구분 포함 → 상장시장 N/A 문제 해결.
        """
        url = NAVER_STOCK_BASIC_URL.format(code=stock_code)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=NAVER_HEADERS)
            resp.raise_for_status()
            d = resp.json()

        exchange     = d.get("stockExchangeType", {}) or {}
        exch_code    = exchange.get("code", "")          # "KS" / "KQ" / "KN"
        market_name  = NAVER_EXCHANGE_MAP.get(
            exch_code, exchange.get("nameEng", "")
        )

        return {
            "stock_code":   stock_code,
            "company_name": d.get("stockName", ""),
            "current_price": d.get("closePrice", "N/A"),
            "change":        d.get("compareToPreviousClosePrice", "N/A"),
            "change_pct":    d.get("fluctuationsRatio", "N/A"),
            "market_cap":    d.get("marketValue") or "N/A",
            "volume":        d.get("accumulatedTradingVolume") or "N/A",
            "market":        market_name,          # "KOSPI (유가증권시장)" 등
            "market_code":   exch_code,            # "KS" / "KQ"
            "listed":        True,                 # 네이버에 있으면 상장 기업
            "_source": {
                "provider":     "Naver Finance (비공식 API)",
                "url":          url,
                "retrieved_at": datetime.now().isoformat(),
            },
        }

    # ────────────────────────────────────────────────────────────────────
    # 3️⃣  FinanceDataReader (FDR) — 네이버 실패 시 폴백
    # ────────────────────────────────────────────────────────────────────
    async def _fetch_fdr_stock(self, stock_code: str) -> Dict:
        """
        FinanceDataReader로 현재가 조회.
        장중에는 Close 컬럼에 실시간 종가가 들어 있음.
        """
        loop = asyncio.get_event_loop()

        def _sync_fetch():
            try:
                import FinanceDataReader as fdr
            except ImportError:
                return None
            try:
                df = fdr.DataReader(stock_code)
                if df is None or df.empty:
                    return None
                latest = df.iloc[-1]
                price = latest.get("Close") or latest.get("close")
                if not price:
                    return None
                return {
                    "stock_code":    stock_code,
                    "company_name":  "",
                    "current_price": f"{int(price):,}",
                    "change":        "N/A",
                    "change_pct":    "N/A",
                    "market_cap":    "N/A",
                    "volume":        f"{int(latest.get('Volume', 0) or 0):,}",
                    "market":        "N/A",
                    "market_code":   "N/A",
                    "listed":        True,
                    "_source": {
                        "provider":     "FinanceDataReader",
                        "retrieved_at": datetime.now().isoformat(),
                    },
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(executor, _sync_fetch)
        return result or {}

    # ────────────────────────────────────────────────────────────────────
    # 4️⃣  Yahoo Finance (yfinance) — 최종 폴백
    # ────────────────────────────────────────────────────────────────────
    async def _fetch_yahoo_stock(self, stock_code: str) -> Dict:
        """
        yfinance 라이브러리로 종목 정보 조회.
        한국 주식: {code}.KS (KOSPI) 또는 {code}.KQ (KOSDAQ) 시도.
        동기 라이브러리이므로 ThreadPoolExecutor에서 실행.
        """
        loop = asyncio.get_event_loop()

        def _sync_fetch():
            try:
                import yfinance as yf
            except ImportError:
                return None

            for suffix, market in [(".KS", "KOSPI (유가증권시장)"),
                                    (".KQ", "KOSDAQ (코스닥시장)")]:
                try:
                    ticker = yf.Ticker(f"{stock_code}{suffix}")
                    info   = ticker.info or {}
                    price  = info.get("currentPrice") or info.get("previousClose")
                    if not price:
                        continue

                    mkt_cap = info.get("marketCap")
                    return {
                        "stock_code":   stock_code,
                        "company_name": info.get("longName", ""),
                        "current_price": f"{price:,.0f}",
                        "change":       "N/A",
                        "change_pct":   "N/A",
                        "market_cap":   f"{mkt_cap:,}" if mkt_cap else "N/A",
                        "volume":       str(info.get("volume", "N/A")),
                        "52w_high":     f"{info.get('fiftyTwoWeekHigh', 0):,.0f}",
                        "52w_low":      f"{info.get('fiftyTwoWeekLow',  0):,.0f}",
                        "market":       market,
                        "market_code":  suffix.lstrip("."),
                        "listed":       True,
                        "_source": {
                            "provider":     f"Yahoo Finance (yfinance · {stock_code}{suffix})",
                            "retrieved_at": datetime.now().isoformat(),
                        },
                    }
                except Exception:
                    continue
            return None

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(executor, _sync_fetch)
        return result or {}

    # ────────────────────────────────────────────────────────────────────
    # 공개 메서드 — 폴백 체인 적용
    # ────────────────────────────────────────────────────────────────────
    async def get_stock_price(self, stock_code: str, date: Optional[str] = None) -> Dict:
        """
        주식 현재가 및 시장 정보 조회 (KRX → 네이버 → Yahoo 폴백).

        Args:
            stock_code: 종목코드 (예: 005930)
            date: 조회 기준일 (YYYYMMDD) — KRX API 전용, 다른 소스는 최신값 반환
        """
        # 1️⃣ KRX Open API
        if self.api_key:
            try:
                query_date = date or datetime.now().strftime("%Y%m%d")
                data = await self._krx_fetch(
                    bld="dbms/MDC/STAT/standard/MDCSTAT01501",
                    params={"isuCd": stock_code, "trdDd": query_date},
                )
                data["_source"] = {
                    "provider":     "KRX (한국거래소) Open API",
                    "stock_code":   stock_code,
                    "query_date":   query_date,
                    "retrieved_at": datetime.now().isoformat(),
                }
                return data
            except Exception:
                pass  # KRX 실패 → 네이버로 폴백

        # 2️⃣ 네이버 금융
        try:
            return await self._fetch_naver_stock(stock_code)
        except Exception:
            pass  # 네이버 실패 → FDR로 폴백

        # 3️⃣ FinanceDataReader
        try:
            result = await self._fetch_fdr_stock(stock_code)
            if result and "error" not in result:
                return result
        except Exception:
            pass  # FDR 실패 → Yahoo로 폴백

        # 4️⃣ Yahoo Finance
        try:
            result = await self._fetch_yahoo_stock(stock_code)
            if result:
                return result
        except Exception:
            pass

        # 모든 소스 실패
        return {
            "error":      "모든 주가 데이터 소스 실패 (KRX 403 / Naver / FDR / Yahoo)",
            "stock_code": stock_code,
            "_source":    {"provider": "없음", "retrieved_at": datetime.now().isoformat()},
        }

    async def get_stock_info(self, stock_code: str) -> Dict:
        """
        기업 종목 정보 조회 — companies.py에서 상장시장 판별에 사용.
        get_stock_price()와 동일한 폴백 체인 사용.
        """
        return await self.get_stock_price(stock_code)

    async def get_stock_history(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """
        일자별 OHLCV 데이터 조회 — FDR 주력, Yahoo Finance 폴백.

        Args:
            stock_code: 종목코드 (예: 005930)
            start_date: 시작일 (YYYYMMDD 또는 YYYY-MM-DD, 기본값: 1년 전)
            end_date:   종료일 (YYYYMMDD 또는 YYYY-MM-DD, 기본값: 오늘)
        """
        loop = asyncio.get_event_loop()

        def _normalize(d: Optional[str]) -> Optional[str]:
            if not d:
                return None
            d = d.strip()
            if len(d) == 8 and d.isdigit():
                return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            return d

        start = _normalize(start_date) or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end   = _normalize(end_date)   or datetime.now().strftime("%Y-%m-%d")

        def _to_records(df) -> Optional[list]:
            if df is None or df.empty:
                return None
            df = df.reset_index()
            records = []
            for _, row in df.iterrows():
                date_val = row.get("Date") or row.get("date") or row.get("Datetime")
                if hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val)[:10]
                records.append({
                    "date":   date_str,
                    "open":   float(row.get("Open",   0) or 0),
                    "high":   float(row.get("High",   0) or 0),
                    "low":    float(row.get("Low",    0) or 0),
                    "close":  float(row.get("Close",  0) or 0),
                    "volume": int(row.get("Volume",   0) or 0),
                })
            return records if records else None

        # 1️⃣ FinanceDataReader (주력)
        def _sync_fdr():
            try:
                import FinanceDataReader as fdr
                df = fdr.DataReader(stock_code, start, end)
                return _to_records(df)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=1) as executor:
            records = await loop.run_in_executor(executor, _sync_fdr)

        if records:
            return {
                "stock_code": stock_code,
                "start_date": start,
                "end_date":   end,
                "records":    records,
                "count":      len(records),
                "_source": {
                    "provider":     "FinanceDataReader",
                    "retrieved_at": datetime.now().isoformat(),
                },
            }

        # 2️⃣ Yahoo Finance 폴백
        def _sync_yahoo():
            try:
                import yfinance as yf
            except ImportError:
                return None, None
            for suffix, market in [(".KS", "KOSPI"), (".KQ", "KOSDAQ")]:
                try:
                    ticker = yf.Ticker(f"{stock_code}{suffix}")
                    df = ticker.history(start=start, end=end)
                    recs = _to_records(df)
                    if recs:
                        return recs, f"Yahoo Finance (yfinance · {stock_code}{suffix})"
                except Exception:
                    continue
            return None, None

        with ThreadPoolExecutor(max_workers=1) as executor:
            records, provider = await loop.run_in_executor(executor, _sync_yahoo)

        if records:
            return {
                "stock_code": stock_code,
                "start_date": start,
                "end_date":   end,
                "records":    records,
                "count":      len(records),
                "_source": {
                    "provider":     provider,
                    "retrieved_at": datetime.now().isoformat(),
                },
            }

        return {
            "error":      "일자별 주가 데이터 조회 실패 (FDR / Yahoo Finance)",
            "stock_code": stock_code,
            "_source":    {"provider": "없음", "retrieved_at": datetime.now().isoformat()},
        }

    # ────────────────────────────────────────────────────────────────────
    # KRX 전용 메서드 (IP 등록 후 활성화)
    # ────────────────────────────────────────────────────────────────────
    async def get_stock_price_list(
        self,
        market: str = "ALL",
        date: Optional[str] = None,
    ) -> Dict:
        """시장 전체 주가 목록 (KRX 전용 — 현재 403)"""
        if not self.api_key:
            return {"error": "KRX API 키가 설정되지 않았습니다."}
        query_date = date or datetime.now().strftime("%Y%m%d")
        market_map = {"ALL": "", "KOSPI": "STK", "KOSDAQ": "KSQ", "KONEX": "KNX"}
        try:
            data = await self._krx_fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT01501",
                params={"mktId": market_map.get(market, ""), "trdDd": query_date},
            )
            data["_source"] = {
                "provider":     "KRX Open API - 주가 목록",
                "market":       market,
                "query_date":   query_date,
                "retrieved_at": datetime.now().isoformat(),
            }
            return data
        except Exception as e:
            return {"error": str(e)}

    async def get_stock_code(self, company_name: str) -> List[Dict]:
        """기업명으로 종목코드 검색 (KRX 전용 — 현재 403)"""
        if not self.api_key:
            return []
        try:
            data  = await self._krx_fetch(bld="dbms/MDC/STAT/standard/MDCSTAT01901", params={})
            items = data.get("OutBlock_1", []) if isinstance(data, dict) else []
            return [
                {
                    "stock_code":   item.get("ISU_SRT_CD", ""),
                    "company_name": item.get("ISU_ABBRV", "") or item.get("ISU_NM", ""),
                    "market":       item.get("MKT_NM", ""),
                    "_source":      {"provider": "KRX Open API", "retrieved_at": datetime.now().isoformat()},
                }
                for item in items
                if company_name in (item.get("ISU_ABBRV", "") or item.get("ISU_NM", ""))
            ]
        except Exception:
            return []

    async def get_holidays(self, year: Optional[str] = None) -> Dict:
        """휴장일 조회 (KRX 전용 — 현재 403)"""
        if not self.api_key:
            return {"error": "KRX API 키가 설정되지 않았습니다."}
        target_year = year or datetime.now().strftime("%Y")
        try:
            data = await self._krx_fetch(
                bld="dbms/MDC/STAT/standard/MDCSTAT03901",
                params={"calnd_dd": target_year},
            )
            data["_source"] = {
                "provider":     "KRX Open API - 휴장일",
                "year":         target_year,
                "retrieved_at": datetime.now().isoformat(),
            }
            return data
        except Exception as e:
            return {"error": str(e)}


# 싱글톤 인스턴스
krx_service = KRXService()
