#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Jarvis Command Center V2
"""

import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Tuple

# Test configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 5

class TestResult:
    """Test result tracker"""
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

def test_server_running() -> bool:
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        return response.status_code == 200
    except:
        return False

def test_get_root(results: TestResult):
    """Test GET / endpoint"""
    test_name = "GET /"
    try:
        response = requests.get(f"{BASE_URL}/", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate required fields
        required_fields = ["name", "version", "status", "capabilities", "endpoints"]
        for field in required_fields:
            if field not in data:
                results.add_fail(test_name, f"Missing field: {field}")
                return

        # Validate capabilities structure
        caps = data["capabilities"]
        expected_caps = ["agents", "commands", "skills", "mcp_servers", "workflows"]
        for cap in expected_caps:
            if cap not in caps:
                results.add_warning(test_name, f"Missing capability: {cap}")
            elif not isinstance(caps[cap], int):
                results.add_fail(test_name, f"Capability {cap} should be int, got {type(caps[cap])}")
                return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_health(results: TestResult):
    """Test GET /health endpoint"""
    test_name = "GET /health"
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        if "status" not in data:
            results.add_fail(test_name, "Missing 'status' field")
            return

        if data["status"] != "healthy":
            results.add_warning(test_name, f"Status is {data['status']}, expected 'healthy'")

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_agents(results: TestResult):
    """Test GET /agents endpoint"""
    test_name = "GET /agents"
    try:
        response = requests.get(f"{BASE_URL}/agents", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "count" not in data or "agents" not in data:
            results.add_fail(test_name, "Missing 'count' or 'agents' field")
            return

        # Check count matches
        if data["count"] != len(data["agents"]):
            results.add_fail(test_name, f"Count mismatch: {data['count']} != {len(data['agents'])}")
            return

        # Validate agents structure
        if not isinstance(data["agents"], dict):
            results.add_fail(test_name, "Agents should be a dictionary")
            return

        # Check for expected agents
        expected_agents = ["general-purpose", "python-expert", "system-architect"]
        for agent in expected_agents:
            if agent not in data["agents"]:
                results.add_warning(test_name, f"Missing expected agent: {agent}")

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_commands(results: TestResult):
    """Test GET /commands endpoint"""
    test_name = "GET /commands"
    try:
        response = requests.get(f"{BASE_URL}/commands", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "count" not in data or "commands" not in data:
            results.add_fail(test_name, "Missing 'count' or 'commands' field")
            return

        # Check count matches
        if data["count"] != len(data["commands"]):
            results.add_fail(test_name, f"Count mismatch: {data['count']} != {len(data['commands'])}")
            return

        # Validate command structure
        for cmd_name, cmd_info in data["commands"].items():
            if not isinstance(cmd_info, dict):
                results.add_fail(test_name, f"Command {cmd_name} should be a dict")
                return

            if "description" not in cmd_info:
                results.add_warning(test_name, f"Command {cmd_name} missing description")

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_skills(results: TestResult):
    """Test GET /skills endpoint"""
    test_name = "GET /skills"
    try:
        response = requests.get(f"{BASE_URL}/skills", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "count" not in data or "skills" not in data:
            results.add_fail(test_name, "Missing 'count' or 'skills' field")
            return

        # Check count matches
        if data["count"] != len(data["skills"]):
            results.add_fail(test_name, f"Count mismatch: {data['count']} != {len(data['skills'])}")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_mcp_servers(results: TestResult):
    """Test GET /mcp-servers endpoint"""
    test_name = "GET /mcp-servers"
    try:
        response = requests.get(f"{BASE_URL}/mcp-servers", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "count" not in data or "servers" not in data:
            results.add_fail(test_name, "Missing 'count' or 'servers' field")
            return

        # Check for expected MCP servers
        expected_servers = ["sequential-thinking", "playwright", "chrome-devtools"]
        for server in expected_servers:
            if server not in data["servers"]:
                results.add_warning(test_name, f"Missing expected MCP server: {server}")

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_workflows(results: TestResult):
    """Test GET /workflows endpoint"""
    test_name = "GET /workflows"
    try:
        response = requests.get(f"{BASE_URL}/workflows", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "count" not in data or "workflows" not in data:
            results.add_fail(test_name, "Missing 'count' or 'workflows' field")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_refresh(results: TestResult):
    """Test GET /refresh endpoint"""
    test_name = "GET /refresh"
    try:
        response = requests.get(f"{BASE_URL}/refresh", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        if "status" not in data:
            results.add_fail(test_name, "Missing 'status' field")
            return

        if data["status"] != "refreshed":
            results.add_fail(test_name, f"Status should be 'refreshed', got {data['status']}")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_post_command(results: TestResult):
    """Test POST /command endpoint"""
    test_name = "POST /command"
    try:
        payload = {
            "command": "status"
        }
        response = requests.post(f"{BASE_URL}/command", json=payload, timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Should have an action field
        if "action" not in data:
            results.add_fail(test_name, "Missing 'action' field in response")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_post_agent_execute(results: TestResult):
    """Test POST /agent/execute endpoint"""
    test_name = "POST /agent/execute"
    try:
        payload = {
            "agent": "general-purpose",
            "task": "Test task"
        }
        response = requests.post(f"{BASE_URL}/agent/execute", json=payload, timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate response structure
        required_fields = ["status", "agent", "task", "task_id"]
        for field in required_fields:
            if field not in data:
                results.add_fail(test_name, f"Missing field: {field}")
                return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_post_workflow_trigger(results: TestResult):
    """Test POST /workflow/trigger endpoint"""
    test_name = "POST /workflow/trigger"
    try:
        payload = {
            "workflow_id": "master-pipeline",
            "parameters": {"test": "value"}
        }
        response = requests.post(f"{BASE_URL}/workflow/trigger", json=payload, timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        if "status" not in data:
            results.add_fail(test_name, "Missing 'status' field")
            return

        # Status could be 'triggered' or 'error' (if n8n not running)
        if data["status"] not in ["triggered", "error"]:
            results.add_warning(test_name, f"Unexpected status: {data['status']}")

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_search_endpoint(results: TestResult):
    """Test GET /search endpoint"""
    test_name = "GET /search"
    try:
        # Test valid search
        response = requests.get(f"{BASE_URL}/search?q=python", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        if "query" not in data or "total_results" not in data or "results" not in data:
            results.add_fail(test_name, "Missing required fields in response")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_get_processes(results: TestResult):
    """Test GET /processes endpoint"""
    test_name = "GET /processes"
    try:
        response = requests.get(f"{BASE_URL}/processes", timeout=TIMEOUT)

        if response.status_code != 200:
            results.add_fail(test_name, f"Status {response.status_code}")
            return

        data = response.json()

        # Validate structure
        required_fields = ["count", "cpu", "memory", "processes"]
        for field in required_fields:
            if field not in data:
                results.add_fail(test_name, f"Missing field: {field}")
                return

        # Validate data types
        if not isinstance(data["processes"], list):
            results.add_fail(test_name, "Processes should be a list")
            return

        results.add_pass(test_name)

    except Exception as e:
        results.add_fail(test_name, str(e))

def test_error_handling(results: TestResult):
    """Test error handling for invalid requests"""
    test_name = "Error Handling"

    # Test 1: Invalid agent
    try:
        payload = {"agent": "nonexistent-agent", "task": "test"}
        response = requests.post(f"{BASE_URL}/agent/execute", json=payload, timeout=TIMEOUT)

        if response.status_code == 404:
            results.add_pass(f"{test_name} - Invalid Agent")
        else:
            results.add_fail(f"{test_name} - Invalid Agent", f"Expected 404, got {response.status_code}")
    except Exception as e:
        results.add_fail(f"{test_name} - Invalid Agent", str(e))

    # Test 2: Invalid workflow
    try:
        payload = {"workflow_id": "nonexistent-workflow"}
        response = requests.post(f"{BASE_URL}/workflow/trigger", json=payload, timeout=TIMEOUT)

        if response.status_code == 404:
            results.add_pass(f"{test_name} - Invalid Workflow")
        else:
            results.add_fail(f"{test_name} - Invalid Workflow", f"Expected 404, got {response.status_code}")
    except Exception as e:
        results.add_fail(f"{test_name} - Invalid Workflow", str(e))

def run_all_tests():
    """Run all backend API tests"""
    print("=" * 70)
    print("JARVIS COMMAND CENTER V2 - BACKEND API TEST SUITE")
    print("=" * 70)
    print()

    # Check if server is running
    if not test_server_running():
        print("❌ ERROR: Backend server is not running at", BASE_URL)
        print("Please start the server with: python backend/main_v2.py")
        return None

    print(f"✅ Server is running at {BASE_URL}")
    print()

    results = TestResult()

    # Run all tests
    print("Running API Endpoint Tests...")
    print("-" * 70)

    test_get_root(results)
    test_get_health(results)
    test_get_agents(results)
    test_get_commands(results)
    test_get_skills(results)
    test_get_mcp_servers(results)
    test_get_workflows(results)
    test_get_refresh(results)
    test_post_command(results)
    test_post_agent_execute(results)
    test_post_workflow_trigger(results)
    test_search_endpoint(results)
    test_get_processes(results)
    test_error_handling(results)

    # Print summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    summary = results.summary()
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

    return results

if __name__ == "__main__":
    results = run_all_tests()

    # Exit with appropriate code
    if results and results.failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)
