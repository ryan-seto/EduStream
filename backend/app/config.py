from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Get the directory where this config file lives, then go up to backend/
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://edustream:edustream_dev@localhost:5432/edustream"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # AI APIs
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Paths
    output_dir: str = "./output"
    temp_dir: str = "./temp"

    # CORS
    frontend_url: str = "http://localhost:5173"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Allowed email addresses (comma-separated) - leave empty to allow all
    allowed_emails: str = ""

    # Twitter/X API
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = ""
    s3_prefix: str = "diagrams/"
    cloudfront_domain: str = ""
    sqs_queue_url: str = ""
    sqs_publish_interval_minutes: int = 120

    @property
    def use_s3(self) -> bool:
        return bool(self.s3_bucket_name and self.aws_access_key_id)

    @property
    def use_sqs(self) -> bool:
        return bool(self.sqs_queue_url and self.aws_access_key_id)

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
