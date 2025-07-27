import pytest
import time
from unittest.mock import patch

from app.services.rate_limiter import RateLimiter


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        # 5 requests per minute (0.0833 per second)
        return RateLimiter(requests_per_minute=5)
    
    def test_allow_initial_requests(self, limiter):
        # Should allow first 5 requests
        for i in range(5):
            assert limiter.check() is True
            limiter.consume()
    
    def test_block_when_limit_exceeded(self, limiter):
        # Consume all tokens
        for i in range(5):
            limiter.check()
            limiter.consume()
        
        # Next request should be blocked
        assert limiter.check() is False
    
    def test_tokens_replenish_over_time(self, limiter):
        # Consume all tokens
        for i in range(5):
            limiter.consume()
        
        # Should be blocked
        assert limiter.check() is False
        
        # Wait for tokens to replenish (12 seconds for 1 token at 5/min rate)
        time.sleep(12.1)
        
        # Should have 1 token available
        assert limiter.check() is True
    
    def test_get_wait_time(self, limiter):
        # Consume all tokens
        for i in range(5):
            limiter.consume()
        
        # Get wait time for next token
        wait_time = limiter.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 12  # Should be ~12 seconds for 5/min rate
    
    def test_remaining_requests(self, limiter):
        assert limiter.get_remaining() == 5
        
        limiter.consume()
        assert limiter.get_remaining() == 4
        
        for i in range(4):
            limiter.consume()
        
        assert limiter.get_remaining() == 0
    
    def test_reset_time(self, limiter):
        # Consume a token
        limiter.consume()
        
        reset_time = limiter.get_reset_time()
        current_time = time.time()
        
        # Reset time should be in the future
        assert reset_time > current_time
        # But not more than 60 seconds away
        assert reset_time - current_time <= 60
    
    def test_thread_safety(self, limiter):
        import threading
        
        consumed = []
        
        def try_consume():
            if limiter.check():
                limiter.consume()
                consumed.append(1)
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=try_consume)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should only allow 5 requests
        assert len(consumed) == 5
        assert limiter.get_remaining() == 0