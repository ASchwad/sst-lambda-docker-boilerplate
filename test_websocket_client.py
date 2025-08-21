#!/usr/bin/env python3

import asyncio
import websockets
import json
import sys
import argparse
import os

from dotenv import load_dotenv

load_dotenv()

async def test_websocket_route(route_name="invokeModel"):
    # WebSocket URL from the deployment
    uri = os.getenv("WEBSOCKET_URL")
    
    try:
        print(f"🚀 Testing WebSocket route: {route_name}")
        print(f"Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Test message - different actions for different routes
            test_message = {
                "action": route_name,
                "prompt": "Hello! Can you tell me a short joke?",
                "parameters": {
                    "modelId": os.getenv("TEST_MODEL_ID"),
                    "maxTokens": 100,
                    "temperature": 0.7
                }
            }
            
            print(f"📤 Sending to '{route_name}' route:")
            print(f"   {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))
            
            print("🎯 Message sent! Waiting for responses...")
            
            # Listen for streaming responses
            response_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    response_count += 1
                    print(f"📨 Response {response_count}: {response}")
                    
                    # Check if this is the end message
                    if "<End of LLM response>" in response:
                        print("🎉 Streaming completed!")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 Connection closed")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    return True

async def test_invoke_model_route():
    """Test the invokeModel route"""
    print("=" * 60)
    print("🔄 TESTING: invokeModel route only")
    print("=" * 60)
    
    result = await test_websocket_route("invokeModel")
    
    print(f"\n{'='*20} RESULTS SUMMARY {'='*20}")
    status = "✅ SUCCESS" if result else "❌ FAILED"
    print(f"  invokeModel     : {status}")
    
    print(f"{'='*60}")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WebSocket invokeModel route")
    parser.add_argument("--route", choices=["invokeModel"], 
                       default="invokeModel", help="Route to test (only invokeModel available)")
    
    args = parser.parse_args()
    
    success = asyncio.run(test_invoke_model_route())
    
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)