import pytest
from unittest.mock import Mock, patch
from datetime import date
import httpx

from app.services.polygon_client import PolygonClient
from app.core.exceptions import PolygonAPIError, RateLimitError


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
            "results": {
                "T": "SPY",
                "c": 567.89,
                "h": 568.50,
                "l": 566.20,
                "o": 567.00,
                "v": 45678900,
                "vw": 567.45,
                "t": 1690000000000
            }
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            quote = await client.get_quote("SPY")
            assert quote.ticker == "SPY"
            assert quote.price == 567.89
            assert quote.volume == 45678900
    
    @pytest.mark.asyncio
    async def test_get_quote_not_found(self, client):
        mock_response = {
            "status": "error",
            "message": "Ticker not found"
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            with pytest.raises(PolygonAPIError) as exc_info:
                await client.get_quote("INVALID")
            assert "Ticker not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client):
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Rate limit exceeded",
                request=Mock(),
                response=Mock(status_code=429, headers={"X-RateLimit-Reset": "1690000060"})
            )
            
            with pytest.raises(RateLimitError) as exc_info:
                await client.get_quote("SPY")
            assert exc_info.value.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, client):
        # First two calls fail, third succeeds
        mock_response = {
            "status": "success",
            "results": {"T": "SPY", "c": 567.89}
        }
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            
            quote = await client.get_quote("SPY")
            assert quote.ticker == "SPY"
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_option_chain(self, client):
        mock_response = {
            "status": "success",
            "results": [
                {
                    "details": {
                        "contract_type": "call",
                        "expiration_date": "2025-07-26",
                        "strike_price": 565
                    },
                    "day": {
                        "close": 3.28,
                        "volume": 12500
                    },
                    "last_quote": {
                        "ask": 3.30,
                        "bid": 3.25
                    }
                }
            ]
        }
        
        with patch.object(client, '_make_request', return_value=mock_response):
            options = await client.get_option_chain("SPY", date(2025, 7, 26))
            assert len(options.options) == 1
            assert options.options[0].strike == 565
            assert options.options[0].type == "call"