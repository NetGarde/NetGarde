from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DB_URL: str
    CORS_ORIGINS: str = (
        "https://d2qp7beltc09b8.cloudfront.net,https://daemixzdg8jfd.cloudfront.net"
    )

    # Service identity: Agent-API upsert, detection-engine, network-flow ingest
    TRUSTEDGE_INGEST_TOKEN: str = ""

    REDIS_URL: str = "redis://redis:6379/0"

    # Admin identity: dashboard APIs
    ADMIN_API_TOKEN: str = ""

    # L4 flow twin (conntrack ingest on EC2 host)
    NETWORK_FLOWS_ENABLED: bool = True
    NETWORK_FLOWS_MAX_AGE_SEC: int = 300
    NETWORK_FLOWS_DNS_RESOLUTION_TTL_SEC: int = 600
    NETWORK_FLOWS_MAP_LIMIT: int = 80

    # Dashboard network / AI review (template | openai | ollama)
    NETWORK_REVIEW_MODE: str = "template"
    NETWORK_REVIEW_CACHE_TTL_SEC: int = 90
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    LLM_TIMEOUT_SEC: float = 180.0

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
