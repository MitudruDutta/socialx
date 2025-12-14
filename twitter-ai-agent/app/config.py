from pydantic_settings import BaseSettings
from typing import List, Optional, Any
from functools import lru_cache
from pydantic import BeforeValidator, field_validator
from typing_extensions import Annotated
import urllib.parse

def parse_comma_separated_list(v: Any) -> List[str]:
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Security - Fail fast if missing
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    
    API_VERSION: str = "v1"
    
    # Database - Fail fast if missing
    DATABASE_URL: str
    
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    TWITTER_USERNAME: str = ""
    TWITTER_PASSWORD: str = ""
    TWITTER_EMAIL: str = ""
    
    PROXY_HOST: str = ""
    PROXY_PORT: int = 22225
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""
    
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo-0125"
    OPENAI_TEMPERATURE: float = 0.7
    GOOGLE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    IMAGE_MODEL: str = "nano-banana"
    IMAGE_USE_LOCAL: bool = True
    IMAGE_DEVICE: str = "cuda"
    IMAGE_OUTPUT_FORMAT: str = "png"
    IMAGE_MAX_SIZE: int = 1024
    
    SENTRY_DSN: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    MAX_TWEETS_PER_HOUR: int = 5
    MAX_REPLIES_PER_HOUR: int = 10
    MIN_ACTION_DELAY: int = 30
    MAX_ACTION_DELAY: int = 120
    
    BRAND_VOICE: str = "professional"
    # Use str to avoid Pydantic parsing errors from .env, parse via property
    CONTENT_TOPICS: str = "AI, technology"
    
    ENABLE_AUTO_POSTING: bool = True
    ENABLE_AUTO_REPLIES: bool = True
    ENABLE_IMAGE_GENERATION: bool = True
    ENABLE_VIDEO_GENERATION: bool = False
    REQUIRE_HUMAN_REVIEW: bool = True
    
    @property
    def content_topics_list(self) -> List[str]:
        if not self.CONTENT_TOPICS:
            return []
        return [item.strip() for item in self.CONTENT_TOPICS.split(",") if item.strip()]
    
    @property
    def proxy_url(self) -> str:
        if not self.PROXY_HOST:
            return ""
            
        if self.PROXY_USERNAME and self.PROXY_PASSWORD:
            user = urllib.parse.quote_plus(self.PROXY_USERNAME)
            pwd = urllib.parse.quote_plus(self.PROXY_PASSWORD)
            return f"http://{user}:{pwd}@{self.PROXY_HOST}:{self.PROXY_PORT}"
            
        return f"http://{self.PROXY_HOST}:{self.PROXY_PORT}"
    
    @property
    def database_url_async(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
