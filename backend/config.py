from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    app_name: str = "DART·KRX 기업분석 플랫폼"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # DART API
    dart_api_key: str
    dart_base_url: str = "https://opendart.fss.or.kr/api"

    # KRX API
    krx_api_key: str = ""
    krx_base_url: str = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"

    # Google Gemini
    google_api_key: str = ""
    # 일반 모듈 (8개): 안정 모델, 무료 1,500 RPD
    gemini_model: str = "gemini-2.0-flash"
    # 투자심화 분석 전용: 고품질 모델, 하루 몇 번 사용
    gemini_model_meta: str = "gemini-2.5-flash-preview-04-17"

    # CORS — 쉼표 구분으로 여러 origin 허용
    # 배포: ALLOWED_ORIGINS="https://pathwaypartners-dart-analysis-platf.vercel.app"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # .env에 정의된 미사용 키 무시

    def get_allowed_origins(self) -> List[str]:
        """CORS 허용 origins를 리스트로 반환"""
        return [origin.strip() for origin in self.allowed_origins.split(',') if origin.strip()]


settings = Settings()
