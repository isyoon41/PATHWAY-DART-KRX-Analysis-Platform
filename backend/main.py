from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from app.routers import companies, analysis

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DART 및 KRX 데이터를 활용한 실시간 기업 분석 플랫폼"
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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
