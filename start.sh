#!/bin/bash
# Jarvis Command Center - Startup Script

echo "🚀 Starting Jarvis Command Center..."

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
echo "📦 Installing dependencies..."
pip3 install -q fastapi uvicorn websockets psutil requests click rich python-telegram-bot 2>/dev/null

# Start the API backend
echo "🔧 Starting API backend on port 8000..."
cd /Volumes/AI_WORKSPACE/CORE/jarvis_command_center/backend
python3 main.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Open the web interface
echo "🌐 Opening web interface..."
open /Volumes/AI_WORKSPACE/CORE/jarvis_command_center/frontend/index.html

# Optional: Start Telegram bot (uncomment if you want it to run)
# echo "🤖 Starting Telegram bot..."
# python3 telegram_bot.py &
# BOT_PID=$!
# echo "Bot PID: $BOT_PID"

echo ""
echo "✅ Jarvis Command Center is running!"
echo ""
echo "📍 Access Points:"
echo "   Web Interface: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   CLI: jarvis cmd 'your command'"
echo "   Telegram: @Videosxrapebot"
echo ""
echo "📋 Quick Commands:"
echo "   CLI Interactive Mode: python3 cli/jarvis_cli.py interactive"
echo "   CLI Monitor Mode: python3 cli/jarvis_cli.py monitor"
echo "   Stop All: Press Ctrl+C"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running and handle cleanup
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID 2>/dev/null; exit" INT TERM

# Wait for background processes
wait