"""
Shared context and state models for Agentic SOC POC.
Defines Pydantic models for alert data, agent state, and workflow context.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert processing status"""
    NEW = "new"
    TRIAGING = "triaging"
    INVESTIGATING = "investigating"
    DECIDING = "deciding"
    RESPONDING = "responding"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(str, Enum):
    """Alert verdict classification"""
    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    """Alert priority levels"""
    P1 = "P1"  # Critical - Immediate action
    P2 = "P2"  # High - Action within hours
    P3 = "P3"  # Medium - Action within day
    P4 = "P4"  # Low - Action within week
    P5 = "P5"  # Informational - No action needed


class MITREData(BaseModel):
    """MITRE ATT&CK framework data"""
    tactics: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)


class Assets(BaseModel):
    """Affected assets"""
    host: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    user: Optional[str] = None


class Alert(BaseModel):
    """Raw alert data from SIEM"""
    alert_id: str
    rule_id: str
    rule_name: Optional[str] = None
    timestamp: str
    severity: AlertSeverity
    description: str
    mitre: MITREData = Field(default_factory=MITREData)
    assets: Assets = Field(default_factory=Assets)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class TriageResult(BaseModel):
    """Results from triage agent"""
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    noise_score: float = Field(ge=0.0, le=1.0, description="Higher = more likely noise")
    requires_investigation: bool
    key_indicators: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class InvestigationResult(BaseModel):
    """Results from investigation agent"""
    findings: List[str] = Field(default_factory=list)
    threat_context: Dict[str, Any] = Field(default_factory=dict)
    related_alerts: List[str] = Field(default_factory=list)
    attack_chain: List[str] = Field(default_factory=list)
    risk_score: float = Field(ge=0.0, le=10.0)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DecisionResult(BaseModel):
    """Results from decision agent"""
    final_verdict: Verdict
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    recommended_actions: List[str] = Field(default_factory=list)
    escalation_required: bool
    estimated_impact: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ResponseResult(BaseModel):
    """Results from response agent"""
    actions_taken: List[str] = Field(default_factory=list)
    ticket_id: Optional[str] = None
    notifications_sent: List[str] = Field(default_factory=list)
    automation_applied: List[str] = Field(default_factory=list)
    status: str
    summary: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SOCWorkflowState(BaseModel):
    """Complete state for SOC workflow - passed between agents"""
    
    # Alert Data
    alert: Alert
    
    # Processing Status
    status: AlertStatus = AlertStatus.NEW
    current_agent: Optional[str] = None
    
    # Agent Results
    triage_result: Optional[TriageResult] = None
    investigation_result: Optional[InvestigationResult] = None
    decision_result: Optional[DecisionResult] = None
    response_result: Optional[ResponseResult] = None
    
    # Workflow Metadata
    workflow_id: str
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    
    # Error Handling
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Ground Truth (for evaluation)
    ground_truth: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class WorkflowSummary(BaseModel):
    """Summary of workflow execution for API responses"""
    workflow_id: str
    alert_id: str
    status: AlertStatus
    current_agent: Optional[str]
    verdict: Optional[Verdict]
    priority: Optional[Priority]
    started_at: str
    completed_at: Optional[str]
    processing_time_seconds: Optional[float]
    errors: List[str]


class AgentMetrics(BaseModel):
    """Metrics for agent performance"""
    agent_name: str
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    average_processing_time: float = 0.0
    last_execution: Optional[str] = None


class SystemMetrics(BaseModel):
    """Overall system metrics"""
    total_alerts_processed: int = 0
    alerts_in_progress: int = 0
    true_positives: int = 0
    false_positives: int = 0
    benign: int = 0
    average_mttr: float = 0.0  # Mean Time To Respond
    agent_metrics: Dict[str, AgentMetrics] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
