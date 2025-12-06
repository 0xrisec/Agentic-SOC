"""
LLM Factory - Centralized LLM provider management
Supports multiple LLM providers (OpenAI, Gemini, etc.)
"""

from typing import Optional, Any, Dict
from types import SimpleNamespace
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings


class MockLLM:
    """Mock LLM provider compatible with LangChain's chain.ainvoke.

    Produces reasonable JSON outputs for our four agents so UI works without real keys.
    """
    def __init__(self, model: str = "mock-llm", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature

    async def ainvoke(self, input_vars: Dict[str, Any]):
        # Decide which agent by inspecting keys present in input_vars
        content = "{}"
        if {
            "noise_score",
            "requires_investigation",
            "key_indicators",
        }.intersection(set(input_vars.keys())):
            # Triage-like request
            content = (
                '{"verdict":"suspicious","confidence":0.72,"noise_score":0.35,'
                '"requires_investigation":true,"key_indicators":["Anomalous login","Multiple failed attempts"],'
                '"reasoning":"Indicators suggest potential account compromise; further investigation warranted."}'
            )
        elif "investigation_summary" in input_vars:
            # Decision-like request
            content = (
                '{"final_verdict":"true_positive","priority":"P2","confidence":0.81,'
                '"rationale":"Correlated events and threat intel indicate active compromise.",' 
                '"recommended_actions":["Contain affected host","Reset user credentials","Increase monitoring"],' 
                '"escalation_required":true,"estimated_impact":"HIGH"}'
            )
        elif "recommended_actions" in input_vars and "estimated_impact" in input_vars:
            # Response-like request
            content = (
                '{"actions_taken":["Ticket created","IR team notified"],'
                '"ticket_id":"INC-20250101-FAKE1234",'
                '"notifications_sent":["SOC Lead","IR On-call"],'
                '"automation_applied":["Firewall block","Disable account"],'
                '"status":"COMPLETED",'
                '"summary":"Incident contained; actions executed per playbook."}'
            )
        else:
            # Investigation-like default
            content = (
                '{"findings":["Suspicious lateral movement","Credential reuse detected"],'
                '"threat_context":{"threat_actor":"Unknown","campaign":"N/A","ttps":["T1021","T1078"]},'
                '"related_alerts":["ALERT-123","ALERT-456"],'
                '"attack_chain":["Initial Access","Execution","Lateral Movement"],'
                '"risk_score":7.9,'
                '"evidence":{"key_data_points":["Multiple hosts accessed","Admin login outside hours"],'
                '"timeline":["00:01 login","00:05 host access"],'
                '"indicators_of_compromise":["1.2.3.4","malicious.exe"]}}'
            )

        return SimpleNamespace(content=content)


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
    
    elif provider in ("mock", "none", "disabled"):
        # Fallback mock provider when real LLM isn't available
        return MockLLM(model=model or "mock-llm", temperature=temperature)
    
    else:
        # If an unknown provider is configured but keys are missing, fallback to mock
        return MockLLM(model=model or f"mock-{provider}", temperature=temperature)


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
