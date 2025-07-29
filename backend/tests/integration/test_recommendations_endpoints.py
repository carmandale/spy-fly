"""
Integration tests for spread recommendations API endpoints.

These tests verify the REST API endpoint for retrieving formatted
spread recommendations with proper parameter validation and response formatting.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import MarketDataError, RateLimitError
from app.models.spread import SpreadRecommendation


class TestRecommendationsEndpoints:
    """Test the /api/recommendations/spreads endpoint."""

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_success(self, client):
        """Test successful retrieval of spread recommendations."""
        # Mock spread recommendation data
        mock_recommendations = [
            SpreadRecommendation(
                long_strike=470.0,
                short_strike=472.0,
                long_premium=6.05,
                short_premium=4.25,
                net_debit=1.80,
                max_risk=1.80,
                max_profit=0.20,
                risk_reward_ratio=0.11,
                probability_of_profit=0.65,
                breakeven_price=471.80,
                long_bid=6.00,
                long_ask=6.10,
                short_bid=4.20,
                short_ask=4.30,
                long_volume=1500,
                short_volume=1200,
                expected_value=0.05,
                sentiment_score=0.6,
                ranking_score=0.78,
                timestamp=datetime.now(),
                contracts_to_trade=2,
                total_cost=360.0,
                buying_power_used_pct=0.036,
            ),
            SpreadRecommendation(
                long_strike=472.0,
                short_strike=474.0,
                long_premium=4.25,
                short_premium=2.65,
                net_debit=1.60,
                max_risk=1.60,
                max_profit=0.40,
                risk_reward_ratio=0.25,
                probability_of_profit=0.58,
                breakeven_price=473.60,
                long_bid=4.20,
                long_ask=4.30,
                short_bid=2.60,
                short_ask=2.70,
                long_volume=1800,
                short_volume=2200,
                expected_value=0.07,
                sentiment_score=0.6,
                ranking_score=0.72,
                timestamp=datetime.now(),
                contracts_to_trade=3,
                total_cost=480.0,
                buying_power_used_pct=0.048,
            ),
        ]

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000.0,
                    "max_recommendations": 5,
                    "format": "json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "recommendations" in data
            assert "summary" in data
            assert "metadata" in data
            
            # Verify recommendations content
            recommendations = data["recommendations"]
            assert len(recommendations) == 2
            
            # Check first recommendation
            rec1 = recommendations[0]
            assert rec1["strikes"]["long"] == 470.0
            assert rec1["strikes"]["short"] == 472.0
            assert rec1["metrics"]["net_debit"] == 1.80
            assert rec1["probability"]["profit"] == 0.65
            assert "order_ticket" in rec1
            
            # Verify summary
            summary = data["summary"]
            assert summary["total_recommendations"] == 2
            assert summary["avg_probability"] > 0
            assert summary["avg_expected_value"] > 0
            
            # Verify metadata
            metadata = data["metadata"]
            assert metadata["account_size"] == 10000.0
            assert metadata["max_recommendations"] == 5
            assert "generated_at" in metadata

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_text_format(self, client):
        """Test retrieving recommendations in text format."""
        mock_recommendations = [
            SpreadRecommendation(
                long_strike=470.0,
                short_strike=472.0,
                long_premium=6.05,
                short_premium=4.25,
                net_debit=1.80,
                max_risk=1.80,
                max_profit=0.20,
                risk_reward_ratio=0.11,
                probability_of_profit=0.65,
                breakeven_price=471.80,
                long_bid=6.00,
                long_ask=6.10,
                short_bid=4.20,
                short_ask=4.30,
                long_volume=1500,
                short_volume=1200,
                expected_value=0.05,
                sentiment_score=0.6,
                ranking_score=0.78,
                timestamp=datetime.now(),
                contracts_to_trade=2,
                total_cost=360.0,
                buying_power_used_pct=0.036,
            )
        ]

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000.0,
                    "format": "text"
                }
            )

            assert response.status_code == 200
            content = response.text
            
            # Verify text format content
            assert "SPY Bull Call Spread Recommendations" in content
            assert "470/472" in content
            assert "Net Debit: $1.80" in content
            assert "Probability: 65.0%" in content

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_clipboard_format(self, client):
        """Test retrieving recommendations in clipboard format."""
        mock_recommendations = [
            SpreadRecommendation(
                long_strike=470.0,
                short_strike=472.0,
                long_premium=6.05,
                short_premium=4.25,
                net_debit=1.80,
                max_risk=1.80,
                max_profit=0.20,
                risk_reward_ratio=0.11,
                probability_of_profit=0.65,
                breakeven_price=471.80,
                long_bid=6.00,
                long_ask=6.10,
                short_bid=4.20,
                short_ask=4.30,
                long_volume=1500,
                short_volume=1200,
                expected_value=0.05,
                sentiment_score=0.6,
                ranking_score=0.78,
                timestamp=datetime.now(),
                contracts_to_trade=2,
                total_cost=360.0,
                buying_power_used_pct=0.036,
            )
        ]

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000.0,
                    "format": "clipboard"
                }
            )

            assert response.status_code == 200
            content = response.text
            
            # Verify clipboard format contains order ticket
            assert "BUY +2 VERTICAL SPY" in content
            assert "470/472 CALL @1.80 LMT" in content

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_parameter_validation(self, client):
        """Test parameter validation for spread recommendations endpoint."""
        # Test missing account_size
        response = client.get("/api/v1/recommendations/spreads")
        assert response.status_code == 422
        
        # Test invalid account_size
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": -1000}
        )
        assert response.status_code == 422
        
        # Test invalid max_recommendations
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={
                "account_size": 10000,
                "max_recommendations": 0
            }
        )
        assert response.status_code == 422
        
        # Test invalid format
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={
                "account_size": 10000,
                "format": "invalid_format"
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_no_results(self, client):
        """Test endpoint when no recommendations are found."""
        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=[])

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000.0,
                    "format": "json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            
            assert data["recommendations"] == []
            assert data["summary"]["total_recommendations"] == 0
            assert "No spread recommendations" in data["message"]

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_rate_limit_error(self, client):
        """Test handling of rate limit errors."""
        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(
                side_effect=RateLimitError("Rate limit exceeded", retry_after=60)
            )

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 10000.0}
            )

            assert response.status_code == 429
            data = response.json()
            assert data["detail"]["error"]["code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry_after" in data["detail"]["error"]["details"]

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_market_data_error(self, client):
        """Test handling of market data errors."""
        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(
                side_effect=MarketDataError("Market data unavailable")
            )

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 10000.0}
            )

            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["error"]["code"] == "MARKET_DATA_ERROR"

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_caching_headers(self, client):
        """Test that appropriate caching headers are set."""
        mock_recommendations = []

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 10000.0}
            )

            assert response.status_code == 200
            
            # Verify caching headers
            assert "Cache-Control" in response.headers
            assert "private" in response.headers["Cache-Control"]
            assert "max-age" in response.headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_rate_limit_headers(self, client):
        """Test that rate limit headers are included."""
        mock_recommendations = []

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 10000.0}
            )

            assert response.status_code == 200
            
            # Verify rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_account_size_ranges(self, client):
        """Test endpoint with different account size ranges."""
        mock_recommendations = []

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations)

            # Test small account
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 5000.0}
            )
            assert response.status_code == 200

            # Test medium account
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 50000.0}
            )
            assert response.status_code == 200

            # Test large account
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 500000.0}
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_spread_recommendations_max_limits(self, client):
        """Test endpoint respects maximum recommendation limits."""
        # Create more recommendations than the limit
        mock_recommendations = []
        for i in range(10):
            mock_recommendations.append(
                SpreadRecommendation(
                    long_strike=470.0 + i,
                    short_strike=472.0 + i,
                    long_premium=6.05,
                    short_premium=4.25,
                    net_debit=1.80,
                    max_risk=1.80,
                    max_profit=0.20,
                    risk_reward_ratio=0.11,
                    probability_of_profit=0.65,
                    breakeven_price=471.80,
                    long_bid=6.00,
                    long_ask=6.10,
                    short_bid=4.20,
                    short_ask=4.30,
                    long_volume=1500,
                    short_volume=1200,
                    expected_value=0.05,
                    sentiment_score=0.6,
                    ranking_score=0.78 - (i * 0.01),  # Decreasing scores
                    timestamp=datetime.now(),
                    contracts_to_trade=2,
                    total_cost=360.0,
                    buying_power_used_pct=0.036,
                )
            )

        with patch("app.api.v1.endpoints.recommendations.spread_service") as mock_service:
            mock_service.get_recommendations = AsyncMock(return_value=mock_recommendations[:3])  # Service returns limited results

            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000.0,
                    "max_recommendations": 3,
                    "format": "json"
                }
            )

            assert response.status_code == 200
            data = response.json()
            
            # Should respect the limit
            assert len(data["recommendations"]) == 3
            assert data["summary"]["total_recommendations"] == 3