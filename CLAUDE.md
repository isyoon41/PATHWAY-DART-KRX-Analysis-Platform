# Weekend Work Allowance Analysis Platform

DART API를 활용한 주말근무수당 분석 플랫폼

## 프로젝트 구조

- **Backend**: FastAPI (Python) - 포트 8000
- **Frontend**: Next.js - 포트 3000
- **Database**: PostgreSQL (선택적)

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
2. **재무제표 분석**: 주말근무수당 관련 데이터 추출
3. **시각화 대시보드**: 차트와 테이블로 데이터 표시

## 미리보기

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
