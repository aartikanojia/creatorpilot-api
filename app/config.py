"""Application configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    app_name: str = "Context Hub API"
    app_version: str = "1.0.0"
    environment: str = "development"

    # LLM Provider (metadata only - actual provider is configured in MCP)
    llm_provider: str = "gemini-flash-latest"

    # MCP Client Configuration
    mcp_base_url: str = "http://context-hub-mcp:8001"
    mcp_timeout: float = 30.0

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS Configuration (comma-separated origins, empty = no CORS in prod)
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Rate Limiting Configuration
    rate_limit_requests: int = 100  # requests per window
    rate_limit_window: int = 60  # window in seconds

    @property
    def debug(self) -> bool:
        """Enable debug mode in development environment."""
        return self.environment == "development"

    # Google OAuth Configuration
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/youtube/callback"

    # Google OAuth Endpoints
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    youtube_channels_api: str = "https://www.googleapis.com/youtube/v3/channels"

    # YouTube OAuth Scopes (comma-separated)
    youtube_scopes: str = "https://www.googleapis.com/auth/youtube.readonly,https://www.googleapis.com/auth/yt-analytics.readonly"


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached).

    Returns:
        Settings: Application configuration instance.
    """
    return Settings()

