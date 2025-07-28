"""Test the fixed market hours implementation with timezone awareness."""

from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter


class TestMarketHoursFixed:
    """Test the timezone-aware market hours implementation."""

    @pytest.fixture
    def service(self):
        """Create market service instance."""
        mock_polygon = Mock(spec=PolygonClient)
        cache = MarketDataCache(max_size=100)
        rate_limiter = RateLimiter(requests_per_minute=5)

        return MarketDataService(
            polygon_client=mock_polygon, cache=cache, rate_limiter=rate_limiter
        )

    @freeze_time("2025-07-29 14:30:00", tz_offset=0)  # UTC time = 10:30 AM ET
    def test_regular_hours_from_utc(self, service):
        """Test regular market hours when server is in UTC."""
        status = service._check_market_hours()
        assert status == "regular"

    @freeze_time("2025-07-29 13:00:00", tz_offset=0)  # UTC time = 9:00 AM ET
    def test_pre_market_from_utc(self, service):
        """Test pre-market hours when server is in UTC."""
        status = service._check_market_hours()
        assert status == "pre-market"

    @freeze_time("2025-07-29 20:30:00", tz_offset=0)  # UTC time = 4:30 PM ET
    def test_after_hours_from_utc(self, service):
        """Test after-hours when server is in UTC."""
        status = service._check_market_hours()
        assert status == "after-hours"

    @freeze_time("2025-08-02 14:30:00", tz_offset=0)  # Saturday in UTC
    def test_weekend_closed(self, service):
        """Test weekend market closed status."""
        status = service._check_market_hours()
        assert status == "closed"

    def test_edge_cases(self, service):
        """Test edge cases at market open and close."""
        # Test exactly at market open (9:30 AM ET)
        with freeze_time("2025-07-29 13:30:00", tz_offset=0):  # UTC
            assert service._check_market_hours() == "regular"

        # Test one minute before market open (9:29 AM ET)
        with freeze_time("2025-07-29 13:29:00", tz_offset=0):  # UTC
            assert service._check_market_hours() == "pre-market"

        # Test exactly at market close (4:00 PM ET)
        with freeze_time("2025-07-29 20:00:00", tz_offset=0):  # UTC
            assert service._check_market_hours() == "regular"

        # Test one minute after market close (4:01 PM ET)
        with freeze_time("2025-07-29 20:01:00", tz_offset=0):  # UTC
            assert service._check_market_hours() == "after-hours"

    def test_dst_handling(self, service):
        """Test that DST transitions are handled correctly."""
        # During EDT (summer) - UTC-4
        with freeze_time("2025-07-15 14:30:00", tz_offset=0):  # 10:30 AM EDT
            assert service._check_market_hours() == "regular"

        # During EST (winter) - UTC-5
        with freeze_time("2025-12-15 15:30:00", tz_offset=0):  # 10:30 AM EST
            assert service._check_market_hours() == "regular"

    @pytest.mark.parametrize(
        "utc_time,expected",
        [
            # Pre-market scenarios
            ("2025-07-29 12:00:00", "pre-market"),  # 8:00 AM ET
            ("2025-07-29 13:00:00", "pre-market"),  # 9:00 AM ET
            ("2025-07-29 13:29:59", "pre-market"),  # 9:29:59 AM ET
            # Regular hours scenarios
            ("2025-07-29 13:30:00", "regular"),  # 9:30 AM ET
            ("2025-07-29 14:00:00", "regular"),  # 10:00 AM ET
            ("2025-07-29 18:00:00", "regular"),  # 2:00 PM ET
            ("2025-07-29 20:00:00", "regular"),  # 4:00 PM ET
            # After-hours scenarios
            ("2025-07-29 20:00:01", "after-hours"),  # 4:00:01 PM ET
            ("2025-07-29 21:00:00", "after-hours"),  # 5:00 PM ET
            ("2025-07-29 23:00:00", "after-hours"),  # 7:00 PM ET
            # Weekend scenarios
            ("2025-08-02 14:30:00", "closed"),  # Saturday
            ("2025-08-03 14:30:00", "closed"),  # Sunday
        ],
    )
    def test_comprehensive_market_hours(self, service, utc_time, expected):
        """Test various times throughout the week."""
        with freeze_time(utc_time, tz_offset=0):
            assert service._check_market_hours() == expected
