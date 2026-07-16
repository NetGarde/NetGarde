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

    # Client behavior profiles
    BEHAVIOR_BASELINE_LOOKBACK_DAYS: int = 7
    # Minimum number of hourly rollup buckets required to mark profile_ready.
    # If set > 0, this overrides BEHAVIOR_MIN_PROFILE_DAYS.
    BEHAVIOR_MIN_PROFILE_HOURS: int = 0
    BEHAVIOR_MIN_PROFILE_DAYS: int = 3
    BEHAVIOR_MIN_PROFILE_QUERIES: int = 500
    BEHAVIOR_BASELINE_RECOMPUTE_HOURS: int = 1
    BEHAVIOR_SCORE_WINDOW_MINUTES: int = 15
    BEHAVIOR_ALERT_THRESHOLD: int = 70
    BEHAVIOR_AUTO_BLOCK_THRESHOLD: int = 85
    BEHAVIOR_AUTO_BLOCK_DEFAULT: bool = False
    BEHAVIOR_AUTO_BLOCK_TTL_HOURS: int = 24
    BEHAVIOR_AUTO_BLOCK_DOMAINS_PER_EVENT: int = 5
    BEHAVIOR_MAX_BLOCKS_PER_DAY: int = 10
    # Parent-facing behavior text (template | openai | ollama)
    BEHAVIOR_REVIEW_MODE: str = "template"
    BEHAVIOR_REVIEW_CACHE_TTL_SEC: int = 300
    # Alert when a device uses domains associated with a new country/region (ccTLD heuristic)
    DEVICE_COUNTRY_ALERT_ENABLED: bool = True
    DEVICE_COUNTRY_ALERT_COOLDOWN_HOURS: int = 24

    # Physical location observations (GeoIP)
    DEVICE_LOGIN_GEO_ENABLED: bool = True
    DEVICE_LOGIN_GEO_ALERT_ENABLED: bool = True
    DEVICE_LOGIN_GEO_ALERT_COOLDOWN_HOURS: int = 24
    GEOIP_ENABLED: bool = True
    GEOIP_PROVIDER: str = "ip_api"
    GEOIP_TIMEOUT_SEC: float = 3.0

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
