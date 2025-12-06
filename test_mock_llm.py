#!/usr/bin/env python3
"""
Test script to verify Mock LLM provider works correctly.
Run this to test the application without API keys.
"""

import asyncio
import json
from app.llm_factory import get_llm, MockLLM


async def test_mock_llm():
    """Test the mock LLM provider with all agent types"""
    
    print("=" * 70)
    print("Testing Mock LLM Provider")
    print("=" * 70)
    print()
    
    # Create mock LLM instance
    mock_llm = get_llm(provider="mock", temperature=0.1)
    
    # Verify it's a MockLLM instance
    assert isinstance(mock_llm, MockLLM), "Expected MockLLM instance"
    print("✓ Mock LLM provider initialized successfully")
    print(f"  Model: {mock_llm.model}")
    print(f"  Temperature: {mock_llm.temperature}")
    print()
    
    # Test 1: Triage Agent
    print("-" * 70)
    print("Test 1: Triage Agent Response")
    print("-" * 70)
    triage_input = {
        "alert_id": "TEST-001",
        "rule_name": "Suspicious Login",
        "severity": "HIGH",
        "raw_data": '{"login": "failed"}'
    }
    
    response = await mock_llm.ainvoke(triage_input)
    triage_data = json.loads(response.content)
    
    print(json.dumps(triage_data, indent=2))
    assert "verdict" in triage_data
    assert "confidence" in triage_data
    assert "noise_score" in triage_data
    assert "requires_investigation" in triage_data
    assert "key_indicators" in triage_data
    assert "reasoning" in triage_data
    print("✓ Triage response structure validated")
    print()
    
    # Test 2: Investigation Agent
    print("-" * 70)
    print("Test 2: Investigation Agent Response")
    print("-" * 70)
    investigation_input = {
        "alert_id": "TEST-001",
        "triage_verdict": "suspicious",
        "triage_confidence": 0.8,
        "key_indicators": ["failed login"],
        "triage_reasoning": "suspicious activity",
        "threat_intel": "some intel data"
    }
    
    response = await mock_llm.ainvoke(investigation_input)
    investigation_data = json.loads(response.content)
    
    print(json.dumps(investigation_data, indent=2))
    assert "findings" in investigation_data
    assert "threat_context" in investigation_data
    assert "related_alerts" in investigation_data
    assert "attack_chain" in investigation_data
    assert "risk_score" in investigation_data
    assert "evidence" in investigation_data
    print("✓ Investigation response structure validated")
    print()
    
    # Test 3: Decision Agent
    print("-" * 70)
    print("Test 3: Decision Agent Response")
    print("-" * 70)
    decision_input = {
        "alert_id": "TEST-001",
        "triage_verdict": "suspicious",
        "investigation_summary": "Comprehensive investigation completed",
        "noise_score": 0.3
    }
    
    response = await mock_llm.ainvoke(decision_input)
    decision_data = json.loads(response.content)
    
    print(json.dumps(decision_data, indent=2))
    assert "final_verdict" in decision_data
    assert "priority" in decision_data
    assert "confidence" in decision_data
    assert "rationale" in decision_data
    assert "recommended_actions" in decision_data
    assert "escalation_required" in decision_data
    assert "estimated_impact" in decision_data
    print("✓ Decision response structure validated")
    print()
    
    # Test 4: Response Agent
    print("-" * 70)
    print("Test 4: Response Agent Response")
    print("-" * 70)
    response_input = {
        "alert_id": "TEST-001",
        "priority": "P2",
        "recommended_actions": ["action1", "action2"],
        "estimated_impact": "HIGH"
    }
    
    response = await mock_llm.ainvoke(response_input)
    response_data = json.loads(response.content)
    
    print(json.dumps(response_data, indent=2))
    assert "actions_taken" in response_data
    assert "ticket_id" in response_data
    assert "notifications_sent" in response_data
    assert "automation_applied" in response_data
    assert "status" in response_data
    assert "summary" in response_data
    print("✓ Response response structure validated")
    print()
    
    # Summary
    print("=" * 70)
    print("✓ All Mock LLM Tests Passed!")
    print("=" * 70)
    print()
    print("The Mock LLM provider is working correctly.")
    print("You can now run the application without any API keys!")
    print()
    print("To start the application:")
    print("  1. Ensure LLM_PROVIDER=mock in your .env file (or just don't create .env)")
    print("  2. Run: python run.py")
    print("  3. Open the UI at http://localhost:8000")
    print()


if __name__ == "__main__":
    asyncio.run(test_mock_llm())
