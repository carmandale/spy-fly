"""
Integration tests for risk validation within the spread selection pipeline.

Tests the complete integration of RiskValidator with SpreadSelectionService
to ensure risk constraints are properly enforced throughout the system.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import date, datetime
import pandas as pd

from app.services.spread_selection_service import (
    SpreadSelectionService,
    SpreadConfiguration
)
from app.models.spread import SpreadRecommendation
from app.services.risk_validator import RiskValidator
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator
from app.services.options_chain_processor import OptionsChainProcessor
from app.services.spread_generator import SpreadGenerator
from app.models.market import OptionContract, OptionChainResponse, QuoteResponse


class TestRiskValidationIntegration:
    """Test risk validation integration with spread selection service."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.black_scholes = BlackScholesCalculator()
        self.market_service = AsyncMock(spec=MarketDataService)
        self.sentiment_calculator = AsyncMock(spec=SentimentCalculator)
        self.risk_validator = RiskValidator()
        
        # Create service with risk validator
        self.config = SpreadConfiguration(
            max_buying_power_pct=0.05,
            min_risk_reward_ratio=1.0
        )
        
        self.spread_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=self.config
        )

    def create_test_option_chain(self, spot_price=475.0):
        """Create a test option chain with various spreads."""
        strikes = [470, 472, 474, 475, 476, 478, 480, 485]
        options = []
        
        for strike in strikes:
            # Price based on moneyness
            if strike < spot_price:
                # ITM - intrinsic + time value
                intrinsic = spot_price - strike
                mid_price = intrinsic + 0.50
            else:
                # OTM - time value only
                mid_price = max(0.05, 2.0 - (strike - spot_price) * 0.2)
            
            bid = round(mid_price * 0.95, 2)
            ask = round(mid_price * 1.05, 2)
            
            option = OptionContract(
                symbol=f"SPY{date.today().strftime('%y%m%d')}C{int(strike*1000):08d}",
                type="call",
                strike=strike,
                expiration=date.today().isoformat(),
                bid=bid,
                ask=ask,
                mid=mid_price,
                last=mid_price,
                volume=1000,
                open_interest=5000
            )
            options.append(option)
            
        return OptionChainResponse(
            ticker="SPY",
            underlying_price=spot_price,
            expiration=date.today().isoformat(),
            options=options,
            cached=False
        )

    @pytest.mark.asyncio
    async def test_risk_validation_filters_excessive_buying_power(self):
        """Test that spreads exceeding buying power limits are filtered out."""
        # Setup market data
        spot_price = 475.0
        account_size = 10000.0
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        # Create option chain with expensive spreads
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        # Mock sentiment
        self.sentiment_calculator.calculate_sentiment.return_value = 0.20
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # Verify all recommendations respect buying power limits
        for rec in recommendations:
            assert rec.buying_power_used_pct <= 0.05, (
                f"Recommendation uses {rec.buying_power_used_pct:.1%} of buying power"
            )
            
            # Verify position sizing
            max_allowed_cost = account_size * 0.05
            assert rec.total_cost <= max_allowed_cost, (
                f"Total cost ${rec.total_cost} exceeds max ${max_allowed_cost}"
            )

    @pytest.mark.asyncio
    async def test_risk_validation_filters_poor_risk_reward(self):
        """Test that spreads with poor risk/reward ratios are filtered out."""
        # Setup market data
        spot_price = 475.0
        account_size = 25000.0
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        # Create option chain
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        # Mock sentiment
        self.sentiment_calculator.calculate_sentiment.return_value = 0.15
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(
            account_size=account_size,
            max_recommendations=10
        )
        
        # Verify all recommendations meet risk/reward requirements
        for rec in recommendations:
            assert rec.risk_reward_ratio >= 1.0, (
                f"Risk/reward ratio {rec.risk_reward_ratio:.2f} below minimum"
            )

    @pytest.mark.asyncio
    async def test_position_sizing_with_fractional_contracts(self):
        """Test that position sizing properly handles fractional contract scenarios."""
        # Setup with specific account size that creates fractional contracts
        spot_price = 475.0
        account_size = 12345.0  # Odd number to force fractional calculations
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        self.sentiment_calculator.calculate_sentiment.return_value = 0.10
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # Verify position sizing
        for rec in recommendations:
            # Contracts should be whole numbers
            assert rec.contracts_to_trade == int(rec.contracts_to_trade)
            assert rec.contracts_to_trade >= 1
            
            # Verify actual cost calculation
            expected_cost = rec.contracts_to_trade * rec.net_debit * 100
            assert abs(rec.total_cost - expected_cost) < 0.01

    @pytest.mark.asyncio
    async def test_risk_validator_with_custom_configuration(self):
        """Test risk validation with custom risk parameters."""
        # Create service with stricter risk limits
        strict_config = SpreadConfiguration(
            max_buying_power_pct=0.02,  # Only 2% instead of 5%
            min_risk_reward_ratio=1.5   # 1.5:1 instead of 1:1
        )
        
        strict_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=strict_config
        )
        
        # Setup market data
        spot_price = 475.0
        account_size = 50000.0
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        self.sentiment_calculator.calculate_sentiment.return_value = 0.25
        
        # Get recommendations with strict limits
        recommendations = await strict_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # Verify stricter limits are enforced
        for rec in recommendations:
            assert rec.buying_power_used_pct <= 0.02
            assert rec.risk_reward_ratio >= 1.5

    @pytest.mark.asyncio
    async def test_edge_case_small_account(self):
        """Test risk validation with very small account size."""
        # Small account that can barely afford 1 contract
        spot_price = 475.0
        account_size = 1000.0  # Very small account
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        self.sentiment_calculator.calculate_sentiment.return_value = 0.15
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # With small account, we might get fewer or no recommendations
        # due to minimum 1 contract requirement
        if recommendations:
            for rec in recommendations:
                # Should always trade at least 1 contract
                assert rec.contracts_to_trade >= 1
                
                # May exceed 5% due to minimum contract requirement
                if rec.buying_power_used_pct > 0.05:
                    # This is acceptable for small accounts
                    assert rec.contracts_to_trade == 1

    @pytest.mark.asyncio
    async def test_no_valid_spreads_after_risk_filtering(self):
        """Test behavior when all spreads are filtered out by risk constraints."""
        # Setup with configuration that will likely filter everything
        ultra_strict_config = SpreadConfiguration(
            max_buying_power_pct=0.001,  # 0.1% - extremely low
            min_risk_reward_ratio=5.0,   # 5:1 - extremely high
            min_probability_of_profit=0.9  # 90% - very high
        )
        
        ultra_strict_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=ultra_strict_config
        )
        
        # Setup market data
        spot_price = 475.0
        account_size = 10000.0
        
        mock_quote = QuoteResponse(
            ticker="SPY",
            price=spot_price,
            bid=474.95,
            ask=475.05,
            bid_size=100,
            ask_size=100,
            volume=50000000,
            timestamp=datetime.now().isoformat(),
            market_status="regular",
            change=1.5,
            change_percent=0.32,
            previous_close=473.5,
            cached=False
        )
        self.market_service.get_spy_quote.return_value = mock_quote
        
        option_chain = self.create_test_option_chain(spot_price)
        self.market_service.get_spy_options.return_value = option_chain
        
        self.sentiment_calculator.calculate_sentiment.return_value = 0.10
        
        # Get recommendations
        recommendations = await ultra_strict_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # Should return empty list when no spreads meet criteria
        assert recommendations == []

    def test_risk_validator_used_in_service(self):
        """Test that RiskValidator is properly integrated into the service."""
        # The service should use risk validation internally
        # This test verifies the configuration is properly passed through
        assert self.spread_service.config.max_buying_power_pct == 0.05
        assert self.spread_service.config.min_risk_reward_ratio == 1.0
        
        # Test configuration update
        new_config = SpreadConfiguration(
            max_buying_power_pct=0.03,
            min_risk_reward_ratio=1.2
        )
        self.spread_service.update_configuration(new_config)
        
        assert self.spread_service.config.max_buying_power_pct == 0.03
        assert self.spread_service.config.min_risk_reward_ratio == 1.2