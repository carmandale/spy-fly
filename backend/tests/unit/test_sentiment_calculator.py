from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.sentiment import SentimentResult
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator


class TestSentimentCalculator:
    @pytest.fixture
    def mock_market_service(self):
        service = Mock(spec=MarketDataService)
        service.get_historical_data = AsyncMock()
        return service

    @pytest.fixture
    def cache(self):
        return MarketDataCache(max_size=100)

    @pytest.fixture
    def calculator(self, mock_market_service, cache):
        return SentimentCalculator(mock_market_service, cache)

    @pytest.fixture
    def mock_historical_data(self):
        # Generate 60 days of trending up price data
        prices = []
        base_price = 560.0
        for i in range(60):
            price = base_price + i * 0.3 + (i % 3 - 1) * 1.5
            prices.append(
                {
                    "timestamp": f"2025-05-{i+1:02d}T09:30:00",
                    "open": price - 0.5,
                    "high": price + 1.0,
                    "low": price - 1.0,
                    "close": price,
                    "volume": 50000000,
                    "vwap": price,
                }
            )

        return {"ticker": "SPY", "bars": prices, "result_count": len(prices)}

    @pytest.mark.asyncio
    async def test_bullish_sentiment(
        self, calculator, mock_market_service, mock_historical_data
    ):
        # Setup bullish market conditions
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 14.5}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5680.0, "previous_close": 5670.0},
            ):
                result = await calculator.calculate_sentiment()

        assert isinstance(result, SentimentResult)
        assert result.score >= 60  # Should be bullish
        assert result.decision == "PROCEED"
        assert result.breakdown.vix.score == 20  # Low VIX
        assert result.breakdown.futures.score == 20  # Positive futures
        assert result.technical_status.all_bullish is True
        assert result.cached is False

    @pytest.mark.asyncio
    async def test_bearish_sentiment(
        self, calculator, mock_market_service, mock_historical_data
    ):
        # Setup bearish market conditions
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 25.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5650.0, "previous_close": 5670.0},
            ):
                result = await calculator.calculate_sentiment()

        assert result.score < 60
        assert result.decision == "SKIP"
        assert result.breakdown.vix.score == 0  # High VIX
        assert result.breakdown.futures.score == 0  # Negative futures

    @pytest.mark.asyncio
    async def test_edge_case_sentiment(
        self, calculator, mock_market_service, mock_historical_data
    ):
        # Setup edge case - score exactly at threshold
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 16.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={
                    "current": 5675.67,  # Exactly 0.1% up
                    "previous_close": 5670.0,
                },
            ):
                result = await calculator.calculate_sentiment()

        # With these conditions, score should be around threshold
        assert result.score > 0
        assert result.decision in ["PROCEED", "SKIP"]

    @pytest.mark.asyncio
    async def test_cache_hit(
        self, calculator, mock_market_service, mock_historical_data
    ):
        # First call populates cache
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 15.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5680.0, "previous_close": 5670.0},
            ):
                result1 = await calculator.calculate_sentiment()

        # Second call should hit cache
        result2 = await calculator.calculate_sentiment()

        assert result2.cached is True
        assert result2.score == result1.score
        assert result2.decision == result1.decision
        # Market service should only be called once
        assert mock_market_service.get_historical_data.call_count == 1

    @pytest.mark.asyncio
    async def test_force_refresh(
        self, calculator, mock_market_service, mock_historical_data
    ):
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        # First call
        with patch.object(calculator, "_get_vix_data", return_value={"value": 15.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5680.0, "previous_close": 5670.0},
            ):
                await calculator.calculate_sentiment()

        # Force refresh should bypass cache
        with patch.object(calculator, "_get_vix_data", return_value={"value": 18.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5685.0, "previous_close": 5670.0},
            ):
                result = await calculator.calculate_sentiment(force_refresh=True)

        assert result.cached is False
        assert result.breakdown.vix.value == 18.0  # New VIX value
        assert mock_market_service.get_historical_data.call_count == 2

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, calculator, mock_market_service):
        # Only 10 days of data
        short_history = {
            "ticker": "SPY",
            "bars": [
                {
                    "timestamp": f"2025-07-{i+16:02d}T09:30:00",
                    "close": 565.0 + i,
                    "volume": 50000000,
                }
                for i in range(10)
            ],
            "result_count": 10,
        }

        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: short_history
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 15.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5680.0, "previous_close": 5670.0},
            ):
                result = await calculator.calculate_sentiment()

        # Should still calculate but with limited indicators
        assert result.score >= 0
        assert result.breakdown.ma50.score == 0  # Insufficient data for MA50
        assert "Insufficient data" in result.breakdown.ma50.label

    @pytest.mark.asyncio
    async def test_technical_status_evaluation(
        self, calculator, mock_market_service, mock_historical_data
    ):
        mock_market_service.get_historical_data.return_value = Mock(
            model_dump=lambda: mock_historical_data
        )

        with patch.object(calculator, "_get_vix_data", return_value={"value": 15.0}):
            with patch.object(
                calculator,
                "_get_futures_data",
                return_value={"current": 5680.0, "previous_close": 5670.0},
            ):
                result = await calculator.calculate_sentiment()

        # Check technical status details
        assert "trend" in result.technical_status.details
        assert "momentum" in result.technical_status.details
        assert "volatility" in result.technical_status.details

        # With bullish conditions
        assert result.technical_status.details["trend"] == "up"
        assert result.technical_status.details["volatility"] == "low"
