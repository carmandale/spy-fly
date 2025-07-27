"""In-memory cache for market data."""
import time
from typing import Any, Optional, Dict
from cachetools import TTLCache
import hashlib
import json
import threading


class MarketDataCache:
    """Thread-safe in-memory cache for market data."""
    
    def __init__(self, max_size: int = 1000):
        self._cache = TTLCache(maxsize=max_size, ttl=3600)  # Default 1 hour TTL
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            value = self._cache.get(key)
            if value is not None:
                self._hits += 1
            else:
                self._misses += 1
            return value
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with specific TTL."""
        with self._lock:
            # Create a new cache item with specific TTL
            self._cache[key] = value
            # Store expiration time
            expire_time = time.time() + ttl
            self._cache.expire(key, expire_time)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "max_size": self._cache.maxsize,
                "hit_rate": round(hit_rate, 3)
            }
    
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        # Create a string representation of all parameters
        parts = [prefix]
        parts.extend(str(arg) for arg in args)
        parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(parts)
        
        # For long keys, use hash
        if len(key_string) > 250:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key_string