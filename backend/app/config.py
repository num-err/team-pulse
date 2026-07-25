from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings that must be non-empty when APP_ENV=production — missing any of
# these means a core feature would silently no-op or a security check would
# silently skip itself, which is worse than refusing to boot.
_REQUIRED_IN_PRODUCTION = [
    "supabase_url",
    "supabase_key",
    "anthropic_api_key",
    "slack_bot_token",
    "api_key",
    "github_webhook_secret",
    "linear_webhook_secret",
    "notion_token",
]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    supabase_url: str = ""
    supabase_key: str = ""
    app_env: str = "development"
    github_webhook_secret: str = ""
    linear_webhook_secret: str = ""
    figma_webhook_passcode: str = ""
    notion_token: str = ""
    anthropic_api_key: str = ""
    api_key: str = ""
    slack_bot_token: str = ""
    slack_default_channel: str = "#standup"
    digest_cron_hour: int = 9
    digest_cron_minute: int = 0
    # Comma-separated list of allowed CORS origins, e.g.
    # "https://app.example.com,https://staging.example.com"
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def validate_production_settings(settings: Settings) -> None:
    """Refuse to boot with APP_ENV=production if required secrets are missing.

    Signature/API-key checks in this app skip themselves when their secret
    is unset (open-in-dev behavior) — fine for local work, dangerous if that
    happens silently in production. This makes the failure loud instead.
    """
    if settings.app_env != "production":
        return
    missing = [name.upper() for name in _REQUIRED_IN_PRODUCTION if not getattr(settings, name)]
    if missing:
        raise RuntimeError(
            "APP_ENV=production but required settings are missing: " + ", ".join(missing)
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    validate_production_settings(settings)
    return settings
