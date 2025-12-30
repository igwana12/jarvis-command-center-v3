"""
Security Middleware for Jarvis Command Center V2
Implements authentication, rate limiting, and security headers
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import re

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json

# ======================
# Configuration
# ======================

SECRET_KEY = os.environ.get("JARVIS_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
TOKEN_EXPIRY = timedelta(hours=24)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Security bearer
security = HTTPBearer()

# WebSocket tokens (in production, use Redis)
VALID_WS_TOKENS: Dict[str, dict] = {}

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# ======================
# Logging
# ======================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("jarvis_security")

class AuditLogger:
    """Security audit logging"""

    @staticmethod
    def log_access(user: str, endpoint: str, success: bool, ip: str):
        logger.info(json.dumps({
            "event": "api_access",
            "user": user,
            "endpoint": endpoint,
            "success": success,
            "ip": ip,
            "timestamp": datetime.now().isoformat()
        }))

    @staticmethod
    def log_auth_attempt(username: str, success: bool, ip: str):
        level = logging.INFO if success else logging.WARNING
        logger.log(level, json.dumps({
            "event": "auth_attempt",
            "username": username,
            "success": success,
            "ip": ip,
            "timestamp": datetime.now().isoformat()
        }))

    @staticmethod
    def log_suspicious_activity(description: str, ip: str, data: dict):
        logger.critical(json.dumps({
            "event": "suspicious_activity",
            "description": description,
            "ip": ip,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))

# ======================
# User Management
# ======================

class User:
    """User model"""
    def __init__(self, username: str, hashed_password: str, roles: list = None):
        self.username = username
        self.hashed_password = hashed_password
        self.roles = roles or ["user"]

# Mock user database (replace with real database in production)
USERS_DB = {
    "admin": User("admin", pwd_context.hash("CHANGE_THIS_PASSWORD"), ["admin", "user"])
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = USERS_DB.get(username)
    if user is None:
        raise credentials_exception

    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ======================
# WebSocket Authentication
# ======================

def generate_ws_token(user: str) -> str:
    """Generate WebSocket authentication token"""
    token = secrets.token_urlsafe(32)
    VALID_WS_TOKENS[token] = {
        'expires': datetime.now() + TOKEN_EXPIRY,
        'user': user
    }
    return token

async def verify_ws_token(token: str) -> bool:
    """Verify WebSocket authentication token"""
    if token not in VALID_WS_TOKENS:
        return False

    # Check expiry
    if VALID_WS_TOKENS[token]['expires'] < datetime.now():
        del VALID_WS_TOKENS[token]
        return False

    return True

def cleanup_expired_tokens():
    """Clean up expired WebSocket tokens"""
    now = datetime.now()
    expired = [token for token, data in VALID_WS_TOKENS.items() if data['expires'] < now]
    for token in expired:
        del VALID_WS_TOKENS[token]

# ======================
# Input Validation
# ======================

def sanitize_command(command: str) -> str:
    """Sanitize command input"""
    # Remove dangerous characters
    sanitized = re.sub(r'[;&|`$()<>]', '', command)
    # Limit length
    sanitized = sanitized[:500]
    # Remove multiple spaces
    sanitized = ' '.join(sanitized.split())
    return sanitized

def validate_agent_name(agent: str) -> bool:
    """Validate agent name format"""
    return bool(re.match(r'^[a-z][a-z0-9-]*$', agent))

def validate_workflow_id(workflow_id: str) -> bool:
    """Validate workflow ID format"""
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', workflow_id))

# ======================
# Path Security
# ======================

ALLOWED_BASE_PATHS = {
    'commands': Path('/Users/igwanapc/.claude/commands'),
    'skills': Path('/Volumes/AI_WORKSPACE/SKILLS_LIBRARY'),
    'workflows': Path('/Volumes/AI_WORKSPACE/n8n_automation'),
}

def validate_path(path: Path, base_key: str) -> bool:
    """Validate path is within allowed base directory"""
    try:
        # Resolve to absolute path
        resolved_path = path.resolve()
        base_path = ALLOWED_BASE_PATHS[base_key].resolve()

        # Check if path is within base
        return str(resolved_path).startswith(str(base_path))
    except (ValueError, KeyError):
        return False

def safe_read_file(file_path: Path, base_key: str, max_size: int = 50000) -> str:
    """Safely read file with validation"""

    # Validate path
    if not validate_path(file_path, base_key):
        raise ValueError(f"Path {file_path} is outside allowed directory")

    # Check file exists and is regular file
    if not file_path.is_file():
        raise ValueError(f"Path {file_path} is not a regular file")

    # Check file size
    if file_path.stat().st_size > max_size:
        raise ValueError(f"File {file_path} exceeds maximum size")

    # Read file
    return file_path.read_text(encoding='utf-8', errors='ignore')

# ======================
# Security Headers Middleware
# ======================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws://localhost:8000 wss://localhost:8000"
        )
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

# ======================
# Request Validation Middleware
# ======================

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate all incoming requests"""

    SUSPICIOUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'<script',  # XSS
        r'javascript:',  # XSS
        r'on\w+\s*=',  # Event handlers
        r'eval\(',  # Code execution
        r'exec\(',  # Code execution
        r'\bor\b.*=.*',  # SQL injection patterns
        r'union\s+select',  # SQL injection
    ]

    async def dispatch(self, request: Request, call_next):
        # Check request body for suspicious patterns
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_str = body.decode('utf-8')

                for pattern in self.SUSPICIOUS_PATTERNS:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        AuditLogger.log_suspicious_activity(
                            f"Suspicious pattern detected: {pattern}",
                            request.client.host,
                            {"path": request.url.path, "pattern": pattern}
                        )

                        return HTTPException(
                            status_code=400,
                            detail="Request contains suspicious content"
                        )

            except Exception:
                pass  # Continue if body can't be read

        response = await call_next(request)
        return response
