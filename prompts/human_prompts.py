"""
Centralized human prompt templates for agents.

Add new constants here for each agent's human prompt.
"""

# Investigation Agent human prompt
INVESTIGATION_HUMAN_PROMPT = """Conduct comprehensive investigation of this alert:

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

TRIAGE ASSESSMENT:
Verdict: {triage_verdict}
Confidence: {triage_confidence}
Key Indicators: {key_indicators}
Reasoning: {triage_reasoning}

THREAT INTELLIGENCE:
{threat_intel}

RAW DATA:
{raw_data}

Provide comprehensive investigation results in the following JSON format:
{{
    "findings": ["finding1", "finding2", ...],
    "threat_context": {{
        "threat_actor": "actor name or unknown",
        "campaign": "campaign name or unknown",
        "ttps": ["ttp1", "ttp2", ...]
    }},
    "related_alerts": ["alert_id1", "alert_id2", ...],
    "attack_chain": ["stage1", "stage2", ...],
    "risk_score": 0.0-10.0,
    "evidence": {{
        "key_data_points": ["point1", "point2", ...],
        "timeline": ["event1 at time1", "event2 at time2", ...],
        "indicators_of_compromise": ["ioc1", "ioc2", ...]
    }}
}}"""

# Triage Agent human prompt
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
{{
    "verdict": "true_positive|false_positive|benign|suspicious|unknown",
    "confidence": 0.0-1.0,
    "noise_score": 0.0-1.0,
    "requires_investigation": true|false,
    "key_indicators": ["indicator1", "indicator2", ...],
    "reasoning": "Your 2-3 sentence explanation"
}}
"""

# Decision Agent human prompt
DECISION_HUMAN_PROMPT = """Make final decision on this alert based on complete analysis:

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
User: {user}

TRIAGE ASSESSMENT:
Verdict: {triage_verdict}
Confidence: {triage_confidence}
Noise Score: {noise_score}
Key Indicators: {key_indicators}
Reasoning: {triage_reasoning}

INVESTIGATION RESULTS:
{investigation_summary}

Provide your decision in the following JSON format:
{{
    "final_verdict": "true_positive|false_positive|benign|suspicious",
    "priority": "P1|P2|P3|P4|P5",
    "confidence": 0.0-1.0,
    "rationale": "3-5 sentence explanation of your decision",
    "recommended_actions": ["action1", "action2", ...],
    "escalation_required": true|false,
    "estimated_impact": "CRITICAL|HIGH|MEDIUM|LOW|MINIMAL"
}}
"""

# Response Agent human prompt
RESPONSE_HUMAN_PROMPT = """Execute response actions for this alert:

ALERT DETAILS:
Alert ID: {alert_id}
Rule Name: {rule_name}
Severity: {severity}
Affected Assets: Host={host}, Source IP={source_ip}, User={user}

FINAL DECISION:
Verdict: {final_verdict}
Priority: {priority}
Confidence: {confidence}
Escalation Required: {escalation_required}
Estimated Impact: {estimated_impact}

RECOMMENDED ACTIONS:
{recommended_actions}

RATIONALE:
{rationale}

Based on the priority level ({priority}), execute appropriate response actions and provide details in JSON format:
{{
    "actions_taken": ["action1", "action2", ...],
    "ticket_id": "INC-YYYYMMDD-XXX",
    "notifications_sent": ["recipient1", "recipient2", ...],
    "automation_applied": ["automation1", "automation2", ...],
    "status": "COMPLETED|IN_PROGRESS|ESCALATED",
    "summary": "2-3 sentence incident summary for notifications"
}}
"""
