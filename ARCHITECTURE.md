# 🏗️ Agentic SOC - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Web Dashboard (Browser)                          │  │
│  │  • Real-time metrics    • Alert visualization             │  │
│  │  • Auto-refresh         • Detailed analysis view          │  │
│  │  HTML + CSS + Vanilla JavaScript                          │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │ HTTP/REST                               │
└───────────────────────┼─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Alert      │  │   Status     │  │   Metrics    │         │
│  │  Ingestion   │  │   Tracking   │  │   Endpoint   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                 │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│               ORCHESTRATION LAYER (LangGraph)                     │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Workflow State Management                     │  │
│  │  • SOCWorkflowState (Pydantic)                            │  │
│  │  • State transitions                                       │  │
│  │  • Conditional routing                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│                    ┌──────────────┐                             │
│                    │  LangGraph   │                             │
│                    │   Workflow   │                             │
│                    └──────┬───────┘                             │
│                           │                                      │
│         ┌─────────────────┼─────────────────┬─────────────┐    │
│         │                 │                 │             │    │
└─────────┼─────────────────┼─────────────────┼─────────────┼────┘
          │                 │                 │             │
┌─────────▼─────────────────▼─────────────────▼─────────────▼────┐
│                     AGENT LAYER (GPT-4)                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Triage     │  │ Investigation│  │   Decision   │         │
│  │   Agent      │  │    Agent     │  │    Agent     │         │
│  │              │  │              │  │              │         │
│  │ • Filter     │  │ • Threat     │  │ • Verdict    │         │
│  │   noise      │  │   Intel      │  │ • Priority   │         │
│  │ • Verdict    │  │ • Risk       │  │ • Impact     │         │
│  │ • Confidence │  │   score      │  │ • Actions    │         │
│  │              │  │ • Attack     │  │              │         │
│  │ Temp: 0.1    │  │   chain      │  │ Temp: 0.1    │         │
│  │              │  │              │  │              │         │
│  │              │  │ Temp: 0.3    │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Response   │                                               │
│  │    Agent     │                                               │
│  │              │                                               │
│  │ • Ticket     │                                               │
│  │   creation   │                                               │
│  │ • Notify     │                                               │
│  │ • Actions    │                                               │
│  │              │                                               │
│  │ Temp: 0.2    │                                               │
│  └──────────────┘                                               │
│                                                                  │
└──────────────────┬───────────────────┬───────────────────────────┘
                   │                   │
┌──────────────────▼──────┐   ┌────────▼──────────────────────────┐
│     DATA LAYER          │   │    KNOWLEDGE BASE                  │
│                         │   │                                    │
│  ┌─────────────────┐   │   │  ┌──────────────────────────────┐ │
│  │ alerts.json     │   │   │  │  Agent Prompts               │ │
│  │ (15 samples)    │   │   │  │  • triage_agent.md           │ │
│  └─────────────────┘   │   │  │  • investigation_agent.md    │ │
│                         │   │  │  • decision_agent.md         │ │
│  ┌─────────────────┐   │   │  │  • response_agent.md         │ │
│  │ ground_truth    │   │   │  │                              │ │
│  │ .json           │   │   │  │  Domain Knowledge:           │ │
│  │ (validation)    │   │   │  │  • MITRE ATT&CK              │ │
│  └─────────────────┘   │   │  │  • SOC best practices        │ │
│                         │   │  │  • Priority SLAs             │ │
│  ┌─────────────────┐   │   │  │  • Response playbooks        │ │
│  │ threat_intel    │   │   │  └──────────────────────────────┘ │
│  │ .json           │   │   │                                    │
│  │ (IOCs, IPs)     │   │   └────────────────────────────────────┘
│  └─────────────────┘   │
│                         │
└─────────────────────────┘
```

---

## Data Flow

### 1. Alert Ingestion
```
User/SIEM → POST /api/alerts/process → FastAPI
                                         ↓
                                    Create SOCWorkflowState
                                         ↓
                                    Background Task
                                         ↓
                                    LangGraph Orchestrator
```

### 2. Agent Processing
```
Orchestrator
    ↓
┌───▼────────────┐
│ Triage Agent   │ → requires_investigation?
└───┬────────────┘
    │                Yes             No
    ├─────────────────┴───────────────┐
    │                                 │
┌───▼─────────────┐                  │
│ Investigation   │                  │
│ Agent           │                  │
└───┬─────────────┘                  │
    │                                 │
    └─────────────┬───────────────────┘
                  ↓
          ┌───────────────┐
          │ Decision      │
          │ Agent         │
          └───┬───────────┘
              ↓
          ┌───────────────┐
          │ Response      │
          │ Agent         │
          └───┬───────────┘
              ↓
          Final State
              ↓
          Update Metrics
```

### 3. State Management
```
SOCWorkflowState {
  alert: Alert
  status: AlertStatus
  triage_result: TriageResult
  investigation_result: InvestigationResult
  decision_result: DecisionResult
  response_result: ResponseResult
  workflow_id: str
  errors: List[str]
  processing_time: float
}
```

---

## Component Details

### FastAPI Server (`app/main.py`)
- **Endpoints**:
  - `POST /api/alerts/process` - Submit alert
  - `GET /api/alerts/status/{id}` - Check status
  - `GET /api/alerts/list` - List workflows
  - `GET /api/metrics` - System metrics
  - `POST /api/alerts/batch` - Batch processing
  - `DELETE /api/workflows/clear` - Reset

- **Features**:
  - Async background processing
  - CORS enabled
  - Auto-generated API docs
  - In-memory storage (demo)

### LangGraph Orchestrator (`app/orchestrator.py`)
- **Workflow Graph**:
  ```
  START → triage → [investigate?] → decide → respond → END
  ```

- **State Transitions**:
  - Entry: triage
  - Conditional: investigate (based on triage result)
  - Sequential: decide → respond
  - Exit: END

- **Error Handling**:
  - Graceful degradation
  - Error logging in state
  - Continue on non-critical errors

### Agents (`agents/`)

#### Triage Agent
- **Purpose**: Rapid assessment, noise filtering
- **Input**: Alert details
- **Output**: Verdict, confidence, noise_score, requires_investigation
- **Temperature**: 0.1 (deterministic)
- **Processing Time**: 2-5s

#### Investigation Agent
- **Purpose**: Deep analysis, threat correlation
- **Input**: Alert + Triage + Threat Intel
- **Output**: Findings, risk_score, attack_chain, evidence
- **Temperature**: 0.3 (balanced)
- **Processing Time**: 3-8s
- **Conditional**: Only if triage.requires_investigation

#### Decision Agent
- **Purpose**: Final verdict, prioritization
- **Input**: Alert + Triage + Investigation
- **Output**: Final verdict, priority (P1-P5), actions, impact
- **Temperature**: 0.1 (deterministic)
- **Processing Time**: 1-2s

#### Response Agent
- **Purpose**: Ticket creation, notifications, actions
- **Input**: All previous results
- **Output**: Ticket ID, actions taken, notifications
- **Temperature**: 0.2 (mostly deterministic)
- **Processing Time**: 1-2s

### Shared Context (`app/context.py`)
- **Pydantic Models**:
  - Alert
  - TriageResult
  - InvestigationResult
  - DecisionResult
  - ResponseResult
  - SOCWorkflowState
  - SystemMetrics

- **Enums**:
  - AlertStatus (new, triaging, investigating, etc.)
  - Verdict (true_positive, false_positive, benign, suspicious)
  - Priority (P1-P5)
  - AlertSeverity (critical, high, medium, low, info)

### Web Dashboard (`ui/`)
- **Technology**: Vanilla JS (no frameworks)
- **Features**:
  - Real-time metrics
  - Auto-refresh (5s interval)
  - Alert table with filtering
  - Detailed modal view
  - Toast notifications
  - Loading indicators

---

## Design Decisions

### Why LangGraph?
- **State Management**: Built-in state handling across agents
- **Conditional Routing**: Skip investigation if not needed
- **Observability**: Clear workflow visualization
- **Extensibility**: Easy to add new agents

### Why GPT-4?
- **Accuracy**: Best-in-class reasoning
- **Context Window**: 128K tokens
- **Structured Output**: JSON mode support
- **Reliability**: Production-ready API

### Why FastAPI?
- **Performance**: Async/await support
- **Developer Experience**: Auto-generated docs
- **Type Safety**: Pydantic integration
- **Modern**: Python 3.11+ support

### Why Pydantic?
- **Validation**: Automatic data validation
- **Type Safety**: Runtime type checking
- **Serialization**: JSON conversion
- **Documentation**: Schema generation

---

## Security Considerations

### Current Implementation (POC)
- ⚠️ No authentication
- ⚠️ No authorization
- ⚠️ In-memory storage
- ⚠️ No encryption at rest
- ⚠️ API key in environment

### Production Requirements
- ✅ OAuth2/JWT authentication
- ✅ Role-based access control (RBAC)
- ✅ Database with encryption
- ✅ TLS/HTTPS
- ✅ Secrets management (Vault)
- ✅ Rate limiting
- ✅ Input validation
- ✅ Audit logging
- ✅ Network segmentation

---

## Scalability Considerations

### Current Capacity
- **Sequential Processing**: 1 alert at a time
- **Throughput**: ~4-8 alerts/minute
- **Concurrency**: Configurable (default: 5)
- **Storage**: In-memory (limited by RAM)

### Production Scaling
```
┌─────────────────────────────────────────────┐
│           Load Balancer (Nginx/ALB)         │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐
│ FastAPI     │ │ FastAPI   │ │ FastAPI    │
│ Instance 1  │ │ Instance 2│ │ Instance 3 │
└──────┬──────┘ └────┬──────┘ └─────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                      │
            ┌─────────▼─────────┐
            │  Message Queue    │
            │  (RabbitMQ/Kafka) │
            └─────────┬─────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼────┐  ┌───▼────┐  ┌───▼────┐
    │ Worker  │  │ Worker │  │ Worker │
    │    1    │  │    2   │  │    3   │
    └─────────┘  └────────┘  └────────┘
         │            │            │
         └────────────┼────────────┘
                      │
              ┌───────▼────────┐
              │   PostgreSQL   │
              │   + Redis      │
              └────────────────┘
```

**Scaling Strategy**:
1. Horizontal scaling (multiple API instances)
2. Message queue for async processing
3. Worker pool for parallel agent execution
4. Database for persistent storage
5. Redis for caching and session management

**Expected Performance**:
- **Throughput**: 100+ alerts/minute
- **Latency**: P95 < 30s
- **Availability**: 99.9%

---

## Monitoring & Observability

### Metrics to Track
- **Processing Time**: Per agent and total
- **Throughput**: Alerts per minute
- **Accuracy**: Verdict vs. ground truth
- **Error Rate**: Failed workflows
- **API Latency**: Response times
- **Cost**: OpenAI API usage

### Logging
```python
# Structured logging with context
logger.info(
    "workflow_completed",
    extra={
        "workflow_id": workflow_id,
        "alert_id": alert_id,
        "verdict": verdict,
        "priority": priority,
        "processing_time": elapsed,
        "agents_executed": agents
    }
)
```

### Alerting
- Processing time > 60s
- Error rate > 5%
- Queue depth > 100
- API 5xx errors
- Low disk space

---

## Cost Analysis

### OpenAI API Costs (GPT-4 Turbo)
- **Input**: $10 per 1M tokens
- **Output**: $30 per 1M tokens

**Per Alert**:
- Triage: ~2K tokens → $0.02
- Investigation: ~3K tokens → $0.04
- Decision: ~2K tokens → $0.02
- Response: ~1.5K tokens → $0.02
- **Total**: ~$0.10 per alert

**Monthly (1000 alerts/day)**:
- Cost: $3,000/month
- vs. L1 Analyst: $12,500/month
- **Savings**: $9,500/month (76%)

---

## Conclusion

This architecture provides:
- ✅ **Modularity**: Independent, replaceable agents
- ✅ **Scalability**: Easy to scale horizontally
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Observability**: Complete audit trail
- ✅ **Extensibility**: Easy to add features
- ✅ **Production-Ready**: Clear path to production

The POC demonstrates feasibility. With database integration, authentication, and scaling infrastructure, this system can handle production workloads.
