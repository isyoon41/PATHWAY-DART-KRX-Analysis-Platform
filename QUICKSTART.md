# 빠른 시작 가이드

## DART·KRX 기업분석 플랫폼

### 사전 준비

✅ DART API 키가 설정되었습니다!
- API Key: `41b7f01d3cfef20afb6a064b0ce883bfaa73e6dd`

### 옵션 1: Docker Compose 사용 (권장)

가장 빠르고 쉬운 방법입니다.

```bash
# 1. 환경 변수 설정
export DART_API_KEY=41b7f01d3cfef20afb6a064b0ce883bfaa73e6dd

# 2. 모든 서비스 시작 (PostgreSQL, 백엔드, 프론트엔드)
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f

# 4. 접속
# - 프론트엔드: http://localhost:3000
# - 백엔드 API 문서: http://localhost:8000/docs

# 5. 종료
docker-compose down
```

### 옵션 2: 개별 실행

#### 백엔드 실행

```bash
# 1. 백엔드 디렉토리로 이동
cd backend

# 2. Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. (선택사항) DART API 연결 테스트
python test_dart_connection.py

# 5. 서버 시작
python main.py

# 백엔드 API 문서: http://localhost:8000/docs
```

#### 프론트엔드 실행

```bash
# 1. 새 터미널을 열고 프론트엔드 디렉토리로 이동
cd frontend

# 2. 패키지 설치
npm install

# 3. 개발 서버 시작
npm run dev

# 프론트엔드: http://localhost:3000
```

### 테스트해보기

1. **http://localhost:3000** 접속
2. 검색창에 기업명 입력 (예: "삼성전자", "SK하이닉스", "현대자동차")
3. 검색 결과에서 기업 선택
4. 종합 분석 리포트 확인

### 주요 기능

- ✅ **기업 검색**: 기업명 또는 종목코드로 검색
- ✅ **기업 정보**: 대표이사, 설립일, 주소, 홈페이지 등
- ✅ **최근 공시**: 최근 3개월 공시 내역 (각 공시마다 DART 원문 링크 제공)
- ✅ **출처 표시**: 모든 데이터에 출처, URL, 조회 시각 명시

### API 엔드포인트 예제

백엔드가 실행 중이라면 다음 URL로 직접 API를 테스트할 수 있습니다:

```bash
# 기업 검색
curl "http://localhost:8000/api/companies/search?query=삼성전자"

# 종합 분석 (기업코드 필요)
curl "http://localhost:8000/api/analysis/{corp_code}/comprehensive"
```

또는 브라우저에서:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### 데이터 출처

모든 데이터는 공식 출처에서 실시간으로 수집됩니다:

1. **DART (금융감독원 전자공시시스템)**
   - 기업 정보, 재무제표, 공시 내역
   - https://dart.fss.or.kr

2. **KRX (한국거래소)**
   - 시장 데이터, 주가 정보
   - http://data.krx.co.kr

### 문제 해결

#### 백엔드가 시작되지 않을 때

```bash
# DART API 연결 테스트
cd backend
python test_dart_connection.py

# 로그 확인
python main.py  # 에러 메시지 확인
```

#### 프론트엔드가 백엔드에 연결되지 않을 때

1. `frontend/.env.local` 파일 확인:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. 백엔드가 실행 중인지 확인:
   ```bash
   curl http://localhost:8000/health
   ```

#### Docker 문제

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs backend
docker-compose logs frontend

# 전체 재시작
docker-compose down
docker-compose up --build
```

### 다음 단계

1. **재무제표 분석 추가**: 기업의 재무 건전성 지표 시각화
2. **비교 분석**: 동종 업계 기업들과 비교
3. **알림 기능**: 특정 기업의 새로운 공시 알림
4. **데이터 캐싱**: 자주 조회되는 데이터 캐싱으로 성능 향상

### 기여하기

이슈나 개선사항이 있다면 GitHub에서 Issue를 등록해주세요!

---

**면책 조항**: 본 플랫폼은 정보 제공 목적이며, 투자 자문을 대체할 수 없습니다.
