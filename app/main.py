"""
FastAPI Main Application - Agentic SOC POC
Production-ready REST API for SOC alert processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi import WebSocket, WebSocketDisconnect
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
import tempfile


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

# CORS middleware (avoid '*' with credentials; include 'null' for file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# In-memory storage for demo (in production, use database)
workflows: Dict[str, SOCWorkflowState] = {}
system_metrics = SystemMetrics()

# Initialize orchestrator
# WebSocket connection manager to broadcast workflow updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, workflow_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(workflow_id, []).append(websocket)

    def disconnect(self, workflow_id: str, websocket: WebSocket):
        conns = self.active_connections.get(workflow_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(workflow_id, None)

    async def broadcast(self, workflow_id: str, message: Dict[str, Any]):
        for ws in self.active_connections.get(workflow_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                # Best-effort; skip failures
                pass


manager = ConnectionManager()

# Event queue for async broadcasting
event_queue: Dict[str, list] = {}

def _event_callback(workflow_id: str, payload: Dict[str, Any]):
    """Queue events for async broadcasting - called from orchestrator"""
    if workflow_id not in event_queue:
        event_queue[workflow_id] = []
    
    # Normalize payload for UI-V2 consumers
    normalized = {"type": "progress"}
    normalized.update(payload)
    
    # Map stage/status to UI fields
    stage = payload.get("stage")
    status = payload.get("status")
    
    if stage in {"triage", "investigation", "decision", "response"}:
        normalized["current_agent"] = stage
        agent_status = {
            "triage": "waiting",
            "investigation": "waiting",
            "decision": "waiting",
            "response": "waiting"
        }
        
        if status == "started":
            agent_status[stage] = "running"
            normalized["progress"] = {
                "triage": 15,
                "investigation": 40,
                "decision": 65,
                "response": 85
            }.get(stage, 10)
            normalized["message"] = f"Starting {stage} analysis..."
            normalized["agent"] = stage.capitalize() + " Agent"
            normalized["level"] = "processing"
        elif status == "completed":
            agent_status[stage] = "completed"
            normalized["progress"] = {
                "triage": 25,
                "investigation": 50,
                "decision": 75,
                "response": 95
            }.get(stage, 50)
            normalized["message"] = f"{stage.capitalize()} completed"
            normalized["agent"] = stage.capitalize() + " Agent"
            normalized["level"] = "success"
        elif status == "failed":
            agent_status[stage] = "error"
            normalized["progress"] = 100
            normalized["message"] = f"{stage.capitalize()} error: {payload.get('error', 'Unknown error')}"
            normalized["agent"] = stage.capitalize() + " Agent"
            normalized["level"] = "error"
            
        normalized["agent_status"] = agent_status
    
    # Add timestamp
    normalized["timestamp"] = datetime.utcnow().strftime("%H:%M:%S")
    
    # Queue the event
    event_queue[workflow_id].append(normalized)
    logger.info(f"Event queued for {workflow_id}: {stage} - {status}")


orchestrator = get_orchestrator(event_callback=_event_callback)


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


# Helper Functions
def normalize_alert_data(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize alert data to fix common validation issues
    - Add missing timestamp field
    - Convert severity to lowercase
    - Map field names to expected schema
    - Add default values for optional fields
    """
    normalized = alert_data.copy()
    
    # Fix severity - convert to lowercase (High -> high, Critical -> critical, etc.)
    if "severity" in normalized:
        severity_str = str(normalized["severity"]).lower()
        # Map common variations
        severity_map = {
            "informational": "info",
            "information": "info",
            "inf": "info"
        }
        normalized["severity"] = severity_map.get(severity_str, severity_str)
    else:
        normalized["severity"] = "medium"  # Default
    
    # Add timestamp if missing - try to extract from evidence or use current time
    if "timestamp" not in normalized:
        # Try to get first event time from evidence_sample
        if "evidence_sample" in normalized and len(normalized["evidence_sample"]) > 0:
            first_event = normalized["evidence_sample"][0]
            if "time_utc" in first_event:
                normalized["timestamp"] = first_event["time_utc"]
            else:
                normalized["timestamp"] = datetime.utcnow().isoformat()
        else:
            normalized["timestamp"] = datetime.utcnow().isoformat()
    
    # Ensure required fields exist
    if "alert_id" not in normalized:
        normalized["alert_id"] = f"ALERT-{uuid.uuid4().hex[:8].upper()}"
    
    if "rule_id" not in normalized:
        normalized["rule_id"] = normalized.get("alert_id", "UNKNOWN")
    
    if "description" not in normalized:
        normalized["description"] = normalized.get("title", "No description provided")
    
    # Map MITRE data - handle both nested and flat structures
    if "mitre" not in normalized:
        mitre_data = {
            "tactics": normalized.get("tactics", []),
            "techniques": normalized.get("techniques", [])
        }
        normalized["mitre"] = mitre_data
    
    # Map assets - handle various field names
    if "assets" not in normalized:
        entities = normalized.get("entities", {})
        assets_data = {
            "host": entities.get("host"),
            "source_ip": entities.get("source_ip"),
            "destination_ip": entities.get("destination_ip"),
            "user": entities.get("user") or entities.get("account")
        }
        normalized["assets"] = assets_data
    
    # Store original data in raw_data
    if "raw_data" not in normalized:
        # Store evidence and other non-standard fields
        raw_data = {}
        for key in ["evidence_sample", "time_window_minutes", "thresholds", "entities", 
                    "category", "title", "tactics", "techniques"]:
            if key in normalized:
                raw_data[key] = normalized[key]
        normalized["raw_data"] = raw_data
    
    return normalized


# API Endpoints
@app.post("/api/upload-alert")
async def upload_alert(file: UploadFile = File(...)):
    """Upload a JSON file containing a single alert or list of alerts."""
    try:
        contents = await file.read()
        data = json.loads(contents.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")

    # Accept either single alert or list under key
    alerts_payload = []
    if isinstance(data, dict) and "alerts" in data and isinstance(data["alerts"], list):
        alerts_payload = data["alerts"]
    elif isinstance(data, list):
        alerts_payload = data
    elif isinstance(data, dict):
        alerts_payload = [data]
    else:
        raise HTTPException(status_code=400, detail="Unsupported alert JSON format")

    submitted = []
    for raw in alerts_payload:
        try:
            # Normalize alert data
            raw = normalize_alert_data(raw)
            # Create Alert pydantic model
            alert = Alert(**raw)
            # Reuse existing process pipeline
            req = ProcessAlertRequest(alert=alert)
            # Generate ID and kick off processing inline (without BackgroundTasks here)
            workflow_id = str(uuid.uuid4())
            initial_state = SOCWorkflowState(alert=alert, workflow_id=workflow_id)
            workflows[workflow_id] = initial_state
            # Start processing asynchronously
            import asyncio
            asyncio.create_task(process_workflow(workflow_id, initial_state))
            # Notify
            await manager.broadcast(workflow_id, {"type": "status", "stage": "submitted", "status": "processing"})
            submitted.append({"workflow_id": workflow_id, "alert_id": alert.alert_id})
        except Exception as e:
            submitted.append({"error": f"Failed to submit alert: {str(e)}", "raw": raw})

    return {"message": f"Uploaded {len(submitted)} alerts", "workflows": submitted}

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve landing page with UI options"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agentic SOC - AI-Powered SOC Automation</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
                color: #fff;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                max-width: 800px;
                padding: 40px;
            }
            h1 {
                font-size: 48px;
                margin-bottom: 20px;
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p {
                font-size: 18px;
                color: #9ca3af;
                margin-bottom: 40px;
            }
            .options {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .option {
                background: rgba(99, 102, 241, 0.1);
                border: 2px solid rgba(99, 102, 241, 0.3);
                border-radius: 12px;
                padding: 30px;
                text-decoration: none;
                color: #fff;
                transition: all 0.3s ease;
            }
            .option:hover {
                transform: translateY(-5px);
                border-color: #6366f1;
                background: rgba(99, 102, 241, 0.2);
                box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
            }
            .option h3 {
                margin: 0 0 10px 0;
                font-size: 24px;
            }
            .option p {
                margin: 0;
                font-size: 14px;
                color: #9ca3af;
            }
            .badge {
                display: inline-block;
                background: #10b981;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 10px;
            }
            .links {
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
            }
            .links a {
                color: #6366f1;
                text-decoration: none;
                padding: 10px 20px;
                border: 1px solid #6366f1;
                border-radius: 6px;
                transition: all 0.3s ease;
            }
            .links a:hover {
                background: #6366f1;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Agentic SOC</h1>
            <p>AI-Powered Level 1 SOC Automation with Multi-Agent Intelligence</p>
            
            <div class="options">
                <a href="/ui-v2/index.html" class="option">
                    <h3>New Dashboard <span class="badge">V2</span></h3>
                    <p>Professional Copilot-inspired UI with real-time agent tracking</p>
                </a>
                
                <a href="/ui/dashboard.html" class="option">
                    <h3>Classic Dashboard</h3>
                    <p>Original dashboard interface</p>
                </a>
            </div>
            
            <div class="links">
                <a href="/docs">📚 API Documentation</a>
                <a href="/health">🔍 Health Check</a>
            </div>
        </div>
    </body>
    </html>
    """)

# Mount static files for UI assets (CSS, JS)
app.mount("/static", StaticFiles(directory="ui"), name="static")

# Provide a favicon endpoint to avoid 404s (optional file)
@app.get("/favicon.ico")
async def favicon():
    ico_path = Path("ui/favicon.ico")
    if ico_path.exists():
        return FileResponse(ico_path)
    # No favicon available; return 204 to suppress 404 noise
    from fastapi import Response
    return Response(status_code=204)

# Backward-compatible direct asset routes for clients requesting root paths
@app.get("/styles.css")
async def styles_css():
    css_path = Path("ui/styles.css")
    if css_path.exists():
        return FileResponse(css_path)
    raise HTTPException(status_code=404, detail="styles.css not found")

@app.get("/dashboard.js")
async def dashboard_js():
    js_path = Path("ui/dashboard.js")
    if js_path.exists():
        return FileResponse(js_path)
    raise HTTPException(status_code=404, detail="dashboard.js not found")


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

        # Notify clients that workflow was created
        await manager.broadcast(workflow_id, {"type": "status", "stage": "submitted", "status": "processing"})
        
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
        
        # Initialize event queue for this workflow
        event_queue[workflow_id] = []
        
        # Broadcast initial status
        await manager.broadcast(workflow_id, {
            "type": "status",
            "status": "processing",
            "current_agent": None,
            "message": "Starting analysis",
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        })
        
        # Process through orchestrator
        final_state = await orchestrator.process_alert(state)
        
        # Broadcast all queued events
        if workflow_id in event_queue:
            for event in event_queue[workflow_id]:
                await manager.broadcast(workflow_id, event)
                # Small delay to ensure order
                import asyncio
                await asyncio.sleep(0.1)
        
        # Update stored workflow
        workflows[workflow_id] = final_state
        
        # Update metrics
        update_system_metrics(final_state)
        
        logger.info(f"Completed processing for workflow {workflow_id}")
        
        # Emit final status
        final_message = {
            "type": "final",
            "status": final_state.status.value if final_state.status else "completed",
            "verdict": final_state.decision_result.final_verdict.value if final_state.decision_result and final_state.decision_result.final_verdict else None,
            "priority": final_state.decision_result.priority.value if final_state.decision_result and final_state.decision_result.priority else None,
            "errors": final_state.errors,
            "completed": True,
            "progress": 100,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        }
        
        await manager.broadcast(workflow_id, final_message)
        
        # Clean up event queue
        if workflow_id in event_queue:
            del event_queue[workflow_id]
        
    except Exception as e:
        logger.error(f"Error processing workflow {workflow_id}: {str(e)}")
        state.errors.append(f"Workflow processing error: {str(e)}")
        state.status = AlertStatus.FAILED
        workflows[workflow_id] = state
        await manager.broadcast(workflow_id, {
            "type": "final",
            "status": "failed",
            "error": str(e),
            "completed": True,
            "progress": 100,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        })
        
        # Clean up event queue
        if workflow_id in event_queue:
            del event_queue[workflow_id]


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


@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket to stream live workflow updates to the UI."""
    await manager.connect(workflow_id, websocket)
    try:
        # Optionally send initial status if exists
        if workflow_id in workflows:
            state = workflows[workflow_id]
            await websocket.send_json({
                "type": "status",
                "status": state.status,
                "current_agent": state.current_agent,
            })
        # Keep connection open; client may send pings
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(workflow_id, websocket)


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


# ============================================================================
# UI-V2 API Endpoints - For the new professional Copilot-like UI
# ============================================================================

# Global state for UI-V2
current_analysis = {
    "workflow_id": None,
    "progress": 0,
    "currentAgent": None,
    "agentStatus": {},
    "activities": [],
    "completed": False,
    "results": None
}

@app.post("/api/upload-and-run")
async def upload_and_run(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload alert file and start analysis for UI-V2
    Returns immediately and processing happens in background
    """
    try:
        # Reset current analysis state
        current_analysis.clear()
        current_analysis.update({
            "workflow_id": None,
            "progress": 0,
            "currentAgent": None,
            "agentStatus": {
                "triage": "waiting",
                "investigation": "waiting",
                "decision": "waiting",
                "response": "waiting"
            },
            "activities": [],
            "completed": False,
            "results": None
        })
        
        # Read and parse file
        contents = await file.read()
        data = json.loads(contents.decode("utf-8"))
        
        # Extract alert data
        alerts_payload = []
        if isinstance(data, dict) and "alerts" in data and isinstance(data["alerts"], list):
            alerts_payload = data["alerts"]
        elif isinstance(data, list):
            alerts_payload = data
        elif isinstance(data, dict):
            alerts_payload = [data]
        else:
            return {"success": False, "message": "Invalid alert file format"}
        
        if not alerts_payload:
            return {"success": False, "message": "No alerts found in file"}
        
        # Process first alert only for demo
        alert_data = alerts_payload[0]
        
        # Normalize alert data to fix common issues
        alert_data = normalize_alert_data(alert_data)
        
        alert = Alert(**alert_data)
        
        # Generate workflow ID
        workflow_id = str(uuid.uuid4())
        current_analysis["workflow_id"] = workflow_id
        
        # Add initial activity
        current_analysis["activities"].append({
            "agent": "System",
            "message": f"Starting analysis for alert {alert.alert_id}",
            "type": "start",
            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
        })
        
        # Create initial workflow state
        initial_state = SOCWorkflowState(
            alert=alert,
            workflow_id=workflow_id
        )
        
        # Store workflow
        workflows[workflow_id] = initial_state
        
        # Process in background using unified workflow
        background_tasks.add_task(process_workflow, workflow_id, initial_state)
        
        return {
            "success": True,
            "message": "Analysis started",
            "workflow_id": workflow_id
        }
        
    except Exception as e:
        logger.error(f"Error in upload-and-run: {str(e)}")
        return {"success": False, "message": str(e)}


@app.get("/api/status")
async def get_analysis_status():
    """
    Get current analysis status - fallback for polling when WebSocket not available
    Returns progress, current agent, activities, and results
    """
    # Get most recent workflow if available
    if not workflows:
        return {
            "workflow_id": None,
            "progress": 0,
            "currentAgent": None,
            "agentStatus": {
                "triage": "waiting",
                "investigation": "waiting",
                "decision": "waiting",
                "response": "waiting"
            },
            "activities": [],
            "completed": False,
            "results": None
        }
    
    # Get the most recent workflow (for UI-V2 compatibility)
    workflow_id = current_analysis.get("workflow_id") or list(workflows.keys())[-1]
    state = workflows.get(workflow_id)
    
    if not state:
        return current_analysis
    
    # Build response from workflow state
    response = {
        "workflow_id": workflow_id,
        "progress": 0,
        "currentAgent": state.current_agent,
        "agentStatus": {
            "triage": "waiting",
            "investigation": "waiting",
            "decision": "waiting",
            "response": "waiting"
        },
        "activities": [],
        "completed": state.status in [AlertStatus.COMPLETED, AlertStatus.FAILED],
        "results": None
    }
    
    # Update agent status based on completed stages
    if state.triage_result:
        response["agentStatus"]["triage"] = "completed"
        response["progress"] = 25
    if state.investigation_result:
        response["agentStatus"]["investigation"] = "completed"
        response["progress"] = 50
    if state.decision_result:
        response["agentStatus"]["decision"] = "completed"
        response["progress"] = 75
    if state.response_result:
        response["agentStatus"]["response"] = "completed"
        response["progress"] = 100
    
    # Format results
    if response["completed"] and state.decision_result:
        response["results"] = {
            "severity": state.decision_result.priority.value if state.decision_result.priority else "unknown",
            "recommendation": state.decision_result.final_verdict.value if state.decision_result.final_verdict else "No verdict",
            "summary": state.triage_result.reasoning if state.triage_result else "Analysis completed"
        }
        if state.response_result and state.response_result.actions:
            response["results"]["actions"] = state.response_result.actions
    
    return response


# ============================================================================
# Static File Mounts
# ============================================================================

# Mount UI-V2 (new professional UI)
try:
    app.mount("/ui-v2", StaticFiles(directory="ui-v2"), name="ui-v2")
    logger.info("Mounted UI-V2 at /ui-v2")
except Exception as e:
    logger.warning(f"Could not mount UI-V2 static files: {str(e)}")

# Mount original UI
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
