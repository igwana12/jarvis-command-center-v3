#!/usr/bin/env python3
"""
Comprehensive Error Handling for Jarvis Command Center
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from typing import Any, Optional, Dict, List
from datetime import datetime
import logging
import traceback
import sys

logger = logging.getLogger("jarvis.errors")

# ======================
# Error Response Models
# ======================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    field: Optional[str] = None
    message: str
    type: str

class ErrorResponse(BaseModel):
    """Standardized error response"""
    success: bool = False
    error: str
    error_code: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: str
    path: Optional[str] = None
    request_id: Optional[str] = None

class SuccessResponse(BaseModel):
    """Standardized success response"""
    success: bool = True
    data: Any
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str

# ======================
# Custom Exceptions
# ======================

class JarvisException(Exception):
    """Base exception for Jarvis errors"""
    def __init__(self, message: str, error_code: str, status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class ResourceNotFoundException(JarvisException):
    """Resource not found exception"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            status_code=404
        )

class ValidationException(JarvisException):
    """Validation error exception"""
    def __init__(self, message: str, details: Optional[List[ErrorDetail]] = None):
        self.details = details
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422
        )

class IntegrationException(JarvisException):
    """External integration error"""
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} integration error: {message}",
            error_code="INTEGRATION_ERROR",
            status_code=502
        )

class RateLimitException(JarvisException):
    """Rate limit exceeded"""
    def __init__(self, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window}",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429
        )

class AuthenticationException(JarvisException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            status_code=401
        )

class AuthorizationException(JarvisException):
    """Authorization failed"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            status_code=403
        )

# ======================
# Error Handlers
# ======================

async def jarvis_exception_handler(request: Request, exc: JarvisException) -> JSONResponse:
    """Handle custom Jarvis exceptions"""
    logger.error(
        f"JarvisException: {exc.error_code} - {exc.message}",
        extra={"path": str(request.url), "error_code": exc.error_code}
    )

    error_response = ErrorResponse(
        error=exc.message,
        error_code=exc.error_code,
        timestamp=datetime.now().isoformat(),
        path=str(request.url),
        request_id=request.headers.get("X-Request-ID")
    )

    # Add details if validation exception
    if isinstance(exc, ValidationException) and exc.details:
        error_response.details = exc.details

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"path": str(request.url)}
    )

    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            type=error["type"]
        )
        for error in exc.errors()
    ]

    error_response = ErrorResponse(
        error="Request validation failed",
        error_code="VALIDATION_ERROR",
        details=details,
        timestamp=datetime.now().isoformat(),
        path=str(request.url)
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict()
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"path": str(request.url), "status_code": exc.status_code}
    )

    error_response = ErrorResponse(
        error=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
        timestamp=datetime.now().isoformat(),
        path=str(request.url)
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    # Log full traceback
    logger.exception(
        "Unhandled exception",
        extra={
            "path": str(request.url),
            "exception_type": type(exc).__name__
        }
    )

    # Get traceback for debugging (only in development)
    debug_mode = sys.gettrace() is not None
    debug_info = None

    if debug_mode:
        debug_info = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }

    error_response = ErrorResponse(
        error="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        timestamp=datetime.now().isoformat(),
        path=str(request.url)
    )

    response_data = error_response.dict()
    if debug_info:
        response_data["debug"] = debug_info

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data
    )

# ======================
# Response Helpers
# ======================

def success_response(
    data: Any,
    metadata: Optional[Dict[str, Any]] = None
) -> SuccessResponse:
    """Create standardized success response"""
    return SuccessResponse(
        data=data,
        metadata=metadata,
        timestamp=datetime.now().isoformat()
    )

def error_response(
    error: str,
    error_code: str,
    status_code: int = 500,
    details: Optional[List[ErrorDetail]] = None
) -> JSONResponse:
    """Create standardized error response"""
    response = ErrorResponse(
        error=error,
        error_code=error_code,
        details=details,
        timestamp=datetime.now().isoformat()
    )

    return JSONResponse(
        status_code=status_code,
        content=response.dict()
    )

# ======================
# Error Context Manager
# ======================

class ErrorContext:
    """Context manager for consistent error handling"""

    def __init__(self, operation: str, logger: logging.Logger = logger):
        self.operation = operation
        self.logger = logger

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True

        # Log error with context
        self.logger.error(
            f"Error in {self.operation}: {exc_val}",
            exc_info=(exc_type, exc_val, exc_tb)
        )

        # Don't suppress exception
        return False

# ======================
# Logging Configuration
# ======================

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Configure structured logging"""
    from logging.handlers import RotatingFileHandler
    import json

    # Create logger
    logger = logging.getLogger("jarvis")
    logger.setLevel(getattr(logging, level.upper()))

    # JSON formatter for structured logs
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            }

            # Add extra fields
            if hasattr(record, "path"):
                log_data["path"] = record.path
            if hasattr(record, "error_code"):
                log_data["error_code"] = record.error_code
            if hasattr(record, "request_id"):
                log_data["request_id"] = record.request_id

            # Add exception info if present
            if record.exc_info:
                log_data["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_data)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (JSON format) if specified
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger

# ======================
# Utility Functions
# ======================

def sanitize_error_message(message: str, max_length: int = 500) -> str:
    """Sanitize error messages to prevent information leakage"""
    # Remove file paths
    import re
    message = re.sub(r'/[^\s]+', '[PATH]', message)

    # Truncate if too long
    if len(message) > max_length:
        message = message[:max_length] + "..."

    return message

def get_error_category(exc: Exception) -> str:
    """Categorize exception for metrics/monitoring"""
    if isinstance(exc, (ValidationError, RequestValidationError)):
        return "validation"
    elif isinstance(exc, HTTPException):
        if 400 <= exc.status_code < 500:
            return "client_error"
        return "server_error"
    elif isinstance(exc, ConnectionError):
        return "connection"
    elif isinstance(exc, TimeoutError):
        return "timeout"
    else:
        return "unknown"
