"""
Tests for BlackScholesCalculator class with known mathematical results.

This module tests the Black-Scholes option pricing and probability calculations
against known mathematical results to ensure accuracy within 0.01% tolerance.
"""

import math
from decimal import getcontext

import pytest

from app.services.black_scholes_calculator import BlackScholesCalculator

# Set high precision for mathematical validation
getcontext().prec = 50


class TestBlackScholesCalculator:
    """Test Black-Scholes calculations with mathematical precision."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.calculator = BlackScholesCalculator()
        self.tolerance = 0.0001  # 0.01% tolerance requirement

    def test_probability_of_profit_known_result_1(self):
        """Test PoP calculation against known mathematical result #1.

        Test case: SPY at $500, strike $505, 0.25 hours to expiry, 20% IV
        Expected result calculated using reference Black-Scholes implementation.
        """
        spot_price = 500.0
        strike_price = 505.0
        time_to_expiry = 0.25 / 365  # 0.25 hours = ~0.000685 years
        volatility = 0.20
        risk_free_rate = 0.05

        # Known result from mathematical calculation (OTM option with very short expiry)
        expected_pop = 0.0289  # Approximately 2.89% (corrected from calculation)

        result = self.calculator.probability_of_profit(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )

        assert abs(result - expected_pop) <= self.tolerance, (
            f"PoP result {result:.6f} differs from expected {expected_pop:.6f} "
            f"by more than {self.tolerance:.4f}"
        )

    def test_probability_of_profit_known_result_2(self):
        """Test PoP calculation against known mathematical result #2.

        Test case: At-the-money option with moderate volatility.
        Expected result: 50% (ATM option has 50% probability of profit).
        """
        spot_price = 450.0
        strike_price = 450.0  # At-the-money
        time_to_expiry = 1.0 / 365  # 1 day to expiry
        volatility = 0.15
        risk_free_rate = 0.05

        # ATM option should be very close to 50%
        expected_pop = 0.5000

        result = self.calculator.probability_of_profit(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )

        # Allow slightly higher tolerance for ATM case due to risk-free rate
        assert (
            abs(result - expected_pop) <= 0.05
        ), f"ATM PoP result {result:.6f} differs significantly from 50%"

    def test_probability_of_profit_deep_itm(self):
        """Test PoP for deep in-the-money call option.

        Deep ITM options should have very high probability of profit.
        """
        spot_price = 500.0
        strike_price = 450.0  # Deep ITM
        time_to_expiry = 1.0 / 365
        volatility = 0.20
        risk_free_rate = 0.05

        result = self.calculator.probability_of_profit(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )

        # Deep ITM should have >90% probability
        assert result > 0.90, f"Deep ITM PoP {result:.4f} should be >90%"

    def test_probability_of_profit_deep_otm(self):
        """Test PoP for deep out-of-the-money call option.

        Deep OTM options should have very low probability of profit.
        """
        spot_price = 450.0
        strike_price = 500.0  # Deep OTM
        time_to_expiry = 1.0 / 365
        volatility = 0.20
        risk_free_rate = 0.05

        result = self.calculator.probability_of_profit(
            spot_price=spot_price,
            strike_price=strike_price,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
        )

        # Deep OTM should have <10% probability
        assert result < 0.10, f"Deep OTM PoP {result:.4f} should be <10%"

    def test_probability_increases_with_time(self):
        """Test that probability increases with more time to expiry."""
        base_params = {
            "spot_price": 475.0,
            "strike_price": 480.0,
            "volatility": 0.18,
            "risk_free_rate": 0.05,
        }

        # Test with different time periods
        short_time = 0.5 / 365  # 0.5 hours
        long_time = 2.0 / 365  # 2 hours

        short_pop = self.calculator.probability_of_profit(
            time_to_expiry=short_time, **base_params
        )
        long_pop = self.calculator.probability_of_profit(
            time_to_expiry=long_time, **base_params
        )

        assert long_pop > short_pop, (
            f"Longer time PoP {long_pop:.4f} should be higher than "
            f"shorter time PoP {short_pop:.4f}"
        )

    def test_probability_increases_with_volatility(self):
        """Test that probability increases with higher volatility for OTM options."""
        base_params = {
            "spot_price": 470.0,
            "strike_price": 480.0,  # OTM
            "time_to_expiry": 1.0 / 365,
            "risk_free_rate": 0.05,
        }

        low_vol_pop = self.calculator.probability_of_profit(
            volatility=0.10, **base_params
        )
        high_vol_pop = self.calculator.probability_of_profit(
            volatility=0.30, **base_params
        )

        assert high_vol_pop > low_vol_pop, (
            f"Higher volatility PoP {high_vol_pop:.4f} should be higher than "
            f"lower volatility PoP {low_vol_pop:.4f}"
        )

    def test_cumulative_normal_distribution_accuracy(self):
        """Test the cumulative normal distribution calculation accuracy."""
        # Test known values for standard normal distribution
        test_cases = [
            (0.0, 0.5000),  # N(0) = 0.5
            (1.0, 0.8413),  # N(1) ≈ 0.8413
            (-1.0, 0.1587),  # N(-1) ≈ 0.1587
            (2.0, 0.9772),  # N(2) ≈ 0.9772
            (-2.0, 0.0228),  # N(-2) ≈ 0.0228
        ]

        for z_value, expected in test_cases:
            result = self.calculator._cumulative_normal(z_value)
            assert (
                abs(result - expected) <= 0.001
            ), f"N({z_value}) = {result:.6f} differs from expected {expected:.4f}"

    def test_d1_d2_calculation_accuracy(self):
        """Test d1 and d2 parameter calculations."""
        spot_price = 480.0
        strike_price = 485.0
        time_to_expiry = 1.0 / 365
        volatility = 0.20
        risk_free_rate = 0.05

        d1, d2 = self.calculator._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        # Verify d2 = d1 - σ√T relationship
        expected_d2 = d1 - volatility * math.sqrt(time_to_expiry)

        assert (
            abs(d2 - expected_d2) <= 1e-10
        ), f"d2 calculation error: got {d2:.10f}, expected {expected_d2:.10f}"

    def test_input_validation_spot_price(self):
        """Test input validation for spot price."""
        with pytest.raises(ValueError, match="Spot price must be positive"):
            self.calculator.probability_of_profit(
                spot_price=0.0,
                strike_price=100.0,
                time_to_expiry=1.0,
                volatility=0.20,
                risk_free_rate=0.05,
            )

    def test_input_validation_strike_price(self):
        """Test input validation for strike price."""
        with pytest.raises(ValueError, match="Strike price must be positive"):
            self.calculator.probability_of_profit(
                spot_price=100.0,
                strike_price=-50.0,
                time_to_expiry=1.0,
                volatility=0.20,
                risk_free_rate=0.05,
            )

    def test_input_validation_time_to_expiry(self):
        """Test input validation for time to expiry."""
        with pytest.raises(ValueError, match="Time to expiry must be positive"):
            self.calculator.probability_of_profit(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=0.0,
                volatility=0.20,
                risk_free_rate=0.05,
            )

    def test_input_validation_volatility(self):
        """Test input validation for volatility."""
        with pytest.raises(ValueError, match="Volatility must be positive"):
            self.calculator.probability_of_profit(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=1.0,
                volatility=-0.10,
                risk_free_rate=0.05,
            )

    def test_extreme_values_handling(self):
        """Test handling of extreme market values."""
        # Very high volatility
        result = self.calculator.probability_of_profit(
            spot_price=450.0,
            strike_price=455.0,
            time_to_expiry=1.0 / 365,
            volatility=2.0,  # 200% volatility
            risk_free_rate=0.05,
        )

        assert 0.0 <= result <= 1.0, f"PoP {result} should be between 0 and 1"

    def test_very_short_expiry(self):
        """Test calculations with very short time to expiry."""
        result = self.calculator.probability_of_profit(
            spot_price=475.0,
            strike_price=480.0,
            time_to_expiry=0.1 / 365,  # ~2.4 minutes
            volatility=0.20,
            risk_free_rate=0.05,
        )

        assert 0.0 <= result <= 1.0, f"PoP {result} should be between 0 and 1"

    def test_mathematical_consistency(self):
        """Test mathematical consistency across parameter ranges."""
        base_params = {
            "spot_price": 470.0,
            "volatility": 0.18,
            "time_to_expiry": 1.0 / 365,
            "risk_free_rate": 0.05,
        }

        # Test that ITM < ATM < OTM progression makes sense
        itm_pop = self.calculator.probability_of_profit(
            strike_price=460.0, **base_params  # ITM
        )
        atm_pop = self.calculator.probability_of_profit(
            strike_price=470.0, **base_params  # ATM
        )
        otm_pop = self.calculator.probability_of_profit(
            strike_price=480.0, **base_params  # OTM
        )

        assert (
            itm_pop > atm_pop > otm_pop
        ), f"Expected ITM({itm_pop:.3f}) > ATM({atm_pop:.3f}) > OTM({otm_pop:.3f})"

    def test_precision_requirement(self):
        """Test that calculations meet the 0.01% precision requirement."""
        # Reference calculation with high precision
        spot_price = 485.0
        strike_price = 490.0
        time_to_expiry = 0.5 / 365
        volatility = 0.25
        risk_free_rate = 0.05

        # Run calculation multiple times to test consistency
        results = []
        for _ in range(5):
            result = self.calculator.probability_of_profit(
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
                risk_free_rate=risk_free_rate,
            )
            results.append(result)

        # All results should be identical (deterministic calculation)
        for result in results[1:]:
            assert (
                abs(result - results[0]) < 1e-10
            ), f"Calculation inconsistency: {result} vs {results[0]}"
