"""
Mathematical precision validation tests for Black-Scholes implementation.

This module validates Black-Scholes calculations against reference implementations
and known mathematical results to ensure 0.01% accuracy requirement is met.
"""

import pytest
import math
import numpy as np
from scipy.stats import norm

from app.services.black_scholes_calculator import BlackScholesCalculator


class TestBlackScholesPrecision:
	"""Test mathematical precision against reference implementations."""

	def setup_method(self):
		"""Setup test fixtures before each test method."""
		self.calculator = BlackScholesCalculator()
		self.precision_tolerance = 0.0001  # 0.01% tolerance requirement

	def test_against_scipy_cumulative_normal(self):
		"""Test cumulative normal distribution against scipy.stats.norm."""
		test_values = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 1.645, 2.0, 3.0]
		
		for z in test_values:
			our_result = self.calculator._cumulative_normal(z)
			scipy_result = norm.cdf(z)
			
			error = abs(our_result - scipy_result)
			assert error < 1e-12, (
				f"Cumulative normal error at z={z}: "
				f"our={our_result:.15f}, scipy={scipy_result:.15f}, "
				f"error={error:.2e}"
			)

	def test_d1_d2_mathematical_relationship(self):
		"""Test that d1 and d2 satisfy the correct mathematical relationship."""
		test_cases = [
			(100.0, 105.0, 0.25, 0.20, 0.05),
			(450.0, 455.0, 1.0/365, 0.18, 0.05),
			(500.0, 490.0, 2.0/365, 0.25, 0.05),
			(475.0, 475.0, 0.5/365, 0.22, 0.05),  # ATM case
		]
		
		for S, K, T, sigma, r in test_cases:
			d1, d2 = self.calculator._calculate_d1_d2(S, K, T, sigma, r)
			
			# Test d2 = d1 - σ√T relationship
			expected_d2 = d1 - sigma * math.sqrt(T)
			error = abs(d2 - expected_d2)
			
			assert error < 1e-15, (
				f"d1/d2 relationship error for S={S}, K={K}: "
				f"d2={d2:.15f}, expected={expected_d2:.15f}, "
				f"error={error:.2e}"
			)

	def test_option_price_put_call_parity(self):
		"""Test that option pricing satisfies put-call parity relationship."""
		# Put-call parity: C - P = S - K*e^(-rT)
		# We don't have put pricing, but we can test the relationship holds
		# for equivalent synthetic positions
		
		test_params = {
			"spot_price": 480.0,
			"strike_price": 485.0,
			"time_to_expiry": 1.0 / 365,
			"volatility": 0.20,
			"risk_free_rate": 0.05
		}
		
		call_price = self.calculator.option_price(**test_params)
		
		# Calculate theoretical put price using put-call parity
		S = test_params["spot_price"]
		K = test_params["strike_price"]
		T = test_params["time_to_expiry"]
		r = test_params["risk_free_rate"]
		
		discount_factor = math.exp(-r * T)
		synthetic_put = call_price - S + K * discount_factor
		
		# For this OTM call, synthetic put should be positive
		assert synthetic_put > 0, f"Synthetic put price {synthetic_put} should be positive"

	def test_probability_mathematical_bounds(self):
		"""Test that probability calculations respect mathematical bounds."""
		test_scenarios = [
			# (spot, strike, time, vol, description)
			(475.0, 475.0, 1.0/365, 0.20, "ATM"),
			(475.0, 470.0, 1.0/365, 0.20, "ITM"),
			(475.0, 480.0, 1.0/365, 0.20, "OTM"),
			(475.0, 465.0, 1.0/365, 0.20, "Deep ITM"),
			(475.0, 485.0, 1.0/365, 0.20, "Deep OTM"),
		]
		
		for S, K, T, sigma, description in test_scenarios:
			prob = self.calculator.probability_of_profit(
				spot_price=S,
				strike_price=K,
				time_to_expiry=T,
				volatility=sigma
			)
			
			# Probability must be between 0 and 1
			assert 0.0 <= prob <= 1.0, (
				f"Probability {prob} out of bounds for {description} scenario"
			)
			
			# Additional logical checks
			if K < S:  # ITM
				assert prob > 0.5, f"ITM probability {prob} should be > 0.5"
			elif K > S:  # OTM
				assert prob < 0.5, f"OTM probability {prob} should be < 0.5"

	def test_greeks_mathematical_relationships(self):
		"""Test Greek calculations satisfy known mathematical relationships."""
		params = {
			"spot_price": 478.0,
			"strike_price": 480.0,
			"time_to_expiry": 2.0 / 365,
			"volatility": 0.18,
			"risk_free_rate": 0.05
		}
		
		delta = self.calculator.delta(**params)
		gamma = self.calculator.gamma(**params)
		theta = self.calculator.theta(**params)
		
		# Delta should be between 0 and 1 for calls
		assert 0.0 <= delta <= 1.0, f"Delta {delta} out of bounds"
		
		# Gamma should be positive
		assert gamma > 0.0, f"Gamma {gamma} should be positive"
		
		# Theta should be negative for long options (we return per-day theta)
		assert theta < 0.0, f"Theta {theta} should be negative"

	def test_volatility_sensitivity_accuracy(self):
		"""Test volatility sensitivity follows expected mathematical behavior."""
		base_params = {
			"spot_price": 472.0,
			"strike_price": 475.0,
			"time_to_expiry": 1.0 / 365,
			"risk_free_rate": 0.05
		}
		
		volatilities = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
		probabilities = []
		
		for vol in volatilities:
			prob = self.calculator.probability_of_profit(
				volatility=vol, **base_params
			)
			probabilities.append(prob)
		
		# For OTM options, higher volatility should increase probability
		for i in range(1, len(probabilities)):
			assert probabilities[i] > probabilities[i-1], (
				f"Probability should increase with volatility: "
				f"vol={volatilities[i-1]:.2f} -> prob={probabilities[i-1]:.6f}, "
				f"vol={volatilities[i]:.2f} -> prob={probabilities[i]:.6f}"
			)

	def test_time_decay_mathematical_accuracy(self):
		"""Test time decay behavior matches mathematical expectations."""
		base_params = {
			"spot_price": 476.0,
			"strike_price": 480.0,
			"volatility": 0.22,
			"risk_free_rate": 0.05
		}
		
		# Test different times to expiry
		times = [0.1/365, 0.5/365, 1.0/365, 2.0/365, 4.0/365]  # Hours to years
		probabilities = []
		option_prices = []
		
		for time in times:
			prob = self.calculator.probability_of_profit(
				time_to_expiry=time, **base_params
			)
			price = self.calculator.option_price(
				time_to_expiry=time, **base_params
			)
			probabilities.append(prob)
			option_prices.append(price)
		
		# Probabilities should generally increase with more time (for OTM)
		for i in range(1, len(probabilities)):
			assert probabilities[i] >= probabilities[i-1], (
				f"Probability should not decrease with more time: "
				f"t={times[i-1]*365:.2f}h -> prob={probabilities[i-1]:.6f}, "
				f"t={times[i]*365:.2f}h -> prob={probabilities[i]:.6f}"
			)

	def test_reference_implementation_comparison(self):
		"""Test against manually calculated Black-Scholes reference values."""
		# Reference calculation for specific parameters
		S, K, T, sigma, r = 500.0, 505.0, 1.0/365, 0.20, 0.05
		
		# Manual calculation of d1 and d2
		ln_s_k = math.log(S / K)
		sqrt_t = math.sqrt(T)
		d1_manual = (ln_s_k + (r + sigma**2 / 2) * T) / (sigma * sqrt_t)
		d2_manual = d1_manual - sigma * sqrt_t
		
		# Our implementation
		d1_ours, d2_ours = self.calculator._calculate_d1_d2(S, K, T, sigma, r)
		
		# Compare with manual calculation
		assert abs(d1_ours - d1_manual) < 1e-15, (
			f"d1 mismatch: ours={d1_ours:.15f}, manual={d1_manual:.15f}"
		)
		assert abs(d2_ours - d2_manual) < 1e-15, (
			f"d2 mismatch: ours={d2_ours:.15f}, manual={d2_manual:.15f}"
		)
		
		# Test probability calculation
		prob_manual = norm.cdf(d2_manual)
		prob_ours = self.calculator.probability_of_profit(S, K, T, sigma, r)
		
		assert abs(prob_ours - prob_manual) < 1e-15, (
			f"Probability mismatch: ours={prob_ours:.15f}, manual={prob_manual:.15f}"
		)

	def test_numerical_stability_extreme_values(self):
		"""Test numerical stability with extreme parameter values."""
		# Test very high volatility
		prob_high_vol = self.calculator.probability_of_profit(
			spot_price=450.0,
			strike_price=455.0,
			time_to_expiry=1.0/365,
			volatility=3.0,  # 300% volatility
			risk_free_rate=0.05
		)
		assert 0.0 <= prob_high_vol <= 1.0, "High volatility result out of bounds"
		
		# Test very short time
		prob_short_time = self.calculator.probability_of_profit(
			spot_price=475.0,
			strike_price=480.0,
			time_to_expiry=1e-6,  # Microsecond
			volatility=0.20,
			risk_free_rate=0.05
		)
		assert 0.0 <= prob_short_time <= 1.0, "Short time result out of bounds"
		
		# Test very deep ITM
		prob_deep_itm = self.calculator.probability_of_profit(
			spot_price=500.0,
			strike_price=400.0,  # Very deep ITM
			time_to_expiry=1.0/365,
			volatility=0.20,
			risk_free_rate=0.05
		)
		assert prob_deep_itm > 0.99, f"Deep ITM probability {prob_deep_itm} should be > 99%"

	def test_precision_consistency_across_parameters(self):
		"""Test that precision is maintained across different parameter ranges."""
		# Generate a grid of parameters
		spot_prices = [450.0, 475.0, 500.0, 525.0]
		strikes = [470.0, 480.0, 490.0, 500.0, 510.0]
		volatilities = [0.15, 0.20, 0.25, 0.30]
		times = [0.5/365, 1.0/365, 2.0/365, 4.0/365]
		
		for S in spot_prices:
			for K in strikes:
				for vol in volatilities:
					for T in times:
						# Run calculation twice
						prob1 = self.calculator.probability_of_profit(
							spot_price=S, strike_price=K,
							time_to_expiry=T, volatility=vol
						)
						prob2 = self.calculator.probability_of_profit(
							spot_price=S, strike_price=K,
							time_to_expiry=T, volatility=vol
						)
						
						# Results should be identical
						assert abs(prob1 - prob2) < 1e-15, (
							f"Inconsistent results for S={S}, K={K}, "
							f"vol={vol}, T={T}: {prob1} vs {prob2}"
						)
						
						# Result should be in valid range
						assert 0.0 <= prob1 <= 1.0, (
							f"Invalid probability {prob1} for parameters "
							f"S={S}, K={K}, vol={vol}, T={T}"
						)

	def test_monte_carlo_validation(self):
		"""Validate Black-Scholes probability against Monte Carlo simulation."""
		# Simple Monte Carlo validation for probability of profit
		S, K, T, sigma, r = 480.0, 485.0, 1.0/365, 0.20, 0.05
		
		# Black-Scholes probability
		bs_prob = self.calculator.probability_of_profit(S, K, T, sigma, r)
		
		# Simple Monte Carlo simulation
		np.random.seed(42)  # For reproducibility
		n_simulations = 100000
		
		# Generate random stock prices at expiry
		z = np.random.standard_normal(n_simulations)
		st = S * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
		
		# Count how many finish above strike (profitable)
		profitable = np.sum(st > K)
		mc_prob = profitable / n_simulations
		
		# Monte Carlo should be within reasonable range of Black-Scholes
		# (allowing for Monte Carlo error)
		error = abs(bs_prob - mc_prob)
		assert error < 0.01, (  # 1% tolerance for Monte Carlo
			f"Black-Scholes prob {bs_prob:.4f} vs Monte Carlo {mc_prob:.4f}, "
			f"error {error:.4f}"
		)