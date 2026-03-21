from pydantic_settings import BaseSettings
from typing import List
from pydantic import field_validator


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 설정
    app_name: str = "DART·KRX 기업분석 플랫폼"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # DART API
    dart_api_key: str
    dart_base_url: str = "https://opendart.fss.or.kr/api"

    # KRX API
    krx_api_key: str = ""
    krx_base_url: str = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"

    # Anthropic (Claude) — 선택적
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Google Gemini
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-preview-04-17"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_allowed_origins(self) -> List[str]:
        """CORS 허용 origins를 리스트로 반환"""
        return [origin.strip() for origin in self.allowed_origins.split(',')]


settings = Settings()
