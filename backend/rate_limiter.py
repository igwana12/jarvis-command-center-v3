"""
Rate Limiting System for DoS Prevention
Implements token bucket algorithm with IP-based tracking
Council Security Recommendation Implementation
"""

import time
import json
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from pathlib import Path
import threading
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class TokenBucket:
    """
    Token bucket algorithm for smooth rate limiting
    Allows burst traffic while maintaining average rate
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket
        capacity: Maximum number of tokens
        refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        Returns True if successful, False if rate limited
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class RateLimiter:
    """
    Comprehensive rate limiting system
    Prevents DoS attacks with multiple protection layers
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize rate limiter with configuration"""
        self.config_path = config_path or "/Volumes/AI_WORKSPACE/CORE/jarvis_command_center/config/rate_limits.json"
        self.config = self._load_config()

        # IP-based token buckets
        self.ip_buckets: Dict[str, TokenBucket] = {}
        self.ip_buckets_lock = threading.Lock()

        # Request history for pattern detection
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Blocked IPs
        self.blocked_ips: Dict[str, datetime] = {}
        self.blocked_ips_lock = threading.Lock()

        # Whitelist for trusted IPs
        self.whitelist = set(self.config.get('whitelist', ['127.0.0.1', 'localhost']))

        # Statistics
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'rate_limited_requests': 0,
            'unique_ips': set()
        }

        # Start cleanup thread
        self._start_cleanup_thread()

    def _load_config(self) -> Dict:
        """Load rate limiting configuration"""
        default_config = {
            # Global limits
            'global_rate_limit': 100,  # requests per second
            'global_burst': 200,       # burst capacity

            # Per-IP limits
            'ip_rate_limit': 30,       # requests per second per IP
            'ip_burst': 60,            # burst capacity per IP

            # Endpoint-specific limits (requests per minute)
            'endpoint_limits': {
                '/api/knowledge/search': 30,
                '/api/knowledge/index': 5,
                '/api/antigravity/toggle': 10,
                '/api/cache/clear': 5,
                '/api/workflows/start': 10,
                '/api/costs/current': 60,
                '/api/metrics/history': 30,
                '/api/logs/recent': 20
            },

            # Protection thresholds
            'block_threshold': 1000,   # requests per minute to trigger block
            'block_duration': 3600,     # block duration in seconds (1 hour)
            'burst_threshold': 50,      # requests in 1 second to trigger burst protection

            # Whitelist (never rate limited)
            'whitelist': ['127.0.0.1', 'localhost', '::1'],

            # Advanced protection
            'enable_pattern_detection': True,
            'enable_distributed_attack_detection': True,
            'enable_slowloris_protection': True
        }

        # Try to load custom config
        config_path = Path(self.config_path)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    custom_config = json.load(f)
                    default_config.update(custom_config)
            except Exception as e:
                print(f"Warning: Could not load custom rate limit config: {e}")

        return default_config

    def check_rate_limit(self, request: Request, endpoint: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request should be rate limited
        Returns (allowed, reason) tuple
        """
        # Extract client IP
        client_ip = self._get_client_ip(request)

        # Update statistics
        self.stats['total_requests'] += 1
        self.stats['unique_ips'].add(client_ip)

        # Check whitelist
        if client_ip in self.whitelist:
            return True, None

        # Check if IP is blocked
        if self._is_blocked(client_ip):
            self.stats['blocked_requests'] += 1
            return False, f"IP {client_ip} is temporarily blocked due to excessive requests"

        # Check for attack patterns
        if self.config['enable_pattern_detection']:
            if self._detect_attack_pattern(client_ip, endpoint):
                self._block_ip(client_ip)
                return False, "Suspicious request pattern detected"

        # Get or create token bucket for IP
        bucket = self._get_ip_bucket(client_ip)

        # Check endpoint-specific limits
        endpoint_limit = self.config['endpoint_limits'].get(endpoint)
        if endpoint_limit:
            if not self._check_endpoint_limit(client_ip, endpoint, endpoint_limit):
                self.stats['rate_limited_requests'] += 1
                return False, f"Endpoint rate limit exceeded for {endpoint}"

        # Check IP rate limit
        if not bucket.consume():
            self.stats['rate_limited_requests'] += 1

            # Check if should block IP
            self._record_request(client_ip, endpoint)
            if self._should_block_ip(client_ip):
                self._block_ip(client_ip)
                return False, f"IP {client_ip} blocked due to excessive requests"

            return False, "Rate limit exceeded. Please slow down your requests."

        # Record successful request
        self._record_request(client_ip, endpoint)

        return True, None

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request"""
        # Check for proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(',')[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        return request.client.host if request.client else "unknown"

    def _get_ip_bucket(self, ip: str) -> TokenBucket:
        """Get or create token bucket for IP"""
        with self.ip_buckets_lock:
            if ip not in self.ip_buckets:
                self.ip_buckets[ip] = TokenBucket(
                    capacity=self.config['ip_burst'],
                    refill_rate=self.config['ip_rate_limit']
                )
            return self.ip_buckets[ip]

    def _check_endpoint_limit(self, ip: str, endpoint: str, limit: int) -> bool:
        """Check endpoint-specific rate limit (per minute)"""
        key = f"{ip}:{endpoint}"
        now = time.time()

        # Get request times for this endpoint
        if key not in self.request_history:
            self.request_history[key] = deque(maxlen=limit)

        history = self.request_history[key]

        # Remove old entries (older than 1 minute)
        while history and history[0] < now - 60:
            history.popleft()

        # Check if under limit
        if len(history) >= limit:
            return False

        history.append(now)
        return True

    def _record_request(self, ip: str, endpoint: str):
        """Record request for pattern analysis"""
        key = f"requests:{ip}"
        now = time.time()

        if key not in self.request_history:
            self.request_history[key] = deque(maxlen=1000)

        self.request_history[key].append({
            'time': now,
            'endpoint': endpoint
        })

    def _detect_attack_pattern(self, ip: str, endpoint: str) -> bool:
        """
        Detect potential attack patterns
        Returns True if suspicious pattern detected
        """
        key = f"requests:{ip}"
        history = self.request_history.get(key, [])

        if not history:
            return False

        now = time.time()

        # Check for burst attacks (too many requests in 1 second)
        recent_second = [r for r in history if r['time'] > now - 1]
        if len(recent_second) > self.config['burst_threshold']:
            return True

        # Check for slowloris attack (keeping connections open)
        if self.config['enable_slowloris_protection']:
            slow_endpoints = ['/api/knowledge/search', '/api/logs/recent']
            if endpoint in slow_endpoints:
                recent_minute = [r for r in history if r['time'] > now - 60 and r['endpoint'] in slow_endpoints]
                if len(recent_minute) > 100:
                    return True

        # Check for scanning patterns (hitting many different endpoints rapidly)
        if self.config['enable_distributed_attack_detection']:
            recent_10s = [r for r in history if r['time'] > now - 10]
            unique_endpoints = set(r['endpoint'] for r in recent_10s)
            if len(unique_endpoints) > 20:  # Hitting too many different endpoints
                return True

        return False

    def _should_block_ip(self, ip: str) -> bool:
        """Check if IP should be blocked based on request history"""
        key = f"requests:{ip}"
        history = self.request_history.get(key, [])

        if not history:
            return False

        now = time.time()

        # Count requests in last minute
        recent_minute = [r for r in history if r['time'] > now - 60]

        return len(recent_minute) > self.config['block_threshold']

    def _block_ip(self, ip: str):
        """Block an IP address temporarily"""
        with self.blocked_ips_lock:
            self.blocked_ips[ip] = datetime.now() + timedelta(seconds=self.config['block_duration'])
            print(f"⚠️  Blocked IP {ip} until {self.blocked_ips[ip]}")

    def _is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        with self.blocked_ips_lock:
            if ip in self.blocked_ips:
                if datetime.now() < self.blocked_ips[ip]:
                    return True
                else:
                    # Block expired, remove it
                    del self.blocked_ips[ip]
        return False

    def _start_cleanup_thread(self):
        """Start background thread to clean up old data"""
        def cleanup():
            while True:
                time.sleep(300)  # Run every 5 minutes

                # Clean up old request history
                now = time.time()
                for key in list(self.request_history.keys()):
                    history = self.request_history[key]
                    if isinstance(history, deque) and history:
                        # Remove if all entries are old
                        if all(isinstance(r, dict) and r.get('time', 0) < now - 3600 for r in history):
                            del self.request_history[key]

                # Clean up expired blocks
                with self.blocked_ips_lock:
                    expired = [ip for ip, expiry in self.blocked_ips.items() if datetime.now() > expiry]
                    for ip in expired:
                        del self.blocked_ips[ip]

                # Clean up old token buckets
                with self.ip_buckets_lock:
                    # Remove buckets not used in last hour
                    to_remove = []
                    for ip, bucket in self.ip_buckets.items():
                        if bucket.last_refill < now - 3600:
                            to_remove.append(ip)
                    for ip in to_remove:
                        del self.ip_buckets[ip]

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()

    def get_stats(self) -> Dict:
        """Get rate limiting statistics"""
        return {
            'total_requests': self.stats['total_requests'],
            'blocked_requests': self.stats['blocked_requests'],
            'rate_limited_requests': self.stats['rate_limited_requests'],
            'unique_ips': len(self.stats['unique_ips']),
            'currently_blocked_ips': len(self.blocked_ips),
            'active_buckets': len(self.ip_buckets),
            'config': {
                'ip_rate_limit': self.config['ip_rate_limit'],
                'ip_burst': self.config['ip_burst'],
                'block_threshold': self.config['block_threshold'],
                'block_duration': self.config['block_duration']
            }
        }

    def reset_ip(self, ip: str):
        """Manually reset/unblock an IP (admin function)"""
        with self.blocked_ips_lock:
            if ip in self.blocked_ips:
                del self.blocked_ips[ip]

        with self.ip_buckets_lock:
            if ip in self.ip_buckets:
                del self.ip_buckets[ip]

        # Clear request history
        keys_to_remove = [k for k in self.request_history.keys() if ip in k]
        for key in keys_to_remove:
            del self.request_history[key]

        return {"message": f"IP {ip} has been reset"}


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get singleton instance of rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# FastAPI middleware
async def rate_limit_middleware(request: Request, call_next):
    """
    FastAPI middleware for rate limiting
    Add this to your FastAPI app:
    app.middleware("http")(rate_limit_middleware)
    """
    rate_limiter = get_rate_limiter()

    # Get endpoint path
    endpoint = request.url.path

    # Check rate limit
    allowed, reason = rate_limiter.check_rate_limit(request, endpoint)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": reason,
                "retry_after": 60
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(rate_limiter.config['ip_rate_limit']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.config['ip_rate_limit'])
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

    return response