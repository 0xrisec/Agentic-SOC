"""
LLM Factory - Centralized LLM provider management
Supports multiple LLM providers (OpenAI, Gemini, etc.)
"""

from typing import Optional, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings


def get_llm(
    temperature: float = 0.7,
    model: Optional[str] = None,
    provider: Optional[str] = None
):
    """
    Factory function to create LLM instance based on configured provider.
    
    Args:
        temperature: Temperature setting for the LLM
        model: Specific model to use (overrides default from settings)
        provider: LLM provider to use (overrides default from settings)
        
    Returns:
        LLM instance (ChatOpenAI or ChatGoogleGenerativeAI)
        
    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    provider = provider or settings.llm_provider
    provider = provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")

        return ChatOpenAI(
            model=model or settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key
        )

    elif provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")

        return ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            google_api_key=settings.gemini_api_key
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def get_current_provider() -> str:
    """Get the currently configured LLM provider"""
    return settings.llm_provider


def get_current_model() -> str:
    """Get the currently configured model for the active provider"""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return settings.openai_model
    elif provider == "gemini":
        return settings.gemini_model
    else:
        return "unknown"
