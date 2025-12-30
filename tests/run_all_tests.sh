#!/bin/bash

# Jarvis Command Center V2 - Test Runner Script
# Executes all automated tests and generates summary

set -e

echo "======================================================================="
echo "JARVIS COMMAND CENTER V2 - AUTOMATED TEST SUITE RUNNER"
echo "======================================================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Navigate to project directory
cd "$(dirname "$0")/.."

# Check if backend is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend already running, using existing server${NC}"
    SERVER_STARTED=false
else
    echo "🚀 Starting backend server..."
    python3 backend/main_v2.py > /tmp/jarvis_test_server.log 2>&1 &
    SERVER_PID=$!
    SERVER_STARTED=true

    # Wait for server to start
    echo "⏳ Waiting for server to start..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Server started successfully${NC}"
            break
        fi
        sleep 1

        if [ $i -eq 10 ]; then
            echo -e "${RED}❌ Server failed to start${NC}"
            exit 1
        fi
    done
fi

echo ""
echo "======================================================================="
echo "RUNNING TEST SUITES"
echo "======================================================================="
echo ""

# Track results
TOTAL_PASSED=0
TOTAL_FAILED=0
FAILED_SUITES=()

# Function to run a test suite
run_test_suite() {
    local test_name=$1
    local test_file=$2

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Running: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if python3 "$test_file"; then
        echo -e "${GREEN}✅ $test_name: PASSED${NC}"
        # Extract pass/fail counts from test output
        # This is a simplified version - actual implementation would parse output
        TOTAL_PASSED=$((TOTAL_PASSED + 15))
    else
        echo -e "${RED}❌ $test_name: FAILED${NC}"
        FAILED_SUITES+=("$test_name")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi

    echo ""
}

# Run all test suites
run_test_suite "Backend API Tests" "tests/test_backend_api.py"
run_test_suite "WebSocket Tests" "tests/test_websocket.py"
run_test_suite "Edge Cases & Error Handling Tests" "tests/test_edge_cases.py"

# Frontend tests (manual - provide instructions)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Frontend Integration Tests (Manual)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  Frontend tests require manual execution in browser"
echo ""
echo "To run frontend tests:"
echo "  1. Open: file://$(pwd)/frontend/index_v2.html"
echo "  2. Open browser console (F12)"
echo "  3. Execute: const runner = new FrontendTestRunner(); await runner.runAll();"
echo ""

# Cleanup
if [ "$SERVER_STARTED" = true ]; then
    echo "🛑 Stopping test server..."
    kill $SERVER_PID 2>/dev/null || true
fi

# Summary
echo "======================================================================="
echo "TEST SUMMARY"
echo "======================================================================="
echo ""

TOTAL_TESTS=$((TOTAL_PASSED + TOTAL_FAILED))

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Total Test Suites: 3"
    echo "Passed: 3"
    echo "Failed: 0"
    echo "Success Rate: 100%"
    echo ""
    echo -e "${GREEN}🎉 Jarvis Command Center V2 is ready!${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Total Test Suites: 3"
    echo "Passed: $((3 - TOTAL_FAILED))"
    echo "Failed: $TOTAL_FAILED"
    echo ""
    echo "Failed Suites:"
    for suite in "${FAILED_SUITES[@]}"; do
        echo "  - $suite"
    done
    echo ""
    exit 1
fi
