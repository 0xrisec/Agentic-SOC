#!/usr/bin/env python3
"""
Simple evaluation script to compare agent results with ground truth
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from app.context import Alert, SOCWorkflowState, Verdict, Priority
from app.orchestrator import get_orchestrator
from datetime import datetime


def load_alerts() -> List[Alert]:
    """Load alerts from sample data"""
    with open("data/alerts.json", "r") as f:
        data = json.load(f)
    
    return [Alert(**alert) for alert in data["alerts"]]


def load_ground_truth() -> Dict[str, Any]:
    """Load ground truth expectations"""
    with open("data/ground_truth.json", "r") as f:
        data = json.load(f)
    
    return {gt["alert_id"]: gt for gt in data["ground_truth"]}


async def evaluate_alerts():
    """Evaluate agent performance against ground truth"""
    print("=" * 80)
    print("AGENTIC SOC - EVALUATION REPORT")
    print("=" * 80)
    print()
    
    # Load data
    print("Loading alerts and ground truth...")
    alerts = load_alerts()
    ground_truth = load_ground_truth()
    
    print(f"Loaded {len(alerts)} alerts")
    print(f"Loaded {len(ground_truth)} ground truth entries")
    print()
    
    # Initialize orchestrator
    orchestrator = get_orchestrator()
    
    # Process each alert
    results = []
    total_time = 0
    
    print("Processing alerts...\n")
    
    for i, alert in enumerate(alerts, 1):
        print(f"[{i}/{len(alerts)}] Processing {alert.alert_id}...")
        
        # Create workflow state
        workflow_state = SOCWorkflowState(
            alert=alert,
            workflow_id=f"eval-{i}",
            ground_truth=ground_truth.get(alert.alert_id)
        )
        
        # Process
        start = datetime.now()
        final_state = await orchestrator.process_alert(workflow_state)
        elapsed = (datetime.now() - start).total_seconds()
        total_time += elapsed
        
        # Compare with ground truth if available
        gt = ground_truth.get(alert.alert_id)
        if gt and final_state.decision_result:
            verdict_match = final_state.decision_result.final_verdict == gt["verdict"]
            priority_match = final_state.decision_result.priority == gt["expected_priority"]
            
            results.append({
                "alert_id": alert.alert_id,
                "verdict_match": verdict_match,
                "priority_match": priority_match,
                "processing_time": elapsed,
                "errors": len(final_state.errors) > 0
            })
            
            status = "✓" if (verdict_match and priority_match) else "✗"
            print(f"  {status} Verdict: {verdict_match}, Priority: {priority_match}, Time: {elapsed:.2f}s")
        else:
            print(f"  ⚠ No ground truth available")
        
        print()
    
    # Calculate metrics
    print("=" * 80)
    print("EVALUATION METRICS")
    print("=" * 80)
    print()
    
    if results:
        verdict_accuracy = sum(r["verdict_match"] for r in results) / len(results) * 100
        priority_accuracy = sum(r["priority_match"] for r in results) / len(results) * 100
        avg_time = total_time / len(results)
        error_rate = sum(r["errors"] for r in results) / len(results) * 100
        
        print(f"Total Alerts Evaluated:     {len(results)}")
        print(f"Verdict Accuracy:           {verdict_accuracy:.1f}%")
        print(f"Priority Accuracy:          {priority_accuracy:.1f}%")
        print(f"Average Processing Time:    {avg_time:.2f}s")
        print(f"Error Rate:                 {error_rate:.1f}%")
        print(f"Total Processing Time:      {total_time:.2f}s")
        print()
        
        # Detailed breakdown
        print("DETAILED RESULTS:")
        print("-" * 80)
        for r in results:
            status = "PASS" if r["verdict_match"] and r["priority_match"] else "FAIL"
            print(f"{status:4} | {r['alert_id']:50} | {r['processing_time']:5.2f}s")
    else:
        print("No ground truth data available for evaluation")
    
    print()
    print("=" * 80)
    print("Evaluation complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(evaluate_alerts())
