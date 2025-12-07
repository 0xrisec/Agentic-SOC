"""
Response Agent - Action Execution and Ticket Creation
"""

from typing import Dict, Any, List, Callable
from langchain.prompts import ChatPromptTemplate
from prompts.human_prompts import RESPONSE_HUMAN_PROMPT
from app.context import SOCWorkflowState, ResponseResult, AlertStatus, Priority
from app.config import settings
from app.llm_factory import get_llm
import json
from datetime import datetime
import uuid
import asyncio


class ResponseAgent:
    """Agent responsible for executing response actions"""
    
    def __init__(self):
        self.llm = get_llm(
            temperature=settings.response_temperature
        )
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> ChatPromptTemplate:
        """Load response agent prompt"""
        with open("prompts/response_agent.md", "r") as f:
            system_prompt = f.read()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", RESPONSE_HUMAN_PROMPT)
        ])
        
        return prompt
    
    def _generate_ticket_id(self) -> str:
        """Generate unique ticket ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        suffix = str(uuid.uuid4())[:8].upper()
        return f"INC-{timestamp}-{suffix}"
    
    def _format_recommended_actions(self, actions: List[str]) -> str:
        """Format recommended actions list"""
        if not actions:
            return "No specific actions recommended"
        
        formatted = []
        for i, action in enumerate(actions, 1):
            formatted.append(f"{i}. {action}")
        
        return "\n".join(formatted)
    
    def _simulate_actions(self, state: SOCWorkflowState) -> Dict[str, Any]:
        """Simulate actual response actions (in production, this would execute real actions)"""
        decision = state.decision_result
        actions_taken = []
        notifications = []
        automations = []
        
        if not decision:
            return {
                "actions_taken": ["Alert processed without decision"],
                "notifications": [],
                "automations": []
            }
        
        priority = decision.priority
        
        # P1 - Critical
        if priority == Priority.P1:
            actions_taken.extend([
                "Created P1 critical incident ticket",
                "Sent emergency notifications to SOC team and on-call IR",
                "Initiated automated containment procedures"
            ])
            notifications.extend([
                "SOC Team Lead (SMS + Email)",
                "On-call IR Team (PagerDuty)",
                "CISO (Email)",
                "Asset Owner (Email)"
            ])
            automations.extend([
                "Firewall block rule created",
                "Affected accounts disabled",
                "Enhanced monitoring enabled"
            ])
        
        # P2 - High
        elif priority == Priority.P2:
            actions_taken.extend([
                "Created P2 high-priority incident ticket",
                "Notified SOC team and security analysts",
                "Scheduled incident response meeting"
            ])
            notifications.extend([
                "SOC Team (Email + Slack)",
                "Senior Security Analyst",
                "Asset Owner"
            ])
            automations.extend([
                "IP reputation check completed",
                "Enhanced logging enabled"
            ])
        
        # P3 - Medium
        elif priority == Priority.P3:
            actions_taken.extend([
                "Created P3 monitoring ticket",
                "Added to analyst queue",
                "Scheduled follow-up review"
            ])
            notifications.extend([
                "SOC Team (Email)",
                "Assigned Analyst"
            ])
            automations.extend([
                "Watchlist entry created",
                "Monitoring alert configured"
            ])
        
        # P4 - Low
        elif priority == Priority.P4:
            actions_taken.extend([
                "Created P4 tracking ticket",
                "Added to monitoring dashboard"
            ])
            notifications.extend([
                "Daily digest (SOC Team)"
            ])
            automations.extend([
                "Metrics updated"
            ])
        
        # P5 - Informational
        else:  # P5
            actions_taken.extend([
                "Alert closed as false positive",
                "Detection rule tuning recommended"
            ])
            notifications.extend([
                "No immediate notifications"
            ])
            automations.extend([
                "False positive counter updated",
                "Rule optimization queued"
            ])
        
        return {
            "actions_taken": actions_taken,
            "notifications": notifications,
            "automations": automations
        }
    
    async def execute(self, state: SOCWorkflowState, event_callback: Callable[[str, Dict[str, Any]], None] | None = None) -> SOCWorkflowState:
        """Execute response actions"""
        try:
            # Update state
            state.status = AlertStatus.RESPONDING
            state.current_agent = "response_agent"
            
            decision = state.decision_result
            
            if not decision:
                state.errors.append("Cannot execute response without decision")
                state.status = AlertStatus.FAILED
                return state
            
            # Prepare prompt variables
            alert = state.alert
            
            prompt_vars = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name or alert.rule_id,
                "severity": alert.severity,
                "host": alert.assets.host or "N/A",
                "source_ip": alert.assets.source_ip or "N/A",
                "user": alert.assets.user or "N/A",
                "final_verdict": decision.final_verdict,
                "priority": decision.priority,
                "confidence": decision.confidence,
                "escalation_required": decision.escalation_required,
                "estimated_impact": decision.estimated_impact,
                "recommended_actions": self._format_recommended_actions(decision.recommended_actions),
                "rationale": decision.rationale
            }
            
            # Create chain and invoke
            chain = self.prompt_template | self.llm
            if event_callback:
                event_callback(state.workflow_id, {"type": "progress", "stage": "respond", "status": "processing"})
            
            if not state.enable_ai:
                # Fallback to mock data
                mock_data = {
                    "actions_taken": ["Block IP 192.168.1.1", "Create incident ticket"],
                    "ticket_id": self._generate_ticket_id(),
                    "notifications_sent": ["SOC Team notified", "Incident response team alerted"],
                    "automation_applied": ["Firewall rule created", "Account monitoring enabled"],
                    "status": "COMPLETED",
                    "summary": "Alert processed successfully with automated response actions",
                    "timestamp": datetime.utcnow().isoformat()
                }

                response_result = ResponseResult(
                    actions_taken=mock_data["actions_taken"],
                    ticket_id=mock_data["ticket_id"],
                    notifications_sent=mock_data["notifications_sent"],
                    automation_applied=mock_data["automation_applied"],
                    status=mock_data["status"],
                    summary=mock_data["summary"],
                    timestamp=mock_data["timestamp"]
                )

                state.response_result = response_result
                state.status = AlertStatus.COMPLETED
                await asyncio.sleep(settings.mock_data_delay)
                return state
            else:
                response = await asyncio.wait_for(chain.ainvoke(prompt_vars), timeout=settings.llm_timeout_seconds)  # Set a configurable timeout
            
            if not response or not response.content:
                raise ValueError("LLM invocation failed or returned an empty response")

            
            # Parse response
            result_dict = self._parse_response(response.content)
            
            # Simulate actual actions (in production, this would execute real actions)
            simulated = self._simulate_actions(state)
            
            # Merge LLM response with simulated actions
            all_actions = list(set(result_dict.get("actions_taken", []) + simulated["actions_taken"]))
            all_notifications = list(set(result_dict.get("notifications_sent", []) + simulated["notifications"]))
            all_automations = list(set(result_dict.get("automation_applied", []) + simulated["automations"]))
            
            # Generate ticket ID if not in P5
            ticket_id = None
            if decision.priority != Priority.P5:
                ticket_id = result_dict.get("ticket_id") or self._generate_ticket_id()
            
            # Create ResponseResult
            response_result = ResponseResult(
                actions_taken=all_actions,
                ticket_id=ticket_id,
                notifications_sent=all_notifications,
                automation_applied=all_automations,
                status=result_dict.get("status", "COMPLETED"),
                summary=result_dict.get("summary", "Alert processed successfully"),
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Update state
            state.response_result = response_result
            state.status = AlertStatus.COMPLETED
            state.completed_at = datetime.utcnow().isoformat()
            
            # Calculate processing time
            started = datetime.fromisoformat(state.started_at)
            completed = datetime.fromisoformat(state.completed_at)
            state.processing_time_seconds = (completed - started).total_seconds()
            
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
            raise ValueError(f"Failed to parse response agent output: {str(e)}")


def create_response_agent() -> ResponseAgent:
    """Factory function to create response agent"""
    return ResponseAgent()
