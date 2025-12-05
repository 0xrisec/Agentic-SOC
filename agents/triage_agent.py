"""
Triage Agent - Level 1 SOC Alert Triage and Noise Filtering
"""

from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from app.context import SOCWorkflowState, TriageResult, Verdict, AlertStatus
from app.config import settings
from app.llm_factory import get_llm
import json
from datetime import datetime


class TriageAgent:
    """Agent responsible for initial alert triage and noise filtering"""
    
    def __init__(self):
        self.llm = get_llm(
            temperature=settings.triage_temperature
        )
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> ChatPromptTemplate:
        """Load triage agent prompt"""
        with open("prompts/triage_agent.md", "r") as f:
            system_prompt = f.read()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """Analyze the following alert and provide triage assessment:

ALERT DETAILS:
Alert ID: {alert_id}
Rule ID: {rule_id}
Rule Name: {rule_name}
Severity: {severity}
Timestamp: {timestamp}
Description: {description}

MITRE ATT&CK:
Tactics: {tactics}
Techniques: {techniques}

AFFECTED ASSETS:
Host: {host}
Source IP: {source_ip}
Destination IP: {destination_ip}
User: {user}

RAW DATA:
{raw_data}

Provide your triage assessment in the following JSON format:
{{
    "verdict": "true_positive|false_positive|benign|suspicious|unknown",
    "confidence": 0.0-1.0,
    "noise_score": 0.0-1.0,
    "requires_investigation": true|false,
    "key_indicators": ["indicator1", "indicator2", ...],
    "reasoning": "Your 2-3 sentence explanation"
}}""")
        ])
        
        return prompt
    
    async def execute(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Execute triage analysis"""
        try:
            # Update state
            state.status = AlertStatus.TRIAGING
            state.current_agent = "triage_agent"
            
            # Prepare prompt variables
            alert = state.alert
            prompt_vars = {
                "alert_id": alert.alert_id,
                "rule_id": alert.rule_id,
                "rule_name": alert.rule_name or "N/A",
                "severity": alert.severity,
                "timestamp": alert.timestamp,
                "description": alert.description,
                "tactics": ", ".join(alert.mitre.tactics) if alert.mitre.tactics else "None",
                "techniques": ", ".join(alert.mitre.techniques) if alert.mitre.techniques else "None",
                "host": alert.assets.host or "N/A",
                "source_ip": alert.assets.source_ip or "N/A",
                "destination_ip": alert.assets.destination_ip or "N/A",
                "user": alert.assets.user or "N/A",
                "raw_data": json.dumps(alert.raw_data, indent=2) if alert.raw_data else "No additional data"
            }
            
            # Create chain and invoke
            chain = self.prompt_template | self.llm
            response = await chain.ainvoke(prompt_vars)
            
            # Parse response
            result_dict = self._parse_response(response.content)
            
            # Create TriageResult
            triage_result = TriageResult(
                verdict=Verdict(result_dict["verdict"]),
                confidence=result_dict["confidence"],
                reasoning=result_dict["reasoning"],
                noise_score=result_dict["noise_score"],
                requires_investigation=result_dict["requires_investigation"],
                key_indicators=result_dict["key_indicators"],
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Update state
            state.triage_result = triage_result
            
            return state
            
        except Exception as e:
            state.errors.append(f"Triage agent error: {str(e)}")
            state.status = AlertStatus.FAILED
            return state
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response to extract structured data"""
        try:
            # Try to find JSON in response
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            # Fallback: try to extract information manually
            raise ValueError(f"Failed to parse triage response: {str(e)}")


def create_triage_agent() -> TriageAgent:
    """Factory function to create triage agent"""
    return TriageAgent()
