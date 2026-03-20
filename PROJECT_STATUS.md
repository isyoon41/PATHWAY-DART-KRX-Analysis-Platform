# PATHWAY DART·KRX 기업분석 플랫폼 - 프로젝트 상태

📅 **마지막 업데이트**: 2026-03-20
🌿 **현재 브랜치**: `main`

---

## ✅ 구현 완료된 기능

### 1. 백엔드 (FastAPI)
**위치**: `/backend`
**포트**: 8000

#### 핵심 모듈
- ✅ **DART API 연동** (`app/services/dart_service.py`)
  - 기업 검색
  - 공시 목록 조회
  - 재무제표 조회

- ✅ **DART 문서 파서** (`app/services/dart_parser.py`)
  - **섹션별 분해**: 사업보고서를 11개 표준 섹션으로 자동 분해
  - **섹션 감지**: 정규식 패턴으로 경계 자동 탐지
  - **AI 최적화**: 섹션당 최대 30K자로 컨텍스트 최적화

  **11개 표준 섹션**:
  1. 회사의 개요
  2. 사업의 내용
  3. 재무에 관한 사항
  4. 경영진단 및 분석의견 (MD&A)
  5. 감사인의 감사의견
  6. 이사회 및 지배구조
  7. 주주에 관한 사항
  8. 임원 및 직원
  9. 계열회사
  10. 이해관계자 거래
  11. 기타 사항

- ✅ **섹션별 특화 분석** (`SectionAnalyzer`)
  - **재무 섹션**: ROA, ROE, 부채비율 자동 계산
  - **사업 섹션**: 15종 리스크 키워드 탐지
  - **감사의견**: 적정/한정/부적정/의견거절 분류
  - **MD&A**: 긍정/부정 신호어 분석 (경영진 어조)

- ✅ **재무제표 XBRL 구조화** (`app/services/financial_parser.py`)
  - DART 평탄 리스트 → 구조화된 분석 데이터
  - income_statement, balance_sheet, cash_flow 분류
  - 재무 비율 자동 계산 (수익성, 안정성, 유동성)
  - 전년 대비 성장률 계산

- ✅ **KRX 데이터 연동** (`app/services/krx_service.py`)

#### API 엔드포인트
- `GET /api/companies/search` - 기업 검색
- `GET /api/companies/{corp_code}/reports` - 공시 목록
- `GET /api/companies/{corp_code}/financials` - 재무제표
- `GET /api/analysis/parse-report/{rcept_no}` - 보고서 섹션 분해
- `GET /health` - 서버 상태 확인

---

### 2. 프론트엔드 (Next.js)
**위치**: `/frontend`
**포트**: 3000

#### 페이지
- ✅ **메인 페이지** (`/`)
  - 기업 검색 기능
  - DART + KRX 통합 검색

- ✅ **기업 상세** (`/company/[id]`)
  - 기업 개요
  - 재무제표 조회
  - 공시 목록

- ✅ **분석 대시보드** (`/analysis`)
  - 섹션별 분해 분석 결과 표시
  - 차트 시각화 준비

---

## 🏗️ 아키텍처

### DART 문서 분석 파이프라인

```
DART HTML (200페이지 사업보고서)
     ↓
[DARTReportParser]
     ↓
섹션별 분해 (11개)
     ├── Ⅰ 회사개요 (30K자)
     ├── Ⅱ 사업내용 → 리스크 키워드 탐지
     ├── Ⅲ 재무      → ROA/ROE/부채비율
     ├── Ⅳ MD&A     → 긍정/부정 신호어
     ├── Ⅴ 감사의견 → 적정/한정/부적정
     └── ...
     ↓
[SectionAnalyzer]
     ↓
섹션별 특화 분석
```

### 재무제표 구조화

```
DART 재무제표 API (평탄 리스트)
     ↓
[structure_financial_data]
     ↓
{
  income_statement: {당기, 전기, 전전기},
  balance_sheet: {당기, 전기},
  cash_flow: {당기, 전기},
  ratios: {수익성, 안정성, 유동성},
  growth: {전년대비 성장률}
}
```

---

## 🚀 서버 실행 방법

### 백엔드
```bash
cd backend
source venv/bin/activate
python main.py
```
→ http://localhost:8000

### 프론트엔드
```bash
cd frontend
npm run dev
```
→ http://localhost:3000

---

## 📦 의존성

### 백엔드
- FastAPI
- httpx (DART API 호출)
- BeautifulSoup4 (HTML 파싱)
- lxml (파서)
- python-dotenv (환경변수)

### 프론트엔드
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Recharts (차트)
- Lucide Icons

---

## 🔑 환경 변수

### `/backend/.env`
```
DART_API_KEY=your_dart_api_key_here
```

---

## 📂 주요 파일 구조

```
PATHWAY-DART-KRX-Analysis-Platform/
├── backend/
│   ├── main.py                           # FastAPI 앱 진입점
│   ├── config.py                         # 설정
│   ├── app/
│   │   ├── routers/
│   │   │   ├── companies.py             # 기업 검색/조회 API
│   │   │   └── analysis.py              # 분석 API
│   │   ├── services/
│   │   │   ├── dart_service.py          # DART API 클라이언트
│   │   │   ├── dart_parser.py           # 📊 섹션별 분해 파서
│   │   │   ├── financial_parser.py      # 📊 XBRL 구조화
│   │   │   └── krx_service.py           # KRX 연동
│   │   └── schemas/
│   │       └── company.py               # Pydantic 스키마
│   └── venv/                             # Python 가상환경
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                 # 메인 페이지
│   │   │   ├── company/[id]/page.tsx    # 기업 상세
│   │   │   └── analysis/page.tsx        # 분석 대시보드
│   │   ├── components/                   # React 컴포넌트
│   │   └── lib/                          # 유틸리티
│   └── node_modules/
│
├── CLAUDE.md                             # 프로젝트 설명
└── PROJECT_STATUS.md                     # 이 파일
```

---

## 🎯 다음 단계 (미구현)

1. **Lovable MVP 분석**
   - Computer Use로 Lovable 프로젝트 화면 캡처
   - 구현된 기능 파악
   - 현재 프로젝트와 비교

2. **프론트엔드 개선**
   - 섹션별 분석 결과 시각화
   - 차트 구현 (Recharts)
   - 리스크 키워드 하이라이트

3. **AI 분석 통합**
   - Claude API로 섹션 요약
   - 섹션별 핵심 지표 텍스트 추출
   - 자연어 질의응답

4. **데이터베이스**
   - PostgreSQL 스키마 설계
   - 분석 결과 저장
   - 캐싱

---

## 📝 참고 사항

- 모든 코드는 `claude/company-analysis-platform-fYhpR` 브랜치에 push됨
- 서버 로그: `/tmp/backend.log`, `/tmp/frontend.log`
- DART API 키 필요 (https://opendart.fss.or.kr)

---

## 🔗 관련 링크

- DART API: https://opendart.fss.or.kr/guide/main.do
- KRX 정보데이터시스템: http://data.krx.co.kr
- Lovable MVP: https://lovable.dev/projects/7939d401-7527-43b2-b561-362bf8257824

---

**이 프로젝트를 claude.ai 웹에서 이어서 작업하려면**:
1. GitHub에서 이 리포지토리 clone
2. Computer Use 활성화
3. 서버 실행 후 Lovable URL 분석
