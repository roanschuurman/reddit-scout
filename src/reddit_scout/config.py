"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    secret_key: str = "change-me-in-production-use-a-real-secret-key"

    # Database
    database_url: str = "postgresql+asyncpg://reddit_scout:reddit_scout_dev@localhost:5432/reddit_scout"

    # Reddit API
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "reddit-scout/0.1.0"

    # Discord
    discord_bot_token: str = ""

    # OpenRouter
    openrouter_api_key: str = ""

    # SuperTokens
    supertokens_connection_uri: str = ""
    supertokens_api_key: str = ""


settings = Settings()
