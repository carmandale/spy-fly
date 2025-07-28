"""Test market hours timezone handling."""
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import sys

from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter


class TestMarketHoursTimezone:
    """Test market hours detection with proper timezone handling."""
    
    @pytest.fixture
    def service(self):
        """Create market service instance."""
        mock_polygon = Mock(spec=PolygonClient)
        cache = MarketDataCache(max_size=100)
        rate_limiter = RateLimiter(requests_per_minute=5)
        
        return MarketDataService(
            polygon_client=mock_polygon,
            cache=cache,
            rate_limiter=rate_limiter
        )
    
    def test_market_hours_during_regular_trading_et(self, service):
        """Test market hours during regular trading (9:30 AM - 4:00 PM ET)."""
        # Test at 10:00 AM ET on a Tuesday
        et_time = datetime(2025, 7, 29, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = et_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            status = service._check_market_hours()
            assert status == "regular"
    
    def test_market_hours_pre_market_et(self, service):
        """Test pre-market hours (before 9:30 AM ET)."""
        # Test at 8:00 AM ET on a Wednesday
        et_time = datetime(2025, 7, 30, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = et_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            status = service._check_market_hours()
            assert status == "pre-market"
    
    def test_market_hours_after_hours_et(self, service):
        """Test after-hours (after 4:00 PM ET)."""
        # Test at 5:00 PM ET on a Thursday
        et_time = datetime(2025, 7, 31, 17, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = et_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            status = service._check_market_hours()
            assert status == "after-hours"
    
    def test_market_hours_weekend(self, service):
        """Test weekend hours."""
        # Test on Saturday at 10:00 AM ET
        et_time = datetime(2025, 8, 2, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = et_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            status = service._check_market_hours()
            assert status == "closed"
    
    def test_market_hours_from_different_timezones(self, service):
        """Test market hours detection from different server timezones."""
        test_cases = [
            # Server in UTC during regular trading hours
            {
                "server_time": datetime(2025, 7, 29, 14, 30, 0, tzinfo=timezone.utc),  # 10:30 AM ET
                "expected": "regular"
            },
            # Server in PST during pre-market
            {
                "server_time": datetime(2025, 7, 29, 6, 0, 0, tzinfo=ZoneInfo("America/Los_Angeles")),  # 9:00 AM ET
                "expected": "pre-market"
            },
            # Server in CST during after-hours
            {
                "server_time": datetime(2025, 7, 29, 16, 30, 0, tzinfo=ZoneInfo("America/Chicago")),  # 5:30 PM ET
                "expected": "after-hours"
            },
            # Server in Europe during US market hours
            {
                "server_time": datetime(2025, 7, 29, 16, 0, 0, tzinfo=ZoneInfo("Europe/London")),  # 11:00 AM ET
                "expected": "regular"
            }
        ]
        
        for case in test_cases:
            with patch('app.services.market_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = case["server_time"]
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                
                status = service._check_market_hours()
                assert status == case["expected"], f"Failed for server time {case['server_time']}"
    
    def test_market_hours_edge_cases(self, service):
        """Test edge cases at market open and close."""
        edge_cases = [
            # Exactly at market open
            {
                "time": datetime(2025, 7, 29, 9, 30, 0, tzinfo=ZoneInfo("America/New_York")),
                "expected": "regular"
            },
            # One second before market open
            {
                "time": datetime(2025, 7, 29, 9, 29, 59, tzinfo=ZoneInfo("America/New_York")),
                "expected": "pre-market"
            },
            # Exactly at market close
            {
                "time": datetime(2025, 7, 29, 16, 0, 0, tzinfo=ZoneInfo("America/New_York")),
                "expected": "regular"
            },
            # One second after market close
            {
                "time": datetime(2025, 7, 29, 16, 0, 1, tzinfo=ZoneInfo("America/New_York")),
                "expected": "after-hours"
            }
        ]
        
        for case in edge_cases:
            with patch('app.services.market_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = case["time"]
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                
                status = service._check_market_hours()
                assert status == case["expected"], f"Failed for time {case['time']}"
    
    def test_market_hours_dst_transitions(self, service):
        """Test market hours during daylight saving time transitions."""
        # During EDT (Eastern Daylight Time) - summer
        edt_time = datetime(2025, 7, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        # During EST (Eastern Standard Time) - winter  
        est_time = datetime(2025, 12, 15, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            # Test EDT
            mock_datetime.now.return_value = edt_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            status = service._check_market_hours()
            assert status == "regular"
            
            # Test EST
            mock_datetime.now.return_value = est_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            status = service._check_market_hours()
            assert status == "regular"
    
    def test_market_hours_holidays(self, service):
        """Test that holidays are not handled by this method (should be handled elsewhere)."""
        # Christmas Day 2025 (Thursday) - market closed but method doesn't know about holidays
        christmas = datetime(2025, 12, 25, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        
        with patch('app.services.market_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = christmas
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            
            # Method should return "regular" since it's a weekday during market hours
            # Holiday handling would be a separate concern
            status = service._check_market_hours()
            assert status == "regular"