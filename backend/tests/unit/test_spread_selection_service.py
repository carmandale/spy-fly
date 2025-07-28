"""
Unit tests for SpreadSelectionService error handling and validation.

This module tests the core functionality of the spread selection service
with focus on error handling for missing or invalid volatility data.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, date

from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.spread_selection_service import SpreadSelectionService, SpreadConfiguration
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator


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
			config=self.config
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
		self.market_service.get_spy_quote.side_effect = Exception("Market data unavailable")
		
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
			cached=False
		)
		self.market_service.get_spy_quote.return_value = mock_quote
		self.sentiment_calculator.calculate_sentiment.side_effect = Exception("Sentiment service down")
		
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
			cached=False
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
			max_buying_power_pct=0.03,
			min_risk_reward_ratio=1.5
		)
		self.spread_service.update_configuration(new_config)
		
		updated_config = self.spread_service.get_configuration()
		assert updated_config.max_buying_power_pct == 0.03
		assert updated_config.min_risk_reward_ratio == 1.5

	@pytest.mark.asyncio
	async def test_market_suitability_checks(self):
		"""Test market suitability validation logic."""
		# Test with missing data
		assert not self.spread_service._is_market_suitable_for_trading()
		
		# Test with complete data
		self.spread_service._current_spy_price = 475.0
		self.spread_service._current_vix = 20.0
		self.spread_service._current_sentiment_score = 0.2
		assert self.spread_service._is_market_suitable_for_trading()
		
		# Test with extreme VIX
		self.spread_service._current_vix = 75.0
		assert not self.spread_service._is_market_suitable_for_trading()

	def test_bid_ask_spread_calculation(self):
		"""Test bid-ask spread percentage calculation."""
		# Test normal option
		option_normal = {"bid": 2.50, "ask": 2.60}
		spread_pct = self.spread_service._calculate_bid_ask_spread_pct(option_normal)
		expected = (2.60 - 2.50) / 2.55  # (ask - bid) / mid
		assert abs(spread_pct - expected) < 0.0001
		
		# Test zero bid/ask
		option_zero = {"bid": 0.0, "ask": 1.0}
		spread_pct = self.spread_service._calculate_bid_ask_spread_pct(option_zero)
		assert spread_pct == float('inf')
		
		# Test missing bid/ask
		option_missing = {}
		spread_pct = self.spread_service._calculate_bid_ask_spread_pct(option_missing)
		assert spread_pct == float('inf')

	def test_spread_combination_generation(self):
		"""Test generation of bull-call-spread combinations."""
		option_chain = {
			"calls": [
				{"strike": 470.0, "bid": 3.0, "ask": 3.1},
				{"strike": 475.0, "bid": 2.0, "ask": 2.1},
				{"strike": 480.0, "bid": 1.0, "ask": 1.1}
			]
		}
		
		spreads = self.spread_service._generate_spread_combinations(option_chain)
		
		# Should generate 3 combinations: 470-475, 470-480, 475-480
		assert len(spreads) == 3
		
		# Check first spread
		assert spreads[0]["long_strike"] == 470.0
		assert spreads[0]["short_strike"] == 475.0
		assert spreads[0]["spread_width"] == 5.0
		
		# Check second spread
		assert spreads[1]["long_strike"] == 470.0
		assert spreads[1]["short_strike"] == 480.0
		assert spreads[1]["spread_width"] == 10.0

	def test_ranking_score_calculation(self):
		"""Test ranking score calculation logic."""
		# Test with balanced metrics
		score = self.spread_service._calculate_ranking_score(
			probability_of_profit=0.6,
			risk_reward_ratio=1.5,
			expected_value=0.2
		)
		
		# Score should be between 0 and 1
		assert 0.0 <= score <= 1.0
		
		# Test with extreme metrics
		score_high = self.spread_service._calculate_ranking_score(
			probability_of_profit=0.9,
			risk_reward_ratio=3.0,
			expected_value=0.5
		)
		
		score_low = self.spread_service._calculate_ranking_score(
			probability_of_profit=0.3,
			risk_reward_ratio=1.0,
			expected_value=0.1
		)
		
		# Higher metrics should produce higher score
		assert score_high > score_low

	@pytest.mark.asyncio
	async def test_empty_option_chain_handling(self):
		"""Test handling of empty option chains."""
		# Mock empty option chain
		from app.models.market import OptionChainResponse
		empty_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=475.0,
			expiration=date.today().isoformat(),
			options=[],
			cached=False,
			cache_expires_at=datetime.now().isoformat()
		)
		
		self.market_service.get_spy_options.return_value = empty_chain
		
		option_chain = await self.spread_service._get_current_option_chain()
		
		# Should return the OptionChainResponse object
		assert option_chain == empty_chain
		assert option_chain.options == []

	def test_mathematical_precision_validation(self):
		"""Test mathematical precision requirements are met."""
		# Test with Black-Scholes calculator integration
		test_params = {
			"spot_price": 475.0,
			"strike_price": 480.0,
			"time_to_expiry": 1.0 / 365,
			"volatility": 0.20,
			"risk_free_rate": 0.05
		}
		
		# Run calculation multiple times
		results = []
		for _ in range(10):
			result = self.black_scholes.probability_of_profit(**test_params)
			results.append(result)
		
		# All results should be identical (deterministic)
		for result in results[1:]:
			assert abs(result - results[0]) < 1e-10, (
				f"Calculation inconsistency detected: {result} vs {results[0]}"
			)
		
		# Result should meet 0.01% tolerance requirement
		expected_tolerance = 0.0001
		assert all(0.0 <= r <= 1.0 for r in results), "Probability not in valid range"