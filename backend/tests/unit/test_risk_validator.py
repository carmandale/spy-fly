"""
Unit tests for RiskValidator class.

Tests the enforcement of risk management constraints including:
- 5% maximum buying power per trade
- 1:1 minimum risk/reward ratio
- Position sizing calculations
- Edge case handling
"""

import pytest
from decimal import Decimal

from app.services.risk_validator import RiskValidator, RiskValidationResult
from app.models.spread import SpreadRecommendation
from datetime import datetime


class TestRiskValidator:
    """Test suite for RiskValidator risk management constraints."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.validator = RiskValidator()

    def create_test_recommendation(
        self,
        net_debit: float = 2.50,
        max_profit: float = 2.50,
        contracts: int = 4,
        account_size: float = 10000.0
    ) -> SpreadRecommendation:
        """Create a test spread recommendation with specified parameters."""
        max_risk = net_debit
        risk_reward_ratio = max_profit / max_risk if max_risk > 0 else 0
        total_cost = contracts * net_debit * 100
        buying_power_used_pct = total_cost / account_size if account_size > 0 else 0

        return SpreadRecommendation(
            long_strike=470.0,
            short_strike=475.0,
            long_premium=3.50,
            short_premium=1.00,
            net_debit=net_debit,
            max_risk=max_risk,
            max_profit=max_profit,
            risk_reward_ratio=risk_reward_ratio,
            probability_of_profit=0.60,
            breakeven_price=472.50,
            long_bid=3.45,
            long_ask=3.55,
            short_bid=0.95,
            short_ask=1.05,
            long_volume=1000,
            short_volume=800,
            expected_value=0.50,
            sentiment_score=0.15,
            ranking_score=0.75,
            timestamp=datetime.now(),
            contracts_to_trade=contracts,
            total_cost=total_cost,
            buying_power_used_pct=buying_power_used_pct
        )

    def test_validate_buying_power_within_limit(self):
        """Test validation passes when buying power is within 5% limit."""
        # Create recommendation using 4% of buying power
        recommendation = self.create_test_recommendation(
            net_debit=2.00,
            contracts=2,
            account_size=10000.0
        )
        
        result = self.validator.validate_buying_power(recommendation, account_size=10000.0)
        
        assert result.is_valid is True
        assert result.actual_percentage == 0.04  # 4%
        assert result.max_allowed_percentage == 0.05  # 5%
        assert result.message == "Buying power usage within limits"

    def test_validate_buying_power_exceeds_limit(self):
        """Test validation fails when buying power exceeds 5% limit."""
        # Create recommendation using 8% of buying power
        recommendation = self.create_test_recommendation(
            net_debit=4.00,
            contracts=2,
            account_size=10000.0
        )
        
        result = self.validator.validate_buying_power(recommendation, account_size=10000.0)
        
        assert result.is_valid is False
        assert result.actual_percentage == 0.08  # 8%
        assert result.max_allowed_percentage == 0.05  # 5%
        assert "exceeds maximum" in result.message

    def test_validate_buying_power_edge_cases(self):
        """Test buying power validation with edge cases."""
        # Test with zero account size
        recommendation = self.create_test_recommendation()
        
        with pytest.raises(ValueError, match="Account size must be positive"):
            self.validator.validate_buying_power(recommendation, account_size=0)
        
        # Test with negative account size
        with pytest.raises(ValueError, match="Account size must be positive"):
            self.validator.validate_buying_power(recommendation, account_size=-1000)
        
        # Test with exactly 5% usage
        recommendation = self.create_test_recommendation(
            net_debit=2.50,
            contracts=2,
            account_size=10000.0
        )
        result = self.validator.validate_buying_power(recommendation, account_size=10000.0)
        assert result.is_valid is True
        assert result.actual_percentage == 0.05

    def test_validate_risk_reward_ratio_valid(self):
        """Test risk/reward ratio validation with valid ratios."""
        # Test 1:1 ratio (minimum allowed)
        recommendation = self.create_test_recommendation(
            net_debit=2.50,
            max_profit=2.50
        )
        
        result = self.validator.validate_risk_reward_ratio(recommendation)
        
        assert result.is_valid is True
        assert result.actual_ratio == 1.0
        assert result.min_required_ratio == 1.0
        assert result.message == "Risk/reward ratio meets requirements"
        
        # Test 2:1 ratio (better than minimum)
        recommendation = self.create_test_recommendation(
            net_debit=2.00,
            max_profit=4.00
        )
        
        result = self.validator.validate_risk_reward_ratio(recommendation)
        
        assert result.is_valid is True
        assert result.actual_ratio == 2.0

    def test_validate_risk_reward_ratio_invalid(self):
        """Test risk/reward ratio validation with invalid ratios."""
        # Test 0.5:1 ratio (below minimum)
        recommendation = self.create_test_recommendation(
            net_debit=4.00,
            max_profit=2.00
        )
        
        result = self.validator.validate_risk_reward_ratio(recommendation)
        
        assert result.is_valid is False
        assert result.actual_ratio == 0.5
        assert result.min_required_ratio == 1.0
        assert "below minimum" in result.message

    def test_validate_risk_reward_ratio_edge_cases(self):
        """Test risk/reward ratio validation with edge cases."""
        # Test with zero max profit
        recommendation = self.create_test_recommendation(
            net_debit=2.50,
            max_profit=0.0
        )
        
        result = self.validator.validate_risk_reward_ratio(recommendation)
        assert result.is_valid is False
        assert result.actual_ratio == 0.0
        
        # Test with zero net debit (should not happen in practice)
        recommendation = self.create_test_recommendation(
            net_debit=0.0,
            max_profit=2.50
        )
        
        result = self.validator.validate_risk_reward_ratio(recommendation)
        assert result.is_valid is False
        assert "Invalid spread" in result.message

    def test_calculate_position_size_standard(self):
        """Test standard position size calculation."""
        account_size = 25000.0
        net_debit = 2.50
        max_buying_power_pct = 0.05
        
        result = self.validator.calculate_position_size(
            account_size=account_size,
            net_debit=net_debit,
            max_buying_power_pct=max_buying_power_pct
        )
        
        # Should be able to afford 5 contracts: (25000 * 0.05) / (2.50 * 100) = 5
        assert result['contracts'] == 5
        assert result['total_cost'] == 1250.0  # 5 * 2.50 * 100
        assert result['buying_power_pct'] == 0.05  # Exactly 5%

    def test_calculate_position_size_fractional_rounding(self):
        """Test position size calculation with fractional contract rounding."""
        # Case where calculation yields 4.8 contracts - should round down to 4
        account_size = 24000.0
        net_debit = 2.50
        max_buying_power_pct = 0.05
        
        result = self.validator.calculate_position_size(
            account_size=account_size,
            net_debit=net_debit,
            max_buying_power_pct=max_buying_power_pct
        )
        
        assert result['contracts'] == 4  # Rounded down from 4.8
        assert result['total_cost'] == 1000.0  # 4 * 2.50 * 100
        assert result['buying_power_pct'] < 0.05  # Less than 5%

    def test_calculate_position_size_minimum_contract(self):
        """Test position size calculation enforces minimum 1 contract."""
        # Very small account that can only afford < 1 contract at 5%
        account_size = 1000.0
        net_debit = 25.00  # Expensive spread
        max_buying_power_pct = 0.05
        
        result = self.validator.calculate_position_size(
            account_size=account_size,
            net_debit=net_debit,
            max_buying_power_pct=max_buying_power_pct
        )
        
        # Should still trade 1 contract minimum
        assert result['contracts'] == 1
        assert result['total_cost'] == 2500.0  # 1 * 25.00 * 100
        assert result['buying_power_pct'] == 2.5  # 250% of intended!
        assert result['warning'] == "Position size exceeds buying power limit"

    def test_calculate_position_size_edge_cases(self):
        """Test position size calculation edge cases."""
        # Zero net debit
        with pytest.raises(ValueError, match="Net debit must be positive"):
            self.validator.calculate_position_size(
                account_size=10000.0,
                net_debit=0.0,
                max_buying_power_pct=0.05
            )
        
        # Negative net debit
        with pytest.raises(ValueError, match="Net debit must be positive"):
            self.validator.calculate_position_size(
                account_size=10000.0,
                net_debit=-2.50,
                max_buying_power_pct=0.05
            )
        
        # Zero buying power percentage
        with pytest.raises(ValueError, match="Buying power percentage must be positive"):
            self.validator.calculate_position_size(
                account_size=10000.0,
                net_debit=2.50,
                max_buying_power_pct=0.0
            )

    def test_validate_spread_comprehensive(self):
        """Test comprehensive spread validation combining all checks."""
        account_size = 10000.0
        
        # Valid spread - passes all checks
        valid_spread = self.create_test_recommendation(
            net_debit=2.00,
            max_profit=3.00,  # 1.5:1 ratio
            contracts=2,      # 4% buying power
            account_size=account_size
        )
        
        result = self.validator.validate_spread(valid_spread, account_size)
        
        assert result['is_valid'] is True
        assert result['buying_power_check'].is_valid is True
        assert result['risk_reward_check'].is_valid is True
        assert len(result['errors']) == 0
        
        # Invalid spread - fails risk/reward
        invalid_spread = self.create_test_recommendation(
            net_debit=3.00,
            max_profit=2.00,  # 0.67:1 ratio - fails
            contracts=1,      # 3% buying power - passes
            account_size=account_size
        )
        
        result = self.validator.validate_spread(invalid_spread, account_size)
        
        assert result['is_valid'] is False
        assert result['buying_power_check'].is_valid is True
        assert result['risk_reward_check'].is_valid is False
        assert len(result['errors']) == 1
        assert "risk/reward ratio" in result['errors'][0].lower()

    def test_validate_multiple_spreads_batch(self):
        """Test validation of multiple spreads in batch."""
        account_size = 20000.0
        
        spreads = [
            self.create_test_recommendation(net_debit=2.00, max_profit=3.00, contracts=4, account_size=account_size),   # Valid - 4%
            self.create_test_recommendation(net_debit=5.00, max_profit=2.00, contracts=2, account_size=account_size),   # Invalid R/R - 0.4:1
            self.create_test_recommendation(net_debit=3.00, max_profit=3.00, contracts=10, account_size=account_size),  # Invalid BP - 15%
            self.create_test_recommendation(net_debit=1.50, max_profit=2.00, contracts=3, account_size=account_size),   # Valid - 2.25%
        ]
        
        results = self.validator.validate_spreads_batch(spreads, account_size)
        
        assert len(results['valid_spreads']) == 2
        assert len(results['invalid_spreads']) == 2
        assert results['validation_details'][1]['errors'][0] == "Risk/reward ratio below minimum"
        assert "exceeds maximum" in results['validation_details'][2]['errors'][0]

    def test_position_size_with_custom_limit(self):
        """Test position sizing with custom buying power limit."""
        validator = RiskValidator(max_buying_power_pct=0.03)  # 3% instead of 5%
        
        account_size = 10000.0
        net_debit = 2.00
        
        result = validator.calculate_position_size(
            account_size=account_size,
            net_debit=net_debit,
            max_buying_power_pct=0.03
        )
        
        # Should be 1 contract: (10000 * 0.03) / (2.00 * 100) = 1.5 -> 1
        assert result['contracts'] == 1
        assert result['total_cost'] == 200.0
        assert result['buying_power_pct'] == 0.02  # 2%

    def test_risk_validator_configuration(self):
        """Test RiskValidator configuration management."""
        # Test default configuration
        assert self.validator.max_buying_power_pct == 0.05
        assert self.validator.min_risk_reward_ratio == 1.0
        
        # Test custom configuration
        custom_validator = RiskValidator(
            max_buying_power_pct=0.02,
            min_risk_reward_ratio=1.5
        )
        assert custom_validator.max_buying_power_pct == 0.02
        assert custom_validator.min_risk_reward_ratio == 1.5
        
        # Test configuration update
        self.validator.update_configuration(
            max_buying_power_pct=0.04,
            min_risk_reward_ratio=1.2
        )
        assert self.validator.max_buying_power_pct == 0.04
        assert self.validator.min_risk_reward_ratio == 1.2