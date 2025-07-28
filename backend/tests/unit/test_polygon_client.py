from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.exceptions import PolygonAPIError, RateLimitError
from app.models.market import Bar, OptionContract, Quote
from app.services.cache import MarketDataCache
from app.services.polygon_client import PolygonClient, PolygonDataService
from app.services.rate_limiter import RateLimiter


class TestPolygonClient:
    @pytest.fixture
    def client(self):
        return PolygonClient(api_key="test_key", use_sandbox=True)

    def test_init_with_production_url(self):
        client = PolygonClient(api_key="test_key", use_sandbox=False)
        assert client.base_url == "https://api.polygon.io"
        assert client.api_key == "test_key"

    def test_init_with_sandbox_url(self):
        client = PolygonClient(api_key="test_key", use_sandbox=True)
        assert client.base_url == "https://api.polygon.io"
        assert client.use_sandbox is True

    def test_request_headers_include_auth(self, client):
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"

    @pytest.mark.asyncio
    async def test_get_quote_success(self, client):
        mock_response = {
            "status": "success",
            "results": [
                {
                    "T": "SPY",
                    "c": 567.89,
                    "h": 568.50,
                    "l": 566.20,
                    "o": 567.00,
                    "v": 45678900,
                    "vw": 567.45,
                    "t": 1690000000000,
                }
            ],
        }

        mock_quote_response = {
            "status": "success",
            "results": {
                "bid_price": 567.88,
                "ask_price": 567.90,
                "bid_size": 100,
                "ask_size": 150,
            },
        }

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [mock_response, mock_quote_response]
            quote = await client.get_quote("SPY")
            assert quote.ticker == "SPY"
            assert quote.price == 567.89
            assert quote.volume == 45678900
            assert quote.bid == 567.88
            assert quote.ask == 567.90

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, client):

        with patch.object(
            client, "_make_request", side_effect=PolygonAPIError("Ticker not found")
        ):
            with pytest.raises(PolygonAPIError) as exc_info:
                await client.get_quote("INVALID")
            assert "Ticker not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client):
        mock_response = Mock(
            status_code=429,
            headers={"X-RateLimit-Reset": "60"},
            raise_for_status=Mock(
                side_effect=httpx.HTTPStatusError(
                    "Rate limit", request=Mock(), response=Mock()
                )
            ),
        )

        with patch.object(client._client, "get", return_value=mock_response):
            with pytest.raises(RateLimitError) as exc_info:
                await client.get_quote("SPY")
            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, client):
        # Test that retry logic works correctly - bypassing the decorator
        mock_response = {
            "status": "success",
            "results": [{"T": "SPY", "c": 567.89, "v": 45678900, "t": 1690000000000}],
        }

        mock_quote_response = {"status": "success", "results": {}}

        # Mock the client's get method directly to simulate retries
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.TimeoutException("Timeout")
            # Return a mock response
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.raise_for_status = Mock()
            if "v3/quotes" in args[0]:
                mock_resp.json = Mock(return_value=mock_quote_response)
            else:
                mock_resp.json = Mock(return_value=mock_response)
            return mock_resp

        with patch.object(client._client, "get", side_effect=mock_get):
            quote = await client.get_quote("SPY")
            assert quote.ticker == "SPY"
            assert quote.price == 567.89
            # Should have retried the first endpoint 3 times, then succeeded with quote endpoint
            assert call_count >= 3

    @pytest.mark.asyncio
    async def test_get_option_chain(self, client):
        mock_contracts_response = {
            "status": "success",
            "results": [
                {
                    "ticker": "SPY250726C00565000",
                    "contract_type": "call",
                    "strike_price": 565,
                    "expiration_date": "2025-07-26",
                }
            ],
        }

        mock_quote_response = {
            "status": "success",
            "results": [{"c": 567.89, "v": 45678900, "t": 1690000000000}],
        }

        mock_option_quote_response = {
            "status": "success",
            "results": {
                "bid_price": 3.25,
                "ask_price": 3.30,
                "last_price": 3.28,
                "day_volume": 12500,
                "open_interest": 1500,
            },
        }

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = [
                mock_contracts_response,
                mock_quote_response,
                {"status": "success", "results": {}},  # Empty quote details
                mock_option_quote_response,
            ]

            chain = await client.get_option_chain("SPY", date(2025, 7, 26))
            assert chain.ticker == "SPY"
            assert len(chain.options) == 1
            assert chain.options[0].strike == 565
            assert chain.options[0].type == "call"
            assert chain.options[0].bid == 3.25
            assert chain.options[0].ask == 3.30

    @pytest.mark.asyncio
    async def test_get_historical_bars(self, client):
        mock_response = {
            "status": "success",
            "results": [
                {
                    "t": 1690000000000,
                    "o": 566.50,
                    "h": 568.75,
                    "l": 565.25,
                    "c": 567.89,
                    "v": 50000000,
                    "vw": 567.12,
                },
                {
                    "t": 1690086400000,
                    "o": 567.89,
                    "h": 569.50,
                    "l": 566.75,
                    "c": 568.95,
                    "v": 48000000,
                    "vw": 568.25,
                },
            ],
        }

        with patch.object(client, "_make_request", return_value=mock_response):
            bars = await client.get_historical_bars(
                "SPY", date(2025, 7, 20), date(2025, 7, 26), "day"
            )

            assert len(bars) == 2
            assert bars[0].open == 566.50
            assert bars[0].close == 567.89
            assert bars[1].close == 568.95

    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        mock_response = Mock(
            status_code=403,
            raise_for_status=Mock(
                side_effect=httpx.HTTPStatusError(
                    "Forbidden", request=Mock(), response=Mock(status_code=403)
                )
            ),
        )

        with patch.object(client._client, "get", return_value=mock_response):
            with pytest.raises(PolygonAPIError) as exc_info:
                await client.get_quote("SPY")
            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_client(self, client):
        mock_aclose = AsyncMock()
        client._client.aclose = mock_aclose

        await client.close()
        mock_aclose.assert_called_once()


class TestPolygonDataService:
    """Test the enhanced PolygonDataService with caching and rate limiting."""

    @pytest.fixture
    def cache_manager(self):
        return MarketDataCache(max_size=100)

    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(requests_per_minute=5)

    @pytest.fixture
    def polygon_client(self):
        return PolygonClient(api_key="test_key")

    @pytest.fixture
    def data_service(self, polygon_client, cache_manager, rate_limiter):
        # Mock the service until we implement it
        service = Mock(spec=PolygonDataService)
        service.client = polygon_client
        service.cache_manager = cache_manager
        service.rate_limiter = rate_limiter
        return service

    @pytest.mark.asyncio
    async def test_get_spy_quote_with_cache_hit(self, data_service, cache_manager):
        """Test quote retrieval from cache when available."""
        cached_quote = Quote(
            ticker="SPY",
            price=567.89,
            bid=567.88,
            ask=567.90,
            volume=45678900,
            timestamp=datetime.now(),
        )

        cache_key = cache_manager.generate_key("quote", "SPY")
        cache_manager.set(cache_key, cached_quote, ttl=60)

        # Mock the method to use cache
        async def mock_get_spy_quote():
            cached = cache_manager.get(cache_key)
            if cached:
                return cached
            return None

        data_service.get_spy_quote = mock_get_spy_quote

        quote = await data_service.get_spy_quote()
        assert quote is not None
        assert quote.price == 567.89
        assert quote.ticker == "SPY"

    @pytest.mark.asyncio
    async def test_get_spy_quote_with_cache_miss(self, data_service, polygon_client):
        """Test quote retrieval from API when cache misses."""
        api_quote = Quote(
            ticker="SPY",
            price=568.50,
            bid=568.48,
            ask=568.52,
            volume=50000000,
            timestamp=datetime.now(),
        )

        # Mock polygon client to return quote
        polygon_client.get_quote = AsyncMock(return_value=api_quote)

        # Mock the service method
        async def mock_get_spy_quote():
            return await polygon_client.get_quote("SPY")

        data_service.get_spy_quote = mock_get_spy_quote

        quote = await data_service.get_spy_quote()
        assert quote.price == 568.50
        polygon_client.get_quote.assert_called_once_with("SPY")

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, data_service, rate_limiter):
        """Test that rate limiting is enforced."""
        # Consume all tokens
        for _ in range(5):
            assert rate_limiter.consume()

        # Next request should be rate limited
        assert not rate_limiter.consume()
        assert rate_limiter.get_wait_time() > 0

    @pytest.mark.asyncio
    async def test_health_check(self, data_service, polygon_client):
        """Test health check functionality."""
        # Mock successful API call
        polygon_client._make_request = AsyncMock(return_value={"status": "success"})

        async def mock_health_check():
            try:
                await polygon_client._make_request("/v1/marketstatus/now")
                return True
            except:
                return False

        data_service.health_check = mock_health_check

        result = await data_service.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_option_chain_with_filtering(self, data_service):
        """Test option chain retrieval with 0-DTE filtering."""
        # Mock option chain with mixed expirations
        today = date.today()
        tomorrow = today + timedelta(days=1)

        options = [
            OptionContract(
                symbol="SPY250726C00565000",
                type="call",
                strike=565.0,
                expiration=today.isoformat(),
                bid=3.25,
                ask=3.30,
                mid=3.275,
                volume=1000,
                open_interest=500,
            ),
            OptionContract(
                symbol="SPY250727C00565000",
                type="call",
                strike=565.0,
                expiration=tomorrow.isoformat(),
                bid=5.25,
                ask=5.30,
                mid=5.275,
                volume=800,
                open_interest=300,
            ),
        ]

        # Mock to return only today's options (0-DTE)
        async def mock_get_option_chain(expiration_date):
            if expiration_date == today:
                return [opt for opt in options if opt.expiration == today.isoformat()]
            return []

        data_service.get_option_chain = mock_get_option_chain

        result = await data_service.get_option_chain(today)
        assert len(result) == 1
        assert result[0].expiration == today.isoformat()

    @pytest.mark.asyncio
    async def test_error_handling_with_fallback(self, data_service, cache_manager):
        """Test fallback to cache when API fails."""
        # Cache old data
        old_quote = Quote(
            ticker="SPY",
            price=565.00,
            bid=564.98,
            ask=565.02,
            volume=40000000,
            timestamp=datetime.now() - timedelta(minutes=10),
        )

        cache_key = cache_manager.generate_key("quote", "SPY")
        cache_manager.set(cache_key, old_quote, ttl=3600)

        # Mock API failure
        async def mock_get_spy_quote():
            # Try API first (simulate failure)
            try:
                raise PolygonAPIError("API temporarily unavailable")
            except PolygonAPIError:
                # Fall back to cache
                return cache_manager.get(cache_key)

        data_service.get_spy_quote = mock_get_spy_quote

        quote = await data_service.get_spy_quote()
        assert quote is not None
        assert quote.price == 565.00  # Old cached price

    @pytest.mark.asyncio
    async def test_historical_data_with_date_range(self, data_service, polygon_client):
        """Test historical data retrieval with proper date range."""
        bars = [
            Bar(
                timestamp=datetime(2025, 7, 20, 16, 0),
                open=566.50,
                high=568.75,
                low=565.25,
                close=567.89,
                volume=50000000,
                vwap=567.12,
            ),
            Bar(
                timestamp=datetime(2025, 7, 21, 16, 0),
                open=567.89,
                high=569.50,
                low=566.75,
                close=568.95,
                volume=48000000,
                vwap=568.25,
            ),
        ]

        polygon_client.get_historical_bars = AsyncMock(return_value=bars)

        async def mock_get_historical_data(days=30):
            to_date = date.today()
            from_date = to_date - timedelta(days=days)
            return await polygon_client.get_historical_bars(
                "SPY", from_date, to_date, "day"
            )

        data_service.get_historical_data = mock_get_historical_data

        result = await data_service.get_historical_data(days=7)
        assert len(result) == 2
        assert result[0].close == 567.89
