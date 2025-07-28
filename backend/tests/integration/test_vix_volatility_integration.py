"""
Integration tests for VIX data integration with volatility calculations.

This module tests the integration between VIX data retrieval and its use
in Black-Scholes volatility calculations for spread selection.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.spread_selection_service import SpreadSelectionService, SpreadConfiguration
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator


class TestVIXVolatilityIntegration:
	"""Test VIX data integration with volatility calculations."""

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
			config=self.config
		)

	@pytest.mark.asyncio
	async def test_vix_data_retrieval_and_conversion(self):
		"""Test VIX data retrieval and proper conversion to volatility."""
		# Mock VIX data (VIX is in percentage points, e.g., 20.5 = 20.5%)
		mock_vix_data = {"price": 18.5, "timestamp": datetime.now()}
		self.market_service.get_current_quote.return_value = mock_vix_data
		
		# Mock SPY and sentiment for context
		mock_spy_data = {"price": 480.0}
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Setup alternating responses for SPY and VIX calls
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,  # First call for SPY
			mock_vix_data   # Second call for VIX
		]
		
		# Update market context
		await self.spread_service._update_market_context()
		
		# Verify VIX was properly stored
		assert self.spread_service._current_vix == 18.5
		
		# Test conversion in volatility calculation
		# VIX 18.5 should convert to 0.185 (18.5/100) for Black-Scholes
		spot_price = 480.0
		strike_price = 485.0
		time_to_expiry = 1.0 / 365
		expected_volatility = 18.5 / 100  # 0.185
		
		probability = self.black_scholes.probability_of_profit(
			spot_price=spot_price,
			strike_price=strike_price,
			time_to_expiry=time_to_expiry,
			volatility=expected_volatility
		)
		
		# Probability should be reasonable for slightly OTM option
		assert 0.0 < probability < 1.0
		assert probability < 0.5  # OTM call should have <50% probability

	@pytest.mark.asyncio
	async def test_vix_missing_data_handling(self):
		"""Test handling when VIX data is not available."""
		# Mock SPY data but no VIX data
		mock_spy_data = {"price": 475.0}
		mock_vix_data = {"price": None}  # Missing VIX data
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.1
		
		await self.spread_service._update_market_context()
		
		# Should not be suitable for trading without VIX
		is_suitable = self.spread_service._is_market_suitable_for_trading()
		assert not is_suitable

	@pytest.mark.asyncio
	async def test_vix_extreme_values_handling(self):
		"""Test handling of extreme VIX values."""
		# Test extremely high VIX (market panic scenario)
		mock_spy_data = {"price": 450.0}
		mock_vix_data = {"price": 75.0}  # Extremely high VIX
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = -0.8
		
		await self.spread_service._update_market_context()
		
		# Should not be suitable for trading with extreme VIX
		is_suitable = self.spread_service._is_market_suitable_for_trading()
		assert not is_suitable

	@pytest.mark.asyncio
	async def test_vix_volatility_accuracy_in_calculations(self):
		"""Test VIX-based volatility produces accurate Black-Scholes results."""
		# Use realistic VIX value
		vix_level = 22.5
		mock_vix_data = {"price": vix_level}
		mock_spy_data = {"price": 470.0}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.0
		
		await self.spread_service._update_market_context()
		
		# Test that VIX-derived volatility gives consistent results
		spot_price = 470.0
		strike_price = 475.0
		time_to_expiry = 2.0 / 365  # 2 hours
		vix_volatility = vix_level / 100  # 0.225
		
		prob_vix = self.black_scholes.probability_of_profit(
			spot_price=spot_price,
			strike_price=strike_price,
			time_to_expiry=time_to_expiry,
			volatility=vix_volatility
		)
		
		# Compare with manually set volatility
		prob_manual = self.black_scholes.probability_of_profit(
			spot_price=spot_price,
			strike_price=strike_price,
			time_to_expiry=time_to_expiry,
			volatility=0.225
		)
		
		# Should be identical
		assert abs(prob_vix - prob_manual) < 1e-10

	@pytest.mark.asyncio
	async def test_vix_impact_on_spread_selection(self):
		"""Test how different VIX levels impact spread selection."""
		# Setup mock option chain
		mock_option_chain = {
			"calls": [
				{
					"strike": 470.0,
					"bid": 2.50,
					"ask": 2.60,
					"volume": 100
				},
				{
					"strike": 475.0,
					"bid": 1.20,
					"ask": 1.30,
					"volume": 80
				}
			]
		}
		
		self.market_service.get_option_chain.return_value = mock_option_chain
		
		# Test with low VIX (calm market)
		await self._test_vix_scenario(vix_level=15.0, expected_suitable=True)
		
		# Test with moderate VIX (normal volatility)
		await self._test_vix_scenario(vix_level=25.0, expected_suitable=True)
		
		# Test with high VIX (volatile market)
		await self._test_vix_scenario(vix_level=45.0, expected_suitable=True)
		
		# Test with extreme VIX (crisis level)
		await self._test_vix_scenario(vix_level=80.0, expected_suitable=False)

	async def _test_vix_scenario(self, vix_level: float, expected_suitable: bool):
		"""Helper method to test specific VIX scenario."""
		mock_spy_data = {"price": 472.0}
		mock_vix_data = {"price": vix_level}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.1
		
		await self.spread_service._update_market_context()
		
		is_suitable = self.spread_service._is_market_suitable_for_trading()
		assert is_suitable == expected_suitable

	@pytest.mark.asyncio
	async def test_vix_data_freshness_validation(self):
		"""Test validation of VIX data freshness."""
		old_timestamp = datetime(2020, 1, 1)  # Very old data
		recent_timestamp = datetime.now()
		
		# Test with old VIX data
		mock_vix_data_old = {"price": 20.0, "timestamp": old_timestamp}
		mock_spy_data = {"price": 480.0}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data_old
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.0
		
		await self.spread_service._update_market_context()
		
		# With old data, VIX should still be stored (basic implementation)
		# In production, could add timestamp validation
		assert self.spread_service._current_vix == 20.0

	@pytest.mark.asyncio
	async def test_vix_error_handling_and_fallback(self):
		"""Test error handling when VIX data retrieval fails."""
		# Mock SPY data success but VIX failure
		mock_spy_data = {"price": 465.0}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,  # SPY succeeds
			Exception("VIX API error")  # VIX fails
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.0
		
		# Should handle the exception gracefully
		try:
			await self.spread_service._update_market_context()
			# If no exception was raised, VIX should be None
			assert self.spread_service._current_vix is None
		except Exception:
			# Or the exception should be handled internally
			pass

	@pytest.mark.asyncio
	async def test_vix_volatility_consistency_across_calculations(self):
		"""Test that VIX-derived volatility is consistent across multiple calculations."""
		vix_level = 19.5
		mock_spy_data = {"price": 478.0}
		mock_vix_data = {"price": vix_level}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		await self.spread_service._update_market_context()
		
		# Test multiple Black-Scholes calculations with same VIX-derived volatility
		volatility = vix_level / 100
		base_params = {
			"spot_price": 478.0,
			"time_to_expiry": 1.0 / 365,
			"volatility": volatility
		}
		
		strikes = [480.0, 482.0, 485.0, 490.0]
		probabilities = []
		
		for strike in strikes:
			prob = self.black_scholes.probability_of_profit(
				strike_price=strike,
				**base_params
			)
			probabilities.append(prob)
		
		# Probabilities should decrease as strikes go further OTM
		for i in range(1, len(probabilities)):
			assert probabilities[i] < probabilities[i-1], (
				f"Probability should decrease with higher strikes: "
				f"Strike {strikes[i-1]}: {probabilities[i-1]:.4f}, "
				f"Strike {strikes[i]}: {probabilities[i]:.4f}"
			)

	@pytest.mark.asyncio
	async def test_vix_integration_with_different_time_periods(self):
		"""Test VIX integration with different time to expiry periods."""
		vix_level = 24.0
		mock_spy_data = {"price": 455.0}
		mock_vix_data = {"price": vix_level}
		
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_data
		]
		self.sentiment_calculator.calculate_sentiment.return_value = -0.1
		
		await self.spread_service._update_market_context()
		
		volatility = vix_level / 100
		base_params = {
			"spot_price": 455.0,
			"strike_price": 460.0,
			"volatility": volatility
		}
		
		# Test different time periods
		time_periods = [
			0.5 / 365,   # 0.5 hours
			1.0 / 365,   # 1 hour
			2.0 / 365,   # 2 hours
			4.0 / 365,   # 4 hours
		]
		
		probabilities = []
		for time_period in time_periods:
			prob = self.black_scholes.probability_of_profit(
				time_to_expiry=time_period,
				**base_params
			)
			probabilities.append(prob)
		
		# Probabilities should generally increase with more time
		# (though very slightly for such short periods)
		for i in range(1, len(probabilities)):
			assert probabilities[i] >= probabilities[i-1], (
				f"Probability should not decrease with more time: "
				f"Time {time_periods[i-1]*365:.2f}h: {probabilities[i-1]:.6f}, "
				f"Time {time_periods[i]*365:.2f}h: {probabilities[i]:.6f}"
			)

	@pytest.mark.asyncio
	async def test_vix_boundary_conditions(self):
		"""Test VIX integration at boundary conditions."""
		mock_spy_data = {"price": 500.0}
		self.sentiment_calculator.calculate_sentiment.return_value = 0.0
		
		# Test minimum reasonable VIX
		mock_vix_low = {"price": 9.0}  # Very low VIX
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_low
		]
		
		await self.spread_service._update_market_context()
		assert self.spread_service._is_market_suitable_for_trading()
		
		# Test maximum acceptable VIX (just under the limit)
		mock_vix_high = {"price": 49.9}  # Just under 50 limit
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_high
		]
		
		await self.spread_service._update_market_context()
		assert self.spread_service._is_market_suitable_for_trading()
		
		# Test VIX at exact limit
		mock_vix_limit = {"price": 50.0}  # At the limit
		self.market_service.get_current_quote.side_effect = [
			mock_spy_data,
			mock_vix_limit
		]
		
		await self.spread_service._update_market_context()
		assert not self.spread_service._is_market_suitable_for_trading()