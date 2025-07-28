"""
Integration tests for the complete spread selection pipeline.

Tests the integration of OptionsChainProcessor, SpreadGenerator, and
SpreadSelectionService with real-world scenarios and performance requirements.
"""

import pytest
import asyncio
import time
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock
import pandas as pd
import numpy as np

from app.services.spread_selection_service import (
	SpreadSelectionService,
	SpreadConfiguration,
	SpreadRecommendation
)
from app.services.options_chain_processor import OptionsChainProcessor
from app.services.spread_generator import SpreadGenerator
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator
from app.models.market import OptionContract, OptionChainResponse, QuoteResponse


class TestSpreadSelectionIntegration:
	"""Test the complete spread selection pipeline integration."""

	def setup_method(self):
		"""Setup test fixtures before each test method."""
		self.black_scholes = BlackScholesCalculator()
		self.market_service = AsyncMock(spec=MarketDataService)
		self.sentiment_calculator = AsyncMock(spec=SentimentCalculator)
		self.options_processor = OptionsChainProcessor()
		self.spread_generator = SpreadGenerator()
		
		self.config = SpreadConfiguration(
			max_buying_power_pct=0.05,
			min_risk_reward_ratio=1.0,
			min_probability_of_profit=0.30,
			max_bid_ask_spread_pct=5.0,
			min_volume=10,
			min_time_to_expiry_hours=0.5,
			max_time_to_expiry_hours=8.0
		)
		
		self.spread_service = SpreadSelectionService(
			black_scholes_calculator=self.black_scholes,
			market_service=self.market_service,
			sentiment_calculator=self.sentiment_calculator,
			config=self.config
		)
		
		# Inject our enhanced processors
		self.spread_service.options_processor = self.options_processor
		self.spread_service.spread_generator = self.spread_generator

	def create_realistic_option_chain(self, n_strikes=50, spot_price=475.0):
		"""Create a realistic option chain for testing."""
		strikes = np.arange(spot_price - 25, spot_price + 25, 1.0)[:n_strikes]
		options = []
		
		for strike in strikes:
			# Realistic pricing based on moneyness
			moneyness = strike - spot_price
			if moneyness <= 0:  # ITM
				base_price = abs(moneyness) + 1.0
			else:  # OTM
				base_price = max(0.05, 2.0 * np.exp(-moneyness / 5))
			
			# Add some bid-ask spread
			spread = min(0.10, base_price * 0.03)
			bid = base_price - spread / 2
			ask = base_price + spread / 2
			
			# Volume decreases as we go further OTM/ITM
			volume = int(1000 * np.exp(-abs(moneyness) / 10))
			open_interest = int(volume * 2.5)
			
			option = OptionContract(
				symbol=f"SPY{date.today().strftime('%y%m%d')}C{int(strike*1000):08d}",
				type="call",
				strike=strike,
				expiration=date.today().isoformat(),
				bid=round(bid, 2),
				ask=round(ask, 2),
				mid=round((bid + ask) / 2, 2),
				last=round((bid + ask) / 2, 2),
				volume=volume,
				open_interest=open_interest
			)
			options.append(option)
			
		return options

	@pytest.mark.asyncio
	async def test_full_pipeline_with_realistic_data(self):
		"""Test the complete pipeline with realistic option chain data."""
		# Mock market data
		spot_price = 475.0
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
		
		# Mock option chain
		options = self.create_realistic_option_chain(n_strikes=50, spot_price=spot_price)
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		self.market_service.get_spy_options.return_value = mock_chain
		
		# Mock sentiment
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Get recommendations
		recommendations = await self.spread_service.get_recommendations(
			account_size=10000.0,
			max_recommendations=5
		)
		
		# Verify we got recommendations
		assert len(recommendations) > 0
		assert len(recommendations) <= 5
		
		# Verify recommendation quality
		for rec in recommendations:
			assert isinstance(rec, SpreadRecommendation)
			assert rec.risk_reward_ratio >= 1.0
			assert rec.probability_of_profit >= 0.30
			assert rec.buying_power_used_pct <= 0.05
			assert rec.long_strike < rec.short_strike

	@pytest.mark.asyncio
	async def test_performance_with_large_option_chain(self):
		"""Test performance meets < 10 second requirement with large chain."""
		# Mock market data
		spot_price = 475.0
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
		
		# Create large option chain (200 strikes)
		options = self.create_realistic_option_chain(n_strikes=200, spot_price=spot_price)
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		self.market_service.get_spy_options.return_value = mock_chain
		
		# Mock sentiment
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Time the recommendation generation
		start_time = time.time()
		recommendations = await self.spread_service.get_recommendations(
			account_size=10000.0,
			max_recommendations=5
		)
		elapsed_time = time.time() - start_time
		
		# Verify performance
		assert elapsed_time < 10.0, f"Processing took {elapsed_time:.2f}s, expected < 10s"
		assert len(recommendations) > 0

	@pytest.mark.asyncio
	async def test_enhanced_spread_selection_methods(self):
		"""Test the enhanced spread selection with new processors."""
		# Create test option chain
		spot_price = 475.0
		options = self.create_realistic_option_chain(n_strikes=30, spot_price=spot_price)
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		
		# Process with OptionsChainProcessor
		options_df = self.options_processor.prepare_for_spread_generation(
			mock_chain,
			spot_price=spot_price,
			config={
				'filter_zero_dte': True,
				'validate_data': True,
				'min_volume': 10,
				'max_bid_ask_spread_pct': 5.0
			}
		)
		
		# Generate spreads with SpreadGenerator
		spreads = self.spread_generator.generate_filtered_spreads(
			options_df,
			config={
				'min_risk_reward_ratio': 1.0,
				'min_spread_width': 5.0,
				'max_spread_width': 15.0,
				'min_liquidity_score': 50.0,
				'use_vectorized': True
			}
		)
		
		# Verify spread quality
		assert len(spreads) > 0
		for spread in spreads[:5]:  # Check top 5
			assert spread.risk_reward_ratio >= 1.0
			assert 5.0 <= spread.spread_width <= 15.0
			assert spread.combined_liquidity_score >= 50.0

	@pytest.mark.asyncio
	async def test_edge_cases_no_valid_spreads(self):
		"""Test handling when no valid spreads meet criteria."""
		# Mock market data
		spot_price = 475.0
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
		
		# Create option chain with poor risk/reward
		options = []
		for i, strike in enumerate([470, 475, 480]):
			option = OptionContract(
				symbol=f"SPY{date.today().strftime('%y%m%d')}C{int(strike*1000):08d}",
				type="call",
				strike=strike,
				expiration=date.today().isoformat(),
				bid=5.0 - i * 0.1,  # Very close premiums
				ask=5.1 - i * 0.1,
				mid=5.05 - i * 0.1,
				last=5.05 - i * 0.1,
				volume=10,  # Low volume
				open_interest=5
			)
			options.append(option)
			
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		self.market_service.get_spy_options.return_value = mock_chain
		
		# Mock sentiment
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Get recommendations
		recommendations = await self.spread_service.get_recommendations(
			account_size=10000.0,
			max_recommendations=5
		)
		
		# Should return empty list when no valid spreads
		assert recommendations == []

	@pytest.mark.asyncio
	async def test_position_sizing_with_small_account(self):
		"""Test position sizing works correctly with small accounts."""
		# Mock market data
		spot_price = 475.0
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
		
		# Mock option chain
		options = self.create_realistic_option_chain(n_strikes=20, spot_price=spot_price)
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		self.market_service.get_spy_options.return_value = mock_chain
		
		# Mock sentiment
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Get recommendations with small account
		small_account = 2000.0  # $2,000 account
		recommendations = await self.spread_service.get_recommendations(
			account_size=small_account,
			max_recommendations=3
		)
		
		# Verify position sizing
		for rec in recommendations:
			assert rec.contracts_to_trade >= 1  # At least 1 contract
			assert rec.total_cost <= small_account * 0.05  # Within 5% limit
			assert rec.buying_power_used_pct <= 0.05

	@pytest.mark.asyncio 
	async def test_concurrent_recommendation_requests(self):
		"""Test handling of concurrent recommendation requests."""
		# Mock market data
		spot_price = 475.0
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
		
		# Mock option chain
		options = self.create_realistic_option_chain(n_strikes=30, spot_price=spot_price)
		mock_chain = OptionChainResponse(
			ticker="SPY",
			underlying_price=spot_price,
			expiration=date.today().isoformat(),
			options=options,
			cached=False
		)
		self.market_service.get_spy_options.return_value = mock_chain
		
		# Mock sentiment
		self.sentiment_calculator.calculate_sentiment.return_value = 0.2
		
		# Make concurrent requests
		tasks = []
		for account_size in [5000, 10000, 25000]:
			task = self.spread_service.get_recommendations(
				account_size=account_size,
				max_recommendations=3
			)
			tasks.append(task)
			
		# Wait for all to complete
		results = await asyncio.gather(*tasks)
		
		# Verify all requests succeeded
		assert len(results) == 3
		for i, recs in enumerate(results):
			assert len(recs) > 0
			# Verify position sizing matches account size
			account_size = [5000, 10000, 25000][i]
			for rec in recs:
				assert rec.total_cost <= account_size * 0.05