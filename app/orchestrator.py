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
        
        # After triage, decide whether to investigate
        workflow.add_conditional_edges(
            "triage",
            self._should_investigate,
            {
                "investigate": "investigate",
                "decide": "decide"
            }
        )
        
        # After investigation, go to decision
        workflow.add_edge("investigate", "decide")
        
        # After decision, go to response
        workflow.add_edge("decide", "respond")
        
        # After response, end
        workflow.add_edge("respond", END)
        
        return workflow
    
    async def _triage_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Triage agent node"""
        logger.info(f"Executing triage for alert {state.alert.alert_id}")
        state.current_agent = "triage"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "triage", "status": "started"})
        try:
            result_state = await self.triage_agent.execute(state)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "triage", "status": "completed", "result": result_state.triage_result.model_dump() if result_state.triage_result else None})
            return result_state
        except Exception as e:
            logger.error(f"Triage node error: {str(e)}")
            state.errors.append(f"Triage error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "triage", "status": "failed", "error": str(e)})
            return state
    
    async def _investigation_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Investigation agent node"""
        logger.info(f"Executing investigation for alert {state.alert.alert_id}")
        state.current_agent = "investigation"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "investigation", "status": "started"})
        try:
            result_state = await self.investigation_agent.execute(state)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "investigation", "status": "completed", "result": result_state.investigation_result.model_dump() if result_state.investigation_result else None})
            return result_state
        except Exception as e:
            logger.error(f"Investigation node error: {str(e)}")
            state.errors.append(f"Investigation error: {str(e)}")
            # Don't fail completely - continue to decision
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "investigation", "status": "failed", "error": str(e)})
            return state
    
    async def _decision_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Decision agent node"""
        logger.info(f"Executing decision for alert {state.alert.alert_id}")
        state.current_agent = "decision"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "decision", "status": "started"})
        try:
            result_state = await self.decision_agent.execute(state)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "decision", "status": "completed", "result": result_state.decision_result.model_dump() if result_state.decision_result else None})
            return result_state
        except Exception as e:
            logger.error(f"Decision node error: {str(e)}")
            state.errors.append(f"Decision error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "decision", "status": "failed", "error": str(e)})
            return state
    
    async def _response_node(self, state: SOCWorkflowState) -> SOCWorkflowState:
        """Response agent node"""
        logger.info(f"Executing response for alert {state.alert.alert_id}")
        state.current_agent = "response"
        if self.event_callback:
            self.event_callback(state.workflow_id, {"stage": "response", "status": "started"})
        try:
            result_state = await self.response_agent.execute(state)
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "response", "status": "completed", "result": result_state.response_result.model_dump() if result_state.response_result else None})
            return result_state
        except Exception as e:
            logger.error(f"Response node error: {str(e)}")
            state.errors.append(f"Response error: {str(e)}")
            state.status = AlertStatus.FAILED
            if self.event_callback:
                self.event_callback(state.workflow_id, {"stage": "response", "status": "failed", "error": str(e)})
            return state
    
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
            final_state = await self.app.ainvoke(state)
            
            logger.info(f"Workflow completed for alert {state.alert.alert_id}")
            logger.info(f"Final verdict: {final_state.decision_result.final_verdict if final_state.decision_result else 'None'}")
            logger.info(f"Final priority: {final_state.decision_result.priority if final_state.decision_result else 'None'}")
            if self.event_callback:
                self.event_callback(state.workflow_id, {
                    "stage": "final",
                    "status": "completed",
                    "verdict": final_state.decision_result.final_verdict if final_state.decision_result else None,
                    "priority": final_state.decision_result.priority if final_state.decision_result else None,
                })
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow error for alert {state.alert.alert_id}: {str(e)}")
            state.errors.append(f"Workflow error: {str(e)}")
            state.status = AlertStatus.FAILED
            return state


# Global orchestrator instance
_orchestrator_instance = None


def get_orchestrator(event_callback: Callable[[str, Dict[str, Any]], None] | None = None) -> SOCOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = SOCOrchestrator(event_callback=event_callback)
    
    return _orchestrator_instance
