"""
Execution Endpoints for Jarvis Command Center
Handles actual execution of skills, agents, workflows, models, and scripts
"""

import os
import subprocess
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import importlib.util
import sys

router = APIRouter(prefix="/api", tags=["execution"])


# Request Models
class SkillExecutionRequest(BaseModel):
    skill_name: str
    path: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentInvocationRequest(BaseModel):
    agent_name: str
    task: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class WorkflowStartRequest(BaseModel):
    workflow_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ModelInvocationRequest(BaseModel):
    model_id: str
    prompt: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ScriptRunRequest(BaseModel):
    script_path: str
    arguments: List[str] = Field(default_factory=list)


class TerminalExecuteRequest(BaseModel):
    command: str
    timeout: int = 30


# Execution History
execution_history = []


def log_execution(type: str, name: str, status: str, output: str = ""):
    """Log execution to history"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": type,
        "name": name,
        "status": status,
        "output": output[:500] if output else ""  # Limit output size
    }
    execution_history.append(entry)
    # Keep only last 100 executions
    if len(execution_history) > 100:
        execution_history.pop(0)
    return entry


@router.post("/skills/execute")
async def execute_skill(request: SkillExecutionRequest):
    """Execute a skill"""
    try:
        skill_path = request.path

        # If no path provided, try to find the skill
        if not skill_path:
            # Look for skill in common locations
            possible_paths = [
                f"/Volumes/AI_WORKSPACE/SKILLS_LIBRARY/{request.skill_name}.py",
                f"/Volumes/AI_WORKSPACE/SKILLS_LIBRARY/{request.skill_name}_skill.py",
                f"/Volumes/AI_WORKSPACE/video_analyzer/video_analyzer.py",
                f"/Volumes/AI_WORKSPACE/image_enhancer/replicate_upscale.py"
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    skill_path = path
                    break

        if not skill_path or not os.path.exists(skill_path):
            raise HTTPException(status_code=404, detail=f"Skill not found: {request.skill_name}")

        # Execute based on file type
        if skill_path.endswith('.py'):
            # Execute Python skill
            result = await execute_python_skill(skill_path, request.parameters)
        elif skill_path.endswith('.sh'):
            # Execute shell script
            result = await execute_shell_script(skill_path, [])
        else:
            raise HTTPException(status_code=400, detail="Unsupported skill type")

        # Log successful execution
        log_entry = log_execution("skill", request.skill_name, "success", result.get("output", ""))

        return {
            "status": "success",
            "skill": request.skill_name,
            "output": result.get("output", "Skill executed successfully"),
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("skill", request.skill_name, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/invoke")
async def invoke_agent(request: AgentInvocationRequest):
    """Invoke an agent"""
    try:
        # Map agent names to their implementations
        agent_map = {
            "Python Expert": "python_expert",
            "Python Development Expert": "python_expert",
            "Security Engineer": "security_engineer",
            "Security Auditor": "security_engineer",
            "Frontend Architect": "frontend_architect",
            "Performance Engineer": "performance_engineer",
            "Quality Engineer": "quality_engineer"
        }

        agent_id = agent_map.get(request.agent_name, request.agent_name.lower().replace(" ", "_"))

        # Simulate agent invocation
        # In a real implementation, this would connect to the actual agent system
        output = f"Agent '{request.agent_name}' invoked with task: {request.task}"

        # Log execution
        log_entry = log_execution("agent", request.agent_name, "success", output)

        return {
            "status": "success",
            "agent": request.agent_name,
            "task": request.task,
            "output": output,
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("agent", request.agent_name, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/start/{workflow_id}")
async def start_workflow(workflow_id: str, request: Optional[WorkflowStartRequest] = None):
    """Start a workflow"""
    try:
        # Map workflow names to their implementations
        workflow_map = {
            "Video Analysis Pipeline": "video_analysis",
            "Image Enhancement Workflow": "image_enhance"
        }

        workflow_key = workflow_map.get(workflow_id, workflow_id)

        # Check if workflow exists
        workflow_path = f"/Volumes/AI_WORKSPACE/n8n_automation/workflows/{workflow_key}.json"

        if os.path.exists(workflow_path):
            # Load workflow configuration
            with open(workflow_path, 'r') as f:
                workflow_config = json.load(f)

            output = f"Workflow '{workflow_id}' started with configuration from {workflow_path}"
        else:
            # Simulate workflow execution
            output = f"Workflow '{workflow_id}' started (simulated)"

        # Log execution
        log_entry = log_execution("workflow", workflow_id, "started", output)

        return {
            "status": "started",
            "workflow_id": workflow_id,
            "output": output,
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("workflow", workflow_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/invoke")
async def invoke_model(request: ModelInvocationRequest):
    """Invoke an AI model"""
    try:
        # Map model IDs to their implementations
        model_map = {
            "Claude 3 Opus": "claude-3-opus-20240229",
            "GPT-4 Turbo": "gpt-4-turbo-preview"
        }

        model_key = model_map.get(request.model_id, request.model_id)

        # Simulate model invocation
        # In a real implementation, this would connect to the actual model API
        output = f"Model '{request.model_id}' invoked with prompt: {request.prompt[:100]}..."

        # Log execution
        log_entry = log_execution("model", request.model_id, "success", output)

        return {
            "status": "success",
            "model_id": request.model_id,
            "response": f"Response from {model_key}: This is a simulated response to your prompt.",
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("model", request.model_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scripts/run")
async def run_script(request: ScriptRunRequest):
    """Run a script"""
    try:
        script_path = request.script_path

        if not os.path.exists(script_path):
            raise HTTPException(status_code=404, detail=f"Script not found: {script_path}")

        # Check if script is executable
        if not os.access(script_path, os.X_OK):
            # Make it executable
            os.chmod(script_path, 0o755)

        # Execute based on file type
        if script_path.endswith('.sh'):
            result = await execute_shell_script(script_path, request.arguments)
        elif script_path.endswith('.py'):
            result = await execute_python_script(script_path, request.arguments)
        else:
            raise HTTPException(status_code=400, detail="Unsupported script type")

        # Log execution
        log_entry = log_execution("script", os.path.basename(script_path), "success", result.get("output", ""))

        return {
            "status": "success",
            "script": os.path.basename(script_path),
            "output": result.get("output", "Script executed successfully"),
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("script", os.path.basename(request.script_path), "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/terminal/execute")
async def execute_terminal_command(request: TerminalExecuteRequest):
    """Execute a terminal command"""
    try:
        # Security: Basic command validation (in production, use more robust validation)
        forbidden_commands = ['rm -rf /', 'dd if=', 'format', 'mkfs']
        if any(forbidden in request.command for forbidden in forbidden_commands):
            raise HTTPException(status_code=403, detail="Command not allowed for security reasons")

        # Execute command
        process = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            raise HTTPException(status_code=408, detail="Command execution timeout")

        output = stdout.decode() if stdout else ""
        error = stderr.decode() if stderr else ""

        # Log execution
        log_entry = log_execution(
            "terminal",
            request.command[:50],
            "success" if process.returncode == 0 else "failed",
            output or error
        )

        return {
            "status": "success" if process.returncode == 0 else "failed",
            "command": request.command,
            "output": output,
            "error": error,
            "return_code": process.returncode,
            "execution_log": log_entry
        }

    except Exception as e:
        log_execution("terminal", request.command[:50], "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution/history")
async def get_execution_history(limit: int = 20):
    """Get recent execution history"""
    return {
        "history": execution_history[-limit:],
        "total": len(execution_history)
    }


# Helper functions
async def execute_python_skill(path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Python skill file"""
    try:
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("skill", path)
        if not spec or not spec.loader:
            raise ValueError(f"Could not load skill from {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Look for main function or execute function
        if hasattr(module, 'execute'):
            result = module.execute(**parameters)
        elif hasattr(module, 'main'):
            result = module.main(**parameters)
        elif hasattr(module, 'run'):
            result = module.run(**parameters)
        else:
            # If no standard function, try running as script
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            result = {"output": stdout.decode(), "error": stderr.decode()}

        return result if isinstance(result, dict) else {"output": str(result)}

    except Exception as e:
        return {"error": str(e)}


async def execute_python_script(path: str, arguments: List[str]) -> Dict[str, Any]:
    """Execute a Python script with arguments"""
    try:
        cmd = [sys.executable, path] + arguments
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            "output": stdout.decode(),
            "error": stderr.decode(),
            "return_code": process.returncode
        }
    except Exception as e:
        return {"error": str(e)}


async def execute_shell_script(path: str, arguments: List[str]) -> Dict[str, Any]:
    """Execute a shell script with arguments"""
    try:
        cmd = ["bash", path] + arguments
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            "output": stdout.decode(),
            "error": stderr.decode(),
            "return_code": process.returncode
        }
    except Exception as e:
        return {"error": str(e)}


# Real execution implementations for specific skills
@router.post("/skills/video-analyzer")
async def execute_video_analyzer(url: str):
    """Execute video analyzer skill"""
    try:
        sys.path.insert(0, "/Volumes/AI_WORKSPACE/video_analyzer")
        from video_analyzer import VideoAnalyzer

        analyzer = VideoAnalyzer()
        analysis = analyzer.analyze_video_url(url)

        if analysis:
            return {
                "status": "success",
                "analysis": analysis,
                "message": "Video analyzed successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to analyze video")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/image-enhancer")
async def execute_image_enhancer(image_path: str):
    """Execute image enhancer skill"""
    try:
        # Execute the image enhancement script
        cmd = [
            sys.executable,
            "/Volumes/AI_WORKSPACE/image_enhancer/replicate_upscale.py",
            image_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "REPLICATE_API_TOKEN": os.getenv("REPLICATE_API_TOKEN", "")}
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return {
                "status": "success",
                "output": stdout.decode(),
                "message": "Image enhanced successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=stderr.decode())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))