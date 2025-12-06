"""
LLM Factory - Centralized LLM provider management
Supports multiple LLM providers (OpenAI, Gemini, Mock)
"""

from typing import Optional, Any, Dict
from types import SimpleNamespace
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings
import random
import json
from datetime import datetime


class MockLLM:
    """Mock LLM provider compatible with LangChain's chain.ainvoke.

    Produces realistic JSON outputs for all four agents (triage, investigation, decision, response)
    so the application works without requiring actual LLM API keys.
    
    This mock provider intelligently detects which agent is calling it by inspecting the
    input variables and returns appropriate mock data for each agent type.
    """
    
    def __init__(self, model: str = "mock-llm", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self._call_count = 0
    
    async def ainvoke(self, input_vars: Dict[str, Any]):
        """
        Generate mock response based on agent type detection.
        
        Args:
            input_vars: Dictionary of input variables from the agent prompt
            
        Returns:
            SimpleNamespace with content field containing JSON string
        """
        self._call_count += 1
        
        # Detect which agent is calling based on input variable patterns
        agent_type = self._detect_agent_type(input_vars)
        
        # Generate appropriate mock response
        if agent_type == "triage":
            content = self._generate_triage_response(input_vars)
        elif agent_type == "investigation":
            content = self._generate_investigation_response(input_vars)
        elif agent_type == "decision":
            content = self._generate_decision_response(input_vars)
        elif agent_type == "response":
            content = self._generate_response_response(input_vars)
        else:
            # Fallback
            content = '{"status": "unknown", "message": "Unable to determine agent type"}'
        
        return SimpleNamespace(content=content)
    
    def _detect_agent_type(self, input_vars: Dict[str, Any]) -> str:
        """Detect which agent is calling based on input variables."""
        keys = set(input_vars.keys())
        
        # Triage agent - looks for raw alert data without triage results
        if "raw_data" in keys and "triage_verdict" not in keys:
            return "triage"
        
        # Investigation agent - has triage results and threat intel
        if "triage_verdict" in keys and "threat_intel" in keys:
            return "investigation"
        
        # Decision agent - has investigation summary
        if "investigation_summary" in keys:
            return "decision"
        
        # Response agent - has recommended actions from decision
        if "recommended_actions" in keys and "estimated_impact" in keys:
            return "response"
        
        return "unknown"
    
    def _generate_triage_response(self, input_vars: Dict[str, Any]) -> str:
        """Generate mock triage agent response."""
        # Vary responses for realism
        verdicts = ["suspicious", "true_positive", "benign", "false_positive"]
        verdict = random.choice(verdicts[:2])  # Bias toward suspicious/true_positive
        
        confidence = round(random.uniform(0.65, 0.92), 2)
        noise_score = round(random.uniform(0.15, 0.45), 2)
        requires_investigation = verdict in ["suspicious", "true_positive"]
        
        key_indicators = [
            "Unusual login time detected",
            "Multiple failed authentication attempts",
            "Geographical anomaly in access pattern",
            "Privileged account activity"
        ]
        
        selected_indicators = random.sample(key_indicators, k=random.randint(2, 3))
        
        reasoning_templates = [
            "The alert shows suspicious patterns consistent with credential abuse. Further investigation is warranted to rule out compromise.",
            "Multiple indicators suggest potential malicious activity. The combination of failed attempts and unusual timing requires deeper analysis.",
            "Activity patterns deviate significantly from baseline behavior. Investigation needed to determine if this is legitimate or malicious.",
            "The alert contains several high-confidence indicators of compromise that justify immediate investigation."
        ]
        
        response = {
            "verdict": verdict,
            "confidence": confidence,
            "noise_score": noise_score,
            "requires_investigation": requires_investigation,
            "key_indicators": selected_indicators,
            "reasoning": random.choice(reasoning_templates)
        }
        
        return json.dumps(response)
    
    def _generate_investigation_response(self, input_vars: Dict[str, Any]) -> str:
        """Generate mock investigation agent response."""
        findings = [
            "Lateral movement detected across multiple systems",
            "Credential reuse pattern identified",
            "Suspicious PowerShell execution observed",
            "Network scanning activity from compromised host",
            "Privilege escalation attempts detected"
        ]
        
        ttps = ["T1078", "T1021", "T1059", "T1003", "T1090", "T1069"]
        attack_stages = [
            "Initial Access",
            "Execution", 
            "Persistence",
            "Privilege Escalation",
            "Defense Evasion",
            "Credential Access",
            "Discovery",
            "Lateral Movement"
        ]
        
        response = {
            "findings": random.sample(findings, k=random.randint(3, 4)),
            "threat_context": {
                "threat_actor": random.choice(["APT29", "APT28", "Unknown", "Insider Threat"]),
                "campaign": random.choice(["Unknown", "Operation CloudHopper", "N/A"]),
                "ttps": random.sample(ttps, k=random.randint(3, 5))
            },
            "related_alerts": [
                f"ALERT-{random.randint(10000, 99999)}" for _ in range(random.randint(2, 4))
            ],
            "attack_chain": random.sample(attack_stages, k=random.randint(3, 5)),
            "risk_score": round(random.uniform(6.5, 9.5), 1),
            "evidence": {
                "key_data_points": [
                    "Multiple hosts accessed within short timeframe",
                    "Administrative privileges used",
                    "Access outside normal business hours",
                    "Data exfiltration indicators present"
                ],
                "timeline": [
                    f"{datetime.now().strftime('%Y-%m-%d')} 02:15 - Initial compromise detected",
                    f"{datetime.now().strftime('%Y-%m-%d')} 02:23 - Lateral movement initiated",
                    f"{datetime.now().strftime('%Y-%m-%d')} 02:45 - Privilege escalation observed",
                    f"{datetime.now().strftime('%Y-%m-%d')} 03:12 - Data access detected"
                ],
                "indicators_of_compromise": [
                    "192.168.100.55",
                    "suspicious.exe",
                    "malware_hash_abc123def456",
                    "command-control.badsite.com"
                ]
            }
        }
        
        return json.dumps(response)
    
    def _generate_decision_response(self, input_vars: Dict[str, Any]) -> str:
        """Generate mock decision agent response."""
        final_verdicts = ["true_positive", "false_positive", "suspicious"]
        verdict = random.choice(final_verdicts[:2])  # Bias toward true_positive
        
        if verdict == "true_positive":
            priority = random.choice(["P1", "P2"])
            impact = random.choice(["CRITICAL", "HIGH"])
            escalation = True
        else:
            priority = random.choice(["P3", "P4", "P5"])
            impact = random.choice(["MEDIUM", "LOW", "MINIMAL"])
            escalation = False
        
        action_sets = {
            "P1": [
                "Immediately isolate affected systems",
                "Disable compromised user accounts",
                "Initiate emergency incident response",
                "Notify CISO and executive team",
                "Engage forensics team"
            ],
            "P2": [
                "Contain affected host",
                "Reset user credentials",
                "Enable enhanced monitoring",
                "Review related alerts",
                "Schedule incident response meeting"
            ],
            "P3": [
                "Monitor for additional indicators",
                "Review user activity logs",
                "Update detection rules",
                "Document findings"
            ]
        }
        
        recommended = random.sample(
            action_sets.get(priority, action_sets["P3"]),
            k=random.randint(3, 4)
        )
        
        rationale_templates = {
            "true_positive": "Comprehensive analysis confirms malicious activity. Multiple corroborating indicators and threat intelligence matches indicate an active security incident requiring immediate response.",
            "false_positive": "After thorough investigation, the activity appears to be legitimate business operations misinterpreted by detection rules. Recommending rule tuning to reduce false positives.",
            "suspicious": "Evidence is inconclusive but warrants continued monitoring. Some indicators suggest potential compromise, but alternative explanations exist."
        }
        
        response = {
            "final_verdict": verdict,
            "priority": priority,
            "confidence": round(random.uniform(0.75, 0.95), 2),
            "rationale": rationale_templates.get(verdict, rationale_templates["suspicious"]),
            "recommended_actions": recommended,
            "escalation_required": escalation,
            "estimated_impact": impact
        }
        
        return json.dumps(response)
    
    def _generate_response_response(self, input_vars: Dict[str, Any]) -> str:
        """Generate mock response agent response."""
        priority = input_vars.get("priority", "P3")
        
        # Generate ticket ID
        timestamp = datetime.now().strftime("%Y%m%d")
        ticket_suffix = f"{random.randint(1000, 9999)}"
        ticket_id = f"INC-{timestamp}-{ticket_suffix}"
        
        action_mapping = {
            "P1": {
                "actions": [
                    "Emergency incident ticket created",
                    "Affected systems isolated from network",
                    "User accounts disabled",
                    "CISO and executive team notified",
                    "Forensics team engaged"
                ],
                "notifications": [
                    "CISO (SMS + Email)",
                    "SOC Team Lead (PagerDuty)",
                    "IR Team On-call (PagerDuty)",
                    "Executive Team (Email)",
                    "Asset Owners (Email)"
                ],
                "automations": [
                    "Network isolation applied",
                    "Firewall rules updated",
                    "Account lockout enforced",
                    "Enhanced logging enabled",
                    "Threat hunt initiated"
                ],
                "status": "IN_PROGRESS"
            },
            "P2": {
                "actions": [
                    "High-priority incident ticket created",
                    "Affected host contained",
                    "User credentials reset",
                    "SOC team notified",
                    "IR meeting scheduled"
                ],
                "notifications": [
                    "SOC Team Lead (Email + Slack)",
                    "Senior Security Analyst (Email)",
                    "Asset Owner (Email)"
                ],
                "automations": [
                    "IP reputation check completed",
                    "Enhanced monitoring enabled",
                    "Watchlist entry created"
                ],
                "status": "COMPLETED"
            },
            "P3": {
                "actions": [
                    "Monitoring ticket created",
                    "Added to analyst queue",
                    "Follow-up review scheduled"
                ],
                "notifications": [
                    "SOC Team (Email)",
                    "Assigned Analyst (Email)"
                ],
                "automations": [
                    "Monitoring alert configured",
                    "Metrics dashboard updated"
                ],
                "status": "COMPLETED"
            }
        }
        
        response_data = action_mapping.get(priority, action_mapping["P3"])
        
        summary_templates = [
            f"Security incident {ticket_id} has been processed and appropriate response actions have been executed according to the {priority} playbook.",
            f"Incident response workflow completed for {ticket_id}. All stakeholders notified and containment measures applied.",
            f"Alert processed as {priority} incident. Response actions executed successfully with {len(response_data['automations'])} automations applied."
        ]
        
        response = {
            "actions_taken": response_data["actions"],
            "ticket_id": ticket_id,
            "notifications_sent": response_data["notifications"],
            "automation_applied": response_data["automations"],
            "status": response_data["status"],
            "summary": random.choice(summary_templates)
        }
        
        return json.dumps(response)


def get_llm(
    temperature: float = 0.7,
    model: Optional[str] = None,
    provider: Optional[str] = None
):
    """
    Factory function to create LLM instance based on configured provider.
    
    Supports multiple providers:
    - openai: OpenAI GPT models (requires OPENAI_API_KEY)
    - gemini: Google Gemini models (requires GEMINI_API_KEY)
    - mock: Mock LLM that returns realistic test data (no API key required)
    
    Args:
        temperature: Temperature setting for the LLM
        model: Specific model to use (overrides default from settings)
        provider: LLM provider to use (overrides default from settings)
        
    Returns:
        LLM instance (ChatOpenAI, ChatGoogleGenerativeAI, or MockLLM)
        
    Raises:
        ValueError: If provider requires API key but it's missing
    """
    provider = provider or settings.llm_provider
    provider = provider.lower()
    
    # Mock provider - no API key required
    if provider in ("mock", "mock-data", "none", "disabled"):
        print(f"[LLM Factory] Using Mock LLM provider (no API key required)")
        return MockLLM(model=model or "mock-llm", temperature=temperature)
    
    # OpenAI provider
    if provider == "openai":
        if not settings.openai_api_key:
            print("[LLM Factory] WARNING: OPENAI_API_KEY not set, falling back to Mock LLM")
            return MockLLM(model=model or "mock-openai", temperature=temperature)
        
        print(f"[LLM Factory] Using OpenAI provider with model: {model or settings.openai_model}")
        return ChatOpenAI(
            model=model or settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key
        )
    
    # Gemini provider
    elif provider == "gemini":
        if not settings.gemini_api_key:
            print("[LLM Factory] WARNING: GEMINI_API_KEY not set, falling back to Mock LLM")
            return MockLLM(model=model or "mock-gemini", temperature=temperature)
        
        print(f"[LLM Factory] Using Gemini provider with model: {model or settings.gemini_model}")
        return ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            google_api_key=settings.gemini_api_key
        )
    
    # Unknown provider - fallback to mock
    else:
        print(f"[LLM Factory] WARNING: Unknown provider '{provider}', falling back to Mock LLM")
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
