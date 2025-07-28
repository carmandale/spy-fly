import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import date, datetime

from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter
from app.models.market import Quote, OptionChain, OptionContract
from app.core.exceptions import RateLimitError


class TestMarketDataService:
    @pytest.fixture
    def mock_polygon_client(self):
        client = Mock(spec=PolygonClient)
        client.get_quote = AsyncMock()
        client.get_option_chain = AsyncMock()
        client.get_historical_bars = AsyncMock()
        return client
    
    @pytest.fixture
    def cache(self):
        return MarketDataCache(max_size=100)
    
    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(requests_per_minute=5)
    
    @pytest.fixture
    def service(self, mock_polygon_client, cache, rate_limiter):
        return MarketDataService(
            polygon_client=mock_polygon_client,
            cache=cache,
            rate_limiter=rate_limiter
        )
    
    @pytest.mark.asyncio
    async def test_get_spy_quote_from_api(self, service, mock_polygon_client):
        # Mock API response
        mock_quote = Quote(
            ticker="SPY",
            price=567.89,
            bid=567.87,
            ask=567.91,
            volume=45000000,
            timestamp=datetime.now()
        )
        mock_polygon_client.get_quote.return_value = mock_quote
        
        # First call should hit API
        result = await service.get_spy_quote()
        
        assert result.ticker == "SPY"
        assert result.price == 567.89
        assert result.cached is False
        mock_polygon_client.get_quote.assert_called_once_with("SPY")
    
    @pytest.mark.asyncio
    async def test_get_spy_quote_from_cache(self, service, mock_polygon_client):
        # Mock API response
        mock_quote = Quote(
            ticker="SPY",
            price=567.89,
            bid=567.87,
            ask=567.91,
            volume=45000000,
            timestamp=datetime.now()
        )
        mock_polygon_client.get_quote.return_value = mock_quote
        
        # First call hits API
        await service.get_spy_quote()
        
        # Second call should hit cache
        result = await service.get_spy_quote()
        
        assert result.cached is True
        # API should only be called once
        assert mock_polygon_client.get_quote.call_count == 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, service, mock_polygon_client):
        # Consume all rate limit tokens
        for _ in range(5):
            service.rate_limiter.consume()
        
        # Set up cache with data
        cache_key = service.cache.generate_key("quote", "SPY")
        cached_quote = {
            "ticker": "SPY",
            "price": 566.00,
            "volume": 40000000,
            "timestamp": datetime.now().isoformat(),
            "market_status": "regular",
            "change": 1.23,
            "change_percent": 0.22,
            "previous_close": 564.77,
            "bid": 565.98,
            "ask": 566.02,
            "bid_size": 100,
            "ask_size": 200
        }
        service.cache.set(cache_key, cached_quote, ttl=60)
        
        # Should return cached data when rate limited
        result = await service.get_spy_quote()
        
        assert result.cached is True
        assert result.price == 566.00
        # API should not be called
        mock_polygon_client.get_quote.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_spy_options(self, service, mock_polygon_client):
        # Mock option chain
        mock_chain = OptionChain(
            ticker="SPY",
            expiration="2025-07-26",
            underlying_price=567.89,
            options=[
                OptionContract(
                    symbol="SPY250726C00565000",
                    type="call",
                    strike=565.0,
                    expiration="2025-07-26",
                    bid=3.25,
                    ask=3.30,
                    mid=3.275,
                    volume=12500,
                    open_interest=45000
                )
            ]
        )
        mock_polygon_client.get_option_chain.return_value = mock_chain
        
        expiration = date(2025, 7, 26)
        result = await service.get_spy_options(expiration)
        
        assert result.ticker == "SPY"
        assert len(result.options) == 1
        assert result.options[0].strike == 565.0
        assert result.cached is False
    
    @pytest.mark.asyncio
    async def test_option_filtering(self, service, mock_polygon_client):
        # Mock option chain with multiple strikes
        options = []
        for strike in [560, 565, 570, 575, 580]:
            for opt_type in ["call", "put"]:
                options.append(
                    OptionContract(
                        symbol=f"SPY250726{opt_type[0].upper()}00{strike}000",
                        type=opt_type,
                        strike=float(strike),
                        expiration="2025-07-26",
                        bid=1.0,
                        ask=1.1,
                        mid=1.05,
                        volume=1000,
                        open_interest=5000
                    )
                )
        
        mock_chain = OptionChain(
            ticker="SPY",
            expiration="2025-07-26",
            underlying_price=570.0,
            options=options
        )
        mock_polygon_client.get_option_chain.return_value = mock_chain
        
        # Filter for calls only with strike range of 5
        # With underlying at 570, range of 5 means strikes 565-575 (3 strikes)
        result = await service.get_spy_options(
            expiration=date(2025, 7, 26),
            option_type="call",
            strike_range=5
        )
        
        # Should only have calls
        assert all(opt.type == "call" for opt in result.options)
        # With underlying at 570 and range of 5, we get strikes: 565, 570, 575
        assert len(result.options) == 3
        
        # Test with larger strike range to get all 5 calls
        result_all = await service.get_spy_options(
            expiration=date(2025, 7, 26),
            option_type="call",
            strike_range=10
        )
        assert len(result_all.options) == 5
    
    @pytest.mark.asyncio
    async def test_historical_data_caching(self, service, mock_polygon_client):
        # Mock historical bars
        from app.models.market import Bar
        
        mock_bars = [
            Bar(
                timestamp=datetime(2025, 7, 25, 9, 30),
                open=565.0,
                high=568.0,
                low=564.5,
                close=567.0,
                volume=50000000
            )
        ]
        mock_polygon_client.get_historical_bars.return_value = mock_bars
        
        # First call
        result1 = await service.get_historical_data(days=1)
        assert result1.cached is False
        
        # Second call should be cached
        result2 = await service.get_historical_data(days=1)
        assert result2.cached is True
        
        # API should only be called once
        assert mock_polygon_client.get_historical_bars.call_count == 1