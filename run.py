#!/usr/bin/env python3
"""
Quick start script for Agentic SOC POC
"""

import sys
import os
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_environment():
    """Check if environment is properly configured"""
    env_file = project_root / ".env"
    
    # if not env_file.exists():
    #     print("❌ Error: .env file not found!")
    #     print("   Please copy .env.example to .env and configure your OpenAI API key.")
    #     print()
    #     print("   cp .env.example .env")
    #     print("   # Then edit .env and add your OPENAI_API_KEY")
    #     return False
    
    # Load environment variables from .env file
    load_dotenv()
    
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("❌ Error: OPENAI_API_KEY not configured!")
            return False
    elif llm_provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            print("❌ Error: GEMINI_API_KEY not configured!")
            return False
    else:
        print(f"❌ Error: Unsupported LLM_PROVIDER '{llm_provider}'")
        return False
    
    print("✅ Environment configured correctly")
    return True


def main():
    """Main entry point"""
    # Basic banner
    print("=" * 80)
    print("🛡️  AGENTIC SOC - AI-Powered Level 1 SOC Automation")
    print("=" * 80)
    print()

    # Check environment
    if not check_environment():
        sys.exit(1)

    # Configure logging early (console + file)
    try:
        from app.config import settings
        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(level)
        fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        root_logger = logging.getLogger()
        # Console
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            ch = logging.StreamHandler()
            ch.setFormatter(fmt)
            root_logger.addHandler(ch)
        # File
        if settings.log_file:
            from pathlib import Path as _Path
            log_path = _Path(settings.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
                fh = logging.FileHandler(log_path, encoding="utf-8")
                fh.setFormatter(fmt)
                root_logger.addHandler(fh)
    except Exception:
        # Proceed even if logging setup fails
        pass

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

    try:
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
    except Exception:
        # Log full exception with stack trace to aid debugging
        logging.exception("Fatal error while starting the server")
        raise


if __name__ == "__main__":
    main()
