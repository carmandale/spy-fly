import pytest
from unittest.mock import AsyncMock, patch
from datetime import date, datetime

from app.models.market import Quote, OptionChain, OptionContract, Bar
from app.core.exceptions import RateLimitError


class TestMarketEndpoints:
    @pytest.mark.asyncio
    async def test_get_quote_success(self, client):
        # Mock the market service
        mock_response = {
            "ticker": "SPY",
            "price": 567.89,
            "bid": 567.87,
            "ask": 567.91,
            "bid_size": 100,
            "ask_size": 150,
            "volume": 45678900,
            "timestamp": "2025-07-26T10:30:00",
            "market_status": "open",
            "change": 2.34,
            "change_percent": 0.41,
            "previous_close": 565.55,
            "cached": False
        }
        
        with patch("app.api.v1.endpoints.market.market_service") as mock_service:
            mock_service.get_spy_quote = AsyncMock(return_value=mock_response)
            
            response = client.get("/api/v1/market/quote/SPY")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "SPY"
            assert data["price"] == 567.89
            assert data["cached"] is False
    
    @pytest.mark.asyncio
    async def test_get_quote_invalid_ticker(self, client):
        response = client.get("/api/v1/market/quote/INVALID")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "SPY" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_quote_rate_limit(self, client):
        with patch("app.api.v1.endpoints.market.market_service") as mock_service:
            mock_service.get_spy_quote = AsyncMock(
                side_effect=RateLimitError("Rate limit exceeded", retry_after=45)
            )
            
            response = client.get("/api/v1/market/quote/SPY")
            
            assert response.status_code == 429
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert data["error"]["details"]["retry_after"] == 45
    
    @pytest.mark.asyncio
    async def test_get_options_success(self, client):
        mock_response = {
            "ticker": "SPY",
            "underlying_price": 567.89,
            "expiration": "2025-07-26",
            "options": [
                {
                    "symbol": "SPY250726C00565000",
                    "type": "call",
                    "strike": 565.0,
                    "expiration": "2025-07-26",
                    "bid": 3.25,
                    "ask": 3.30,
                    "mid": 3.275,
                    "volume": 12500,
                    "open_interest": 45000
                }
            ],
            "cached": False,
            "cache_expires_at": "2025-07-26T10:35:00"
        }
        
        with patch("app.api.v1.endpoints.market.market_service") as mock_service:
            mock_service.get_spy_options = AsyncMock(return_value=mock_response)
            
            response = client.get("/api/v1/market/options/SPY?expiration=2025-07-26")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "SPY"
            assert len(data["options"]) == 1
            assert data["options"][0]["strike"] == 565.0
    
    @pytest.mark.asyncio
    async def test_get_options_invalid_date(self, client):
        response = client.get("/api/v1/market/options/SPY?expiration=invalid-date")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "date format" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_options_with_filters(self, client):
        response = client.get(
            "/api/v1/market/options/SPY?expiration=2025-07-26&option_type=call&strike_range=10"
        )
        
        # Should succeed with valid parameters
        assert response.status_code in [200, 429]  # 429 if rate limited
    
    @pytest.mark.asyncio
    async def test_get_historical_success(self, client):
        mock_response = {
            "ticker": "SPY",
            "from_date": "2025-07-20",
            "to_date": "2025-07-26",
            "timeframe": "day",
            "bars": [
                {
                    "timestamp": "2025-07-20T09:30:00",
                    "open": 565.0,
                    "high": 568.0,
                    "low": 564.5,
                    "close": 567.0,
                    "volume": 50000000,
                    "vwap": 566.5
                }
            ],
            "result_count": 1,
            "cached": False
        }
        
        with patch("app.api.v1.endpoints.market.market_service") as mock_service:
            mock_service.get_historical_data = AsyncMock(return_value=mock_response)
            
            response = client.get("/api/v1/market/historical/SPY?from=2025-07-20&to=2025-07-26")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == "SPY"
            assert len(data["bars"]) == 1
            assert data["result_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_historical_invalid_dates(self, client):
        response = client.get("/api/v1/market/historical/SPY?from=2025-07-26&to=2025-07-20")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "before" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_market_status(self, client):
        response = client.get("/api/v1/market/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "market_status" in data
        assert "api_status" in data
        assert "rate_limit_remaining" in data
        assert "cache_stats" in data
    
    @pytest.mark.asyncio
    async def test_cache_headers(self, client):
        with patch("app.api.v1.endpoints.market.market_service") as mock_service:
            mock_response = {
                "ticker": "SPY",
                "price": 567.89,
                "volume": 45678900,
                "timestamp": "2025-07-26T10:30:00",
                "market_status": "open",
                "cached": True
            }
            mock_service.get_spy_quote = AsyncMock(return_value=mock_response)
            
            response = client.get("/api/v1/market/quote/SPY")
            
            # Check cache headers
            assert "Cache-Control" in response.headers
            assert "X-Cached" in response.headers
            assert response.headers["X-Cached"] == "true"