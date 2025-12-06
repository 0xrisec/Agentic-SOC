"""
Configuration management for Agentic SOC POC.
Loads environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Provider Configuration
    llm_provider: str = "openai"  # Supported: openai, gemini
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # Gemini Configuration
    # Load Gemini key from env var GOOGLE_API_KEY for compatibility with langchain-google-genai
    gemini_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    gemini_model: str = "gemini-pro"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    # CORS
    # Note: Browsers disallow '*' when credentials are used. Provide explicit origins.
    # Include 'null' to allow file:// based UI during local testing.
    cors_allow_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "null",
    ]
    # Set to True if the frontend uses cookies/authorization with credentials.
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = "logs/app.log"
    
    # Agent Configuration
    triage_temperature: float = 0.1
    investigation_temperature: float = 0.3
    decision_temperature: float = 0.1
    response_temperature: float = 0.2
    
    # Alert Processing
    max_concurrent_alerts: int = 5
    alert_timeout_seconds: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
