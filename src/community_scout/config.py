"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    secret_key: str = "change-me-in-production-use-a-real-secret-key"

    # Database
    database_url: str = "postgresql+asyncpg://community_scout:community_scout_dev@localhost:5432/community_scout"

    # Discord
    discord_bot_token: str = ""
    discord_guild_id: str = ""  # Required: The server where the bot operates

    # Encryption (for storing user API keys)
    encryption_key: str = ""  # Fernet key - generate with Fernet.generate_key()

    # OpenRouter (default API for users without their own key)
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3-haiku"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Hacker News Scanner
    hn_scan_interval_minutes: int = 5
    hn_stories_per_scan: int = 100  # Number of stories to fetch per scan


settings = Settings()
