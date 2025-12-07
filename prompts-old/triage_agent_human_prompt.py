"""
Human Prompt for Triage Agent
"""

TRIAGE_AGENT_HUMAN_PROMPT = """Analyze the following alert and provide triage assessment:

ALERT DETAILS:
Alert ID: {alert_id}
Rule ID: {rule_id}
Rule Name: {rule_name}
Severity: {severity}
Timestamp: {timestamp}
Description: {description}

MITRE ATT&CK:
Tactics: {tactics}
Techniques: {techniques}

AFFECTED ASSETS:
Host: {host}
Source IP: {source_ip}
Destination IP: {destination_ip}
User: {user}

RAW DATA:
{raw_data}

Provide your triage assessment in the following JSON format:
{
    "verdict": "true_positive|false_positive|benign|suspicious|unknown",
    "confidence": 0.0-1.0,
    "noise_score": 0.0-1.0,
    "requires_investigation": true|false,
    "key_indicators": ["indicator1", "indicator2", ...],
    "reasoning": "Your 2-3 sentence explanation"
}
"""