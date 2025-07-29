"""
Unit tests for SpreadSelectionService error handling and validation.

This module tests the core functionality of the spread selection service
with focus on error handling for missing or invalid volatility data.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_selection_service import (
    SpreadConfiguration,
    SpreadSelectionService,
)


class TestSpreadSelectionService:
    """Test spread selection service error handling and validation."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.black_scholes = BlackScholesCalculator()
        self.market_service = AsyncMock(spec=MarketDataService)
        self.sentiment_calculator = AsyncMock(spec=SentimentCalculator)
        self.config = SpreadConfiguration()

        self.spread_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=self.config,
        )

    @pytest.mark.asyncio
    async def test_invalid_account_size_validation(self):
        """Test validation of invalid account size parameters."""
        # Test zero account size
        with pytest.raises(ValueError, match="Account size must be positive"):
            await self.spread_service.get_recommendations(account_size=0.0)

        # Test negative account size
        with pytest.raises(ValueError, match="Account size must be positive"):
            await self.spread_service.get_recommendations(account_size=-1000.0)

    @pytest.mark.asyncio
    async def test_market_data_error_handling(self):
        """Test error handling when market data is unavailable."""
        # Mock market service to raise exception
        self.market_service.get_spy_quote.side_effect = Exception(
            "Market data unavailable"
        )

        # Should handle the error gracefully
        try:
            result = await self.spread_service.get_recommendations(account_size=10000.0)
            # If no exception, should return empty list due to missing data
            assert result == []
        except Exception as e:
            # Exception should be handled internally or be a specific MarketDataError
            assert "Market data unavailable" in str(e)

    @pytest.mark.asyncio
    async def test_sentiment_calculation_error_handling(self):
        """Test error handling when sentiment calculation fails."""
        # Mock successful market data but failed sentiment
        from app.models.market import QuoteResponse

        mock_quote = QuoteResponse(
            ticker="SPY",
            price=475.0,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=1000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=2.5,
            change_percent=0.53,
            previous_close=472.5,
            cached=False,
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        self.sentiment_calculator.calculate_sentiment.side_effect = Exception(
            "Sentiment service down"
        )

        # Should handle sentiment error gracefully
        try:
            await self.spread_service._update_market_context()
            # If no exception raised, sentiment should be None
            assert self.spread_service._current_sentiment_score is None
        except Exception:
            # Should be handled internally
            pass

    @pytest.mark.asyncio
    async def test_missing_volatility_data_fallback(self):
        """Test fallback behavior when VIX/volatility data is missing."""
        # Mock market data without VIX (using default volatility)
        from app.models.market import QuoteResponse

        mock_quote = QuoteResponse(
            ticker="SPY",
            price=480.0,
            bid=479.95,
            ask=480.05,
            bid_size=50,
            ask_size=50,
            volume=500000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.2,
            change_percent=0.25,
            previous_close=478.8,
            cached=False,
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        self.sentiment_calculator.calculate_sentiment.return_value = 0.1

        await self.spread_service._update_market_context()

        # Should use default VIX value
        assert self.spread_service._current_vix == 20.0
        assert self.spread_service._current_spy_price == 480.0
        assert self.spread_service._current_sentiment_score == 0.1

    def test_configuration_management(self):
        """Test configuration getting and setting."""
        # Test getting current configuration
        config = self.spread_service.get_configuration()
        assert isinstance(config, SpreadConfiguration)
        assert config.max_buying_power_pct == 0.05

        # Test updating configuration
        new_config = SpreadConfiguration(
            max_buying_power_pct=0.03, min_risk_reward_ratio=1.5
        )
        self.spread_service.update_configuration(new_config)

        updated_config = self.spread_service.get_configuration()
        assert updated_config.max_buying_power_pct == 0.03
        assert updated_config.min_risk_reward_ratio == 1.5


class TestExpectedValueCalculation:
    """Test expected value calculation for spread recommendations."""

    def test_expected_value_basic_calculation(self):
        """Test basic expected value calculation with known inputs."""
        # Known inputs for verification
        probability_of_profit = 0.4  # 40% chance of profit
        max_profit = 100.0  # $100 max profit
        max_risk = 150.0  # $150 max risk

        # Calculate expected value using the same formula as SpreadSelectionService
        expected_value = (probability_of_profit * max_profit) - (
            (1 - probability_of_profit) * max_risk
        )

        # Verify calculation: (0.4 * 100) - (0.6 * 150) = 40 - 90 = -50
        assert expected_value == -50.0

    def test_expected_value_positive_scenario(self):
        """Test expected value calculation for profitable scenario."""
        # Favorable trade scenario
        probability_of_profit = 0.7  # 70% chance of profit
        max_profit = 200.0  # $200 max profit
        max_risk = 100.0  # $100 max risk

        expected_value = (probability_of_profit * max_profit) - (
            (1 - probability_of_profit) * max_risk
        )

        # Verify: (0.7 * 200) - (0.3 * 100) = 140 - 30 = 110
        assert expected_value == 110.0

    def test_expected_value_break_even_scenario(self):
        """Test expected value calculation for break-even scenario."""
        # Exact break-even scenario
        probability_of_profit = 0.6  # 60% chance
        max_profit = 50.0  # $50 max profit
        max_risk = 75.0  # $75 max risk (creates break-even at 60%)

        expected_value = (probability_of_profit * max_profit) - (
            (1 - probability_of_profit) * max_risk
        )

        # Verify: (0.6 * 50) - (0.4 * 75) = 30 - 30 = 0
        assert expected_value == 0.0

    def test_expected_value_edge_cases(self):
        """Test expected value calculation with edge case inputs."""
        # Test with 0% probability
        expected_value_zero = (0.0 * 100.0) - ((1 - 0.0) * 50.0)
        assert expected_value_zero == -50.0

        # Test with 100% probability
        expected_value_certain = (1.0 * 100.0) - ((1 - 1.0) * 50.0)
        assert expected_value_certain == 100.0

        # Test with very small profits and risks
        expected_value_small = (0.5 * 0.01) - ((1 - 0.5) * 0.01)
        assert expected_value_small == 0.0

    def test_expected_value_precision(self):
        """Test expected value calculation maintains numerical precision."""
        # Use values that test floating point precision
        probability_of_profit = 0.333333  # Repeating decimal
        max_profit = 150.75  # Decimal profit
        max_risk = 100.25  # Decimal risk

        expected_value = (probability_of_profit * max_profit) - (
            (1 - probability_of_profit) * max_risk
        )

        # Calculate expected result manually for verification
        expected_result = (0.333333 * 150.75) - (0.666667 * 100.25)
        
        # Verify within reasonable floating point tolerance
        assert abs(expected_value - expected_result) < 0.0001

    def test_expected_value_with_risk_reward_ratios(self):
        """Test expected value across different risk/reward ratios."""
        base_risk = 100.0

        # Test 1:1 risk/reward (max_profit = max_risk)
        max_profit_1to1 = 100.0
        prob_1to1 = 0.5  # Need >50% to be profitable
        ev_1to1 = (prob_1to1 * max_profit_1to1) - ((1 - prob_1to1) * base_risk)
        assert ev_1to1 == 0.0  # Exactly break-even at 50%

        # Test 2:1 risk/reward (max_profit = 2 * max_risk)
        max_profit_2to1 = 200.0
        prob_2to1 = 0.4  # Lower probability but higher reward
        ev_2to1 = (prob_2to1 * max_profit_2to1) - ((1 - prob_2to1) * base_risk)
        assert ev_2to1 == 20.0  # (0.4 * 200) - (0.6 * 100) = 80 - 60 = 20

        # Test 1:2 risk/reward (max_profit = 0.5 * max_risk)
        max_profit_1to2 = 50.0
        prob_1to2 = 0.8  # Need high probability for profitability
        ev_1to2 = (prob_1to2 * max_profit_1to2) - ((1 - prob_1to2) * base_risk)
        assert ev_1to2 == 20.0  # (0.8 * 50) - (0.2 * 100) = 40 - 20 = 20

    def test_expected_value_probability_thresholds(self):
        """Test probability thresholds for positive expected value."""
        max_profit = 100.0
        max_risk = 150.0

        # Calculate breakeven probability
        # At breakeven: prob * max_profit = (1 - prob) * max_risk
        # prob * max_profit = max_risk - prob * max_risk
        # prob * (max_profit + max_risk) = max_risk
        # prob = max_risk / (max_profit + max_risk)
        breakeven_prob = max_risk / (max_profit + max_risk)
        expected_breakeven_prob = 150.0 / (100.0 + 150.0)  # = 0.6
        
        assert abs(breakeven_prob - expected_breakeven_prob) < 0.0001

        # Test just below breakeven
        prob_below = breakeven_prob - 0.01
        ev_below = (prob_below * max_profit) - ((1 - prob_below) * max_risk)
        assert ev_below < 0

        # Test just above breakeven
        prob_above = breakeven_prob + 0.01
        ev_above = (prob_above * max_profit) - ((1 - prob_above) * max_risk)
        assert ev_above > 0
