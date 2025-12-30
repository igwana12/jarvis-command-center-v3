#!/usr/bin/env python3
"""
Edge Cases and Error Handling Tests for Jarvis Command Center V2
"""

import requests
import json
import time
from typing import Dict

BASE_URL = "http://localhost:8000"
TIMEOUT = 5

class EdgeCaseTestRunner:
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

def test_empty_search_query(runner):
    """Test search with empty query"""
    test_name = "Empty Search Query"
    try:
        response = requests.get(f"{BASE_URL}/search?q=", timeout=TIMEOUT)

        # Should handle gracefully
        if response.status_code == 200:
            data = response.json()
            if "error" in data:
                runner.add_pass(test_name)
            else:
                runner.add_warning(test_name, "Empty query allowed but should probably error")
                runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Unexpected status {response.status_code}")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_malformed_json_payload(runner):
    """Test endpoints with malformed JSON"""
    test_name = "Malformed JSON Payload"
    try:
        # Send invalid JSON to command endpoint
        response = requests.post(
            f"{BASE_URL}/command",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        # Should return 422 (Unprocessable Entity) for validation error
        if response.status_code in [400, 422]:
            runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Expected 400/422, got {response.status_code}")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_missing_required_fields(runner):
    """Test POST endpoints with missing required fields"""
    test_name = "Missing Required Fields"

    # Test missing 'command' field
    try:
        response = requests.post(
            f"{BASE_URL}/command",
            json={},
            timeout=TIMEOUT
        )

        if response.status_code in [400, 422]:
            runner.add_pass(f"{test_name} - Command")
        else:
            runner.add_fail(f"{test_name} - Command", f"Expected 400/422, got {response.status_code}")
    except Exception as e:
        runner.add_fail(f"{test_name} - Command", str(e))

    # Test missing 'agent' field
    try:
        response = requests.post(
            f"{BASE_URL}/agent/execute",
            json={"task": "test"},
            timeout=TIMEOUT
        )

        if response.status_code in [400, 422]:
            runner.add_pass(f"{test_name} - Agent")
        else:
            runner.add_fail(f"{test_name} - Agent", f"Expected 400/422, got {response.status_code}")
    except Exception as e:
        runner.add_fail(f"{test_name} - Agent", str(e))

def test_very_long_command(runner):
    """Test with extremely long command string"""
    test_name = "Very Long Command"
    try:
        long_command = "a" * 10000  # 10KB command

        response = requests.post(
            f"{BASE_URL}/command",
            json={"command": long_command},
            timeout=TIMEOUT
        )

        # Should handle gracefully (accept or reject with proper error)
        if response.status_code in [200, 413]:  # 413 = Payload Too Large
            runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Unexpected status {response.status_code}")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_special_characters_in_search(runner):
    """Test search with special characters"""
    test_name = "Special Characters in Search"
    try:
        special_queries = [
            "test&query",
            "test/query",
            "test?query",
            "test=query",
            "test%20query",
            "<script>alert('xss')</script>"
        ]

        for query in special_queries:
            response = requests.get(f"{BASE_URL}/search?q={query}", timeout=TIMEOUT)

            if response.status_code != 200:
                runner.add_fail(test_name, f"Failed for query: {query}")
                return

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_concurrent_requests(runner):
    """Test handling of concurrent requests"""
    test_name = "Concurrent Requests"
    try:
        import threading

        results = []

        def make_request():
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
                results.append(response.status_code == 200)
            except:
                results.append(False)

        # Create 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # Wait for all to complete
        for thread in threads:
            thread.join()

        # All should succeed
        if all(results):
            runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Only {sum(results)}/10 requests succeeded")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_invalid_workflow_parameters(runner):
    """Test workflow trigger with invalid parameters"""
    test_name = "Invalid Workflow Parameters"
    try:
        # Valid workflow, but with unexpected parameter types
        response = requests.post(
            f"{BASE_URL}/workflow/trigger",
            json={
                "workflow_id": "master-pipeline",
                "parameters": {"invalid": None, "nested": {"deep": "value"}}
            },
            timeout=TIMEOUT
        )

        # Should handle gracefully (either accept or reject properly)
        if response.status_code in [200, 400]:
            runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Unexpected status {response.status_code}")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_rapid_refresh_requests(runner):
    """Test rapid consecutive refresh requests"""
    test_name = "Rapid Refresh Requests"
    try:
        success_count = 0

        for _ in range(5):
            response = requests.get(f"{BASE_URL}/refresh", timeout=TIMEOUT)
            if response.status_code == 200:
                success_count += 1
            time.sleep(0.1)  # Small delay between requests

        if success_count == 5:
            runner.add_pass(test_name)
        else:
            runner.add_fail(test_name, f"Only {success_count}/5 requests succeeded")

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_search_with_unicode(runner):
    """Test search with unicode characters"""
    test_name = "Unicode in Search"
    try:
        unicode_queries = [
            "python",
            "中文搜索",
            "البحث",
            "🔍🤖",
            "test™"
        ]

        for query in unicode_queries:
            response = requests.get(
                f"{BASE_URL}/search",
                params={"q": query},
                timeout=TIMEOUT
            )

            if response.status_code != 200:
                runner.add_fail(test_name, f"Failed for query: {query}")
                return

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_invalid_endpoint_methods(runner):
    """Test using wrong HTTP methods on endpoints"""
    test_name = "Invalid HTTP Methods"

    # Test POST on GET-only endpoint
    try:
        response = requests.post(f"{BASE_URL}/agents", timeout=TIMEOUT)
        if response.status_code == 405:  # Method Not Allowed
            runner.add_pass(f"{test_name} - POST on GET")
        else:
            runner.add_warning(f"{test_name} - POST on GET", f"Expected 405, got {response.status_code}")
    except Exception as e:
        runner.add_fail(f"{test_name} - POST on GET", str(e))

    # Test GET on POST-only endpoint
    try:
        response = requests.get(f"{BASE_URL}/command", timeout=TIMEOUT)
        if response.status_code == 405:
            runner.add_pass(f"{test_name} - GET on POST")
        else:
            runner.add_warning(f"{test_name} - GET on POST", f"Expected 405, got {response.status_code}")
    except Exception as e:
        runner.add_fail(f"{test_name} - GET on POST", str(e))

def test_nonexistent_endpoints(runner):
    """Test accessing non-existent endpoints"""
    test_name = "Non-existent Endpoints"
    try:
        endpoints = [
            "/nonexistent",
            "/api/v1/test",
            "/../../etc/passwd",
            "/../config"
        ]

        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=TIMEOUT)

            if response.status_code != 404:
                runner.add_fail(test_name, f"Expected 404 for {endpoint}, got {response.status_code}")
                return

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_knowledge_search_edge_cases(runner):
    """Test knowledge search with edge cases"""
    test_name = "Knowledge Search Edge Cases"
    try:
        # Empty query
        response = requests.get(f"{BASE_URL}/knowledge/search?query=", timeout=TIMEOUT)
        if response.status_code not in [200, 400]:
            runner.add_fail(test_name, f"Unexpected status for empty query: {response.status_code}")
            return

        # Very short query
        response = requests.get(f"{BASE_URL}/knowledge/search?query=a", timeout=TIMEOUT)
        if response.status_code != 200:
            runner.add_fail(test_name, f"Failed for single character query")
            return

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

def test_processes_endpoint_reliability(runner):
    """Test processes endpoint reliability"""
    test_name = "Processes Endpoint Reliability"
    try:
        # Make multiple requests to ensure consistent response
        for i in range(3):
            response = requests.get(f"{BASE_URL}/processes", timeout=TIMEOUT)

            if response.status_code != 200:
                runner.add_fail(test_name, f"Request {i+1} failed with status {response.status_code}")
                return

            data = response.json()

            # Validate CPU and memory are reasonable values
            if data["cpu"] < 0 or data["cpu"] > 100:
                runner.add_fail(test_name, f"Invalid CPU value: {data['cpu']}")
                return

            if data["memory"] < 0 or data["memory"] > 100:
                runner.add_fail(test_name, f"Invalid memory value: {data['memory']}")
                return

            time.sleep(0.5)

        runner.add_pass(test_name)

    except Exception as e:
        runner.add_fail(test_name, str(e))

def run_all_tests():
    """Run all edge case and error handling tests"""
    print("=" * 70)
    print("JARVIS COMMAND CENTER V2 - EDGE CASES & ERROR HANDLING TESTS")
    print("=" * 70)
    print()

    runner = EdgeCaseTestRunner()

    print("Running Edge Case Tests...")
    print("-" * 70)

    test_empty_search_query(runner)
    test_malformed_json_payload(runner)
    test_missing_required_fields(runner)
    test_very_long_command(runner)
    test_special_characters_in_search(runner)
    test_concurrent_requests(runner)
    test_invalid_workflow_parameters(runner)
    test_rapid_refresh_requests(runner)
    test_search_with_unicode(runner)
    test_invalid_endpoint_methods(runner)
    test_nonexistent_endpoints(runner)
    test_knowledge_search_edge_cases(runner)
    test_processes_endpoint_reliability(runner)

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
    run_all_tests()
