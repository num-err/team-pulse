from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Settings that must be non-empty when APP_ENV=production — missing any of
# these means a core feature would silently no-op or a security check would
# silently skip itself, which is worse than refusing to boot.
#
# Per-team secrets (webhook signing secrets, Slack bot tokens, Notion tokens)
# are NOT here: since multi-tenancy they live per workspace in the
# workspace_integrations table, not in the server environment.
_REQUIRED_IN_PRODUCTION = [
    "supabase_url",
    "supabase_key",
    "anthropic_api_key",
    "public_api_url",
]


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    supabase_url: str = ""
    # Service-role key: the backend enforces workspace membership itself and
    # bypasses RLS. Never ship this key to a browser.
    supabase_key: str = ""
    # Only needed for Supabase projects still signing user JWTs with the
    # legacy shared HS256 secret. Newer projects use asymmetric signing keys,
    # which are verified via the project's public JWKS endpoint instead.
    supabase_jwt_secret: str = ""
    app_env: str = "development"
    anthropic_api_key: str = ""

    # Public base URL of this API (e.g. https://api.teampulse.app). Used to
    # build the per-workspace webhook URLs shown during setup.
    public_api_url: str = "http://localhost:8001"

    # Development fallbacks only: used when a workspace has no Slack /
    # Notion integration of its own configured yet.
    slack_bot_token: str = ""
    slack_default_channel: str = ""
    notion_token: str = ""

    # How often the scheduler checks which workspaces are due a digest.
    scheduler_tick_minutes: int = 15

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

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def validate_production_settings(settings: Settings) -> None:
    """Refuse to boot with APP_ENV=production if required settings are missing."""
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
