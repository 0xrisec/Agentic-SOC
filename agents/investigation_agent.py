"""
Investigation Agent - Deep Threat Investigation and Analysis
"""

from typing import Dict, Any, List, Callable
from langchain.prompts import ChatPromptTemplate
from prompts.human_prompts import INVESTIGATION_HUMAN_PROMPT
from app.context import SOCWorkflowState, InvestigationResult, AlertStatus
from app.config import settings
from app.llm_factory import get_llm
import json
from datetime import datetime
import asyncio


class InvestigationAgent:
    """Agent responsible for deep threat investigation"""
    
    def __init__(self, threat_intel_path: str = "data/threat_intel.json"):
        self.llm = get_llm(
            temperature=settings.investigation_temperature
        )
        self.prompt_template = self._load_prompt()
        self.threat_intel_path = threat_intel_path
        self.threat_intel = self._load_threat_intel()
    
    def _load_prompt(self) -> ChatPromptTemplate:
        """Load investigation agent prompt"""
        with open("prompts/investigation_agent.md", "r") as f:
            system_prompt = f.read()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", INVESTIGATION_HUMAN_PROMPT)
        ])
        
        return prompt
    
    def _load_threat_intel(self) -> Dict[str, Any]:
        """Load threat intelligence data"""
        try:
            with open(self.threat_intel_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _get_relevant_threat_intel(self, state: SOCWorkflowState) -> str:
        """Get relevant threat intelligence for the alert"""
        if not self.threat_intel:
            return "No threat intelligence data available"
        
        alert = state.alert
        relevant_intel = []
        
        # Check for IP-based intelligence
        if alert.assets.source_ip:
            for intel in self.threat_intel.get("malicious_ips", []):
                if intel["ip"] == alert.assets.source_ip:
                    relevant_intel.append(f"- Source IP {intel['ip']}: {intel['description']} (Confidence: {intel['confidence']})")
        
        # Check for technique-based intelligence
        for technique in alert.mitre.techniques:
            for intel in self.threat_intel.get("attack_patterns", []):
                if technique in intel.get("techniques", []):
                    relevant_intel.append(f"- {intel['name']}: {intel['description']}")
        
        if relevant_intel:
            return "\n".join(relevant_intel)
        else:
            return "No specific threat intelligence matches found for this alert"
    
    async def execute(self, state: SOCWorkflowState, event_callback: Callable[[str, Dict[str, Any]], None] | None = None) -> SOCWorkflowState:
        """Execute investigation analysis"""
        try:
            # Check if investigation is required
            if state.triage_result and not state.triage_result.requires_investigation:
                # Skip investigation for noise
                state.warnings.append("Investigation skipped - triage marked as not requiring investigation")
                return state
            
            # Update state
            state.status = AlertStatus.INVESTIGATING
            state.current_agent = "investigation_agent"
            
            # Prepare prompt variables
            alert = state.alert
            triage = state.triage_result
            
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
                "triage_verdict": triage.verdict if triage else "N/A",
                "triage_confidence": triage.confidence if triage else "N/A",
                "key_indicators": ", ".join(triage.key_indicators) if triage and triage.key_indicators else "None",
                "triage_reasoning": triage.reasoning if triage else "N/A",
                "threat_intel": self._get_relevant_threat_intel(state),
                "raw_data": json.dumps(alert.raw_data, indent=2) if alert.raw_data else "No additional data"
            }
            
            # Create chain and invoke
            chain = self.prompt_template | self.llm
            if event_callback:
                event_callback(state.workflow_id, {"type": "progress", "stage": "investigate", "status": "processing"})

            if not state.enable_ai:
                # Use mock data instead of LLM call
                mock_data = {
                    "findings": ["Potential credential access attempt detected"],
                    "threat_context": {"threat_type": "Credential Access", "confidence": 0.85},
                    "related_alerts": ["Alert1", "Alert2"],
                    "attack_chain": ["Reconnaissance", "Credential Access"],
                    "risk_score": 8.5,
                    "evidence": {"details": ["IP address 192.168.1.1", "Failed login attempts"]},
                    "timestamp": datetime.utcnow().isoformat()
                }

                investigation_result = InvestigationResult(
                    findings=mock_data["findings"],
                    threat_context=mock_data["threat_context"],
                    related_alerts=mock_data["related_alerts"],
                    attack_chain=mock_data["attack_chain"],
                    risk_score=mock_data["risk_score"],
                    evidence=mock_data["evidence"],
                    timestamp=mock_data["timestamp"]
                )
                state.investigation_result = investigation_result
                state.status = AlertStatus.COMPLETED
                await asyncio.sleep(settings.mock_data_delay)
                return state
            else:
                response = await asyncio.wait_for(chain.ainvoke(prompt_vars), timeout=settings.llm_timeout_seconds)  # Set a configurable timeout
            
            if not response or not response.content:
                raise ValueError("LLM invocation failed or returned an empty response")


            # Parse response
            result_dict = self._parse_response(response.content)
            
            # Create InvestigationResult
            investigation_result = InvestigationResult(
                findings=result_dict["findings"],
                threat_context=result_dict["threat_context"],
                related_alerts=result_dict["related_alerts"],
                attack_chain=result_dict["attack_chain"],
                risk_score=result_dict["risk_score"],
                evidence=result_dict["evidence"],
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Update state
            state.investigation_result = investigation_result
            
            return state
            
        except Exception as e:
                raise e
    
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
            raise ValueError(f"Failed to parse investigation response: {str(e)}")


def create_investigation_agent() -> InvestigationAgent:
    """Factory function to create investigation agent"""
    return InvestigationAgent()
