from pydantic_settings import BaseSettings
from typing import List


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
    database_url: str

    # CORS
    allowed_origins: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
