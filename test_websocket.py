#!/usr/bin/env python3
"""
Quick test script to verify WebSocket updates work
"""
import asyncio
import websockets
import json
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"

async def test_upload_and_websocket():
    """Test the upload-and-run endpoint with WebSocket updates"""
    
    # 1. Upload alert file
    print("📤 Uploading alert file...")
    alerts_file = Path("data/alerts.json")
    
    if not alerts_file.exists():
        print("❌ Alert file not found")
        return
    
    with open(alerts_file, 'rb') as f:
        files = {'file': ('alerts.json', f, 'application/json')}
        response = requests.post(f"{BASE_URL}/api/upload-and-run", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return
    
    result = response.json()
    print(f"✅ Upload successful: {result}")
    
    if not result.get('success'):
        print(f"❌ Analysis not started: {result.get('message')}")
        return
    
    workflow_id = result.get('workflow_id')
    if not workflow_id:
        print("❌ No workflow_id returned")
        return
    
    print(f"🔗 Workflow ID: {workflow_id}")
    
    # 2. Connect to WebSocket
    ws_url = f"{WS_BASE}/ws/{workflow_id}"
    print(f"🌐 Connecting to WebSocket: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected")
            
            # Send initial ping
            await websocket.send("ping")
            
            # Listen for updates
            message_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    message_count += 1
                    data = json.loads(message)
                    
                    msg_type = data.get('type', 'unknown')
                    stage = data.get('stage', data.get('current_agent', ''))
                    status = data.get('status', '')
                    progress = data.get('progress', 0)
                    
                    print(f"📨 Message #{message_count}: type={msg_type}, stage={stage}, status={status}, progress={progress}")
                    
                    # Check for completion
                    if data.get('completed') or msg_type == 'final':
                        print("🎉 Analysis completed!")
                        print(f"Final data: {json.dumps(data, indent=2)}")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏱️  Timeout waiting for message")
                    break
            
            print(f"✅ Received {message_count} WebSocket messages")
            
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        print(f"   Trying to check status via polling API...")
        
        # Fallback: check via polling
        status_response = requests.get(f"{BASE_URL}/api/status")
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"📊 Status API response: {json.dumps(status, indent=2)}")

if __name__ == "__main__":
    print("🚀 Starting WebSocket test...\n")
    asyncio.run(test_upload_and_websocket())
