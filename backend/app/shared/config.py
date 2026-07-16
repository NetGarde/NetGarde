from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DB_URL: str
    CORS_ORIGINS: str = (
        "https://d2qp7beltc09b8.cloudfront.net,https://daemixzdg8jfd.cloudfront.net"
    )

    # Service identity: detection-engine / network-flow ingest (historical name: DNS_INGEST_TOKEN)
    DNS_INGEST_TOKEN: str = ""

    REDIS_URL: str = "redis://redis:6379/0"

    # Device identity tokens (HMAC) for device-authenticated APIs such as network attribution
    DEVICE_TOKEN_SECRET: str = ""
    DEVICE_TOKEN_TTL_DAYS: int = 365

    # Admin identity: dashboard APIs
    ADMIN_API_TOKEN: str = ""

    # Endpoint network attribution (foreground app → network context)
    NETWORK_ATTRIBUTION_ENABLED: bool = True
    NETWORK_ATTRIBUTION_MAX_AGE_SEC: int = 120
    NETWORK_ATTRIBUTION_RETENTION_DAYS: int = 30
    CLIENT_ATTRIBUTION_PATH: str = "/v1/network-attribution"
    CLIENT_ATTRIBUTION_POLL_SEC: float = 30.0
    CLIENT_ATTRIBUTION_REPORT_SEC: float = 60.0

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
    def device_token_secret(self) -> str:
        return self.DEVICE_TOKEN_SECRET.strip()

    @property
    def DEVICE_TOKEN_TTL_SECONDS(self) -> int:
        days = max(1, int(self.DEVICE_TOKEN_TTL_DAYS))
        return days * 24 * 60 * 60
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
