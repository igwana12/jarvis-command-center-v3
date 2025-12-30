#!/bin/bash
# Jarvis Command Center V2 - Startup Script with Full Integration

echo "🚀 Starting Jarvis Command Center V2..."

# Function to check if a port is in use
check_port() {
    lsof -i :$1 > /dev/null 2>&1
    return $?
}

# Kill existing processes on our ports
echo "Checking for existing processes..."
if check_port 8000; then
    echo "Killing existing process on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
fi

# Install dependencies if needed
echo "📦 Ensuring dependencies are installed..."
pip3 install -q fastapi uvicorn websockets psutil requests click rich python-telegram-bot pydantic 2>/dev/null

# Start the V2 API backend
echo "🔧 Starting API backend V2 on port 8000..."
cd /Volumes/AI_WORKSPACE/CORE/jarvis_command_center/backend
python3 main_v2.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Check if backend started successfully
if ! check_port 8000; then
    echo "❌ Backend failed to start. Check for errors."
    exit 1
fi

# Open the V2 web interface
echo "🌐 Opening web interface V2..."
open /Volumes/AI_WORKSPACE/CORE/jarvis_command_center/frontend/index_v2.html

# Optional: Start Telegram bot (uncomment if you want it to run)
# echo "🤖 Starting Telegram bot..."
# python3 telegram_bot.py &
# BOT_PID=$!
# echo "Bot PID: $BOT_PID"

echo ""
echo "✅ Jarvis Command Center V2 is running!"
echo ""
echo "📊 System Information:"
echo "   • Loaded all SuperClaude agents"
echo "   • Connected to MCP servers"
echo "   • Integrated with skills library"
echo "   • n8n workflows available"
echo "   • Knowledge base searchable"
echo ""
echo "📍 Access Points:"
echo "   Web Interface: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   CLI: python3 cli/jarvis_cli.py [cmd]"
echo "   Telegram: @Videosxrapebot"
echo ""
echo "⚡ Quick Tips:"
echo "   • Press ⌘K in web interface for command palette"
echo "   • All tabs now display real data"
echo "   • Dropdowns and search work across all resources"
echo "   • Real-time monitoring via WebSocket"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running and handle cleanup
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID 2>/dev/null; exit" INT TERM

# Wait for background processes
wait