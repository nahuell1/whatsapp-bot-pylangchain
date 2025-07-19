"""
Configuration management for the WhatsApp bot backend.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-nano-2025-04-14"
    
    # Backend Configuration
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8000
    BACKEND_URL: str = "http://localhost:8000"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    
    # WhatsApp Configuration
    WHATSAPP_SESSION_PATH: str = "./.wwebjs_auth"
    
    # Function-specific Configuration
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    HOME_ASSISTANT_URL: Optional[str] = None
    HOME_ASSISTANT_TOKEN: Optional[str] = None
    IP_CAMERA_URL: Optional[str] = None
    IP_CAMERA_USERNAME: Optional[str] = None
    IP_CAMERA_PASSWORD: Optional[str] = None
    
    # System Configuration
    MAX_MESSAGE_LENGTH: int = 1000
    FUNCTION_TIMEOUT: int = 30
    
    class Config:
        """Pydantic configuration."""
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        case_sensitive = True
        extra = "allow"  # Allow extra environment variables for dynamic camera configs


# Global settings instance
settings = Settings()
