"""
DART 재무제표 XBRL 구조화 파서

DART API가 반환하는 재무제표 데이터는 계정과목 코드(account_id) 기반의
평탄화된 리스트입니다. 이를 재무분석에 적합한 계층 구조로 변환합니다.

DART 재무제표 API 응답 예시:
  {
    "account_nm": "매출액",
    "account_id": "ifrs-full_Revenue",
    "thstrm_amount": "302,231,360",   ← 당기
    "frmtrm_amount": "279,604,799",   ← 전기
    "bfefrmtrm_amount": "243,771,415" ← 전전기
  }
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


# ──────────────────────────────────────────────────────────────────
# 재무제표 계정 분류 맵핑
# IFRS 기준 DART account_id → 분석 카테고리
# ──────────────────────────────────────────────────────────────────
ACCOUNT_MAPPING = {
    # 손익계산서 (IS)
    "revenue": {
        "names": ["매출액", "수익(매출액)", "영업수익"],
        "ids":   ["ifrs-full_Revenue", "ifrs-full_GrossProfit"],
        "statement": "IS",
    },
    "cost_of_sales": {
        "names": ["매출원가"],
        "ids":   ["ifrs-full_CostOfSales"],
        "statement": "IS",
    },
    "gross_profit": {
        "names": ["매출총이익"],
        "ids":   ["ifrs-full_GrossProfit"],
        "statement": "IS",
    },
    "operating_profit": {
        "names": ["영업이익", "영업손익"],
        "ids":   ["dart_OperatingIncomeLoss"],
        "statement": "IS",
    },
    "ebitda_proxy": {
        "names": ["감가상각비"],
        "ids":   ["ifrs-full_DepreciationAndAmortisationExpense"],
        "statement": "IS",
    },
    "net_income": {
        "names": ["당기순이익", "당기순손익"],
        "ids":   ["ifrs-full_ProfitLoss"],
        "statement": "IS",
    },

    # 재무상태표 (BS)
    "total_assets": {
        "names": ["자산총계"],
        "ids":   ["ifrs-full_Assets"],
        "statement": "BS",
    },
    "current_assets": {
        "names": ["유동자산"],
        "ids":   ["ifrs-full_CurrentAssets"],
        "statement": "BS",
    },
    "non_current_assets": {
        "names": ["비유동자산"],
        "ids":   ["ifrs-full_NoncurrentAssets"],
        "statement": "BS",
    },
    "total_liabilities": {
        "names": ["부채총계"],
        "ids":   ["ifrs-full_Liabilities"],
        "statement": "BS",
    },
    "current_liabilities": {
        "names": ["유동부채"],
        "ids":   ["ifrs-full_CurrentLiabilities"],
        "statement": "BS",
    },
    "total_equity": {
        "names": ["자본총계"],
        "ids":   ["ifrs-full_Equity"],
        "statement": "BS",
    },

    # 현금흐름표 (CF)
    "operating_cashflow": {
        "names": ["영업활동현금흐름", "영업활동으로인한현금흐름"],
        "ids":   ["ifrs-full_CashFlowsFromUsedInOperatingActivities"],
        "statement": "CF",
    },
    "investing_cashflow": {
        "names": ["투자활동현금흐름"],
        "ids":   ["ifrs-full_CashFlowsFromUsedInInvestingActivities"],
        "statement": "CF",
    },
    "financing_cashflow": {
        "names": ["재무활동현금흐름"],
        "ids":   ["ifrs-full_CashFlowsFromUsedInFinancingActivities"],
        "statement": "CF",
    },
}


def parse_amount(value: str) -> Optional[int]:
    """DART 금액 문자열 → 정수 변환 (단위: 백만원)"""
    if not value or value.strip() in ("-", "", "N/A"):
        return None
    clean = value.replace(",", "").replace(" ", "").strip()
    try:
        # DART는 통상 백만원 단위로 제공
        return int(clean)
    except ValueError:
        return None


def find_account_value(
    dart_list: List[Dict],
    account_key: str,
    period: str = "current"  # "current" | "previous" | "two_years_ago"
) -> Optional[int]:
    """
    DART 재무제표 리스트에서 특정 계정의 금액 추출

    Args:
        dart_list: DART API fnlttSinglAcntAll 응답의 list
        account_key: ACCOUNT_MAPPING의 키
        period: 조회 기간 (당기/전기/전전기)
    """
    mapping = ACCOUNT_MAPPING.get(account_key)
    if not mapping:
        return None

    period_field = {
        "current":       "thstrm_amount",
        "previous":      "frmtrm_amount",
        "two_years_ago": "bfefrmtrm_amount",
    }.get(period, "thstrm_amount")

    for item in dart_list:
        account_id = item.get("account_id", "")
        account_nm = item.get("account_nm", "")

        # ID 기반 매칭 우선, 없으면 계정명 기반
        id_match  = any(aid in account_id for aid in mapping["ids"])
        name_match = account_nm in mapping["names"]

        if id_match or name_match:
            return parse_amount(item.get(period_field, ""))

    return None


def structure_financial_data(dart_response: Dict) -> Dict:
    """
    DART fnlttSinglAcntAll API 응답을 분석용 구조로 변환

    Returns:
        {
          "periods": {"current": "2023", "previous": "2022"},
          "income_statement": {...},
          "balance_sheet": {...},
          "cash_flow": {...},
          "ratios": {...},
          "source": {...}
        }
    """
    items: List[Dict] = dart_response.get("list", [])
    if not items:
        return {"error": "재무 데이터 없음", "list": []}

    # 기간 정보 추출 (첫 번째 항목에서)
    first = items[0]
    periods = {
        "current":       first.get("thstrm_nm", "당기"),
        "previous":      first.get("frmtrm_nm", "전기"),
        "two_years_ago": first.get("bfefrmtrm_nm", "전전기"),
    }

    def get(key: str, period: str = "current") -> Optional[int]:
        return find_account_value(items, key, period)

    # ── 손익계산서
    income_statement = {}
    for period in ["current", "previous", "two_years_ago"]:
        income_statement[period] = {
            "revenue":          get("revenue", period),
            "cost_of_sales":    get("cost_of_sales", period),
            "gross_profit":     get("gross_profit", period),
            "operating_profit": get("operating_profit", period),
            "net_income":       get("net_income", period),
        }

    # ── 재무상태표
    balance_sheet = {}
    for period in ["current", "previous"]:
        balance_sheet[period] = {
            "total_assets":        get("total_assets", period),
            "current_assets":      get("current_assets", period),
            "non_current_assets":  get("non_current_assets", period),
            "total_liabilities":   get("total_liabilities", period),
            "current_liabilities": get("current_liabilities", period),
            "total_equity":        get("total_equity", period),
        }

    # ── 현금흐름표
    cash_flow = {}
    for period in ["current", "previous"]:
        cash_flow[period] = {
            "operating":  get("operating_cashflow", period),
            "investing":  get("investing_cashflow", period),
            "financing":  get("financing_cashflow", period),
        }

    # ── 재무 비율 계산 (당기 기준)
    ratios = _calculate_ratios(income_statement["current"], balance_sheet["current"])

    # ── 전년 대비 성장률
    growth = _calculate_growth(income_statement)

    return {
        "periods": periods,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "ratios": ratios,
        "growth": growth,
        "_source": {
            "provider": "DART 재무제표 (XBRL 기반 구조화)",
            "api_endpoint": "fnlttSinglAcntAll",
            "note": "금액 단위: 백만원",
            "retrieved_at": datetime.now().isoformat(),
        }
    }


def _calculate_ratios(is_data: Dict, bs_data: Dict) -> Dict:
    """핵심 재무비율 계산"""
    ratios = {}

    rev  = is_data.get("revenue")
    op   = is_data.get("operating_profit")
    net  = is_data.get("net_income")
    gp   = is_data.get("gross_profit")
    ta   = bs_data.get("total_assets")
    tl   = bs_data.get("total_liabilities")
    te   = bs_data.get("total_equity")
    ca   = bs_data.get("current_assets")
    cl   = bs_data.get("current_liabilities")

    # 수익성
    if rev and gp:
        ratios["gross_margin_pct"]     = _safe_div(gp, rev, pct=True)
    if rev and op:
        ratios["operating_margin_pct"] = _safe_div(op, rev, pct=True)
    if rev and net:
        ratios["net_margin_pct"]       = _safe_div(net, rev, pct=True)

    # 안정성
    if te and tl:
        ratios["debt_ratio_pct"]       = _safe_div(tl, te, pct=True)
    if ta and tl:
        ratios["liability_to_assets_pct"] = _safe_div(tl, ta, pct=True)

    # 유동성
    if ca and cl:
        ratios["current_ratio"]        = _safe_div(ca, cl)

    # 수익성 (자산/자본 기준)
    if net and ta:
        ratios["roa_pct"]              = _safe_div(net, ta, pct=True)
    if net and te:
        ratios["roe_pct"]              = _safe_div(net, te, pct=True)

    return ratios


def _calculate_growth(income_statement: Dict) -> Dict:
    """전년 대비 성장률 계산"""
    curr = income_statement.get("current", {})
    prev = income_statement.get("previous", {})
    growth = {}

    for key in ["revenue", "operating_profit", "net_income"]:
        c, p = curr.get(key), prev.get(key)
        if c is not None and p and p != 0:
            growth[f"{key}_yoy_pct"] = round((c - p) / abs(p) * 100, 2)

    return growth


def _safe_div(a: Optional[int], b: Optional[int], pct: bool = False) -> Optional[float]:
    """안전 나눗셈 (0 또는 None 처리)"""
    if a is None or b is None or b == 0:
        return None
    result = a / b
    return round(result * 100 if pct else result, 2)
