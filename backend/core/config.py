"""Configuration management for the WhatsApp bot backend.

This module defines all application settings and provides validation
for critical configuration values.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class SettingsValidationError(ValueError):
    """Raised when required configuration is missing or invalid."""


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    """
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-nano-2025-04-14"
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 2
    
    # Backend Configuration
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8000"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    # WhatsApp Configuration
    WHATSAPP_SESSION_PATH: str = "./.wwebjs_auth"
    
    # External API Configuration
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    HOME_ASSISTANT_URL: Optional[str] = None
    HOME_ASSISTANT_TOKEN: Optional[str] = None
    IP_CAMERA_URL: Optional[str] = None
    IP_CAMERA_USERNAME: Optional[str] = None
    IP_CAMERA_PASSWORD: Optional[str] = None
    
    # System Configuration
    MAX_MESSAGE_LENGTH: int = 1000
    FUNCTION_TIMEOUT: int = 30
    
    # Memory / Event Log Configuration
    MEMORY_ENABLED: bool = True
    MEMORY_MAX_EVENTS: int = 50
    MEMORY_EVENTS_IN_CONTEXT: int = 10
    MEMORY_TTL_DAYS: int = 7
    REDIS_URL: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        case_sensitive = True
        extra = "allow"


settings = Settings()


def validate_runtime_settings(current_settings: Settings) -> None:
    """Validate critical configuration values.
    
    Args:
        current_settings: Settings instance to validate
        
    Raises:
        SettingsValidationError: If required settings are missing or invalid
    """
    missing_fields = []

    if not (current_settings.OPENAI_API_KEY or "").strip():
        missing_fields.append("OPENAI_API_KEY")

    if not (current_settings.OPENAI_MODEL or "").strip():
        missing_fields.append("OPENAI_MODEL")

    if missing_fields:
        raise SettingsValidationError(
            f"Missing required environment variables: {', '.join(missing_fields)}"
        )

    if current_settings.OPENAI_TIMEOUT <= 0:
        raise SettingsValidationError("OPENAI_TIMEOUT must be greater than 0")

    if current_settings.OPENAI_MAX_RETRIES < 1:
        raise SettingsValidationError("OPENAI_MAX_RETRIES must be at least 1")
