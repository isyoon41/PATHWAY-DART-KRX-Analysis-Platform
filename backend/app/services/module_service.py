"""
분석 모듈 서비스 — S1~S11 표준 섹션 기반 모듈형 분석

GPT 설계 기준 S1-S11 섹션 정의와 9개 분석 모듈을 구현합니다.
각 모듈은 필요한 섹션만 읽어 집중적인 AI 분석을 수행합니다.

섹션 정의 (S1~S11):
  S1  — 기업 개요 (company_overview)
  S2  — 사업의 내용 (business_content)
  S3  — 사업부문 정보 (business_content 내 세그먼트)
  S4  — 위험요인 (risk_factors / business_content fallback)
  S5  — 주주 현황 (shareholders / DART API)
  S6  — 이사회·임원 (board_governance + executives / DART API)
  S7  — 재무제표 (financial_info + DART XBRL)
  S8  — 재무 주석 (financial_info 내 주석)
  S9  — 자본조달 이벤트 (공시 검색: 유상증자·CB·BW)
  S10 — 잠정·이벤트 공시 (공시 검색: 잠정실적·분기실적)
  S11 — 시장 데이터 (KRX/네이버 금융 API)

9개 분석 모듈:
  comprehensive      — 종합 기업분석
  key_financials     — 핵심 재무지표
  full_financials    — 전체 재무제표
  business_segments  — 사업부문별 실적
  shareholders       — 주주현황
  board_executives   — 이사회/임원 분석
  stock_movement     — 주가 변동 원인
  capital_increase   — 유상증자 분석
  preliminary        — 잠정실적 분석
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, date, timedelta

from config import settings
from app.services.dart_parser import create_parser
from app.services.dart_service import dart_service
from app.services.financial_parser import structure_financial_data
from app.services.krx_service import krx_service
from google import genai
from google.genai import types as genai_types


# ══════════════════════════════════════════════════════════════════════
# S1-S11 섹션 정의
# ══════════════════════════════════════════════════════════════════════

SECTION_DEFINITIONS: Dict[str, Dict] = {
    "S1":  {"dart_code": "company_overview",  "name": "기업 개요",         "char_limit": 8000},
    "S2":  {"dart_code": "business_content",  "name": "사업의 내용",       "char_limit": 20000},
    "S3":  {"dart_code": "business_content",  "name": "사업부문 정보",     "char_limit": 20000},  # S2와 동일 섹션
    "S4":  {"dart_code": "risk_factors",      "name": "위험요인",           "char_limit": 15000,
             "fallback": "business_content"},
    "S5":  {"dart_code": "shareholders",      "name": "주주 현황",         "char_limit": 8000},
    "S6":  {"dart_code": "board_governance",  "name": "이사회·임원",       "char_limit": 8000,
             "also": "executives"},
    "S7":  {"dart_code": "financial_info",    "name": "재무제표",           "char_limit": 15000,
             "also": "audit_opinion"},
    "S8":  {"dart_code": "financial_info",    "name": "재무 주석",         "char_limit": 15000},  # S7과 동일
    "S9":  {"dart_code": None,               "name": "자본조달 이벤트",   "char_limit": 0},   # 공시 검색
    "S10": {"dart_code": None,               "name": "잠정·이벤트 공시",  "char_limit": 0},   # 공시 검색
    "S11": {"dart_code": None,               "name": "시장 데이터",        "char_limit": 0},   # KRX/Naver API
}


# ══════════════════════════════════════════════════════════════════════
# 9개 모듈 정의
# ══════════════════════════════════════════════════════════════════════

MODULES: Dict[str, Dict] = {
    "comprehensive": {
        "id": "comprehensive",
        "name": "종합 기업분석",
        "badge": "CORE",
        "is_core": True,
        "desc": "사업·재무·지배구조·감사의견 전체 통합 분석 (DART 원문 기반)",
        "required_sections": ["S1", "S2", "S7"],
        "optional_sections": ["S4", "S6"],
        "uses_financials": True,
        "uses_governance": True,
        "uses_disclosures": True,
        "uses_market_data": True,
        "disc_keywords": [],
        "max_tokens": 65536,
    },
    "key_financials": {
        "id": "key_financials",
        "name": "핵심 재무지표",
        "badge": "FINANCIALS",
        "is_core": True,
        "desc": "수익성·안정성·성장성 핵심 지표 집중 분석 (XBRL 데이터 기반)",
        "required_sections": ["S7"],
        "optional_sections": ["S1"],
        "uses_financials": True,
        "uses_governance": False,
        "uses_disclosures": False,
        "uses_market_data": False,
        "disc_keywords": [],
        "max_tokens": 32768,
    },
    "full_financials": {
        "id": "full_financials",
        "name": "전체 재무제표",
        "badge": "BALANCE",
        "is_core": False,
        "desc": "재무상태표·손익계산서·현금흐름표 3개년 요약 1표",
        "required_sections": ["S7"],
        "optional_sections": [],
        "uses_financials": True,
        "uses_governance": False,
        "uses_disclosures": False,
        "uses_market_data": False,
        "disc_keywords": [],
        "max_tokens": 32768,
    },
    "business_segments": {
        "id": "business_segments",
        "name": "사업부문별 실적",
        "badge": "BUSINESS",
        "is_core": False,
        "desc": "사업부문별 매출·영업이익·경쟁력 분석 (사업보고서 원문)",
        "required_sections": ["S2", "S3"],
        "optional_sections": ["S1"],
        "uses_financials": True,
        "uses_governance": False,
        "uses_disclosures": False,
        "uses_market_data": False,
        "disc_keywords": [],
        "max_tokens": 32768,
    },
    "shareholders": {
        "id": "shareholders",
        "name": "주주현황",
        "badge": "OWNERSHIP",
        "is_core": False,
        "desc": "주요 주주·지분 구조·지배구조 평가 (DART 공시 기반)",
        "required_sections": ["S5"],
        "optional_sections": ["S6"],
        "uses_financials": False,
        "uses_governance": True,
        "uses_disclosures": False,
        "uses_market_data": False,
        "disc_keywords": [],
        "max_tokens": 16384,
    },
    "board_executives": {
        "id": "board_executives",
        "name": "이사회/임원 분석",
        "badge": "GOVERNANCE",
        "is_core": False,
        "desc": "이사회 구성·임원 현황·보수·내부통제 평가",
        "required_sections": ["S6"],
        "optional_sections": ["S5"],
        "uses_financials": False,
        "uses_governance": True,
        "uses_disclosures": False,
        "uses_market_data": False,
        "disc_keywords": [],
        "max_tokens": 16384,
    },
    "stock_movement": {
        "id": "stock_movement",
        "name": "주가 변동 원인",
        "badge": "MARKET",
        "is_core": True,
        "desc": "주가 변동과 공시·이벤트 상관관계 분석 (KRX+DART 연계)",
        "required_sections": ["S11"],
        "optional_sections": ["S1"],
        "uses_financials": False,
        "uses_governance": False,
        "uses_disclosures": True,
        "uses_market_data": True,
        "disc_keywords": [],
        "max_tokens": 16384,
    },
    "capital_increase": {
        "id": "capital_increase",
        "name": "유상증자 / 메자닌",
        "badge": "CAPITAL",
        "is_core": False,
        "desc": "유상증자·CB·BW 이력 및 주주 희석 리스크 분석",
        "required_sections": ["S9"],
        "optional_sections": [],
        "uses_financials": False,
        "uses_governance": False,
        "uses_disclosures": True,
        "uses_market_data": False,
        "disc_keywords": ["유상증자", "전환사채", "신주인수권부사채", "교환사채", "주주배정", "일반공모", "제3자배정"],
        "max_tokens": 16384,
    },
    "preliminary": {
        "id": "preliminary",
        "name": "잠정실적",
        "badge": "EARNINGS",
        "is_core": False,
        "desc": "분기별 잠정실적 공시 및 어닝 서프라이즈 분석",
        "required_sections": ["S10"],
        "optional_sections": ["S7"],
        "uses_financials": True,
        "uses_governance": False,
        "uses_disclosures": True,
        "uses_market_data": False,
        "disc_keywords": ["잠정실적", "영업실적", "실적공시", "분기실적", "반기실적"],
        "max_tokens": 16384,
    },
}


# ══════════════════════════════════════════════════════════════════════
# 공유 시스템 프롬프트
# ══════════════════════════════════════════════════════════════════════

SHARED_SYSTEM_PROMPT = """당신은 국내 최고 수준의 기업 분석 전문가입니다.
DART(금융감독원 전자공시시스템) 공시 원문과 KRX·네이버 금융 시장 데이터를 기반으로
기관투자자와 전문 애널리스트 수준의 분석 리포트를 작성합니다.

## 핵심 원칙
1. **원문 근거 우선**: 공시 원문에서 직접 확인된 사실만 기술합니다. 원문에 없는 내용은 "확인 불가"로 표시합니다.
2. **수치 명시**: 모든 재무 수치에 연도·단위(억원·천원·%)를 명시합니다.
3. **출처 투명성**: 데이터 출처를 "(DART 공시)", "(XBRL 재무제표)", "(KRX)" 형식으로 표시합니다.
4. **구체성**: 해당 기업의 구체적 내용에 집중하며 업종 일반론은 최소화합니다.
5. **완결성**: 요청된 모든 섹션을 빠짐없이 완결하여 작성합니다. 절대 중간에 끊지 않습니다.

## 출력 형식 규칙
- 헤딩 계층: ## 대섹션 → ### 중섹션 → #### 소섹션
- 수치 비교표: 반드시 마크다운 표(| 헤더 | 헤더 |) 형식 사용
- 굵은 강조: **중요 수치·키워드**만 선택적으로 사용 (과용 금지)
- 데이터 부재 시: "(데이터 없음)" 명시 후 분석 가능한 항목만 서술
- 섹션 간 빈 줄: 각 ## 섹션 앞뒤에 빈 줄 한 줄 유지
- 리스트: `-` 불릿 또는 `1.` 숫자 리스트 사용, 들여쓰기 불가"""


# ══════════════════════════════════════════════════════════════════════
# 9개 모듈 프롬프트 템플릿
# ══════════════════════════════════════════════════════════════════════

PROMPTS: Dict[str, str] = {

# ── 1. 종합 기업분석 ────────────────────────────────────────────────
"comprehensive": """\
## {corp_name} 종합 기업분석 리포트
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART 공시 원문 및 재무 데이터를 바탕으로 투자자 관점의 종합 기업분석 리포트를 작성하세요.

{data_context}

---

### 작성 지침 (6개 섹션)

#### 1. 기업 개요 및 사업 구조  ← S1·S2 기반
- 핵심 사업 영역, 주요 제품·서비스, 매출 구성 비중
- 시장 지위 및 주요 경쟁사 (공시 원문 기재 내용)

#### 2. 재무 성과 분석 (3개년 추이)  ← S7 기반
| 항목 | {year1}년 | {year2}년 | {year3}년 | YoY증감 |
|---|---|---|---|---|
| 매출액 (억원) | | | | |
| 영업이익 (억원) | | | | |
| 당기순이익 (억원) | | | | |
| 영업이익률 (%) | | | | |
| ROE (%) | | | | |
| 부채비율 (%) | | | | |

#### 3. 경영진단 및 전략 방향  ← S2·MD&A 기반
- 경영진이 강조한 핵심 사업 성과 및 변동 원인
- 향후 투자·사업 계획 (공시 기재 내용)

#### 4. 감사의견 및 내부통제  ← S7 기반
- 감사의견 종류: **적정/한정/부적정/의견거절** 중 해당
- 핵심감사사항(KAM) 요약
- 계속기업 불확실성 여부

#### 5. 지배구조 및 주주 현황  ← S5·S6 기반
- 최대주주 및 특수관계인 지분 구조
- 이사회 구성 (사내/사외이사 비율)

#### 6. 종합 평가 및 투자 시사점
- 핵심 강점 3가지 / 핵심 리스크 3가지
- 모니터링 필수 이벤트 (향후 6~12개월)
""",

# ── 2. 핵심 재무지표 ────────────────────────────────────────────────
"key_financials": """\
## {corp_name} 핵심 재무지표 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART XBRL 재무 데이터를 바탕으로 핵심 재무지표 분석 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 손익 지표 요약 (단위: 억원)
| 항목 | {year1}년 | {year2}년 | {year3}년 | CAGR |
|---|---|---|---|---|
| 매출액 | | | | |
| 매출총이익 | | | | |
| 영업이익 | | | | |
| EBITDA | | | | |
| 당기순이익 | | | | |

#### 2. 수익성 지표
| 비율 | {year1}년 | {year2}년 | {year3}년 | 추세 |
|---|---|---|---|---|
| 매출총이익률 (%) | | | | |
| 영업이익률 (%) | | | | |
| 순이익률 (%) | | | | |
| ROE (%) | | | | |
| ROA (%) | | | | |

#### 3. 안정성 지표
| 비율 | {year1}년 | {year2}년 | {year3}년 | 평가 |
|---|---|---|---|---|
| 부채비율 (%) | | | | |
| 유동비율 (%) | | | | |
| 이자보상배율 (배) | | | | |

#### 4. 성장성 지표
- 매출 YoY 성장률, 영업이익 YoY 성장률, 순이익 YoY 성장률 (표)

#### 5. 현금창출 능력
- 영업활동 현금흐름 vs 당기순이익 비교
- FCF(잉여현금흐름) 추이

#### 6. 재무 건전성 종합 평가
- 수익성 / 안정성 / 성장성 / 현금창출력 각 항목 평가 (상/중/하)
- 개선·악화 주요 원인 분석
""",

# ── 3. 전체 재무제표 ────────────────────────────────────────────────
"full_financials": """\
## {corp_name} 전체 재무제표 요약
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART XBRL 재무 데이터를 바탕으로 재무제표 요약 리포트를 1개의 통합 표로 정리하세요.

{data_context}

---

### 작성 지침

#### 재무상태표 핵심 항목 (단위: 억원)
| 항목 | {year1}년말 | {year2}년말 | {year3}년말 |
|---|---|---|---|
| **[자산]** | | | |
| 유동자산 | | | |
| 비유동자산 | | | |
| **총자산** | | | |
| **[부채]** | | | |
| 유동부채 | | | |
| 비유동부채 | | | |
| **총부채** | | | |
| **[자본]** | | | |
| 자본금 | | | |
| 이익잉여금 | | | |
| **총자본** | | | |

#### 손익계산서 핵심 항목 (단위: 억원)
| 항목 | {year1}년 | {year2}년 | {year3}년 | YoY |
|---|---|---|---|---|
| 매출액 | | | | |
| 매출원가 | | | | |
| 매출총이익 | | | | |
| 판관비 | | | | |
| **영업이익** | | | | |
| 영업외손익 | | | | |
| 법인세차감전이익 | | | | |
| **당기순이익** | | | | |

#### 현금흐름표 요약 (단위: 억원)
| 구분 | {year1}년 | {year2}년 | {year3}년 |
|---|---|---|---|
| 영업활동 CF | | | |
| 투자활동 CF | | | |
| 재무활동 CF | | | |
| 기말현금 | | | |

#### 핵심 재무비율 요약
- 영업이익률, ROE, 부채비율, 유동비율 (표로 정리)

#### 주요 특이사항
- 재무제표상 눈에 띄는 변동 항목, 감사의견 요약
""",

# ── 4. 사업부문별 실적 ──────────────────────────────────────────────
"business_segments": """\
## {corp_name} 사업부문별 실적 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 사업보고서 원문(S2: 사업의 내용)을 분석하여 사업부문별 실적 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 사업 부문 구조
- 부문별 사업 내용, 주요 제품·서비스 (원문 기반)
- 부문별 매출 비중 (원문 기재 수치 우선)

#### 2. 부문별 실적 요약 (표)
| 사업부문 | {year1}년 매출 | {year2}년 매출 | {year3}년 매출 | YoY | 비중 |
|---|---|---|---|---|---|

원문에 부문별 수치가 없으면 "(원문 수치 없음 — 정성 분석)"으로 표시하고 정성적 분석 진행

#### 3. 핵심 사업 경쟁력
- 시장 점유율 (원문 기재 내용)
- 기술 우위 및 진입장벽
- 주요 고객사 및 매출 집중도

#### 4. 사업별 리스크 및 기회
- 각 부문의 성장 동력과 위협 요인 (원문 근거)

#### 5. 부문 전략 방향
- 경영진 언급 사업 확장·축소 계획 (MD&A 기반)
""",

# ── 5. 주주현황 ─────────────────────────────────────────────────────
"shareholders": """\
## {corp_name} 주주현황 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART 공시 주주 데이터를 바탕으로 주주현황 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 주요 주주 현황 (표)
| 주주명 | 보유주식수 | 지분율(%) | 관계 | 비고 |
|---|---|---|---|---|

#### 2. 지배구조 지분 분석
- 최대주주 + 특수관계인 합산 지분율
- 우호 지분율 vs 외부 지분율
- 기관·외국인·개인 보유 비중 (공시 기재 시)

#### 3. 자사주 현황
- 자사주 보유 규모 및 비율 (공시 기재 내용)

#### 4. 최근 지분 변동 이슈
- 최근 공개매수, 블록딜, 지분 변동 공시

#### 5. 지배구조 평가
- **오너 리스크** 수준 (지분 집중도 기반)
- **소수주주 보호** 제도 현황
- 지배구조 개선 여지 또는 리스크 요인
""",

# ── 6. 이사회/임원 분석 ─────────────────────────────────────────────
"board_executives": """\
## {corp_name} 이사회·임원 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART 공시 이사회·임원 데이터를 바탕으로 지배구조 분석 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 이사회 구성
| 성명 | 직책 | 구분(사내/사외) | 주요 경력 | 임기 |
|---|---|---|---|---|

- 사외이사 비율, 이사회 다양성 평가

#### 2. 주요 임원 현황
| 성명 | 직위 | 담당 업무 | 주요 경력 |
|---|---|---|---|

#### 3. 임원 보수
- 등기이사 평균 보수 (공시 기재 내용)
- 성과 연동 보수 구조 (있을 경우)

#### 4. 내부통제 및 감사위원회
- 감사위원회 구성 및 독립성
- 내부감사 체계 현황

#### 5. 지배구조 종합 평가
- 이사회 독립성 평가 (상/중/하)
- 개선 필요 사항 또는 강점 요인
""",

# ── 7. 주가 변동 원인 ───────────────────────────────────────────────
"stock_movement": """\
## {corp_name} 주가 변동 원인 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 시장 데이터(S11)와 공시 목록을 바탕으로 주가 변동 원인 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 주가 현황 요약 (KRX/네이버 금융)
- 현재가, 52주 고/저, 시가총액
- YTD 등락률, 최근 3·6·12개월 수익률

#### 2. 주가 변동 원인 타임라인
| 시기 | 주가 변동 | 트리거 이벤트 | 근거 공시 |
|---|---|---|---|

공시 목록에서 주가에 영향을 줄 만한 이벤트(실적, 증자, 계약, 인사, 제재 등)를 매핑하세요.

#### 3. 공시별 시장 반응 분석
- 각 주요 공시의 발표 타이밍과 예상 주가 영향 방향

#### 4. 밸류에이션 참고 지표
- PER, PBR (데이터 있을 경우)
- 시가총액 vs 순자산 비교

#### 5. 주가 모니터링 포인트
- 향후 주가에 영향을 줄 수 있는 예정 이벤트 (분기 실적, 증자, 계약 만기 등)
- 단기·중기 리스크 요인
""",

# ── 8. 유상증자/메자닌 ──────────────────────────────────────────────
"capital_increase": """\
## {corp_name} 유상증자·메자닌 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 DART 공시 자료(유상증자·CB·BW 관련)를 바탕으로 자본조달 분석 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 유상증자 이력 (최근 5년)
| 공시일 | 조달방법 | 발행금액(억원) | 발행가액 | 목적 | 자금사용 |
|---|---|---|---|---|---|

#### 2. 메자닌(CB·BW·EB) 현황
| 종류 | 발행일 | 발행금액(억원) | 전환(행사)가액 | 전환청구기간 | 잔액 |
|---|---|---|---|---|---|

#### 3. 주식 희석 리스크 분석
- 잠재 희석 주식수 (CB·BW 전환 가정 시)
- 현재 발행주식 대비 희석 비율 (%)
- 대량 전환 시 주가 영향 시뮬레이션

#### 4. 자금 사용 적정성 평가
- 공시 기재 사용 목적 vs 실제 집행 현황
- 재무 건전성에 미친 영향

#### 5. 향후 자금조달 리스크
- 만기 도래 CB·BW 스케줄
- 추가 증자 가능성 및 조건
""",

# ── 9. 잠정실적 ─────────────────────────────────────────────────────
"preliminary": """\
## {corp_name} 잠정실적 분석
**분석 기준**: {period} | **생성일**: {today}

---

아래 분기 재무 및 잠정실적 공시 데이터를 바탕으로 실적 분석 리포트를 작성하세요.

{data_context}

---

### 작성 지침

#### 1. 최근 분기별 실적 추이
| 분기 | 매출액(억원) | 영업이익(억원) | 당기순이익(억원) | 영업이익률(%) |
|---|---|---|---|---|

#### 2. YoY / QoQ 성장률 분석
- 분기별 전년 동기 대비(YoY), 직전 분기 대비(QoQ) 변동률
- 변동 원인 (공시 기재 내용 기반)

#### 3. 어닝 서프라이즈/쇼크 여부
- 잠정실적 공시 내용 요약
- 시장 예상 대비 초과/미달 여부 (공시 기재 시)

#### 4. 실적 개선·악화 핵심 요인
- 매출 변동 원인 (수량·가격·환율 효과)
- 원가·판관비 구조 변화

#### 5. 향후 실적 전망
- 경영진 가이던스 (공시 기재 내용)
- 다음 분기 주요 변수 및 실적 방향성
""",
}


# ══════════════════════════════════════════════════════════════════════
# 데이터 수집 헬퍼
# ══════════════════════════════════════════════════════════════════════

async def _fetch_sections_from_report(
    corp_code: str,
    disc_list: List[Dict],
    section_ids: List[str],   # ["S1", "S2", "S4", ...]
) -> Dict[str, Dict]:
    """
    공시 목록에서 사업보고서 HTML 다운로드 → 지정 섹션만 추출
    Returns: { "S1": {"title":..., "content":..., ...}, "S2": {...}, ... }
    """
    dart_codes_needed: List[str] = []
    for sid in section_ids:
        sdef = SECTION_DEFINITIONS.get(sid, {})
        dc = sdef.get("dart_code")
        if dc and dc not in dart_codes_needed:
            dart_codes_needed.append(dc)
        # "also" 필드 (ex: S7 → audit_opinion도 필요)
        also = sdef.get("also")
        if also and also not in dart_codes_needed:
            dart_codes_needed.append(also)
        # "fallback" 필드
        fb = sdef.get("fallback")
        if fb and fb not in dart_codes_needed:
            dart_codes_needed.append(fb)

    if not dart_codes_needed:
        return {}

    # 최근 사업보고서 찾기
    annual = [
        d for d in disc_list
        if "사업보고서" in d.get("report_nm", "")
        and "정정" not in d.get("report_nm", "")
    ]
    if not annual:
        return {}

    rcept_no = annual[0].get("rcept_no", "")
    rcept_dt = annual[0].get("rcept_dt", "")
    if not rcept_no:
        return {}

    try:
        parser = create_parser(settings.dart_api_key)
        doc_files = await asyncio.wait_for(parser.fetch_report_index(rcept_no), timeout=25.0)
        if not doc_files:
            return {}

        html = await asyncio.wait_for(
            parser.fetch_document_html(rcept_no, doc_files[0].get("url", "")),
            timeout=30.0,
        )
        parsed = parser.parse_sections(html, rcept_no, {
            "corp_code": corp_code,
            "report_type": "사업보고서",
            "report_date": rcept_dt,
        })

        # dart_code → parsed 섹션 맵
        dart_map: Dict[str, Dict] = {}
        for dc in dart_codes_needed:
            if dc in parsed.sections:
                sec = parsed.sections[dc]
                dart_map[dc] = {
                    "title": sec.title,
                    "content": sec.content,
                    "char_count": sec.char_count,
                    "rcept_no": rcept_no,
                    "rcept_dt": rcept_dt,
                }

        # S-ID → 결과 맵
        result: Dict[str, Dict] = {}
        for sid in section_ids:
            sdef = SECTION_DEFINITIONS.get(sid, {})
            dc   = sdef.get("dart_code")
            char_limit = sdef.get("char_limit", 10000)

            if dc and dc in dart_map:
                data = dict(dart_map[dc])
                data["content"] = data["content"][:char_limit]
                result[sid] = data
                continue

            # fallback 처리 (예: S4가 없으면 S2 사용)
            fb = sdef.get("fallback")
            if fb and fb in dart_map:
                data = dict(dart_map[fb])
                data["content"] = data["content"][:char_limit]
                data["title"] += " (위험요인 섹션 별도 미존재 — 사업의 내용에서 발췌)"
                result[sid] = data

        # S6: executives 추가
        if "S6" in section_ids and "executives" in dart_map and "S6" in result:
            exec_content = dart_map["executives"].get("content", "")[:4000]
            result["S6"]["content"] += f"\n\n[임원 현황]\n{exec_content}"

        return result

    except Exception:
        return {}


async def _fetch_disc_by_keywords(
    corp_code: str,
    keywords: List[str],
    years: int = 4,
) -> List[Dict]:
    """특정 키워드 포함 공시 검색"""
    if not keywords:
        return []
    end_dt   = date.today().strftime("%Y%m%d")
    start_dt = (date.today() - timedelta(days=365 * years)).strftime("%Y%m%d")
    try:
        result    = await dart_service.get_disclosure_list(
            corp_code=corp_code, bgn_de=start_dt, end_de=end_dt, page_count=100,
        )
        disc_list = result.get("list", [])
        return [d for d in disc_list if any(kw in d.get("report_nm", "") for kw in keywords)]
    except Exception:
        return []


def _fmt_section(sid: str, data: Dict) -> str:
    char_count = data.get("char_count", 0)
    content    = data.get("content", "").strip()
    title      = data.get("title", sid)
    rcept_dt   = data.get("rcept_dt", "")
    return (
        f"━━━ [{sid}] {title} ━━━\n"
        f"(접수일: {rcept_dt} | 원문 {char_count:,}자 중 {len(content):,}자 발췌)\n"
        f"{'─' * 60}\n"
        f"{content}"
    )


def _fmt_financials(financials: Dict[str, Any], years: List[str]) -> str:
    lines = []
    for yr in years:
        f = financials.get(yr, {})
        if not f:
            continue
        inc = f.get("income_statement", {})
        bal = f.get("balance_sheet", {})
        rat = f.get("ratios", {})
        cur_i = inc.get("current", {})
        cur_b = bal.get("current", {})
        lines.append(
            f"[{yr}년 재무 — XBRL]\n"
            f"  매출액:          {cur_i.get('revenue','N/A'):>15,} 천원\n"
            f"  영업이익:        {cur_i.get('operating_profit','N/A'):>15,} 천원\n"
            f"  당기순이익:      {cur_i.get('net_income','N/A'):>15,} 천원\n"
            f"  총자산:          {cur_b.get('total_assets','N/A'):>15,} 천원\n"
            f"  자기자본:        {cur_b.get('total_equity','N/A'):>15,} 천원\n"
            f"  영업이익률:      {rat.get('operating_margin_pct','N/A'):>8}%\n"
            f"  ROE:             {rat.get('roe_pct','N/A'):>8}%  |  "
            f"ROA: {rat.get('roa_pct','N/A'):>8}%\n"
            f"  부채비율:        {rat.get('debt_ratio_pct','N/A'):>8}%  |  "
            f"유동비율: {rat.get('current_ratio_pct','N/A'):>8}%"
        )
    return "\n\n".join(lines) if lines else "[XBRL 재무 데이터 없음]"


def _fmt_disc_list(disc_list: List[Dict], limit: int = 40) -> str:
    lines = [
        f"  [{d.get('rcept_dt','')}] {d.get('report_nm','')} (제출: {d.get('flr_nm','')})"
        for d in disc_list[:limit]
    ]
    return "\n".join(lines) if lines else "[공시 없음]"


# ══════════════════════════════════════════════════════════════════════
# 모듈 분석 서비스
# ══════════════════════════════════════════════════════════════════════

class ModuleAnalysisService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model  = settings.gemini_model

    def _call_gemini(self, prompt: str, max_tokens: int) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                system_instruction=SHARED_SYSTEM_PROMPT,
                max_output_tokens=max_tokens,
                temperature=0.25,
            ),
        )
        return response.text

    async def run_module(
        self,
        module_id: str,
        corp_code: str,
        company_info: Dict,
        end_year: str,
        years: List[str],
        financials_by_year: Dict[str, Any],
        financials_quarterly: Dict[str, Any],
        governance_data: Dict[str, Any],
        disc_list: List[Dict],
        market_data: Dict,
    ) -> Dict[str, Any]:
        """단일 모듈 분석 실행 (S1-S11 섹션 기반)"""

        module = MODULES.get(module_id)
        if not module:
            return {"error": f"알 수 없는 모듈: {module_id}"}

        corp_name  = company_info.get("corp_name", corp_code)
        period_str = f"{years[-1]}~{years[0]}년"
        today_str  = datetime.now().strftime("%Y년 %m월 %d일")

        # ── 1. 공시 원문 섹션 수집 ─────────────────────────────────────
        all_section_ids = list(dict.fromkeys(
            module["required_sections"] + module["optional_sections"]
        ))
        # S9·S10·S11은 dart_parser가 아닌 별도 소스
        parser_section_ids = [
            s for s in all_section_ids
            if SECTION_DEFINITIONS.get(s, {}).get("dart_code") is not None
        ]

        fetched_sections: Dict[str, Dict] = {}
        if parser_section_ids and disc_list:
            fetched_sections = await _fetch_sections_from_report(
                corp_code, disc_list, parser_section_ids
            )

        # ── 2. 모듈별 특화 공시 수집 (S9·S10) ─────────────────────────
        specialized_discs: List[Dict] = []
        if module.get("disc_keywords"):
            specialized_discs = await _fetch_disc_by_keywords(
                corp_code, module["disc_keywords"]
            )

        # ── 3. 컨텍스트 블록 조립 ─────────────────────────────────────
        ctx: List[str] = []

        # 기업 기본정보 (항상 포함)
        market = (
            company_info.get("market_name")
            or {"Y": "KOSPI(유가증권시장)", "K": "KOSDAQ", "N": "KONEX", "E": "비상장"}
            .get(company_info.get("corp_cls", ""), "N/A")
        )
        ctx.append(
            f"[기업 기본정보 — DART]\n"
            f"  기업명:    {corp_name}\n"
            f"  종목코드:  {company_info.get('stock_code', 'N/A')}\n"
            f"  상장시장:  {market}\n"
            f"  대표이사:  {company_info.get('ceo_nm', 'N/A')}\n"
            f"  설립일:    {company_info.get('est_dt', 'N/A')}\n"
            f"  업종:      {company_info.get('induty_code', 'N/A')}\n"
            f"  소재지:    {company_info.get('adres', 'N/A')}"
        )

        # 공시 원문 섹션 (S1~S8)
        for sid in parser_section_ids:
            if sid in fetched_sections:
                ctx.append(_fmt_section(sid, fetched_sections[sid]))
            else:
                sname = SECTION_DEFINITIONS.get(sid, {}).get("name", sid)
                ctx.append(f"━━━ [{sid}] {sname} ━━━\n[원문 파싱 실패 또는 해당 섹션 없음]")

        # 재무 데이터 (XBRL)
        if module.get("uses_financials"):
            ctx.append(
                f"[S7 — 재무 데이터 (DART XBRL)]\n{_fmt_financials(financials_by_year, years)}"
            )

        # 분기 재무 (preliminary 모듈)
        if module_id == "preliminary" and financials_quarterly:
            ctx.append(
                f"[분기 재무]\n{json.dumps(financials_quarterly, ensure_ascii=False, indent=2)[:3000]}"
            )

        # 주주·임원 데이터 (DART API)
        if module.get("uses_governance"):
            sh = governance_data.get("major_shareholders")
            ex = governance_data.get("executives")
            if sh:
                ctx.append(
                    f"[S5 — 주요 주주 현황 (DART API)]\n"
                    f"{json.dumps(sh, ensure_ascii=False, indent=2)[:4000]}"
                )
            if ex:
                ctx.append(
                    f"[S6 — 임원 현황 (DART API)]\n"
                    f"{json.dumps(ex, ensure_ascii=False, indent=2)[:3000]}"
                )

        # 일반 공시 목록
        if module.get("uses_disclosures") and disc_list:
            ctx.append(f"[최근 공시 목록]\n{_fmt_disc_list(disc_list, 40)}")

        # 모듈 특화 공시 (S9·S10)
        if specialized_discs:
            label = {
                "capital_increase": "S9 — 유상증자·CB·BW 관련 공시",
                "preliminary":      "S10 — 잠정실적 관련 공시",
            }.get(module_id, "특화 공시")
            ctx.append(
                f"[{label}]\n"
                + "\n".join(
                    f"  [{d.get('rcept_dt','')}] {d.get('report_nm','')} "
                    f"(제출: {d.get('flr_nm','')})"
                    for d in specialized_discs
                )
            )

        # 주가 데이터 (S11 — KRX/Naver)
        if module.get("uses_market_data") and market_data and "error" not in market_data:
            ctx.append(
                f"[S11 — 시장 데이터 (KRX/네이버 금융)]\n"
                f"{json.dumps(market_data, ensure_ascii=False, indent=2)[:2000]}"
            )

        # ── 4. 프롬프트 조립 & Gemini 호출 ───────────────────────────
        data_context = "\n\n".join(ctx)
        prompt_tmpl  = PROMPTS.get(module_id, PROMPTS["comprehensive"])

        prompt = prompt_tmpl.format(
            corp_name=corp_name,
            period=period_str,
            today=today_str,
            data_context=data_context,
            year1=years[0] if len(years) > 0 else "N/A",
            year2=years[1] if len(years) > 1 else "N/A",
            year3=years[2] if len(years) > 2 else "N/A",
        )

        report_text = self._call_gemini(prompt, module["max_tokens"])

        return {
            "module_id":    module_id,
            "module_name":  module["name"],
            "report":       report_text,
            "generated_at": datetime.now().isoformat(),
            "model":        self.model,
            "corp_name":    corp_name,
            "period":       period_str,
        }


# 싱글톤
module_service = ModuleAnalysisService()
