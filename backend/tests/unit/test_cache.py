import pytest
import time
from unittest.mock import patch

from app.services.cache import MarketDataCache


class TestMarketDataCache:
    @pytest.fixture
    def cache(self):
        return MarketDataCache(max_size=10)
    
    def test_set_and_get(self, cache):
        cache.set("test_key", {"data": "value"}, ttl=60)
        result = cache.get("test_key")
        assert result == {"data": "value"}
    
    def test_get_nonexistent_key(self, cache):
        result = cache.get("nonexistent")
        assert result is None
    
    def test_ttl_expiration(self, cache):
        cache.set("test_key", {"data": "value"}, ttl=1)
        time.sleep(1.1)
        result = cache.get("test_key")
        assert result is None
    
    def test_max_size_limit(self, cache):
        # Fill cache to max size
        for i in range(10):
            cache.set(f"key_{i}", {"data": i}, ttl=60)
        
        # Verify all items are in cache
        assert cache.size() == 10
        
        # Add one more item
        cache.set("key_10", {"data": 10}, ttl=60)
        
        # Should still be at max size
        assert cache.size() == 10
        
        # Oldest item should be evicted
        assert cache.get("key_0") is None
        assert cache.get("key_10") is not None
    
    def test_clear_cache(self, cache):
        cache.set("key1", {"data": 1}, ttl=60)
        cache.set("key2", {"data": 2}, ttl=60)
        
        assert cache.size() == 2
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
    
    def test_cache_stats(self, cache):
        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        
        # Add item and hit
        cache.set("key1", {"data": 1}, ttl=60)
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["max_size"] == 10
    
    def test_thread_safety(self, cache):
        import threading
        
        def add_items(start, end):
            for i in range(start, end):
                cache.set(f"key_{i}", {"data": i}, ttl=60)
        
        threads = []
        for i in range(4):
            t = threading.Thread(target=add_items, args=(i*25, (i+1)*25))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have added items safely
        assert cache.size() <= 10  # Max size respected
    
    def test_generate_cache_key(self, cache):
        key1 = cache.generate_key("quote", "SPY")
        key2 = cache.generate_key("quote", "SPY", expiration="2025-07-26")
        key3 = cache.generate_key("quote", "SPY")
        
        assert key1 == key3  # Same params = same key
        assert key1 != key2  # Different params = different key