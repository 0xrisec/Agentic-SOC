#!/usr/bin/env python3
"""
Quick start script for Agentic SOC POC
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_environment():
    """Check if environment is properly configured"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get LLM provider setting
    llm_provider = os.getenv("LLM_PROVIDER", "mock-data").lower()
    
    # If using mock provider, no API key is needed
    if llm_provider in ("mock", "mock-data", "none", "disabled"):
        print("✅ Using Mock LLM provider (no API key required)")
        print(f"   Provider: {llm_provider}")
        return True
    
    # For other providers, check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("   Using default mock provider for testing.")
        print()
        print("   To use OpenAI or Gemini:")
        print("   1. cp .env.example .env")
        print("   2. Edit .env and configure your API key")
        return True
    
    # Check provider-specific API keys
    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("⚠️  Warning: OPENAI_API_KEY not configured!")
            print("   Falling back to Mock LLM provider.")
            return True
        print("✅ Using OpenAI provider")
        print(f"   Model: {os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')}")
    
    elif llm_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            print("⚠️  Warning: GEMINI_API_KEY not configured!")
            print("   Falling back to Mock LLM provider.")
            return True
        print("✅ Using Gemini provider")
        print(f"   Model: {os.getenv('GEMINI_MODEL', 'gemini-pro')}")
    
    else:
        print(f"⚠️  Warning: Unknown provider '{llm_provider}'")
        print("   Falling back to Mock LLM provider.")
    
    return True


def main():
    """Main entry point"""
    print("=" * 80)
    print("🛡️  AGENTIC SOC - AI-Powered Level 1 SOC Automation")
    print("=" * 80)
    print()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print()
    print("Starting FastAPI server...")
    print()
    print("📊 Dashboard:     http://localhost:8000")
    print("📚 API Docs:      http://localhost:8000/docs")
    print("🔍 Health Check:  http://localhost:8000/health")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()
    
    # Start server
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
