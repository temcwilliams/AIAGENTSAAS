from pydantic import Field
from typing import Literal
from urllib.parse import urlsplit, parse_qs
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    database_url_unpooled: str = ""
    environment: Literal["production", "development", "test"] = "production"
    app_origin: str = "http://localhost:3000"
    ai_provider: Literal["local", "cloud", "bridge", "disabled"] = "local"
    openai_base_url: str = "http://127.0.0.1:11434/v1"
    openai_api_key: str = ""
    owner_setup_token_hash: str = ""
    session_hours: int = Field(default=12, ge=1, le=168)
    chat_requests_per_hour: int = Field(default=60, ge=1, le=10000)
    login_requests_per_minute: int = Field(default=30, ge=1, le=1000)
    conversations_per_hour: int = Field(default=120, ge=1, le=10000)

settings = Settings()
if settings.environment == "production":
    if not settings.app_origin.startswith("https://"):
        raise RuntimeError("Production APP_ORIGIN must use HTTPS")
    if not settings.database_url.startswith("postgresql+psycopg://") or parse_qs(urlsplit(settings.database_url).query).get("sslmode", [""])[0] not in ("require", "verify-ca", "verify-full"):
        raise RuntimeError("Production requires PostgreSQL with explicit TLS configuration")
    if settings.ai_provider in ("cloud", "bridge") and not settings.openai_base_url.startswith("https://"):
        raise RuntimeError("Production AI API requires HTTPS")

if settings.ai_provider == "local":
    endpoint = urlsplit(settings.openai_base_url)
    if endpoint.hostname not in {"localhost", "127.0.0.1", "::1", "ollama"} or endpoint.scheme not in {"http", "https"} or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise RuntimeError("Local AI must use a loopback endpoint or the private ollama container")
