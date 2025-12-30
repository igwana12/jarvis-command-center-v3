#!/usr/bin/env python3
"""
Jarvis Command Center Backend V2 - SECURED VERSION
Implements all security remediations from security audit
"""

import os
import sys
import json
import asyncio
import psutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

from fastapi import FastAPI, WebSocket, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, validator
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Import security middleware
from security_middleware import (
    limiter,
    get_current_user,
    require_admin,
    User,
    verify_password,
    create_access_token,
    generate_ws_token,
    verify_ws_token,
    cleanup_expired_tokens,
    sanitize_command,
    validate_agent_name,
    validate_workflow_id,
    validate_path,
    safe_read_file,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    AuditLogger,
    USERS_DB,
    ALLOWED_BASE_PATHS,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Add import paths
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis/modules')
sys.path.append('/Volumes/AI_WORKSPACE/CORE/jarvis')
sys.path.append('/Volumes/AI_WORKSPACE')

# ======================
# Configuration
# ======================

# CORS - Restrictive configuration
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Webhook configuration
WEBHOOK_CONFIG = {
    'base_url': os.environ.get('N8N_WEBHOOK_BASE', 'https://localhost:5678'),
    'timeout': int(os.environ.get('N8N_WEBHOOK_TIMEOUT', '10')),
    'verify_ssl': os.environ.get('N8N_VERIFY_SSL', 'true').lower() == 'true',
}

# Initialize FastAPI with security
app = FastAPI(
    title="Jarvis Command Center V2 - Secured",
    description="Unified AI Assistant Interface with Security Hardening",
    version="2.0.0-secure",
    docs_url="/docs",  # Disable in production
    redoc_url="/redoc",  # Disable in production
)

# ======================
# Security Middleware
# ======================

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Restrictive
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request validation
app.add_middleware(RequestValidationMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# ======================
# Secure Request Session
# ======================

def get_secure_session():
    """Create secure requests session"""
    session = requests.Session()

    # Configure retries
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session

# ======================
# Request/Response Models with Validation
# ======================

class AllowedAction(str, Enum):
    VIDEO_ANALYSIS = "video_analysis"
    WORKFLOW_AUTOMATION = "workflow_automation"
    SYSTEM_MONITORING = "system_monitoring"
    AGENT_EXECUTION = "agent_execution"
    KNOWLEDGE_SEARCH = "knowledge_search"

class CommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=500)
    context: Optional[Dict] = Field(default_factory=dict)
    priority: str = Field(default="normal", regex="^(low|normal|high)$")

    @validator('command')
    def validate_command(cls, v):
        if any(char in v for char in ';&|`$()<>'):
            raise ValueError('Command contains invalid characters')
        return v

    @validator('context')
    def validate_context(cls, v):
        if len(str(v)) > 10000:
            raise ValueError('Context too large')
        return v

class AgentRequest(BaseModel):
    agent: str = Field(..., regex="^[a-z][a-z0-9-]*$")
    task: str = Field(..., min_length=1, max_length=1000)
    parameters: Optional[Dict] = Field(default_factory=dict)

class WorkflowRequest(BaseModel):
    workflow_id: str = Field(..., regex="^[a-zA-Z0-9_-]+$")
    parameters: Optional[Dict] = Field(default_factory=dict)

class AnalysisRequest(BaseModel):
    url: Optional[str] = Field(None, max_length=2048)
    content: Optional[str] = Field(None, max_length=100000)
    analysis_type: str = Field(default="auto", regex="^(auto|video|text|code)$")

# ======================
# Secure Resource Loader
# ======================

class SecureResourceLoader:
    """Securely load resources with path validation"""

    @staticmethod
    def load_slash_commands() -> Dict[str, Dict[str, str]]:
        """Load commands with path validation"""
        commands = {}

        command_dir = ALLOWED_BASE_PATHS['commands']
        if not command_dir.exists():
            return commands

        for cmd_file in command_dir.glob('*.md'):
            try:
                # Validate path
                if not validate_path(cmd_file, 'commands'):
                    continue

                # Safe read
                content = safe_read_file(cmd_file, 'commands', max_size=10000)
                desc = content.split('\n')[0].strip('#').strip()

                commands[f"/{cmd_file.stem}"] = {
                    "name": cmd_file.stem,
                    "description": desc[:200],  # Limit description length
                    "type": "command"
                }
            except Exception as e:
                print(f"Error loading command {cmd_file}: {e}")
                continue

        return commands

    @staticmethod
    def load_skills() -> Dict[str, Dict[str, Any]]:
        """Load skills with path validation"""
        skills = {}

        skills_dir = ALLOWED_BASE_PATHS['skills']
        if not skills_dir.exists():
            return skills

        for skill_folder in skills_dir.iterdir():
            try:
                # Validate path
                if not validate_path(skill_folder, 'skills'):
                    continue

                if not skill_folder.is_dir() or skill_folder.name.startswith('.'):
                    continue

                skill_info = {
                    "name": skill_folder.name,
                    "path": str(skill_folder),
                    "description": "",
                    "files": []
                }

                # Read description safely
                for desc_file in ['README.md', 'skill.md', f'{skill_folder.name}.md']:
                    desc_path = skill_folder / desc_file
                    try:
                        if validate_path(desc_path, 'skills') and desc_path.is_file():
                            content = safe_read_file(desc_path, 'skills', max_size=1000)
                            skill_info["description"] = content.split('\n')[0].strip('#').strip()[:200]
                            break
                    except Exception:
                        continue

                # List files safely
                for f in skill_folder.iterdir():
                    if validate_path(f, 'skills') and f.is_file() and not f.name.startswith('.'):
                        skill_info["files"].append(f.name)
                        if len(skill_info["files"]) >= 10:
                            break

                skills[skill_folder.name] = skill_info

            except Exception as e:
                print(f"Error loading skill {skill_folder}: {e}")
                continue

        return skills

# ======================
# Resource Manager (placeholder - use existing with secure loader)
# ======================

class ResourceManager:
    """Manages system resources securely"""

    def __init__(self):
        self.commands = {}
        self.skills = {}
        # ... other resources
        self.refresh()

    def refresh(self):
        """Refresh all resources"""
        loader = SecureResourceLoader()
        self.commands = loader.load_slash_commands()
        self.skills = loader.load_skills()
        # ... load other resources

resources = ResourceManager()

# ======================
# Authentication Endpoints
# ======================

@app.post("/token")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate and get access token"""

    user = USERS_DB.get(form_data.username)
    auth_success = False

    if user and verify_password(form_data.password, user.hashed_password):
        access_token = create_access_token(data={"sub": user.username})
        auth_success = True

        AuditLogger.log_auth_attempt(form_data.username, True, request.client.host)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    AuditLogger.log_auth_attempt(form_data.username, False, request.client.host)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.post("/auth/ws-token")
@limiter.limit("10/minute")
async def get_ws_token(request: Request, current_user: User = Depends(get_current_user)):
    """Get WebSocket authentication token"""

    token = generate_ws_token(current_user.username)

    return {
        "token": token,
        "expires_in": 86400  # 24 hours
    }

# ======================
# Secured API Endpoints
# ======================

@app.get("/")
async def root():
    """System information"""
    return {
        "name": "Jarvis Command Center V2 - Secured",
        "version": "2.0.0-secure",
        "status": "operational",
        "security": {
            "authentication": "enabled",
            "rate_limiting": "enabled",
            "cors": "restrictive",
            "https_required": True
        }
    }

@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Health check"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/command")
@limiter.limit("10/minute")
async def execute_command(
    request: Request,
    cmd_request: CommandRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute command with authentication and validation"""

    AuditLogger.log_access(current_user.username, "/command", True, request.client.host)

    # Sanitize command
    sanitized = sanitize_command(cmd_request.command)

    # Parse to allowed action
    command_lower = sanitized.lower()
    action = None

    if any(word in command_lower for word in ['analyze', 'video', 'youtube']):
        action = AllowedAction.VIDEO_ANALYSIS
    elif any(word in command_lower for word in ['workflow', 'n8n', 'automation']):
        action = AllowedAction.WORKFLOW_AUTOMATION
    elif any(word in command_lower for word in ['monitor', 'status', 'system']):
        action = AllowedAction.SYSTEM_MONITORING
    elif any(word in command_lower for word in ['agent', 'execute']):
        action = AllowedAction.AGENT_EXECUTION
    elif any(word in command_lower for word in ['search', 'knowledge']):
        action = AllowedAction.KNOWLEDGE_SEARCH

    if not action:
        raise HTTPException(
            status_code=400,
            detail="Invalid command. Allowed: video analysis, workflow, monitoring, agent, knowledge search"
        )

    return {
        "action": action.value,
        "status": "routing",
        "command": sanitized
    }

@app.post("/workflow/trigger")
@limiter.limit("30/hour")
async def trigger_workflow(
    request: Request,
    workflow_request: WorkflowRequest,
    current_user: User = Depends(get_current_user)
):
    """Trigger workflow with secure requests"""

    AuditLogger.log_access(current_user.username, "/workflow/trigger", True, request.client.host)

    # Validate workflow_id
    if not validate_workflow_id(workflow_request.workflow_id):
        raise HTTPException(status_code=400, detail="Invalid workflow ID")

    try:
        session = get_secure_session()

        webhook_url = f"{WEBHOOK_CONFIG['base_url']}/webhook/{workflow_request.workflow_id}"

        response = session.post(
            webhook_url,
            json=workflow_request.parameters or {},
            timeout=WEBHOOK_CONFIG['timeout'],
            verify=WEBHOOK_CONFIG['verify_ssl'],
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'JarvisCommandCenter/2.0-secure'
            }
        )

        response.raise_for_status()

        return {
            "status": "triggered",
            "workflow": workflow_request.workflow_id,
            "success": True
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Workflow timeout")
    except requests.exceptions.SSLError:
        raise HTTPException(status_code=502, detail="SSL verification failed")
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=502, detail="Workflow request failed")

@app.get("/processes")
@limiter.limit("30/minute")
async def get_processes(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """Get system processes - admin only"""

    processes = []
    ALLOWED_PROCESS_NAMES = {'python', 'node', 'uvicorn', 'n8n'}

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info

            # Only expose whitelisted processes
            if pinfo['name'] not in ALLOWED_PROCESS_NAMES:
                continue

            if pinfo['cpu_percent'] > 0.1 or pinfo['memory_percent'] > 0.1:
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu": round(pinfo['cpu_percent'], 1),
                    "memory": round(pinfo['memory_percent'], 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda x: x['cpu'], reverse=True)

    return {
        "count": len(processes),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "processes": processes[:10]
    }

# ======================
# Secured WebSocket
# ======================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket with authentication"""

    # Authenticate before accepting
    if not token or not await verify_ws_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        while True:
            await asyncio.sleep(2)

            # Cleanup expired tokens periodically
            cleanup_expired_tokens()

            status_data = {
                "type": "status_update",
                "timestamp": datetime.now().isoformat(),
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
            }

            await websocket.send_json(status_data)

            # Handle client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)

                # Validate commands
                if data == "refresh":
                    resources.refresh()
                    await websocket.send_json({"type": "refreshed"})
                else:
                    await websocket.send_json({"type": "error", "message": "Invalid command"})

            except asyncio.TimeoutError:
                pass

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# ======================
# Error Handlers
# ======================

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle errors without exposing internals"""

    # Log full error server-side
    print(f"Error on {request.url.path}: {exc}")

    # Return generic message
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": str(datetime.now().timestamp())
        }
    )

# ======================
# Main
# ======================

if __name__ == "__main__":
    import uvicorn

    print("🔒 Starting Jarvis Command Center V2 (SECURED)...")
    print("⚠️  WARNING: Change default password before production deployment!")
    print(f"\n🌐 API: https://localhost:8000")
    print(f"📖 Docs: https://localhost:8000/docs")

    uvicorn.run(
        app,
        host="127.0.0.1",  # Localhost only for security
        port=8000,
        ssl_keyfile="path/to/key.pem",  # Configure SSL
        ssl_certfile="path/to/cert.pem",
    )
