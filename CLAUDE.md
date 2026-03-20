# PATHWAY DART·KRX 기업분석 플랫폼

DART(금융감독원 전자공시시스템)와 KRX(한국거래소) API를 활용한 기업분석 플랫폼

## 프로젝트 구조

- **Backend**: FastAPI (Python) - 포트 8000
- **Frontend**: Next.js - 포트 3000

## 개발 서버

### 백엔드
```bash
cd backend
source venv/bin/activate
python main.py
```
http://localhost:8000

### 프론트엔드
```bash
cd frontend
npm run dev
```
http://localhost:3000

## 주요 기능

1. **기업 검색**: DART API를 통한 기업 정보 조회
2. **공시 분석**: 사업보고서 11개 섹션 자동 분해 및 특화 분석
3. **재무제표**: XBRL 구조화, 재무비율 자동 계산
4. **시각화 대시보드**: 차트와 테이블로 데이터 표시

## 미리보기

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
