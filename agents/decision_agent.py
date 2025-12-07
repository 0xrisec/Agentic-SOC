"""
Decision Agent - Final Verdict and Prioritization
"""

from typing import Dict, Any, Callable
from langchain.prompts import ChatPromptTemplate
from prompts.human_prompts import DECISION_HUMAN_PROMPT
from app.context import SOCWorkflowState, DecisionResult, Verdict, Priority, AlertStatus
from app.config import settings
from app.llm_factory import get_llm
import json
from datetime import datetime
import asyncio


class DecisionAgent:
    """Agent responsible for making final decisions on alerts"""
    
    def __init__(self):
        self.llm = get_llm(
            temperature=settings.decision_temperature
        )
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> ChatPromptTemplate:
        """Load decision agent prompt"""
        with open("prompts/decision_agent.md", "r") as f:
            system_prompt = f.read()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", DECISION_HUMAN_PROMPT)
        ])
        
        return prompt
    
    def _format_investigation_summary(self, state: SOCWorkflowState) -> str:
        """Format investigation results for prompt"""
        inv = state.investigation_result
        
        if not inv:
            return "No investigation performed (triage indicated no investigation needed)"
        
        summary_parts = [
            f"Risk Score: {inv.risk_score}/10",
            f"\nFindings:",
        ]
        
        for finding in inv.findings:
            summary_parts.append(f"  - {finding}")
        
        if inv.attack_chain:
            summary_parts.append(f"\nAttack Chain: {' -> '.join(inv.attack_chain)}")
        
        if inv.threat_context:
            summary_parts.append(f"\nThreat Context: {json.dumps(inv.threat_context, indent=2)}")
        
        if inv.related_alerts:
            summary_parts.append(f"\nRelated Alerts: {', '.join(inv.related_alerts)}")
        
        return "\n".join(summary_parts)
    
    async def execute(self, state: SOCWorkflowState, event_callback: Callable[[str, Dict[str, Any]], None] | None = None) -> SOCWorkflowState:
        """Execute decision making"""
        try:
            # Update state
            state.status = AlertStatus.DECIDING
            state.current_agent = "decision_agent"
            
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
                "user": alert.assets.user or "N/A",
                "triage_verdict": triage.verdict if triage else "N/A",
                "triage_confidence": triage.confidence if triage else "N/A",
                "noise_score": triage.noise_score if triage else "N/A",
                "key_indicators": ", ".join(triage.key_indicators) if triage and triage.key_indicators else "None",
                "triage_reasoning": triage.reasoning if triage else "N/A",
                "investigation_summary": self._format_investigation_summary(state)
            }
            
            # Create chain and invoke
            chain = self.prompt_template | self.llm
            if event_callback:
                event_callback(state.workflow_id, {"type": "progress", "stage": "decide", "status": "processing"})
            
            try:
                response = await asyncio.wait_for(chain.ainvoke(prompt_vars), timeout=settings.llm_timeout_seconds)  # Set a configurable timeout
            except asyncio.TimeoutError:
                 raise TimeoutError(f"LLM invocation timed out after {settings.llm_timeout_seconds} seconds")

            if not response or not response.content:
                raise ValueError("LLM invocation failed or returned an empty response")

            # Parse response
            result_dict = self._parse_response(response.content)
            
            # Create DecisionResult
            decision_result = DecisionResult(
                final_verdict=Verdict(str(result_dict["final_verdict"]).lower().replace(" ", "_")),
                priority=Priority(result_dict["priority"]),
                confidence=result_dict["confidence"],
                rationale=result_dict["rationale"],
                recommended_actions=result_dict["recommended_actions"],
                escalation_required=result_dict["escalation_required"],
                estimated_impact=result_dict["estimated_impact"],
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Update state
            state.decision_result = decision_result
            
            return state
            
        except Exception as e:
            if settings.use_mock_data_on_error:
                # Fallback to mock data
                mock_data = {
                    "final_verdict": "true_positive",
                    "priority": "P1",
                    "confidence": 0.85,
                    "rationale": "High severity alert with multiple indicators of compromise.",
                    "recommended_actions": ["Isolate affected systems", "Reset credentials", "Monitor for further activity"],
                    "escalation_required": True,
                    "estimated_impact": "High - Potential data breach",
                    "timestamp": datetime.utcnow().isoformat()
                }

                decision_result = DecisionResult(
                    final_verdict=Verdict(mock_data["final_verdict"]),
                    priority=Priority(mock_data["priority"]),
                    confidence=mock_data["confidence"],
                    rationale=mock_data["rationale"],
                    recommended_actions=mock_data["recommended_actions"],
                    escalation_required=mock_data["escalation_required"],
                    estimated_impact=mock_data["estimated_impact"],
                    timestamp=mock_data["timestamp"]
                )

                state.decision_result = decision_result
                state.errors.append(f"Decision agent error: {str(e)}")
                state.status = AlertStatus.COMPLETED
                return state
            else:
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
            raise ValueError(f"Failed to parse decision response: {str(e)}")


def create_decision_agent() -> DecisionAgent:
    """Factory function to create decision agent"""
    return DecisionAgent()
