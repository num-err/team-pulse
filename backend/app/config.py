from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    slack_bot_token: str = ""
    slack_default_channel: str = "#standup"
    digest_cron_hour: int = 9
    digest_cron_minute: int = 0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
