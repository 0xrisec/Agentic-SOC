# Mock LLM Provider - Quick Reference

## Overview

The Mock LLM provider allows you to run the Agentic SOC application **without any API keys**. It returns realistic, agent-specific mock data that simulates real LLM responses.

## Features

✅ **No API keys required** - Works immediately without configuration  
✅ **Agent-aware** - Intelligently detects which agent is calling and returns appropriate data  
✅ **Realistic responses** - Returns varied, production-like JSON data  
✅ **Full workflow support** - All 4 agents work seamlessly  
✅ **Perfect for testing** - Great for demos, development, and debugging  

## Quick Start

### 1. Set Mock Provider (Default)

The application uses mock provider by default. No configuration needed!

Or explicitly set in `.env`:
```env
LLM_PROVIDER=mock
```

### 2. Run the Application

```bash
# Activate virtual environment
source .venv312/bin/activate

# Start the application
python run.py
```

### 3. Test the Mock Provider

```bash
# Run the test script
python test_mock_llm.py
```

## Mock Data Examples

### Triage Agent Response
```json
{
  "verdict": "suspicious",
  "confidence": 0.81,
  "noise_score": 0.37,
  "requires_investigation": true,
  "key_indicators": [
    "Geographical anomaly in access pattern",
    "Unusual login time detected"
  ],
  "reasoning": "The alert contains several high-confidence indicators..."
}
```

### Investigation Agent Response
```json
{
  "findings": [
    "Lateral movement detected across multiple systems",
    "Credential reuse pattern identified"
  ],
  "threat_context": {
    "threat_actor": "APT28",
    "campaign": "Operation CloudHopper",
    "ttps": ["T1078", "T1021", "T1059"]
  },
  "risk_score": 7.5,
  "evidence": {...}
}
```

### Decision Agent Response
```json
{
  "final_verdict": "true_positive",
  "priority": "P2",
  "confidence": 0.85,
  "recommended_actions": [
    "Contain affected host",
    "Reset user credentials"
  ],
  "escalation_required": true,
  "estimated_impact": "HIGH"
}
```

### Response Agent Response
```json
{
  "actions_taken": [
    "High-priority incident ticket created",
    "Affected host contained"
  ],
  "ticket_id": "INC-20251206-2971",
  "notifications_sent": ["SOC Team Lead", "IR Team"],
  "automation_applied": ["Enhanced monitoring enabled"],
  "status": "COMPLETED"
}
```

## How It Works

The Mock LLM provider automatically detects which agent is calling by inspecting the input variables:

| Agent Type | Detection Pattern | Mock Response |
|------------|-------------------|---------------|
| **Triage** | Has `raw_data` but no `triage_verdict` | Triage verdict with confidence scores |
| **Investigation** | Has `triage_verdict` and `threat_intel` | Investigation findings with threat context |
| **Decision** | Has `investigation_summary` | Final verdict with priority and actions |
| **Response** | Has `recommended_actions` and `estimated_impact` | Ticket creation and response actions |

## Switching to Real LLM

When ready for production, simply update your `.env`:

### Option 1: OpenAI
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### Option 2: Google Gemini
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-pro
```

## Automatic Fallback

If you set `LLM_PROVIDER=openai` or `LLM_PROVIDER=gemini` but the API key is missing, the application automatically falls back to the mock provider with a warning message.

## Benefits for Development

1. **Zero Setup Time** - Start developing immediately
2. **No API Costs** - Test without consuming API credits
3. **Offline Development** - Work without internet connection
4. **Consistent Testing** - Mock data helps with automated testing
5. **Fast Iteration** - No API latency during development

## Testing

Run the comprehensive test suite:

```bash
python test_mock_llm.py
```

This validates all 4 agent response formats and ensures the mock provider works correctly.

## Production Considerations

⚠️ **Note**: The mock provider is designed for development and testing only.  

For production use:
- Use real LLM providers (OpenAI or Gemini)
- Mock responses are randomized and not based on actual alert analysis
- Real LLMs provide better accuracy and context-aware responses

## Summary

The mock LLM provider makes it incredibly easy to:
- Try the application immediately
- Develop without API keys
- Test the full agent workflow
- Demo the system capabilities

Just run `python run.py` and everything works out of the box! 🚀
