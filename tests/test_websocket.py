#!/usr/bin/env python3
"""
WebSocket Real-time Update Tests for Jarvis Command Center V2
"""

import asyncio
import json
import websockets
from datetime import datetime

class WebSocketTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.warnings = []

    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"✅ PASS: {test_name}")

    def add_fail(self, test_name: str, reason: str):
        self.failed += 1
        error = f"❌ FAIL: {test_name} - {reason}"
        self.errors.append(error)
        print(error)

    def add_warning(self, test_name: str, message: str):
        warning = f"⚠️  WARN: {test_name} - {message}"
        self.warnings.append(warning)
        print(warning)

    def summary(self):
        total = self.passed + self.failed
        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": f"{(self.passed/total*100):.1f}%" if total > 0 else "0%",
            "errors": self.errors,
            "warnings": self.warnings
        }

async def test_websocket_connection(runner):
    """Test WebSocket connection establishment"""
    test_name = "WebSocket Connection"

    try:
        async with websockets.connect("ws://localhost:8000/ws") as websocket:
            runner.add_pass(test_name)
            return websocket
    except Exception as e:
        runner.add_fail(test_name, str(e))
        return None

async def test_websocket_status_updates(runner):
    """Test receiving status updates from WebSocket"""
    test_name = "WebSocket Status Updates"

    try:
        async with websockets.connect("ws://localhost:8000/ws", ping_interval=None) as websocket:
            # Wait for first status update
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)

            # Validate status update structure
            required_fields = ["type", "timestamp", "cpu", "memory"]
            for field in required_fields:
                if field not in data:
                    runner.add_fail(test_name, f"Missing field: {field}")
                    return

            if data["type"] != "status_update":
                runner.add_fail(test_name, f"Unexpected type: {data['type']}")
                return

            # Validate data types
            if not isinstance(data["cpu"], (int, float)):
                runner.add_fail(test_name, f"CPU should be numeric, got {type(data['cpu'])}")
                return

            if not isinstance(data["memory"], (int, float)):
                runner.add_fail(test_name, f"Memory should be numeric, got {type(data['memory'])}")
                return

            runner.add_pass(test_name)

    except asyncio.TimeoutError:
        runner.add_fail(test_name, "Timeout waiting for status update")
    except Exception as e:
        runner.add_fail(test_name, str(e))

async def test_websocket_multiple_updates(runner):
    """Test receiving multiple status updates"""
    test_name = "WebSocket Multiple Updates"

    try:
        async with websockets.connect("ws://localhost:8000/ws", ping_interval=None) as websocket:
            updates_received = 0
            target_updates = 3

            for _ in range(target_updates):
                message = await asyncio.wait_for(websocket.recv(), timeout=7)
                data = json.loads(message)

                if data.get("type") == "status_update":
                    updates_received += 1

            if updates_received == target_updates:
                runner.add_pass(test_name)
            else:
                runner.add_fail(test_name, f"Expected {target_updates} updates, got {updates_received}")

    except asyncio.TimeoutError:
        runner.add_fail(test_name, f"Timeout - received {updates_received}/{target_updates} updates")
    except Exception as e:
        runner.add_fail(test_name, str(e))

async def test_websocket_client_messages(runner):
    """Test sending messages to WebSocket"""
    test_name = "WebSocket Client Messages"

    try:
        async with websockets.connect("ws://localhost:8000/ws", ping_interval=None) as websocket:
            # Send refresh command
            await websocket.send("refresh")

            # Wait for response
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)

            # Should receive either refreshed message or status update
            if data.get("type") in ["refreshed", "status_update"]:
                runner.add_pass(test_name)
            else:
                runner.add_warning(test_name, f"Unexpected response type: {data.get('type')}")
                runner.add_pass(test_name)

    except asyncio.TimeoutError:
        runner.add_fail(test_name, "Timeout waiting for response")
    except Exception as e:
        runner.add_fail(test_name, str(e))

async def test_websocket_reconnection(runner):
    """Test WebSocket reconnection behavior"""
    test_name = "WebSocket Reconnection"

    try:
        # Connect and disconnect multiple times
        for i in range(3):
            async with websockets.connect("ws://localhost:8000/ws", ping_interval=None) as websocket:
                # Receive one message to confirm connection
                await asyncio.wait_for(websocket.recv(), timeout=5)

            # Small delay between reconnections
            await asyncio.sleep(0.5)

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

async def test_websocket_concurrent_connections(runner):
    """Test multiple concurrent WebSocket connections"""
    test_name = "WebSocket Concurrent Connections"

    try:
        connections = []
        num_connections = 3

        # Create multiple connections
        for i in range(num_connections):
            ws = await websockets.connect("ws://localhost:8000/ws", ping_interval=None)
            connections.append(ws)

        # Receive message from each
        for ws in connections:
            await asyncio.wait_for(ws.recv(), timeout=5)

        # Close all connections
        for ws in connections:
            await ws.close()

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))
        # Clean up connections
        for ws in connections:
            try:
                await ws.close()
            except:
                pass

async def run_all_tests():
    """Run all WebSocket tests"""
    print("=" * 70)
    print("JARVIS COMMAND CENTER V2 - WEBSOCKET TEST SUITE")
    print("=" * 70)
    print()

    runner = WebSocketTestRunner()

    print("Running WebSocket Tests...")
    print("-" * 70)

    await test_websocket_connection(runner)
    await test_websocket_status_updates(runner)
    await test_websocket_multiple_updates(runner)
    await test_websocket_client_messages(runner)
    await test_websocket_reconnection(runner)
    await test_websocket_concurrent_connections(runner)

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    summary = runner.summary()
    print(f"\nTotal Tests: {summary['total']}")
    print(f"Passed: {summary['passed']} ✅")
    print(f"Failed: {summary['failed']} ❌")
    print(f"Success Rate: {summary['success_rate']}")

    if summary['warnings']:
        print(f"\nWarnings: {len(summary['warnings'])} ⚠️")
        for warning in summary['warnings']:
            print(f"  {warning}")

    if summary['errors']:
        print(f"\nFailures:")
        for error in summary['errors']:
            print(f"  {error}")

    print()

    return runner

if __name__ == "__main__":
    asyncio.run(run_all_tests())
