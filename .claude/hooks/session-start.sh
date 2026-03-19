#!/bin/bash
set -euo pipefail

# 웹 환경에서만 실행
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

# ── 1. DART API 키 환경변수 설정 ─────────────────────────────────
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export DART_API_KEY=41b7f01d3cfef20afb6a064b0ce883bfaa73e6dd" >> "$CLAUDE_ENV_FILE"
fi

# ── 2. 백엔드 Python 의존성 설치 ─────────────────────────────────
cd "$CLAUDE_PROJECT_DIR/backend"

python3 -m venv venv
source venv/bin/activate
pip install --quiet -r requirements.txt

# .env 파일 생성 (없으면)
if [ ! -f .env ]; then
  cat > .env << 'ENVEOF'
DART_API_KEY=41b7f01d3cfef20afb6a064b0ce883bfaa73e6dd
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/company_analysis
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ENVEOF
fi

# 백엔드 서버 시작 (백그라운드)
nohup python main.py > /tmp/backend.log 2>&1 &

# ── 3. 프론트엔드 Node 의존성 설치 ───────────────────────────────
cd "$CLAUDE_PROJECT_DIR/frontend"

npm install

# 프론트엔드 서버 시작 (백그라운드, 포트 3000)
nohup npm run dev > /tmp/frontend.log 2>&1 &

# ── 4. 서버 기동 대기 ────────────────────────────────────────────
echo "서버 기동 대기 중..."
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1 && \
     curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ 백엔드(8000) + 프론트엔드(3000) 모두 기동 완료"
    exit 0
  fi
  sleep 2
done

echo "⚠️  서버 기동 확인 타임아웃 (로그: /tmp/backend.log, /tmp/frontend.log)"
