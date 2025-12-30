"""
Caching Layer for Jarvis Command Center V2
Provides intelligent resource caching with TTL and invalidation
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib
import json


class CacheEntry:
    """Single cache entry with metadata"""

    def __init__(self, data: Any, ttl: int = 300):
        self.data = data
        self.created_at = datetime.now()
        self.ttl = ttl
        self.hits = 0
        self.etag = self._generate_etag(data)

    def _generate_etag(self, data: Any) -> str:
        """Generate ETag for cache validation"""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return (datetime.now() - self.created_at).seconds > self.ttl

    def increment_hits(self):
        """Track cache hit statistics"""
        self.hits += 1


class ResourceCache:
    """High-performance caching layer for resources"""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'total_requests': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if exists and not expired"""
        self._stats['total_requests'] += 1

        if key in self._cache:
            entry = self._cache[key]

            if entry.is_expired():
                # Expired - remove and return None
                del self._cache[key]
                self._stats['misses'] += 1
                return None

            # Valid cache hit
            entry.increment_hits()
            self._stats['hits'] += 1
            return entry.data

        # Cache miss
        self._stats['misses'] += 1
        return None

    def set(self, key: str, data: Any, ttl: int = 300):
        """Set cache value with TTL"""
        self._cache[key] = CacheEntry(data, ttl)

    def get_or_load(self, key: str, loader: Callable, ttl: int = 300) -> Any:
        """Get from cache or load using provided function"""
        cached = self.get(key)

        if cached is not None:
            return cached

        # Load fresh data
        data = loader()
        self.set(key, data, ttl)
        return data

    def invalidate(self, key: str):
        """Invalidate specific cache key"""
        if key in self._cache:
            del self._cache[key]
            self._stats['invalidations'] += 1

    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        keys_to_delete = [
            k for k in self._cache.keys()
            if pattern in k
        ]

        for key in keys_to_delete:
            del self._cache[key]
            self._stats['invalidations'] += 1

    def clear(self):
        """Clear entire cache"""
        count = len(self._cache)
        self._cache.clear()
        self._stats['invalidations'] += count

    def get_etag(self, key: str) -> Optional[str]:
        """Get ETag for cache entry"""
        if key in self._cache and not self._cache[key].is_expired():
            return self._cache[key].etag
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._stats['total_requests']
        hit_ratio = (self._stats['hits'] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            'hit_ratio': round(hit_ratio, 2),
            'cache_size': len(self._cache),
            'total_hits': sum(e.hits for e in self._cache.values())
        }

    def cleanup_expired(self):
        """Remove all expired entries"""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


class CachedResourceManager:
    """Resource manager with caching layer"""

    def __init__(self, base_manager):
        self.base = base_manager
        self.cache = ResourceCache()

        # Different TTLs for different resource types
        self.ttls = {
            'agents': 600,      # 10 minutes (static)
            'commands': 600,    # 10 minutes (static)
            'skills': 300,      # 5 minutes (semi-dynamic)
            'mcp_servers': 300, # 5 minutes (semi-dynamic)
            'workflows': 300    # 5 minutes (semi-dynamic)
        }

    def get_agents(self) -> Dict[str, str]:
        """Get agents with caching"""
        return self.cache.get_or_load(
            'agents',
            self.base.load_superclaude_agents,
            self.ttls['agents']
        )

    def get_commands(self) -> Dict[str, Dict[str, str]]:
        """Get commands with caching"""
        return self.cache.get_or_load(
            'commands',
            self.base.load_slash_commands,
            self.ttls['commands']
        )

    def get_skills(self) -> Dict[str, Dict[str, Any]]:
        """Get skills with caching"""
        return self.cache.get_or_load(
            'skills',
            self.base.load_skills,
            self.ttls['skills']
        )

    def get_mcp_servers(self) -> Dict[str, Dict[str, str]]:
        """Get MCP servers with caching"""
        return self.cache.get_or_load(
            'mcp_servers',
            self.base.load_mcp_servers,
            self.ttls['mcp_servers']
        )

    def get_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get workflows with caching"""
        return self.cache.get_or_load(
            'workflows',
            self.base.load_workflows,
            self.ttls['workflows']
        )

    def refresh(self):
        """Refresh all resources (invalidate cache)"""
        self.cache.clear()
        self.base.refresh()

    def refresh_resource(self, resource_type: str):
        """Refresh specific resource type"""
        self.cache.invalidate(resource_type)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


def cache_response(ttl: int = 300):
    """Decorator for caching API responses"""

    def decorator(func):
        cache = ResourceCache()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(
                ":".join(key_parts).encode()
            ).hexdigest()

            # Try cache first
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        # Attach cache to wrapper for inspection
        wrapper.cache = cache
        return wrapper

    return decorator


# Metrics collection
class CacheMetrics:
    """Collect and analyze cache performance metrics"""

    def __init__(self, cache: ResourceCache):
        self.cache = cache
        self.start_time = datetime.now()

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        stats = self.cache.get_stats()
        uptime = (datetime.now() - self.start_time).seconds

        return {
            "uptime_seconds": uptime,
            "cache_stats": stats,
            "performance": {
                "hit_ratio": stats['hit_ratio'],
                "requests_per_second": stats['total_requests'] / max(uptime, 1),
                "cache_efficiency": (
                    stats['hits'] / max(stats['total_requests'], 1) * 100
                )
            },
            "recommendations": self._generate_recommendations(stats)
        }

    def _generate_recommendations(self, stats: Dict) -> list:
        """Generate optimization recommendations"""
        recommendations = []

        if stats['hit_ratio'] < 50:
            recommendations.append({
                "priority": "high",
                "message": f"Low cache hit ratio ({stats['hit_ratio']:.1f}%). Consider increasing TTL."
            })

        if stats['cache_size'] > 1000:
            recommendations.append({
                "priority": "medium",
                "message": f"Large cache size ({stats['cache_size']}). Consider cleanup or size limits."
            })

        if stats['total_requests'] > 10000 and stats['hit_ratio'] > 90:
            recommendations.append({
                "priority": "low",
                "message": f"Excellent cache performance ({stats['hit_ratio']:.1f}% hit ratio)."
            })

        return recommendations
