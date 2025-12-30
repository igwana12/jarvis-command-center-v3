"""
Redis Caching Layer with In-Memory Fallback
Provides distributed caching, session management, and real-time updates
Council Performance Recommendation Implementation
"""

import json
import time
import pickle
import hashlib
import threading
from typing import Any, Optional, Dict, List, Set
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from pathlib import Path

try:
    import redis
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis not installed. Using in-memory cache fallback.")


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL support
    Fallback when Redis is not available
    """

    def __init__(self, max_size: int = 10000):
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.max_size = max_size
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache:
                # Check if expired
                entry = self.cache[key]
                if entry['expiry'] and time.time() > entry['expiry']:
                    del self.cache[key]
                    self.stats['misses'] += 1
                    return None

                # Move to end (LRU)
                self.cache.move_to_end(key)
                self.stats['hits'] += 1
                return entry['value']

            self.stats['misses'] += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        with self.lock:
            expiry = time.time() + ttl if ttl else None

            # Evict if at max size
            if len(self.cache) >= self.max_size and key not in self.cache:
                # Remove oldest (LRU)
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1

            self.cache[key] = {
                'value': value,
                'expiry': expiry,
                'created': time.time()
            }
            self.cache.move_to_end(key)
            self.stats['sets'] += 1
            return True

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['deletes'] += 1
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if entry['expiry'] and time.time() > entry['expiry']:
                    del self.cache[key]
                    return False
                return True
            return False

    def flush(self):
        """Clear all cache"""
        with self.lock:
            self.cache.clear()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

            return {
                **self.stats,
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate
            }


class RedisCache:
    """
    Redis caching layer with automatic fallback to in-memory
    Provides distributed caching for scalability
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Redis cache with configuration"""
        self.config = config or self._default_config()
        self.redis_client = None
        self.fallback_cache = InMemoryCache(max_size=self.config['max_memory_items'])

        # Statistics
        self.stats = defaultdict(int)

        # Initialize Redis connection
        self._init_redis()

        # Start cleanup thread
        self._start_cleanup_thread()

    def _default_config(self) -> Dict:
        """Default Redis configuration"""
        return {
            # Redis connection
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'connection_pool_max_connections': 50,

            # Cache settings
            'default_ttl': 300,  # 5 minutes
            'max_ttl': 86400,    # 24 hours
            'key_prefix': 'jarvis:',

            # Memory fallback
            'max_memory_items': 10000,
            'enable_fallback': True,

            # Features
            'enable_compression': True,
            'compression_threshold': 1024,  # Compress values > 1KB
            'enable_json_serialization': True
        }

    def _init_redis(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            print("📦 Redis module not installed. Using in-memory cache.")
            return

        try:
            # Create connection pool
            pool = redis.ConnectionPool(
                host=self.config['host'],
                port=self.config['port'],
                db=self.config['db'],
                password=self.config['password'],
                socket_timeout=self.config['socket_timeout'],
                socket_connect_timeout=self.config['socket_connect_timeout'],
                max_connections=self.config['connection_pool_max_connections']
            )

            self.redis_client = redis.Redis(connection_pool=pool)

            # Test connection
            self.redis_client.ping()
            print(f"✅ Redis connected at {self.config['host']}:{self.config['port']}")

        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Using in-memory cache fallback")
            self.redis_client = None

    def _get_key(self, key: str) -> str:
        """Get prefixed cache key"""
        return f"{self.config['key_prefix']}{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if self.config['enable_json_serialization']:
            try:
                serialized = json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                # Fall back to pickle for non-JSON serializable objects
                serialized = pickle.dumps(value)
        else:
            serialized = pickle.dumps(value)

        # Compress if enabled and value is large enough
        if self.config['enable_compression'] and len(serialized) > self.config['compression_threshold']:
            import zlib
            serialized = b'COMPRESSED:' + zlib.compress(serialized)

        return serialized

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data.startswith(b'COMPRESSED:'):
            import zlib
            data = zlib.decompress(data[11:])

        if self.config['enable_json_serialization']:
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)
        else:
            return pickle.loads(data)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        full_key = self._get_key(key)

        # Try Redis first
        if self.redis_client:
            try:
                data = self.redis_client.get(full_key)
                if data:
                    self.stats['redis_hits'] += 1
                    return self._deserialize(data)
                self.stats['redis_misses'] += 1
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis get error: {e}")

        # Fallback to in-memory cache
        if self.config['enable_fallback']:
            value = self.fallback_cache.get(full_key)
            if value is not None:
                self.stats['memory_hits'] += 1
            else:
                self.stats['memory_misses'] += 1
            return value

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        full_key = self._get_key(key)
        ttl = ttl or self.config['default_ttl']
        ttl = min(ttl, self.config['max_ttl'])

        serialized = self._serialize(value)

        # Try Redis first
        if self.redis_client:
            try:
                result = self.redis_client.setex(full_key, ttl, serialized)
                self.stats['redis_sets'] += 1
                return bool(result)
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis set error: {e}")

        # Fallback to in-memory cache
        if self.config['enable_fallback']:
            self.stats['memory_sets'] += 1
            return self.fallback_cache.set(full_key, value, ttl)

        return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        full_key = self._get_key(key)

        deleted = False

        # Try Redis first
        if self.redis_client:
            try:
                result = self.redis_client.delete(full_key)
                deleted = bool(result)
                self.stats['redis_deletes'] += 1
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis delete error: {e}")

        # Also delete from in-memory cache
        if self.config['enable_fallback']:
            memory_deleted = self.fallback_cache.delete(full_key)
            self.stats['memory_deletes'] += 1
            deleted = deleted or memory_deleted

        return deleted

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        full_key = self._get_key(key)

        # Try Redis first
        if self.redis_client:
            try:
                exists = self.redis_client.exists(full_key)
                return bool(exists)
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis exists error: {e}")

        # Fallback to in-memory cache
        if self.config['enable_fallback']:
            return self.fallback_cache.exists(full_key)

        return False

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys at once"""
        full_keys = [self._get_key(k) for k in keys]
        result = {}

        # Try Redis first
        if self.redis_client:
            try:
                values = self.redis_client.mget(full_keys)
                for key, full_key, value in zip(keys, full_keys, values):
                    if value:
                        result[key] = self._deserialize(value)
                        self.stats['redis_hits'] += 1
                    else:
                        self.stats['redis_misses'] += 1
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis mget error: {e}")

        # Fill missing from in-memory cache
        if self.config['enable_fallback']:
            for key in keys:
                if key not in result:
                    value = self.fallback_cache.get(self._get_key(key))
                    if value is not None:
                        result[key] = value
                        self.stats['memory_hits'] += 1
                    else:
                        self.stats['memory_misses'] += 1

        return result

    def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple keys at once"""
        ttl = ttl or self.config['default_ttl']
        ttl = min(ttl, self.config['max_ttl'])

        success = True

        # Try Redis first
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline()
                for key, value in mapping.items():
                    full_key = self._get_key(key)
                    serialized = self._serialize(value)
                    pipe.setex(full_key, ttl, serialized)
                pipe.execute()
                self.stats['redis_sets'] += len(mapping)
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis mset error: {e}")
                success = False

        # Also set in in-memory cache
        if self.config['enable_fallback']:
            for key, value in mapping.items():
                self.fallback_cache.set(self._get_key(key), value, ttl)
                self.stats['memory_sets'] += 1

        return success

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        full_key = self._get_key(key)

        # Try Redis first
        if self.redis_client:
            try:
                result = self.redis_client.incrby(full_key, amount)
                self.stats['redis_incr'] += 1
                return result
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis incr error: {e}")

        # Fallback to in-memory
        if self.config['enable_fallback']:
            current = self.fallback_cache.get(full_key) or 0
            new_value = current + amount
            self.fallback_cache.set(full_key, new_value)
            return new_value

        return None

    def flush(self, pattern: Optional[str] = None):
        """
        Clear cache
        If pattern provided, only clear matching keys
        """
        if pattern:
            pattern = self._get_key(pattern)

        # Flush Redis
        if self.redis_client:
            try:
                if pattern:
                    # Delete keys matching pattern
                    cursor = 0
                    while True:
                        cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                        if keys:
                            self.redis_client.delete(*keys)
                        if cursor == 0:
                            break
                else:
                    # Flush entire database
                    self.redis_client.flushdb()
                self.stats['redis_flushes'] += 1
            except Exception as e:
                self.stats['redis_errors'] += 1
                print(f"Redis flush error: {e}")

        # Flush in-memory cache
        if self.config['enable_fallback']:
            self.fallback_cache.flush()
            self.stats['memory_flushes'] += 1

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = dict(self.stats)

        # Add Redis info if connected
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats['redis_connected'] = True
                stats['redis_memory_used'] = info.get('used_memory_human', 'N/A')
                stats['redis_keys'] = self.redis_client.dbsize()
                stats['redis_uptime'] = info.get('uptime_in_seconds', 0)
            except:
                stats['redis_connected'] = False
        else:
            stats['redis_connected'] = False

        # Add in-memory stats
        stats['memory_cache'] = self.fallback_cache.get_stats()

        # Calculate hit rates
        total_hits = stats.get('redis_hits', 0) + stats.get('memory_hits', 0)
        total_misses = stats.get('redis_misses', 0) + stats.get('memory_misses', 0)
        total_requests = total_hits + total_misses

        if total_requests > 0:
            stats['overall_hit_rate'] = total_hits / total_requests
        else:
            stats['overall_hit_rate'] = 0

        return stats

    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup():
            while True:
                time.sleep(600)  # Run every 10 minutes

                # Check Redis connection health
                if self.redis_client:
                    try:
                        self.redis_client.ping()
                    except:
                        print("⚠️  Redis connection lost. Attempting reconnect...")
                        self._init_redis()

        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()


# Cache decorators
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results
    Usage:
    @cache_result(ttl=600, key_prefix="api")
    def expensive_function(param):
        return compute_something(param)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str((args, kwargs)).encode()).hexdigest()}"

            # Try to get from cache
            cache = get_redis_cache()
            result = cache.get(cache_key)

            if result is not None:
                return result

            # Compute result
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl)

            return result

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


# Singleton instance
_redis_cache = None

def get_redis_cache() -> RedisCache:
    """Get singleton instance of Redis cache"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache