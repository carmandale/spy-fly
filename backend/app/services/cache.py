"""In-memory cache for market data."""
import time
from typing import Any, Optional, Dict
import hashlib
import json
import threading


class MarketDataCache:
    """Thread-safe in-memory cache for market data."""
    
    def __init__(self, max_size: int = 1000):
        # Store items with their expiration times
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                # Check if expired
                if time.time() < expire_time:
                    self._hits += 1
                    return value
                else:
                    # Remove expired item
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set value in cache with specific TTL."""
        with self._lock:
            # Clean up if we're at max size
            if len(self._cache) >= self._max_size:
                self._cleanup_expired()
                # If still at max, remove oldest
                if len(self._cache) >= self._max_size:
                    oldest_key = min(self._cache.keys(), 
                                   key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
            
            # Store value with expiration time
            expire_time = time.time() + ttl
            self._cache[key] = (value, expire_time)
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            k for k, (_, expire_time) in self._cache.items()
            if expire_time <= current_time
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            self._cleanup_expired()
            return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
                "max_size": self._max_size,
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