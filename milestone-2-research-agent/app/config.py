from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM settings
    LLM_PROVIDER: Literal["gemini", "ollama"] = "gemini"
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Provider settings
    WEATHER_PROVIDER: str = "open-meteo"
    FLIGHT_PROVIDER: str = "opensky"
    FLIGHT_API_KEY: str = ""
    FLIGHT_CLIENT_ID: str = ""
    FLIGHT_CLIENT_SECRET: str = ""

    # Runtime settings
    REQUEST_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    LOG_LEVEL: str = "INFO"
    DATA_MODE: Literal["live", "synthetic"] = "synthetic"


settings = Settings()
