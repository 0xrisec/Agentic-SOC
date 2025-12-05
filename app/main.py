"""
FastAPI Main Application - Agentic SOC POC
Production-ready REST API for SOC alert processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path

from app.context import (
    Alert, SOCWorkflowState, WorkflowSummary, SystemMetrics, 
    AgentMetrics, AlertStatus, Verdict, Priority
)
from app.orchestrator import get_orchestrator
from app.config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Agentic SOC - Alert Processing API",
    description="AI-powered SOC automation for alert triage and incident response",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo (in production, use database)
workflows: Dict[str, SOCWorkflowState] = {}
system_metrics = SystemMetrics()

# Initialize orchestrator
orchestrator = get_orchestrator()


# Request/Response Models
class ProcessAlertRequest(BaseModel):
    """Request to process a new alert"""
    alert: Alert


class ProcessAlertResponse(BaseModel):
    """Response after alert submission"""
    workflow_id: str
    alert_id: str
    status: str
    message: str


class WorkflowStatusResponse(BaseModel):
    """Detailed workflow status"""
    workflow: WorkflowSummary
    details: Optional[Dict[str, Any]] = None


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard UI"""
    ui_path = Path("ui/dashboard.html")
    if ui_path.exists():
        return FileResponse(ui_path)
    return HTMLResponse("<h1>Agentic SOC API</h1><p>Dashboard UI not found. Access API docs at <a href='/docs'>/docs</a></p>")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/alerts/process", response_model=ProcessAlertResponse)
async def process_alert(request: ProcessAlertRequest, background_tasks: BackgroundTasks):
    """
    Submit an alert for processing
    
    The alert will be processed through the complete SOC workflow:
    1. Triage (noise filtering)
    2. Investigation (if needed)
    3. Decision (verdict and priority)
    4. Response (actions and ticketing)
    """
    try:
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        
        # Create initial workflow state
        initial_state = SOCWorkflowState(
            alert=request.alert,
            workflow_id=workflow_id
        )
        
        # Store workflow
        workflows[workflow_id] = initial_state
        
        # Process in background
        background_tasks.add_task(process_workflow, workflow_id, initial_state)
        
        logger.info(f"Alert {request.alert.alert_id} submitted for processing (workflow: {workflow_id})")
        
        return ProcessAlertResponse(
            workflow_id=workflow_id,
            alert_id=request.alert.alert_id,
            status="processing",
            message="Alert submitted successfully and is being processed"
        )
        
    except Exception as e:
        logger.error(f"Error submitting alert: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit alert: {str(e)}")


async def process_workflow(workflow_id: str, state: SOCWorkflowState):
    """Background task to process workflow"""
    try:
        logger.info(f"Starting background processing for workflow {workflow_id}")
        
        # Process through orchestrator
        final_state = await orchestrator.process_alert(state)
        
        # Update stored workflow
        workflows[workflow_id] = final_state
        
        # Update metrics
        update_system_metrics(final_state)
        
        logger.info(f"Completed processing for workflow {workflow_id}")
        
    except Exception as e:
        logger.error(f"Error processing workflow {workflow_id}: {str(e)}")
        state.errors.append(f"Workflow processing error: {str(e)}")
        state.status = AlertStatus.FAILED
        workflows[workflow_id] = state


def update_system_metrics(state: SOCWorkflowState):
    """Update system metrics based on completed workflow"""
    system_metrics.total_alerts_processed += 1
    
    if state.decision_result:
        verdict = state.decision_result.final_verdict
        if verdict == Verdict.TRUE_POSITIVE:
            system_metrics.true_positives += 1
        elif verdict == Verdict.FALSE_POSITIVE:
            system_metrics.false_positives += 1
        elif verdict == Verdict.BENIGN:
            system_metrics.benign += 1
    
    # Update average MTTR
    if state.processing_time_seconds:
        total_time = system_metrics.average_mttr * (system_metrics.total_alerts_processed - 1)
        system_metrics.average_mttr = (total_time + state.processing_time_seconds) / system_metrics.total_alerts_processed
    
    # Update agent metrics
    agents = ["triage_agent", "investigation_agent", "decision_agent", "response_agent"]
    for agent_name in agents:
        if agent_name not in system_metrics.agent_metrics:
            system_metrics.agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)
        
        agent_metrics = system_metrics.agent_metrics[agent_name]
        agent_metrics.total_processed += 1
        
        if state.status == AlertStatus.COMPLETED:
            agent_metrics.successful += 1
        elif state.status == AlertStatus.FAILED:
            agent_metrics.failed += 1
        
        agent_metrics.last_execution = datetime.utcnow().isoformat()
    
    system_metrics.last_updated = datetime.utcnow().isoformat()


@app.get("/api/alerts/status/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str, include_details: bool = False):
    """
    Get the status of a specific workflow
    
    Args:
        workflow_id: The workflow ID returned when alert was submitted
        include_details: Include full analysis details (triage, investigation, decision, response)
    """
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    state = workflows[workflow_id]
    
    # Create summary
    summary = WorkflowSummary(
        workflow_id=state.workflow_id,
        alert_id=state.alert.alert_id,
        status=state.status,
        current_agent=state.current_agent,
        verdict=state.decision_result.final_verdict if state.decision_result else None,
        priority=state.decision_result.priority if state.decision_result else None,
        started_at=state.started_at,
        completed_at=state.completed_at,
        processing_time_seconds=state.processing_time_seconds,
        errors=state.errors
    )
    
    details = None
    if include_details:
        details = {
            "alert": state.alert.model_dump(),
            "triage": state.triage_result.model_dump() if state.triage_result else None,
            "investigation": state.investigation_result.model_dump() if state.investigation_result else None,
            "decision": state.decision_result.model_dump() if state.decision_result else None,
            "response": state.response_result.model_dump() if state.response_result else None,
            "warnings": state.warnings
        }
    
    return WorkflowStatusResponse(workflow=summary, details=details)


@app.get("/api/alerts/list")
async def list_workflows(
    status: Optional[AlertStatus] = None,
    verdict: Optional[Verdict] = None,
    priority: Optional[Priority] = None,
    limit: int = 50
):
    """
    List all workflows with optional filtering
    
    Args:
        status: Filter by workflow status
        verdict: Filter by final verdict
        priority: Filter by priority
        limit: Maximum number of results
    """
    filtered_workflows = []
    
    for workflow_id, state in workflows.items():
        # Apply filters
        if status and state.status != status:
            continue
        
        if verdict and (not state.decision_result or state.decision_result.final_verdict != verdict):
            continue
        
        if priority and (not state.decision_result or state.decision_result.priority != priority):
            continue
        
        summary = WorkflowSummary(
            workflow_id=state.workflow_id,
            alert_id=state.alert.alert_id,
            status=state.status,
            current_agent=state.current_agent,
            verdict=state.decision_result.final_verdict if state.decision_result else None,
            priority=state.decision_result.priority if state.decision_result else None,
            started_at=state.started_at,
            completed_at=state.completed_at,
            processing_time_seconds=state.processing_time_seconds,
            errors=state.errors
        )
        
        filtered_workflows.append(summary)
        
        if len(filtered_workflows) >= limit:
            break
    
    return {
        "total": len(filtered_workflows),
        "workflows": filtered_workflows
    }


@app.get("/api/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Get overall system metrics and statistics"""
    # Calculate alerts in progress
    in_progress = sum(1 for w in workflows.values() if w.status not in [AlertStatus.COMPLETED, AlertStatus.FAILED])
    system_metrics.alerts_in_progress = in_progress
    
    return system_metrics


@app.post("/api/alerts/batch")
async def process_batch(alerts: List[Alert], background_tasks: BackgroundTasks):
    """
    Process multiple alerts in batch
    
    Returns a list of workflow IDs for tracking
    """
    workflow_ids = []
    
    for alert in alerts:
        workflow_id = str(uuid.uuid4())
        initial_state = SOCWorkflowState(alert=alert, workflow_id=workflow_id)
        workflows[workflow_id] = initial_state
        background_tasks.add_task(process_workflow, workflow_id, initial_state)
        workflow_ids.append({
            "alert_id": alert.alert_id,
            "workflow_id": workflow_id
        })
    
    logger.info(f"Batch processing started for {len(alerts)} alerts")
    
    return {
        "message": f"Batch processing started for {len(alerts)} alerts",
        "workflows": workflow_ids
    }


@app.get("/api/alerts/sample")
async def get_sample_alerts():
    """Get sample alerts from the test data file"""
    try:
        with open("data/alerts.json", "r") as f:
            data = json.load(f)
        
        return {
            "total": len(data.get("alerts", [])),
            "alerts": data.get("alerts", [])
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sample alerts file not found")


@app.get("/api/ground-truth")
async def get_ground_truth():
    """Get ground truth data for validation"""
    try:
        with open("data/ground_truth.json", "r") as f:
            data = json.load(f)
        
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ground truth file not found")


@app.delete("/api/workflows/clear")
async def clear_workflows():
    """Clear all workflows (for testing/demo purposes)"""
    workflows.clear()
    
    # Reset metrics
    global system_metrics
    system_metrics = SystemMetrics()
    
    logger.info("All workflows and metrics cleared")
    
    return {"message": "All workflows cleared successfully"}


# Mount static files for UI
try:
    app.mount("/ui", StaticFiles(directory="ui"), name="ui")
except Exception as e:
    logger.warning(f"Could not mount UI static files: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Agentic SOC API server...")
    logger.info(f"API will be available at http://{settings.api_host}:{settings.api_port}")
    logger.info(f"API documentation at http://{settings.api_host}:{settings.api_port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
