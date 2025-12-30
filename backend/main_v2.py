#!/usr/bin/env python3
"""
Jarvis Command Center Backend V2 - Full Integration
Dynamically loads and integrates all available agents, skills, MCP servers, and workflows
"""

import os
import sys
import json
import asyncio
import psutil
import requests
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import subprocess
import re

# Add import paths
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis/modules')
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis')
sys.path.append('/Volumes/AI_WORKSPACE')

# Import Jarvis modules
try:
    from video_analyzer import VideoAnalyzer
    from video_knowledge_loader import search_video_knowledge
except ImportError as e:
    print(f"Warning: Could not import video modules: {e}")

# Initialize FastAPI
app = FastAPI(
    title="Jarvis Command Center V2",
    description="Unified AI Assistant Interface with Full Integration",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# Dynamic Resource Discovery
# ======================

class ResourceLoader:
    """Dynamically loads all available resources from the system"""

    @staticmethod
    def load_superclaude_agents() -> Dict[str, str]:
        """Load all SuperClaude agents from Task tool and commands"""
        agents = {}

        # Core agents from Task tool
        core_agents = {
            "general-purpose": "General-purpose agent for researching complex questions and multi-step tasks",
            "statusline-setup": "Configure the user's Claude Code status line setting",
            "explore": "Fast agent for exploring codebases",
            "plan": "Fast agent for planning and exploration",
            "python-expert": "Deliver production-ready Python code",
            "system-architect": "Design scalable system architecture",
            "refactoring-expert": "Improve code quality and reduce technical debt",
            "devops-architect": "Automate infrastructure and deployment",
            "learning-guide": "Teach programming concepts",
            "security-engineer": "Identify security vulnerabilities",
            "frontend-architect": "Create accessible, performant user interfaces",
            "quality-engineer": "Ensure software quality through testing",
            "root-cause-analyst": "Investigate complex problems",
            "pm-agent": "Self-improvement workflow executor",
            "socratic-mentor": "Educational guide using Socratic method",
            "business-panel-experts": "Multi-expert business strategy panel",
            "performance-engineer": "Optimize system performance",
            "requirements-analyst": "Transform ideas into specifications",
            "backend-architect": "Design reliable backend systems",
            "deep-research-agent": "Comprehensive research with adaptive strategies",
            "technical-writer": "Create clear technical documentation",
            "webapp-testing": "Test local web applications",
        }
        agents.update(core_agents)

        return agents

    @staticmethod
    def load_slash_commands() -> Dict[str, Dict[str, str]]:
        """Load all available slash commands"""
        commands = {}

        # Load from .claude/commands directory
        command_dir = Path('/Users/igwanapc/.claude/commands')
        if command_dir.exists():
            for cmd_file in command_dir.glob('*.md'):
                cmd_name = cmd_file.stem
                try:
                    with open(cmd_file, 'r') as f:
                        content = f.read(500)  # Read first 500 chars for description
                        # Extract description from content
                        desc = content.split('\n')[0].strip('#').strip()
                        commands[f"/{cmd_name}"] = {
                            "name": cmd_name,
                            "description": desc,
                            "type": "command"
                        }
                except:
                    pass

        # Add SC commands
        sc_commands = {
            "/sc:brainstorm": {"name": "brainstorm", "description": "Interactive requirements discovery", "type": "sc"},
            "/sc:test": {"name": "test", "description": "Execute tests with coverage analysis", "type": "sc"},
            "/sc:cleanup": {"name": "cleanup", "description": "Clean up code and optimize structure", "type": "sc"},
            "/sc:pm": {"name": "pm", "description": "Project Manager Agent", "type": "sc"},
            "/sc:design": {"name": "design", "description": "Design system architecture", "type": "sc"},
            "/sc:task": {"name": "task", "description": "Execute complex tasks", "type": "sc"},
            "/sc:git": {"name": "git", "description": "Git operations with intelligent commits", "type": "sc"},
            "/sc:save": {"name": "save", "description": "Session lifecycle management", "type": "sc"},
            "/sc:build": {"name": "build", "description": "Build and package projects", "type": "sc"},
            "/sc:index": {"name": "index", "description": "Generate project documentation", "type": "sc"},
            "/sc:research": {"name": "research", "description": "Deep web research", "type": "sc"},
            "/sc:load": {"name": "load", "description": "Load project context", "type": "sc"},
            "/sc:help": {"name": "help", "description": "List all /sc commands", "type": "sc"},
            "/sc:select-tool": {"name": "select-tool", "description": "Intelligent MCP tool selection", "type": "sc"},
            "/sc:workflow": {"name": "workflow", "description": "Generate implementation workflows", "type": "sc"},
            "/sc:analyze": {"name": "analyze", "description": "Comprehensive code analysis", "type": "sc"},
            "/sc:reflect": {"name": "reflect", "description": "Task reflection and validation", "type": "sc"},
            "/sc:explain": {"name": "explain", "description": "Provide clear explanations", "type": "sc"},
            "/sc:improve": {"name": "improve", "description": "Apply systematic improvements", "type": "sc"},
            "/sc:troubleshoot": {"name": "troubleshoot", "description": "Diagnose and resolve issues", "type": "sc"},
            "/sc:implement": {"name": "implement", "description": "Feature implementation", "type": "sc"},
            "/sc:spec-panel": {"name": "spec-panel", "description": "Multi-expert specification review", "type": "sc"},
            "/sc:estimate": {"name": "estimate", "description": "Development estimates", "type": "sc"},
            "/sc:spawn": {"name": "spawn", "description": "Meta-system task orchestration", "type": "sc"},
            "/sc:document": {"name": "document", "description": "Generate focused documentation", "type": "sc"},
        }
        commands.update(sc_commands)

        return commands

    @staticmethod
    def load_skills() -> Dict[str, Dict[str, Any]]:
        """Load all available skills from SKILLS_LIBRARY"""
        skills = {}

        skills_dir = Path('/Volumes/AI_WORKSPACE/SKILLS_LIBRARY')
        if skills_dir.exists():
            for skill_folder in skills_dir.iterdir():
                if skill_folder.is_dir() and not skill_folder.name.startswith('.'):
                    skill_info = {
                        "name": skill_folder.name,
                        "path": str(skill_folder),
                        "description": "",
                        "files": []
                    }

                    # Try to read skill description from README or skill.md
                    for desc_file in ['README.md', 'skill.md', f'{skill_folder.name}.md']:
                        desc_path = skill_folder / desc_file
                        if desc_path.exists():
                            try:
                                with open(desc_path, 'r') as f:
                                    content = f.read(500)
                                    skill_info["description"] = content.split('\n')[0].strip('#').strip()
                                break
                            except:
                                pass

                    # List available files
                    skill_info["files"] = [f.name for f in skill_folder.iterdir()
                                          if f.is_file() and not f.name.startswith('.')][:10]

                    skills[skill_folder.name] = skill_info

        return skills

    @staticmethod
    def load_mcp_servers() -> Dict[str, Dict[str, str]]:
        """Load available MCP servers"""
        mcp_servers = {
            "sequential-thinking": {
                "name": "Sequential Thinking",
                "description": "Complex multi-step reasoning and hypothesis testing",
                "status": "available"
            },
            "playwright": {
                "name": "Playwright",
                "description": "Browser automation and testing",
                "status": "available"
            },
            "chrome-devtools": {
                "name": "Chrome DevTools",
                "description": "Browser debugging and performance analysis",
                "status": "available"
            },
            "magic": {
                "name": "Magic UI",
                "description": "UI component generation from 21st.dev",
                "status": "available"
            },
            "context7": {
                "name": "Context7",
                "description": "Documentation lookup and pattern guidance",
                "status": "available"
            },
            "morphllm": {
                "name": "MorphLLM",
                "description": "Bulk code transformations and pattern application",
                "status": "available"
            },
            "serena": {
                "name": "Serena",
                "description": "Session management and project persistence",
                "status": "available"
            }
        }
        return mcp_servers

    @staticmethod
    def load_workflows() -> Dict[str, Dict[str, Any]]:
        """Load n8n workflows"""
        workflows = {}

        # Check for workflow configuration
        workflow_config_path = Path('/Volumes/AI_WORKSPACE/n8n_automation/workflows.json')
        if workflow_config_path.exists():
            try:
                with open(workflow_config_path, 'r') as f:
                    workflows = json.load(f)
            except:
                pass

        # Default workflows if no config found
        if not workflows:
            workflows = {
                "master-pipeline": {
                    "name": "Master Pipeline",
                    "description": "Main orchestration workflow",
                    "webhook_id": "master-pipeline",
                    "parameters": ["task", "priority"]
                },
                "video-processor": {
                    "name": "Video Processor",
                    "description": "Process and analyze video content",
                    "webhook_id": "video-processor",
                    "parameters": ["url", "analysis_type"]
                },
                "knowledge-extractor": {
                    "name": "Knowledge Extractor",
                    "description": "Extract knowledge from content",
                    "webhook_id": "knowledge-extractor",
                    "parameters": ["source", "format"]
                },
                "telegram-notifier": {
                    "name": "Telegram Notifier",
                    "description": "Send notifications to Telegram",
                    "webhook_id": "telegram-notifier",
                    "parameters": ["message", "chat_id"]
                }
            }

        return workflows

# ======================
# Global Resource Storage
# ======================

class ResourceManager:
    """Manages all system resources"""

    def __init__(self):
        self.agents = {}
        self.commands = {}
        self.skills = {}
        self.mcp_servers = {}
        self.workflows = {}
        self.refresh()

    def refresh(self):
        """Refresh all resources"""
        loader = ResourceLoader()
        self.agents = loader.load_superclaude_agents()
        self.commands = loader.load_slash_commands()
        self.skills = loader.load_skills()
        self.mcp_servers = loader.load_mcp_servers()
        self.workflows = loader.load_workflows()

    def search(self, query: str) -> Dict[str, List]:
        """Search across all resources"""
        query_lower = query.lower()
        results = {
            "agents": [],
            "commands": [],
            "skills": [],
            "mcp_servers": [],
            "workflows": []
        }

        # Search agents
        for name, desc in self.agents.items():
            if query_lower in name.lower() or query_lower in desc.lower():
                results["agents"].append({"name": name, "description": desc})

        # Search commands
        for cmd, info in self.commands.items():
            if query_lower in cmd.lower() or query_lower in info.get("description", "").lower():
                results["commands"].append(info)

        # Search skills
        for name, info in self.skills.items():
            if query_lower in name.lower() or query_lower in info.get("description", "").lower():
                results["skills"].append(info)

        # Search MCP servers
        for name, info in self.mcp_servers.items():
            if query_lower in name.lower() or query_lower in info.get("description", "").lower():
                results["mcp_servers"].append(info)

        # Search workflows
        for name, info in self.workflows.items():
            if query_lower in name.lower() or query_lower in info.get("description", "").lower():
                results["workflows"].append(info)

        return results

# Initialize resource manager
resources = ResourceManager()

# ======================
# Request/Response Models
# ======================

class CommandRequest(BaseModel):
    command: str
    context: Optional[Dict] = {}
    priority: str = "normal"

class AgentRequest(BaseModel):
    agent: str
    task: str
    parameters: Optional[Dict] = {}

class WorkflowRequest(BaseModel):
    workflow_id: str
    parameters: Optional[Dict] = {}

class AnalysisRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None
    analysis_type: str = "auto"

# ======================
# API Endpoints
# ======================

@app.get("/")
async def root():
    """System information and capabilities"""
    return {
        "name": "Jarvis Command Center V2",
        "version": "2.0.0",
        "status": "operational",
        "capabilities": {
            "agents": len(resources.agents),
            "commands": len(resources.commands),
            "skills": len(resources.skills),
            "mcp_servers": len(resources.mcp_servers),
            "workflows": len(resources.workflows)
        },
        "endpoints": {
            "agents": "/agents",
            "commands": "/commands",
            "skills": "/skills",
            "mcp_servers": "/mcp-servers",
            "workflows": "/workflows",
            "search": "/search"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/refresh")
async def refresh_resources():
    """Refresh all resources"""
    resources.refresh()
    return {
        "status": "refreshed",
        "counts": {
            "agents": len(resources.agents),
            "commands": len(resources.commands),
            "skills": len(resources.skills),
            "mcp_servers": len(resources.mcp_servers),
            "workflows": len(resources.workflows)
        }
    }

@app.get("/agents")
async def get_agents():
    """Get all available agents"""
    return {
        "count": len(resources.agents),
        "agents": resources.agents
    }

@app.get("/commands")
async def get_commands():
    """Get all available commands"""
    return {
        "count": len(resources.commands),
        "commands": resources.commands
    }

@app.get("/skills")
async def get_skills():
    """Get all available skills"""
    return {
        "count": len(resources.skills),
        "skills": resources.skills
    }

@app.get("/mcp-servers")
async def get_mcp_servers():
    """Get all MCP servers"""
    return {
        "count": len(resources.mcp_servers),
        "servers": resources.mcp_servers
    }

@app.get("/workflows")
async def get_workflows():
    """Get all workflows"""
    return {
        "count": len(resources.workflows),
        "workflows": resources.workflows
    }

@app.get("/search")
async def search_resources(q: str):
    """Search across all resources"""
    if not q:
        return {"error": "Query parameter required"}

    results = resources.search(q)
    total = sum(len(v) for v in results.values())

    return {
        "query": q,
        "total_results": total,
        "results": results
    }

@app.post("/command")
async def execute_command(request: CommandRequest):
    """Execute natural language command with intelligent routing"""
    command = request.command.lower()

    # Route to appropriate handler
    if "analyze" in command and any(word in command for word in ["video", "youtube", "tiktok"]):
        return {"action": "video_analysis", "status": "routing", "handler": "video_analyzer"}
    elif any(word in command for word in ["workflow", "n8n", "automation"]):
        return {"action": "workflow_automation", "status": "routing", "handler": "n8n"}
    elif any(word in command for word in ["monitor", "status", "system"]):
        return {"action": "system_monitoring", "status": "routing", "handler": "monitoring"}
    else:
        # Suggest relevant resources
        suggestions = resources.search(command)
        return {
            "action": "suggestion",
            "message": f"Processing: {request.command}",
            "suggestions": suggestions
        }

@app.post("/agent/execute")
async def execute_agent(request: AgentRequest):
    """Execute specific agent"""
    if request.agent not in resources.agents:
        raise HTTPException(status_code=404, detail=f"Agent {request.agent} not found")

    # Here we would integrate with actual agent execution
    return {
        "status": "executing",
        "agent": request.agent,
        "task": request.task,
        "task_id": f"task_{datetime.now().timestamp()}"
    }

@app.post("/workflow/trigger")
async def trigger_workflow(request: WorkflowRequest):
    """Trigger n8n workflow"""
    if request.workflow_id not in resources.workflows:
        raise HTTPException(status_code=404, detail=f"Workflow {request.workflow_id} not found")

    workflow = resources.workflows[request.workflow_id]

    # Trigger via n8n webhook
    try:
        webhook_url = f"http://localhost:5678/webhook/{workflow['webhook_id']}"
        response = requests.post(webhook_url, json=request.parameters or {})
        return {
            "status": "triggered",
            "workflow": request.workflow_id,
            "response": response.json() if response.ok else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/analyze")
async def analyze_content(request: AnalysisRequest):
    """Analyze video or other content"""
    if request.url and "video" in request.analysis_type:
        try:
            analyzer = VideoAnalyzer()
            analysis = analyzer.analyze_video_url(request.url)
            return {
                "status": "completed",
                "analysis_type": "video",
                "analysis": analysis
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return {"status": "pending", "message": "Analysis type not implemented"}

@app.get("/knowledge/search")
async def search_knowledge(query: str):
    """Search knowledge base"""
    try:
        # Search video knowledge
        results = search_video_knowledge(query)

        # Also search skills
        skill_results = []
        for skill_name, skill_info in resources.skills.items():
            if query.lower() in skill_name.lower() or query.lower() in skill_info.get("description", "").lower():
                skill_results.append({
                    "skill": skill_name,
                    "title": skill_info.get("description", skill_name),
                    "snippet": f"Skill: {skill_name} - {skill_info.get('description', 'No description')}",
                    "type": "skill"
                })

        all_results = results[:10] if isinstance(results, list) else []
        all_results.extend(skill_results[:5])

        return {
            "query": query,
            "count": len(all_results),
            "results": all_results
        }
    except Exception as e:
        return {"error": str(e), "results": []}

@app.get("/knowledge/topics")
async def get_knowledge_topics():
    """Get available knowledge topics"""
    topics = set()

    # Get topics from video knowledge
    knowledge_dir = Path('/Volumes/AI_WORKSPACE/SKILLS_LIBRARY/video_knowledge')
    if knowledge_dir.exists():
        for file in knowledge_dir.glob('*.md'):
            topics.add(file.stem.replace('_', ' ').title())

    # Add skill categories
    for skill_name in resources.skills.keys():
        topics.add(skill_name.replace('-', ' ').title())

    return {"topics": sorted(list(topics))}

@app.get("/processes")
async def get_processes():
    """Get system processes and resource usage"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] > 0.1 or pinfo['memory_percent'] > 0.1:
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu": pinfo['cpu_percent'],
                    "memory": pinfo['memory_percent']
                })
        except:
            pass

    # Sort by CPU usage
    processes.sort(key=lambda x: x['cpu'], reverse=True)

    return {
        "count": len(processes),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "processes": processes[:20]
    }

@app.get("/tasks/recent")
async def get_recent_tasks():
    """Get recent tasks (mock for now)"""
    # In production, this would query a task database
    return {
        "tasks": [
            {"id": "1", "type": "video_analysis", "status": "completed", "timestamp": datetime.now().isoformat()},
            {"id": "2", "type": "agent_execution", "status": "running", "agent": "root-cause-analyst"},
            {"id": "3", "type": "workflow", "status": "pending", "workflow": "master-pipeline"}
        ]
    }

# ======================
# WebSocket for Real-time Updates
# ======================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time monitoring"""
    await websocket.accept()

    try:
        while True:
            # Send system status every 2 seconds
            await asyncio.sleep(2)

            status = {
                "type": "status_update",
                "timestamp": datetime.now().isoformat(),
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "active_tasks": 3  # Mock value
            }

            await websocket.send_json(status)

            # Check for client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                if data == "refresh":
                    resources.refresh()
                    await websocket.send_json({"type": "refreshed"})
            except asyncio.TimeoutError:
                pass

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# ======================
# Main Execution
# ======================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Jarvis Command Center V2...")
    print(f"📊 Loaded Resources:")
    print(f"   • {len(resources.agents)} Agents")
    print(f"   • {len(resources.commands)} Commands")
    print(f"   • {len(resources.skills)} Skills")
    print(f"   • {len(resources.mcp_servers)} MCP Servers")
    print(f"   • {len(resources.workflows)} Workflows")
    print(f"\n🌐 API running at http://localhost:8000")
    print(f"📖 Documentation at http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)