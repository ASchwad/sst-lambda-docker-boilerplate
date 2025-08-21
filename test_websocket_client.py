#!/usr/bin/env python3

import asyncio
import websockets
import json
import sys
import argparse

async def test_websocket_route(route_name="invokeModel"):
    # WebSocket URL from the deployment
    uri = "wss://warcyz88jg.execute-api.eu-central-1.amazonaws.com/$default"
    
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
                    "modelId": "arn:aws:bedrock:eu-central-1:037708943013:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
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

async def test_both_routes():
    """Test both routes side by side"""
    print("=" * 60)
    print("🔄 COMPARISON TEST: Testing both implementations")
    print("=" * 60)
    
    routes = ["invokeModel", "chatMessage"]
    results = {}
    
    for route in routes:
        print(f"\n{'='*20} Testing {route} {'='*20}")
        results[route] = await test_websocket_route(route)
        print(f"{'='*50}")
        
        if route != routes[-1]:  # Not the last route
            print("⏸️  Waiting 2 seconds before next test...")
            await asyncio.sleep(2)
    
    print(f"\n{'='*20} RESULTS SUMMARY {'='*20}")
    for route, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {route:15} : {status}")
    
    print(f"{'='*60}")
    return all(results.values())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WebSocket implementations")
    parser.add_argument("--route", choices=["invokeModel", "chatMessage", "both"], 
                       default="both", help="Route to test")
    
    args = parser.parse_args()
    
    if args.route == "both":
        success = asyncio.run(test_both_routes())
    else:
        success = asyncio.run(test_websocket_route(args.route))
    
    if success:
        print("✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)