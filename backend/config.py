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

    # 데이터베이스
    database_url: str = "postgresql://postgres:postgres@localhost:5432/company_analysis"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_allowed_origins(self) -> List[str]:
        """CORS 허용 origins를 리스트로 반환"""
        return [origin.strip() for origin in self.allowed_origins.split(',')]


settings = Settings()
