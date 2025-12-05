"""
Configuration management for Agentic SOC POC.
Loads environment variables and provides centralized config access.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Provider Configuration
    llm_provider: str = "openai"  # Supported: openai, gemini
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    
    # Gemini Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-pro"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Logging
    log_level: str = "INFO"
    
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
