import numpy as np
import pandas as pd
import pytest

from app.services.sentiment_calculator import (
    calculate_bollinger_position,
    calculate_rsi,
    score_bollinger,
    score_futures,
    score_ma50,
    score_rsi,
    score_vix,
)


class TestVIXScoring:
    def test_low_vix_score(self):
        score = score_vix(14.5)
        assert score.score == 20
        assert score.value == 14.5
        assert "Low volatility" in score.label

    def test_medium_vix_score(self):
        score = score_vix(18.0)
        assert score.score == 10
        assert score.value == 18.0
        assert "Medium volatility" in score.label

    def test_high_vix_score(self):
        score = score_vix(25.0)
        assert score.score == 0
        assert score.value == 25.0
        assert "High volatility" in score.label

    def test_vix_edge_cases(self):
        # Exactly at threshold
        assert score_vix(16.0).score == 10
        assert score_vix(20.0).score == 10

    def test_vix_none_handling(self):
        score = score_vix(None)
        assert score.score == 0
        assert score.value == 0
        assert "unavailable" in score.label.lower()


class TestFuturesScoring:
    def test_bullish_futures(self):
        score = score_futures(5680.0, 5670.0)
        assert score.score == 20
        assert score.change_percent == pytest.approx(0.176, rel=0.01)
        assert "Positive overnight" in score.label

    def test_neutral_futures(self):
        score = score_futures(5674.0, 5670.0)
        assert score.score == 10
        assert score.change_percent == pytest.approx(0.071, rel=0.01)
        assert "Slightly positive" in score.label

    def test_bearish_futures(self):
        score = score_futures(5665.0, 5670.0)
        assert score.score == 0
        assert score.change_percent == pytest.approx(-0.088, rel=0.01)
        assert "Negative overnight" in score.label

    def test_futures_exact_threshold(self):
        # Exactly 0.1%
        score = score_futures(5675.67, 5670.0)
        assert score.score == 20  # Should be bullish

    def test_futures_missing_data(self):
        score = score_futures(None, 5670.0)
        assert score.score == 0
        assert "unavailable" in score.label.lower()


class TestTechnicalIndicators:
    @pytest.fixture
    def sample_prices(self):
        # Generate 50 days of price data
        np.random.seed(42)
        prices = pd.Series(
            [560.0 + i * 0.3 + np.random.uniform(-2, 2) for i in range(50)]
        )
        return prices

    def test_rsi_calculation(self, sample_prices):
        rsi = calculate_rsi(sample_prices)
        assert 0 <= rsi <= 100
        assert isinstance(rsi, (int, float))

    def test_rsi_scoring_neutral(self):
        score = score_rsi(55.0)
        assert score.score == 10
        assert score.value == 55.0
        assert "Neutral" in score.label

    def test_rsi_scoring_oversold(self):
        score = score_rsi(25.0)
        assert score.score == 0
        assert "Oversold" in score.label

    def test_rsi_scoring_overbought(self):
        score = score_rsi(75.0)
        assert score.score == 0
        assert "Overbought" in score.label

    def test_rsi_edge_cases(self):
        assert score_rsi(30.0).score == 10  # Exactly at threshold
        assert score_rsi(70.0).score == 10  # Exactly at threshold

    def test_ma50_scoring_above(self, sample_prices):
        current_price = sample_prices.iloc[-1]
        ma50 = sample_prices.rolling(window=50).mean().iloc[-1]

        # Test when price is above MA
        score = score_ma50(current_price + 5, ma50)
        assert score.score == 10
        assert score.position == "above"
        assert "Above 50-MA" in score.label

    def test_ma50_scoring_below(self, sample_prices):
        current_price = sample_prices.iloc[-1]
        ma50 = sample_prices.rolling(window=50).mean().iloc[-1]

        # Test when price is below MA
        score = score_ma50(current_price - 5, ma50)
        assert score.score == 0
        assert score.position == "below"
        assert "Below 50-MA" in score.label

    def test_bollinger_position_calculation(self, sample_prices):
        position = calculate_bollinger_position(sample_prices)
        assert 0 <= position <= 1

    def test_bollinger_scoring_middle(self):
        # Position in middle 60%
        score = score_bollinger(0.5)
        assert score.score == 10
        assert "Middle range" in score.label

    def test_bollinger_scoring_extreme(self):
        # Position near upper band
        score = score_bollinger(0.95)
        assert score.score == 0
        assert "Near upper band" in score.label

        # Position near lower band
        score = score_bollinger(0.05)
        assert score.score == 0
        assert "Near lower band" in score.label

    def test_bollinger_edge_cases(self):
        # Exactly at inner range boundary
        assert score_bollinger(0.2).score == 10
        assert score_bollinger(0.8).score == 10
        assert score_bollinger(0.19).score == 0
        assert score_bollinger(0.81).score == 0
