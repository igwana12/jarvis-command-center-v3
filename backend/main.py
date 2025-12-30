#!/usr/bin/env python3
"""
Jarvis Command Center - Unified API Backend
Clean, minimalist, powerful interface for all Jarvis capabilities
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio
import json
import os
import sys
import psutil
import subprocess
from pathlib import Path
import importlib.util

# Add parent directories to path
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis')
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis/modules')
sys.path.append('/Volumes/AI_WORKSPACE/video_analyzer')
sys.path.append('/Volumes/AI_WORKSPACE')

# Import Jarvis modules
try:
    from video_knowledge_loader import search_video_knowledge, get_video_transcript, list_videos_about
    from video_analyzer import VideoAnalyzer
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")

# Models for API
class CommandRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = {}
    priority: str = "normal"  # normal, high, urgent

class WorkflowTrigger(BaseModel):
    workflow_id: str
    parameters: Dict[str, Any] = {}
    webhook_url: Optional[str] = "http://localhost:5678/webhook/master-pipeline"

class AgentRequest(BaseModel):
    agent: str
    task: str
    parameters: Dict[str, Any] = {}

class AnalysisRequest(BaseModel):
    url: str
    analysis_type: str = "video"  # video, image, text, code

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.system_status = {
            "cpu": 0,
            "memory": 0,
            "disk": 0,
            "active_processes": [],
            "recent_tasks": [],
            "active_agents": []
        }

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial status
        await self.send_personal_message(json.dumps({
            "type": "connected",
            "data": self.system_status
        }), websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Background task for system monitoring
async def monitor_system():
    """Monitor system status and broadcast updates"""
    while True:
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get running processes
            active_procs = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                if 'python' in proc.info['name'].lower():
                    active_procs.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu": proc.info['cpu_percent'],
                        "memory": proc.info['memory_percent']
                    })

            # Update manager status
            manager.system_status.update({
                "cpu": cpu_percent,
                "memory": memory.percent,
                "disk": disk.percent,
                "active_processes": active_procs[:10],  # Top 10 processes
                "timestamp": datetime.now().isoformat()
            })

            # Broadcast to all connected clients
            await manager.broadcast(json.dumps({
                "type": "system_update",
                "data": manager.system_status
            }))

            await asyncio.sleep(5)  # Update every 5 seconds
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(monitor_system())
    yield
    # Shutdown
    task.cancel()

# Create FastAPI app
app = FastAPI(
    title="Jarvis Command Center API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Available agents and their capabilities
AVAILABLE_AGENTS = {
    "root-cause-analyst": "Systematically investigate complex problems",
    "performance-engineer": "Optimize system performance",
    "frontend-architect": "Create accessible, performant user interfaces",
    "backend-architect": "Design reliable backend systems",
    "security-engineer": "Identify security vulnerabilities",
    "learning-guide": "Teach programming concepts",
    "refactoring-expert": "Improve code quality",
    "quality-engineer": "Ensure software quality through testing",
    "devops-architect": "Automate infrastructure and deployment",
    "requirements-analyst": "Transform ideas into specifications",
    "technical-writer": "Create clear technical documentation",
    "pm-agent": "Self-improvement workflow executor"
}

# MCP Servers available
MCP_SERVERS = {
    "sequential-thinking": "Complex multi-step reasoning",
    "playwright": "Browser automation and testing",
    "chrome-devtools": "Browser debugging and performance",
    "magic": "UI component generation",
    "context7": "Documentation lookup",
    "morphllm": "Bulk code transformations",
    "serena": "Session management and persistence"
}

# Routes

@app.get("/")
async def root():
    """Root endpoint with system info"""
    return {
        "name": "Jarvis Command Center",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "websocket": "ws://localhost:8000/ws",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "up",
            "websocket": "up",
            "monitoring": "up"
        }
    }

@app.get("/agents")
async def list_agents():
    """List all available agents"""
    return {"agents": AVAILABLE_AGENTS}

@app.get("/mcp-servers")
async def list_mcp_servers():
    """List all available MCP servers"""
    return {"servers": MCP_SERVERS}

@app.post("/command")
async def execute_command(request: CommandRequest):
    """
    Universal command endpoint - routes to appropriate handler
    Uses natural language understanding to determine intent
    """
    command = request.command.lower()

    # Route based on command patterns
    if "analyze" in command and ("video" in command or "url" in command):
        # Route to video analysis
        return {"action": "video_analysis", "status": "routing"}

    elif "workflow" in command or "n8n" in command or "automate" in command:
        # Route to workflow automation
        return {"action": "workflow_automation", "status": "routing"}

    elif "code" in command or "develop" in command or "build" in command:
        # Route to code development
        return {"action": "code_development", "status": "routing"}

    elif "monitor" in command or "status" in command or "system" in command:
        # Return system status
        return {"action": "system_monitoring", "data": manager.system_status}

    else:
        # Use AI to understand intent
        return {
            "action": "ai_routing",
            "message": f"Processing: {request.command}",
            "suggested_agents": _suggest_agents(command)
        }

def _suggest_agents(command: str) -> List[str]:
    """Suggest appropriate agents based on command"""
    suggestions = []

    keywords = {
        "debug": ["root-cause-analyst"],
        "slow": ["performance-engineer"],
        "ui": ["frontend-architect"],
        "api": ["backend-architect"],
        "security": ["security-engineer"],
        "learn": ["learning-guide"],
        "test": ["quality-engineer"],
        "deploy": ["devops-architect"]
    }

    for keyword, agents in keywords.items():
        if keyword in command.lower():
            suggestions.extend(agents)

    return list(set(suggestions)) if suggestions else ["pm-agent"]

@app.post("/workflow/trigger")
async def trigger_workflow(request: WorkflowTrigger):
    """Trigger an n8n workflow"""
    try:
        import requests

        # Send to n8n webhook
        response = requests.post(
            request.webhook_url or f"http://localhost:5678/webhook/{request.workflow_id}",
            json={
                "workflow_id": request.workflow_id,
                "parameters": request.parameters,
                "timestamp": datetime.now().isoformat()
            }
        )

        return {
            "status": "triggered",
            "workflow_id": request.workflow_id,
            "response": response.status_code == 200
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/execute")
async def execute_agent(request: AgentRequest):
    """Execute a specific agent with a task"""
    if request.agent not in AVAILABLE_AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent {request.agent} not found")

    # Add to active agents
    manager.system_status["active_agents"].append({
        "agent": request.agent,
        "task": request.task[:100],
        "started": datetime.now().isoformat()
    })

    # Broadcast status update
    await manager.broadcast(json.dumps({
        "type": "agent_started",
        "data": {
            "agent": request.agent,
            "task": request.task
        }
    }))

    return {
        "status": "executing",
        "agent": request.agent,
        "task_id": f"{request.agent}_{datetime.now().timestamp()}"
    }

@app.post("/analyze")
async def analyze_content(request: AnalysisRequest):
    """Analyze video or other content"""
    if request.analysis_type == "video":
        try:
            analyzer = VideoAnalyzer()
            analysis = analyzer.analyze_video_url(request.url)

            # Add to recent tasks
            manager.system_status["recent_tasks"].insert(0, {
                "type": "video_analysis",
                "url": request.url,
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if analysis else "failed"
            })

            # Keep only last 10 tasks
            manager.system_status["recent_tasks"] = manager.system_status["recent_tasks"][:10]

            return {
                "status": "completed",
                "analysis": analysis
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "unsupported_type", "type": request.analysis_type}

@app.get("/knowledge/search")
async def search_knowledge(query: str):
    """Search the video knowledge base"""
    try:
        results = search_video_knowledge(query)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": str(e)
        }

@app.get("/knowledge/topics")
async def get_knowledge_topics():
    """Get all available knowledge topics"""
    topics = ["ai", "agent", "automation", "n8n", "code", "tools", "gemini", "prompts"]
    return {"topics": topics}

@app.get("/processes")
async def get_processes():
    """Get running processes"""
    return {
        "processes": manager.system_status["active_processes"],
        "count": len(manager.system_status["active_processes"])
    }

@app.get("/tasks/recent")
async def get_recent_tasks():
    """Get recent tasks"""
    return {
        "tasks": manager.system_status["recent_tasks"],
        "count": len(manager.system_status["recent_tasks"])
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(json.dumps({"type": "pong"}), websocket)
            elif message.get("type") == "command":
                # Process command through websocket
                result = await execute_command(CommandRequest(command=message.get("command", "")))
                await manager.send_personal_message(json.dumps({
                    "type": "command_result",
                    "data": result
                }), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)