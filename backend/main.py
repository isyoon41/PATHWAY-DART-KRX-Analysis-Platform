import os
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

# .env를 pydantic_settings가 읽기 전에 환경변수로 직접 로드
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from app.routers import companies, analysis
from app.services import job_service

# ── 로깅 설정 ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pathway")


# ── 백그라운드 작업 정리 ──────────────────────────────────────────────
async def _periodic_job_cleanup():
    """완료된 오래된 작업을 주기적으로 정리 (메모리 누수 방지)"""
    while True:
        await asyncio.sleep(3600)  # 1시간마다
        try:
            deleted = job_service.cleanup_old_jobs(hours=24)
            if deleted:
                logger.info("작업 정리: %d건 삭제됨", deleted)
        except Exception:
            logger.warning("작업 정리 중 오류", exc_info=True)


# ── Lifespan (앱 시작/종료 이벤트) ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 기동 시 백그라운드 태스크 시작, 종료 시 정리"""
    logger.info("PATHWAY API 서버 시작 (v%s)", settings.app_version)
    cleanup_task = asyncio.create_task(_periodic_job_cleanup())
    yield
    cleanup_task.cancel()
    logger.info("PATHWAY API 서버 종료")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DART 및 KRX 데이터를 활용한 실시간 기업 분석 플랫폼",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(companies.router, prefix="/api/companies", tags=["기업 정보"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["기업 분석"])


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "DART·KRX 기업분석 플랫폼 API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    from app.services import cache_service
    return {
        "status": "healthy",
        "cache": cache_service.get_stats(),
        "jobs": len(job_service.list_jobs(limit=100)),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False  # reload=True 시 포트 충돌 발생
    )
