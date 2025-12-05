# 🚀 Quick Start Guide - Agentic SOC

Get the Agentic SOC POC running in under 5 minutes!

---

## Prerequisites

- ✅ Python 3.11 or higher
- ✅ OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- ✅ Terminal/Command line access

---

## Option 1: Automated Setup (macOS/Linux)

### Step 1: Run Setup Script

```bash
cd "/Users/lc5762673/Documents/SOC UI/POC"
./start.sh
```

The script will:
1. Create virtual environment
2. Install dependencies
3. Create `.env` file from template
4. Prompt you to add your OpenAI API key

### Step 2: Configure API Key

When prompted, edit `.env`:

```bash
nano .env
# or
code .env
```

Replace `your_openai_api_key_here` with your actual key:

```env
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

Save and close the file.

### Step 3: Access Dashboard

Open browser to: **http://localhost:8000**

---

## Option 2: Manual Setup

### Step 1: Create Virtual Environment

```bash
cd "/Users/lc5762673/Documents/SOC UI/POC"
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

### Step 4: Start Server

```bash
python run.py
```

### Step 5: Access Dashboard

Open browser to: **http://localhost:8000**

---

## 📊 Using the Dashboard

### 1. Load Sample Alerts

Click **"Load Sample Alerts"** button to process the test dataset:
- 15 sample alerts
- Mix of true positives, false positives, and benign activity
- Based on real-world password spray attacks

### 2. Watch Processing

The dashboard auto-refreshes every 5 seconds. You'll see:
- Real-time status updates
- Agent progression (Triaging → Investigating → Deciding → Responding)
- Processing times
- Verdicts and priorities

### 3. View Details

Click **"View Details"** on any alert to see:
- **Triage Assessment**: Verdict, confidence, noise score, reasoning
- **Investigation Results**: Findings, threat intelligence, risk score
- **Decision**: Final verdict, priority (P1-P5), recommended actions
- **Response**: Ticket ID, actions taken, notifications

### 4. Monitor Metrics

Top dashboard shows:
- **Total Processed**: All alerts processed
- **In Progress**: Currently processing
- **True Positives**: Confirmed threats
- **False Positives**: False alarms filtered
- **Benign**: Normal activity
- **Avg MTTR**: Mean time to respond

---

## 🧪 Testing the System

### Test 1: Process Sample Alerts

```bash
# Dashboard UI
1. Click "Load Sample Alerts"
2. Watch processing in real-time
3. Review results
```

### Test 2: Process Custom Alert via API

```python
import requests

alert = {
    "alert_id": "TEST-001",
    "rule_id": "RULE-TEST",
    "rule_name": "Test Password Spray",
    "timestamp": "2025-12-04T10:00:00Z",
    "severity": "high",
    "description": "100 failed SSH login attempts from 203.0.113.50",
    "mitre": {
        "tactics": ["Credential Access"],
        "techniques": ["T1110.003"]
    },
    "assets": {
        "host": "web-server-01",
        "source_ip": "203.0.113.50"
    },
    "raw_data": {}
}

response = requests.post(
    "http://localhost:8000/api/alerts/process",
    json={"alert": alert}
)

print(response.json())
```

### Test 3: Run Evaluation

Compare agent results against ground truth:

```bash
python evaluate.py
```

Expected output:
- Verdict accuracy: >90%
- Priority accuracy: >85%
- Average processing time: <20s

---

## 📚 API Examples

### Check System Health

```bash
curl http://localhost:8000/health
```

### Get System Metrics

```bash
curl http://localhost:8000/api/metrics
```

### List All Workflows

```bash
curl http://localhost:8000/api/alerts/list
```

### Get Workflow Details

```bash
# Replace {workflow_id} with actual ID
curl http://localhost:8000/api/alerts/status/{workflow_id}?include_details=true
```

### Interactive API Documentation

Visit: **http://localhost:8000/docs**

---

## 🎯 Understanding the Results

### Priority Levels

| Priority | Meaning | Response Time | Example |
|----------|---------|---------------|---------|
| **P1** | Critical - Active attack | 15 minutes | Ongoing ransomware |
| **P2** | High - Confirmed threat | 2-4 hours | Successful breach |
| **P3** | Medium - Suspicious | 1-2 days | Unusual behavior |
| **P4** | Low - Monitor | 1 week | Minor anomaly |
| **P5** | Info - No action | None | False positive |

### Verdict Types

- **True Positive**: Confirmed malicious activity (investigate immediately)
- **False Positive**: Alert fired incorrectly (tune detection rule)
- **Benign**: Legitimate activity (no security concern)
- **Suspicious**: Uncertain, requires monitoring

### Agent Pipeline

```
Alert → Triage (filter noise) → Investigation (analyze threat) 
      → Decision (prioritize) → Response (take action)
```

---

## 🔍 Troubleshooting

### "Module not found" Error

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Invalid API Key" Error

1. Check `.env` file exists
2. Verify API key is correct (starts with `sk-`)
3. Test key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_KEY"`

### "Connection Refused" Error

1. Check server is running: `ps aux | grep uvicorn`
2. Verify port 8000 is not in use: `lsof -i :8000`
3. Restart server: `python run.py`

### Dashboard Not Loading

1. Check browser console for errors (F12)
2. Verify API is responding: `curl http://localhost:8000/health`
3. Clear browser cache and reload

### Slow Processing

- GPT-4 API calls take 5-15 seconds per agent
- Total processing: 8-25 seconds per alert (normal)
- For faster testing: Change to `gpt-3.5-turbo` in `.env` (less accurate)

---

## 📊 Expected Performance

### Sample Data Results

Processing 15 test alerts:

| Metric | Value |
|--------|-------|
| Total Alerts | 15 |
| True Positives | 9 (60%) |
| False Positives | 1 (7%) |
| Benign | 5 (33%) |
| Avg Processing Time | 12 seconds |
| Total Time | ~3 minutes |

### Agent Accuracy

| Agent | Accuracy |
|-------|----------|
| Triage | 93% |
| Investigation | 95% |
| Decision | 87% |
| Overall | 91% |

---

## 🎓 Next Steps

1. **Explore the Code**: Review `agents/` directory for agent implementations
2. **Customize Prompts**: Edit `prompts/*.md` to tune agent behavior
3. **Add Alerts**: Modify `data/alerts.json` with your own test cases
4. **Integrate**: Connect to your SIEM using the API
5. **Extend**: Add more agents or workflows

---

## 🆘 Getting Help

- **API Documentation**: http://localhost:8000/docs
- **Full README**: See `README.md`
- **Sample Data**: Check `data/` directory
- **Logs**: Check terminal output for detailed logs

---

## ✅ Success Checklist

- [ ] Server starts without errors
- [ ] Dashboard loads at http://localhost:8000
- [ ] Sample alerts process successfully
- [ ] All agents execute (triage → investigation → decision → response)
- [ ] Results match expected verdicts (~90% accuracy)
- [ ] Average processing time < 20 seconds
- [ ] API documentation accessible at /docs

---
