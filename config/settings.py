# config/settings.py

import logging
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenAI and LLM credentials and connection settings
    OPENAI_API_URL: str
    OPENAI_API_KEY: str
    LLM_MODEL_NAME: str

    # Generation parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # Default system prompt
    SYSTEM_PROMPT: str = "You are a helpful and concise AI assistant."

    # Logging params
    LOG_LEVEL: int = logging.INFO
    LOG_FILE: str = "logs/bot.log"
    LOG_ROTATION_SIZE: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHANNEL_ID: str

    # Schedule
    MOSCOW_TZ: ZoneInfo = ZoneInfo("Europe/Moscow")
    POSTING_HOURS: list[int] = [11, 13, 16, 19, 22]


# Create a single instance of settings for the entire application
settings: Settings = Settings()  # pyright: ignore[reportCallIssue]
