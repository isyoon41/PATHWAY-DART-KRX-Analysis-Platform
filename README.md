# DART·KRX 기업분석 플랫폼

## 개요

DART(금융감독원 전자공시시스템)와 KRX(한국거래소) 데이터를 활용하여 실시간 기업 분석 리포트를 생성하는 웹 플랫폼입니다.

## 주요 기능

### 1. 실시간 기업 분석
- DART 공시 데이터를 기반으로 종합 기업분석 리포트 생성
- 재무제표, 공시 내역, 시장 데이터를 통합하여 제공
- 최신 정보를 실시간으로 수집 및 분석

### 2. 근거 기반 분석
- **모든 데이터에 출처와 근거 명시**
- 각 정보마다 데이터 제공처, URL, 조회 시각 표시
- 신뢰성 있는 공식 데이터 출처만 사용

### 3. 사용자 친화적 인터페이스
- 직관적인 검색 기능 (기업명, 종목코드)
- 시각화된 데이터 표현
- 반응형 디자인 (모바일, 태블릿, PC 지원)

## 기술 스택

### 백엔드
- **Python 3.11+**
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **SQLAlchemy**: ORM
- **PostgreSQL**: 데이터베이스
- **httpx**: 비동기 HTTP 클라이언트
- **BeautifulSoup4**: 웹 스크래핑

### 프론트엔드
- **Next.js 14**: React 기반 프레임워크 (App Router)
- **TypeScript**: 타입 안정성
- **TailwindCSS**: 유틸리티 기반 CSS 프레임워크
- **Axios**: HTTP 클라이언트
- **Lucide React**: 아이콘 라이브러리

## 프로젝트 구조

```
.
├── backend/                # 백엔드 (FastAPI)
│   ├── app/
│   │   ├── routers/       # API 엔드포인트
│   │   ├── services/      # 비즈니스 로직 (DART, KRX 연동)
│   │   ├── models/        # 데이터베이스 모델
│   │   └── schemas/       # Pydantic 스키마
│   ├── main.py           # FastAPI 앱 진입점
│   ├── config.py         # 설정 파일
│   └── requirements.txt  # Python 패키지
│
├── frontend/              # 프론트엔드 (Next.js)
│   ├── app/              # Next.js App Router
│   ├── components/       # React 컴포넌트
│   ├── lib/              # 유틸리티 함수
│   └── types/            # TypeScript 타입
│
└── README.md
```

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- DART API 키 (https://opendart.fss.or.kr/ 에서 발급)

### 백엔드 설정

1. 백엔드 디렉토리로 이동
```bash
cd backend
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 패키지 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 다음 항목들을 설정하세요:
# - DART_API_KEY: DART API 키
# - DATABASE_URL: PostgreSQL 연결 문자열
```

5. 서버 실행
```bash
python main.py
# 또는
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

백엔드 API 문서: http://localhost:8000/docs

### 프론트엔드 설정

1. 프론트엔드 디렉토리로 이동
```bash
cd frontend
```

2. 패키지 설치
```bash
npm install
```

3. 환경 변수 설정
```bash
cp .env.local.example .env.local
# .env.local 파일에서 API URL 확인
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. 개발 서버 실행
```bash
npm run dev
```

프론트엔드: http://localhost:3000

## API 엔드포인트

### 기업 정보

- `GET /api/companies/search?query={기업명}` - 기업 검색
- `GET /api/companies/{corp_code}` - 기업 기본 정보
- `GET /api/companies/{corp_code}/disclosures` - 공시 목록
- `GET /api/companies/{corp_code}/financial` - 재무제표

### 분석 리포트

- `GET /api/analysis/{corp_code}/comprehensive` - 종합 분석 리포트
- `GET /api/analysis/{corp_code}/summary` - 분석 요약

## 데이터 출처

모든 데이터는 다음의 공식 출처에서 수집됩니다:

1. **DART (금융감독원 전자공시시스템)**
   - URL: https://dart.fss.or.kr
   - 데이터: 기업 정보, 재무제표, 공시 내역
   - API 문서: https://opendart.fss.or.kr/guide/main.do

2. **KRX (한국거래소)**
   - URL: http://data.krx.co.kr
   - 데이터: 시장 데이터, 주가 정보, 상장 기업 목록

## 주요 컴포넌트

### SourceBadge
모든 데이터에 출처 정보를 표시하는 컴포넌트입니다.
- 데이터 제공자
- 출처 URL
- 조회 시각
- 원본 데이터 링크

### CompanySearch
기업 검색 기능을 제공하는 컴포넌트입니다.
- 기업명 또는 종목코드로 검색
- 검색 결과 목록 표시
- 각 결과에 출처 정보 포함

### CompanyAnalysis
종합 기업 분석 리포트를 표시하는 컴포넌트입니다.
- 기업 기본 정보
- 최근 공시 내역
- 데이터 출처 요약

## 개발 가이드

### 새로운 데이터 소스 추가

1. `backend/app/services/`에 새로운 서비스 파일 생성
2. 데이터 수집 로직 구현
3. 모든 응답에 `_source` 필드 추가 (출처 정보)
4. `backend/app/routers/`에 새로운 엔드포인트 추가
5. 프론트엔드에서 API 호출 및 UI 구현

### 출처 정보 규칙

모든 데이터는 반드시 다음 형식의 출처 정보를 포함해야 합니다:

```python
{
    "_source": {
        "provider": "데이터 제공자명",
        "url": "출처 URL",
        "retrieved_at": "조회 시각 (ISO 8601)",
        "additional_info": {...}  # 선택사항
    }
}
```

## 라이선스

본 프로젝트는 교육 및 정보 제공 목적으로 개발되었습니다.

## 면책 조항

본 플랫폼은 투자 자문이 아닌 정보 제공 목적으로 운영됩니다.
투자 결정은 사용자 본인의 책임이며, 본 플랫폼은 투자 손실에 대한 책임을 지지 않습니다.

## 기여

이슈 및 풀 리퀘스트를 환영합니다!

## 문의

기술 지원이 필요하시면 이슈를 등록해 주세요.
