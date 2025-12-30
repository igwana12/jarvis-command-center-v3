#!/usr/bin/env python3
"""
Integration Improvements: Enhanced n8n, Video Analyzer, and Service Integrations
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
import asyncio
import logging
from enum import Enum
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger("jarvis.integrations")

# ======================
# Models
# ======================

class IntegrationStatus(str, Enum):
    """Integration health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"

class WebhookResponse(BaseModel):
    """n8n webhook response"""
    success: bool
    execution_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ServiceHealth(BaseModel):
    """Service health check result"""
    service_name: str
    status: IntegrationStatus
    response_time_ms: Optional[float] = None
    last_check: str = Field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None

class VideoAnalysisRequest(BaseModel):
    """Video analysis request"""
    url: HttpUrl
    analysis_type: str = "auto"
    extract_audio: bool = False
    extract_frames: bool = False
    generate_summary: bool = True

class VideoAnalysisResult(BaseModel):
    """Video analysis result"""
    url: str
    title: Optional[str] = None
    duration: Optional[float] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    frames: List[str] = []
    metadata: Dict[str, Any] = {}

# ======================
# Enhanced n8n Integration
# ======================

class N8nClient:
    """Enhanced n8n webhook client with retry logic"""

    def __init__(
        self,
        base_url: str = "http://localhost:5678",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
    )
    async def trigger_webhook(
        self,
        webhook_id: str,
        data: Dict[str, Any],
        method: str = "POST"
    ) -> WebhookResponse:
        """
        Trigger n8n webhook with retry logic

        Args:
            webhook_id: Webhook identifier
            data: Payload to send
            method: HTTP method (POST, GET, etc.)

        Returns:
            WebhookResponse with execution details
        """
        url = f"{self.base_url}/webhook/{webhook_id}"
        logger.info(f"Triggering n8n webhook: {webhook_id}")

        try:
            if method.upper() == "POST":
                response = await self.client.post(url, json=data)
            else:
                response = await self.client.get(url, params=data)

            response.raise_for_status()

            # Parse response
            response_data = response.json() if response.text else {}

            return WebhookResponse(
                success=True,
                execution_id=response.headers.get("x-n8n-execution-id"),
                data=response_data
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"n8n webhook failed: {e.response.status_code} - {e.response.text}")
            return WebhookResponse(
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text}"
            )

        except httpx.TimeoutException:
            logger.error(f"n8n webhook timeout: {webhook_id}")
            return WebhookResponse(
                success=False,
                error="Request timeout"
            )

        except Exception as e:
            logger.exception(f"n8n webhook error: {e}")
            return WebhookResponse(
                success=False,
                error=str(e)
            )

    async def check_health(self) -> ServiceHealth:
        """Check n8n service health"""
        start_time = datetime.now()

        try:
            response = await self.client.get(f"{self.base_url}/healthz", timeout=5.0)
            response.raise_for_status()

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            return ServiceHealth(
                service_name="n8n",
                status=IntegrationStatus.HEALTHY,
                response_time_ms=elapsed_ms
            )

        except httpx.HTTPStatusError as e:
            return ServiceHealth(
                service_name="n8n",
                status=IntegrationStatus.DEGRADED,
                error_message=f"HTTP {e.response.status_code}"
            )

        except Exception as e:
            return ServiceHealth(
                service_name="n8n",
                status=IntegrationStatus.DOWN,
                error_message=str(e)
            )

    async def close(self):
        """Close client connection"""
        await self.client.aclose()

# ======================
# Enhanced Video Analyzer Integration
# ======================

class AsyncVideoAnalyzer:
    """Async wrapper for video analyzer"""

    def __init__(self, analyzer_module=None):
        self.analyzer = analyzer_module
        self._executor = None

    async def analyze_video(self, request: VideoAnalysisRequest) -> VideoAnalysisResult:
        """
        Analyze video asynchronously

        Args:
            request: Video analysis request

        Returns:
            VideoAnalysisResult with analysis data
        """
        logger.info(f"Analyzing video: {request.url}")

        try:
            # Run synchronous analyzer in thread pool
            result = await asyncio.to_thread(
                self._analyze_sync,
                request
            )

            return VideoAnalysisResult(**result)

        except Exception as e:
            logger.exception(f"Video analysis failed: {e}")
            raise

    def _analyze_sync(self, request: VideoAnalysisRequest) -> Dict[str, Any]:
        """Synchronous video analysis (runs in thread pool)"""
        if not self.analyzer:
            raise RuntimeError("Video analyzer not available")

        # Call actual video analyzer
        analysis = self.analyzer.analyze_video_url(str(request.url))

        return {
            "url": str(request.url),
            "title": analysis.get("title"),
            "duration": analysis.get("duration"),
            "summary": analysis.get("summary"),
            "transcript": analysis.get("transcript"),
            "metadata": analysis.get("metadata", {})
        }

# ======================
# Service Registry
# ======================

class ServiceRegistry:
    """Central registry for all service integrations"""

    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.health_cache: Dict[str, ServiceHealth] = {}
        self.health_ttl = 60  # seconds

    def register(self, name: str, service: Any):
        """Register a service"""
        self.services[name] = service
        logger.info(f"Registered service: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Get a service by name"""
        return self.services.get(name)

    async def check_all_health(self) -> Dict[str, ServiceHealth]:
        """Check health of all registered services"""
        results = {}

        for name, service in self.services.items():
            if hasattr(service, 'check_health'):
                try:
                    health = await service.check_health()
                    results[name] = health
                    self.health_cache[name] = health
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {e}")
                    results[name] = ServiceHealth(
                        service_name=name,
                        status=IntegrationStatus.UNKNOWN,
                        error_message=str(e)
                    )
            else:
                results[name] = ServiceHealth(
                    service_name=name,
                    status=IntegrationStatus.UNKNOWN,
                    error_message="No health check available"
                )

        return results

    def get_health_summary(self) -> Dict[str, Any]:
        """Get summary of service health"""
        healthy = sum(1 for h in self.health_cache.values() if h.status == IntegrationStatus.HEALTHY)
        total = len(self.health_cache)

        return {
            "total_services": total,
            "healthy": healthy,
            "degraded": sum(1 for h in self.health_cache.values() if h.status == IntegrationStatus.DEGRADED),
            "down": sum(1 for h in self.health_cache.values() if h.status == IntegrationStatus.DOWN),
            "health_percentage": (healthy / total * 100) if total > 0 else 0,
            "services": {name: health.dict() for name, health in self.health_cache.items()}
        }

# ======================
# Circuit Breaker Pattern
# ======================

class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Circuit breaker for failing services"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit"""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.timeout

# ======================
# Background Health Monitor
# ======================

class HealthMonitor:
    """Background service health monitoring"""

    def __init__(self, registry: ServiceRegistry, check_interval: int = 60):
        self.registry = registry
        self.check_interval = check_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start health monitoring"""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started")

    async def stop(self):
        """Stop health monitoring"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                await self.registry.check_all_health()
                logger.debug("Health check completed")
            except Exception as e:
                logger.error(f"Health check error: {e}")

            await asyncio.sleep(self.check_interval)

# ======================
# Example Usage
# ======================

async def example_usage():
    """Example of using enhanced integrations"""

    # Initialize services
    n8n = N8nClient()
    registry = ServiceRegistry()
    registry.register("n8n", n8n)

    # Check service health
    health = await registry.check_all_health()
    print(f"Service health: {health}")

    # Trigger workflow with retry
    response = await n8n.trigger_webhook(
        webhook_id="master-pipeline",
        data={"task": "analyze video", "url": "https://example.com/video"}
    )

    print(f"Webhook response: {response}")

    # Start health monitoring
    monitor = HealthMonitor(registry)
    await monitor.start()

    # Get health summary
    summary = registry.get_health_summary()
    print(f"Health summary: {summary}")

    # Cleanup
    await monitor.stop()
    await n8n.close()

if __name__ == "__main__":
    asyncio.run(example_usage())
