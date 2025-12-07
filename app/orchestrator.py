"""
SOC Workflow Orchestrator using LangGraph
Coordinates the multi-agent workflow for alert processing
"""

from typing import Dict, Any, Callable
from langgraph.graph import StateGraph, END
from app.context import SOCWorkflowState, AlertStatus
from agents.triage_agent import create_triage_agent
from agents.investigation_agent import create_investigation_agent
from agents.decision_agent import create_decision_agent
from agents.response_agent import create_response_agent
import logging

logger = logging.getLogger(__name__)


class SOCOrchestrator:
    """Orchestrates the SOC agent workflow using LangGraph"""
    
    def __init__(self, event_callback: Callable[[str, Dict[str, Any]], None] | None = None):
        # Initialize agents
        self.triage_agent = create_triage_agent()
        self.investigation_agent = create_investigation_agent()
        self.decision_agent = create_decision_agent()
        self.response_agent = create_response_agent()
        self.event_callback = event_callback
        
        # Build workflow graph
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create workflow graph
        workflow = StateGraph(SOCWorkflowState)
        
        # Add nodes
        workflow.add_node("triage", self._triage_node)
        workflow.add_node("investigate", self._investigation_node)
        workflow.add_node("decide", self._decision_node)
        workflow.add_node("respond", self._response_node)
        
        # Define edges
        workflow.set_entry_point("triage")
        
        # After triage, decide whether to investigate, decide, or end if failed
        workflow.add_conditional_edges(
            "triage",
            self._after_triage,
            {
                "investigate": "investigate",
                "decide": "decide",
                END: END
            }
        )
        
        # After investigation, go to decision or end if failed
        workflow.add_conditional_edges(
            "investigate",
            self._after_investigation,
            {
                "decide": "decide",
                END: END
            }
        )
        
        # After decision, go to response or end if failed
        workflow.add_conditional_edges(
            "decide",
            self._after_decision,
            {
                "respond": "respond",
                END: END
            }
        )
        
        # After response, end
        workflow.add_edge("respond", END)
        
        return workflow

    def _to_plain(self, obj: Any) -> Any:
        """Convert Pydantic models, Enums, and complex structures to plain Python types.
        Ensures LangGraph receives a pure dict with lists/scalars only.
        """
        try:
            from enum import Enum
            from pydantic import BaseModel
        except Exception:
            # Fallback imports not strictly necessary but keep function safe
            BaseModel = tuple()
            class Enum:  # type: ignore
                pass

        if isinstance(obj, BaseModel):
            # Force deep conversion via JSON to avoid any nested BaseModel leakage
            try:
                import json as _json
                if hasattr(obj, "model_dump_json"):
                    return self._to_plain(_json.loads(obj.model_dump_json()))
                elif hasattr(obj, "json"):
                    return self._to_plain(_json.loads(obj.json()))
            except Exception:
                # Fallback to dict-based deep conversion
                if hasattr(obj, "model_dump"):
                    return {k: self._to_plain(v) for k, v in obj.model_dump(mode="python").items()}
                else:
                    return {k: self._to_plain(v) for k, v in obj.dict().items()}
        if isinstance(obj, Enum):
            return getattr(obj, "value", str(obj))
        if isinstance(obj, dict):
            return {self._to_plain(k): self._to_plain(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._to_plain(v) for v in obj]
        # Primitive or unknown - return as-is
        return obj
    
    async def _triage_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Triage agent node"""
        logger.info(f"Executing triage for alert {state.alert.alert_id}")
        state.current_agent = "triage"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "triage", "status": "started"})
        try:
            result_state = await self.triage_agent.execute(state, self.event_callback)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "triage", "status": "completed", "result": result_state.triage_result.model_dump() if result_state.triage_result else None})
            # Return dict updates for LangGraph
            return {
                "status": result_state.status,
                "current_agent": result_state.current_agent,
                "triage_result": self._to_plain(result_state.triage_result) if result_state.triage_result else None,
                "errors": result_state.errors,
                "warnings": result_state.warnings,
            }
        except Exception as e:
            logger.error(f"Triage node error: {str(e)}")
            state.errors.append(f"Triage error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "triage", "status": "failed", "error": str(e)})
            return {
                "status": state.status,
                "current_agent": state.current_agent,
                "errors": state.errors,
            }
    
    async def _investigation_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Investigation agent node"""
        logger.info(f"Executing investigation for alert {state.alert.alert_id}")
        state.current_agent = "investigation"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "investigation", "status": "started"})
        try:
            result_state = await self.investigation_agent.execute(state, self.event_callback)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "investigation", "status": "completed", "result": result_state.investigation_result.model_dump() if result_state.investigation_result else None})
            return {
                "status": result_state.status,
                "current_agent": result_state.current_agent,
                "investigation_result": self._to_plain(result_state.investigation_result) if result_state.investigation_result else None,
                "warnings": result_state.warnings,
                "errors": result_state.errors,
            }
        except Exception as e:
            logger.error(f"Investigation node error: {str(e)}")
            state.errors.append(f"Investigation error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "investigation", "status": "failed", "error": str(e)})
            return {
                "status": state.status,
                "current_agent": state.current_agent,
                "warnings": state.warnings,
                "errors": state.errors,
            }
    
    async def _decision_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Decision agent node"""
        logger.info(f"Executing decision for alert {state.alert.alert_id}")
        state.current_agent = "decision"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "decision", "status": "started"})
        try:
            result_state = await self.decision_agent.execute(state, self.event_callback)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "decision", "status": "completed", "result": result_state.decision_result.model_dump() if result_state.decision_result else None})
            return {
                "status": result_state.status,
                "current_agent": result_state.current_agent,
                "decision_result": self._to_plain(result_state.decision_result) if result_state.decision_result else None,
                "errors": result_state.errors,
            }
        except Exception as e:
            logger.error(f"Decision node error: {str(e)}")
            state.errors.append(f"Decision error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "decision", "status": "failed", "error": str(e)})
            return {
                "status": state.status,
                "current_agent": state.current_agent,
                "errors": state.errors,
            }
    
    async def _response_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Response agent node"""
        logger.info(f"Executing response for alert {state.alert.alert_id}")
        state.current_agent = "response"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "response", "status": "started"})
        try:
            result_state = await self.response_agent.execute(state, self.event_callback)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "response", "status": "completed", "result": result_state.response_result.model_dump() if result_state.response_result else None})
            return {
                "status": result_state.status,
                "current_agent": result_state.current_agent,
                "response_result": self._to_plain(result_state.response_result) if result_state.response_result else None,
                "completed_at": result_state.completed_at,
                "processing_time_seconds": result_state.processing_time_seconds,
                "errors": result_state.errors,
            }
        except Exception as e:
            logger.error(f"Response node error: {str(e)}")
            state.errors.append(f"Response error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "response", "status": "failed", "error": str(e)})
            return {
                "status": state.status,
                "current_agent": state.current_agent,
                "errors": state.errors,
            }
    
    def _should_investigate(self, state: SOCWorkflowState) -> str:
        """Conditional edge: determine if investigation is needed"""
        
        # If triage failed, skip to decision
        if state.status == AlertStatus.FAILED:
            return "decide"
        
        # If triage says investigation needed, investigate
        if state.triage_result and state.triage_result.requires_investigation:
            return "investigate"
        
        # Otherwise, skip investigation
        return "decide"
    
    def _after_triage(self, state: SOCWorkflowState) -> str:
        """Conditional edge after triage"""
        if state.status == AlertStatus.FAILED:
            return END
        return self._should_investigate(state)
    
    def _after_investigation(self, state: SOCWorkflowState) -> str:
        """Conditional edge after investigation"""
        if state.status == AlertStatus.FAILED:
            return END
        return "decide"
    
    def _after_decision(self, state: SOCWorkflowState) -> str:
        """Conditional edge after decision"""
        if state.status == AlertStatus.FAILED:
            return END
        return "respond"
    
    async def process_alert(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """
        Process a single alert through the complete workflow
        
        Args:
            state: Initial SOCWorkflowState with alert data
            
        Returns:
            Final SOCWorkflowState with all agent results
        """
        logger.info(f"Starting workflow for alert {state.alert.alert_id}")
        
        try:
            # Run the workflow
            print(f"[DEBUG] Calling ainvoke: alert_id={state.alert.alert_id}, workflow_id={state.workflow_id}, status={state.status}")
            # Convert state to a plain dict (no Pydantic models or Enums)
            input_payload = self._to_plain(state)
            
            if not isinstance(input_payload, dict):
                raise TypeError(f"Expected dict for ainvoke input, got {type(input_payload)}")
            
            result = await self.app.ainvoke(input_payload)
            
            # Convert result back to SOCWorkflowState
            if isinstance(result, dict):
                try:
                    # Use model_validate for Pydantic v2, parse_obj for v1
                    if hasattr(SOCWorkflowState, "model_validate"):
                        final_state = SOCWorkflowState.model_validate(result)
                    else:
                        final_state = SOCWorkflowState(**result)
                except Exception as e:
                    logger.error(f"Error converting result to SOCWorkflowState: {str(e)}")
                    raise
            elif isinstance(result, SOCWorkflowState):
                # Already a SOCWorkflowState object
                final_state = result
            else:
                raise TypeError(f"Unexpected result type from ainvoke: {type(result)}")
            print(f"[DEBUG] ainvoke returned: decision_verdict={getattr(final_state.decision_result, 'final_verdict', None)}, priority={getattr(final_state.decision_result, 'priority', None)}, status={final_state.status}, errors={final_state.errors}")
            
            logger.info(f"Workflow completed for alert {state.alert.alert_id}")
            logger.info(f"Final verdict: {final_state.decision_result.final_verdict if final_state.decision_result else 'None'}")
            logger.info(f"Final priority: {final_state.decision_result.priority if final_state.decision_result else 'None'}")
            if self.event_callback:
                self.event_callback(state.workflow_id, {
                    "stage": "final",
                    "status": "completed" if final_state.status != AlertStatus.FAILED else "failed",
                    "verdict": final_state.decision_result.final_verdict if final_state.decision_result else None,
                    "priority": final_state.decision_result.priority if final_state.decision_result else None,
                    "message": "Please retry the alert processing." if final_state.status == AlertStatus.FAILED else None,
                })
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow error for alert {state.alert.alert_id}: {str(e)}")
            state.errors.append(f"Workflow error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {
                    "stage": "final",
                    "status": "failed",
                    "message": "Please retry the alert processing.",
                    "error": str(e)
                })
            return state


# Global orchestrator instance
_orchestrator_instance = None


def get_orchestrator(event_callback: Callable[[str, Dict[str, Any]], None] | None = None) -> SOCOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = SOCOrchestrator(event_callback=event_callback)
    
    return _orchestrator_instance
