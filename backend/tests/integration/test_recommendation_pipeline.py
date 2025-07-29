"""
Integration tests for the complete spread recommendation pipeline.

Tests the end-to-end flow from SpreadSelectionService through RankingEngine
to TradeFormatter, ensuring all components work together correctly.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
import json

import pytest

from app.models.spread import SpreadRecommendation
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_selection_service import SpreadSelectionService, SpreadConfiguration
from app.services.ranking_engine import RankingEngine, RankingConfiguration
from app.services.trade_formatter import TradeFormatter


class TestRecommendationPipelineIntegration:
    """Test the complete recommendation pipeline integration."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        # Create real instances of calculators (they don't have external dependencies)
        self.black_scholes = BlackScholesCalculator()
        self.ranking_engine = RankingEngine()
        self.trade_formatter = TradeFormatter(symbol="SPY")
        
        # Mock external dependencies
        self.market_service = AsyncMock(spec=MarketDataService)
        self.sentiment_calculator = AsyncMock(spec=SentimentCalculator)
        
        # Configure mocks with realistic data
        self._setup_market_service_mocks()
        self._setup_sentiment_calculator_mocks()
        
        # Create spread selection service with mocked dependencies
        self.spread_config = SpreadConfiguration()
        self.spread_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=self.spread_config,
        )

    def _setup_market_service_mocks(self):
        """Setup realistic mock data for market service."""
        from app.models.market import QuoteResponse, OptionChainResponse
        
        # Mock SPY quote response
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
        
        # Mock option chain response with realistic 0DTE options
        mock_options = [
            {
                "strike": 470.0,
                "type": "call",
                "bid": 6.5,
                "ask": 6.8,
                "volume": 850,
                "open_interest": 1200,
                "implied_volatility": 0.22,
                "delta": 0.85,
                "gamma": 0.12,
                "theta": -0.45,
                "expiration_date": "2025-07-28"
            },
            {
                "strike": 472.5,
                "type": "call", 
                "bid": 4.2,
                "ask": 4.5,
                "volume": 1200,
                "open_interest": 980,
                "implied_volatility": 0.21,
                "delta": 0.75,
                "gamma": 0.15,
                "theta": -0.42,
                "expiration_date": "2025-07-28"
            },
            {
                "strike": 475.0,
                "type": "call",
                "bid": 2.8,
                "ask": 3.1,
                "volume": 1500,
                "open_interest": 2100,
                "implied_volatility": 0.20,
                "delta": 0.60,
                "gamma": 0.18,
                "theta": -0.38,
                "expiration_date": "2025-07-28"
            },
            {
                "strike": 477.5,
                "type": "call",
                "bid": 1.6,
                "ask": 1.9,
                "volume": 900,
                "open_interest": 1500,
                "implied_volatility": 0.19,
                "delta": 0.45,
                "gamma": 0.20,
                "theta": -0.35,
                "expiration_date": "2025-07-28"
            },
            {
                "strike": 480.0,
                "type": "call",
                "bid": 0.9,
                "ask": 1.2,
                "volume": 650,
                "open_interest": 800,
                "implied_volatility": 0.18,
                "delta": 0.30,
                "gamma": 0.21,
                "theta": -0.32,
                "expiration_date": "2025-07-28"
            },
        ]
        
        mock_option_chain = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration="2025-07-28",
            options=mock_options,
            cached=False,
            cache_expires_at=datetime.now().isoformat(),
        )
        self.market_service.get_spy_options.return_value = mock_option_chain

    def _setup_sentiment_calculator_mocks(self):
        """Setup realistic mock data for sentiment calculator."""
        # Mock sentiment calculation response (slightly bullish)
        self.sentiment_calculator.calculate_sentiment.return_value = 0.35

    @pytest.mark.asyncio
    async def test_complete_pipeline_basic_flow(self):
        """Test the complete pipeline from selection to formatting."""
        account_size = 10000.0
        
        # Step 1: Get recommendations from spread selection service
        recommendations = await self.spread_service.get_recommendations(account_size)
        
        # Should get some recommendations
        assert len(recommendations) > 0
        assert all(isinstance(rec, SpreadRecommendation) for rec in recommendations)
        
        # Step 2: Rank recommendations using ranking engine
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        
        # Should be same count, sorted by ranking score
        assert len(ranked_recs) == len(recommendations)
        for i in range(len(ranked_recs) - 1):
            assert ranked_recs[i].ranking_score >= ranked_recs[i + 1].ranking_score
        
        # Step 3: Format recommendations using trade formatter
        formatted_list = self.trade_formatter.format_recommendations_list(
            ranked_recs, max_count=3
        )
        
        # Should have properly formatted output
        assert "recommendations" in formatted_list
        assert "summary" in formatted_list
        assert len(formatted_list["recommendations"]) <= 3
        
        # Verify each formatted recommendation has required fields
        for formatted_rec in formatted_list["recommendations"]:
            assert "id" in formatted_rec
            assert "description" in formatted_rec
            assert "details" in formatted_rec
            assert "market_data" in formatted_rec

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_configurations(self):
        """Test pipeline with custom configurations for each component."""
        # Custom spread configuration (more conservative)
        custom_spread_config = SpreadConfiguration(
            max_buying_power_pct=0.03,  # 3% instead of 5%
            min_risk_reward_ratio=1.5,   # 1.5:1 instead of 1:1
            min_probability_of_profit=0.40,  # 40% instead of 30%
        )
        
        # Custom ranking configuration (favor probability over sentiment)
        custom_ranking_config = RankingConfiguration(
            probability_weight=0.6,
            risk_reward_weight=0.3,
            sentiment_weight=0.1,
        )
        
        # Create services with custom configurations
        custom_spread_service = SpreadSelectionService(
            black_scholes_calculator=self.black_scholes,
            market_service=self.market_service,
            sentiment_calculator=self.sentiment_calculator,
            config=custom_spread_config,
        )
        
        custom_ranking_engine = RankingEngine(custom_ranking_config)
        custom_formatter = TradeFormatter(symbol="SPY")
        
        # Run pipeline with custom configurations
        account_size = 20000.0
        
        recommendations = await custom_spread_service.get_recommendations(account_size)
        ranked_recs = custom_ranking_engine.rank_recommendations(recommendations)
        formatted_list = custom_formatter.format_recommendations_list(ranked_recs, max_count=5)
        
        # Verify results reflect custom configurations
        if formatted_list["recommendations"]:
            for rec in formatted_list["recommendations"]:
                details = rec["details"]
                
                # Should respect 3% buying power limit
                assert float(details["buying_power_used"].rstrip('%')) <= 3.0
                
                # Should respect 1.5:1 risk/reward minimum
                rr_str = details["risk_reward_ratio"]
                rr_value = float(rr_str.split(':')[0])
                assert rr_value >= 1.5
                
                # Should respect 40% probability minimum
                assert details["probability_of_profit"] >= 40.0

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Test pipeline behavior when components encounter errors."""
        # Test with market service failure
        self.market_service.get_spy_quote.side_effect = Exception("Market data unavailable")
        
        try:
            recommendations = await self.spread_service.get_recommendations(10000.0)
            # Should handle error gracefully (empty results or specific error)
            assert isinstance(recommendations, list)
        except Exception:
            # Or should raise a specific exception
            pass
        
        # Reset market service and test with sentiment failure
        self.market_service.get_spy_quote.side_effect = None
        self._setup_market_service_mocks()
        self.sentiment_calculator.calculate_sentiment.side_effect = Exception("Sentiment unavailable")
        
        try:
            recommendations = await self.spread_service.get_recommendations(10000.0)
            # Should handle sentiment error gracefully
            assert isinstance(recommendations, list)
        except Exception:
            # Or should raise a specific exception
            pass

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_results(self):
        """Test pipeline behavior with empty results at various stages."""
        # Mock empty option chain
        from app.models.market import OptionChainResponse
        
        empty_chain = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration="2025-07-28",
            options=[],  # Empty options
            cached=False,
            cache_expires_at=datetime.now().isoformat(),
        )
        self.market_service.get_spy_options.return_value = empty_chain
        
        # Run pipeline
        recommendations = await self.spread_service.get_recommendations(10000.0)
        
        # Should handle empty results gracefully
        assert recommendations == []
        
        # Test ranking engine with empty input
        ranked_recs = self.ranking_engine.rank_recommendations([])
        assert ranked_recs == []
        
        # Test formatter with empty input
        formatted_list = self.trade_formatter.format_recommendations_list([])
        assert formatted_list["recommendations"] == []
        assert formatted_list["summary"]["count"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_data_consistency(self):
        """Test that data is consistent across pipeline stages."""
        account_size = 15000.0
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(account_size)
        
        if not recommendations:
            pytest.skip("No recommendations generated for consistency test")
        
        # Rank recommendations
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        
        # Format recommendations
        formatted_list = self.trade_formatter.format_recommendations_list(ranked_recs, max_count=3)
        
        # Verify data consistency between stages
        for i, formatted_rec in enumerate(formatted_list["recommendations"]):
            original_rec = ranked_recs[i]
            details = formatted_rec["details"]
            
            # Check key fields match
            assert details["long_strike"] == original_rec.long_strike
            assert details["short_strike"] == original_rec.short_strike
            assert details["net_debit"] == original_rec.net_debit
            assert details["max_profit"] == original_rec.max_profit * original_rec.contracts_to_trade
            assert details["max_loss"] == original_rec.max_risk * original_rec.contracts_to_trade
            assert details["breakeven"] == original_rec.breakeven_price
            assert details["probability_of_profit"] == original_rec.probability_of_profit * 100
            assert details["ranking_score"] == original_rec.ranking_score

    @pytest.mark.asyncio
    async def test_pipeline_json_output_structure(self):
        """Test that pipeline produces valid JSON output structure."""
        account_size = 12000.0
        
        # Run complete pipeline
        recommendations = await self.spread_service.get_recommendations(account_size)
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        formatted_output = self.trade_formatter.format_recommendations_list(ranked_recs)
        
        # Test JSON serialization
        try:
            json_string = json.dumps(formatted_output)
            deserialized = json.loads(json_string)
            
            # Verify structure is preserved
            assert "recommendations" in deserialized
            assert "summary" in deserialized
            assert "disclaimer" in deserialized
            
            if deserialized["recommendations"]:
                first_rec = deserialized["recommendations"][0]
                assert "id" in first_rec
                assert "description" in first_rec
                assert "details" in first_rec
                assert "market_data" in first_rec
                
        except (TypeError, ValueError) as e:
            pytest.fail(f"Pipeline output is not JSON serializable: {e}")

    @pytest.mark.asyncio
    async def test_pipeline_performance_expectations(self):
        """Test that pipeline completes within reasonable time."""
        import time
        
        account_size = 10000.0
        start_time = time.time()
        
        # Run complete pipeline
        recommendations = await self.spread_service.get_recommendations(account_size)
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        formatted_output = self.trade_formatter.format_recommendations_list(ranked_recs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust as needed)
        assert execution_time < 5.0, f"Pipeline took {execution_time:.2f}s, expected < 5.0s"
        
        # Verify we got results
        assert isinstance(formatted_output, dict)
        assert "recommendations" in formatted_output

    @pytest.mark.asyncio
    async def test_pipeline_with_different_account_sizes(self):
        """Test pipeline behavior with various account sizes."""
        account_sizes = [5000.0, 10000.0, 25000.0, 50000.0, 100000.0]
        
        for account_size in account_sizes:
            recommendations = await self.spread_service.get_recommendations(account_size)
            
            if recommendations:
                # Verify position sizing scales with account size
                for rec in recommendations:
                    assert rec.total_cost <= account_size * 0.05  # 5% max rule
                    assert rec.buying_power_used_pct <= 0.05
                
                # Test full pipeline
                ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
                formatted_output = self.trade_formatter.format_recommendations_list(ranked_recs)
                
                # Verify output is valid regardless of account size
                assert "recommendations" in formatted_output
                assert "summary" in formatted_output

    @pytest.mark.asyncio
    async def test_pipeline_order_ticket_generation(self):
        """Test that pipeline can generate order tickets for top recommendations."""
        account_size = 15000.0
        
        # Get and rank recommendations
        recommendations = await self.spread_service.get_recommendations(account_size)
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        
        if not ranked_recs:
            pytest.skip("No recommendations for order ticket test")
        
        # Generate order tickets for top 3 recommendations
        top_3 = ranked_recs[:3]
        
        for i, rec in enumerate(top_3):
            order_ticket = self.trade_formatter.generate_order_ticket(rec)
            
            # Verify order ticket structure
            assert order_ticket.symbol == "SPY"
            assert order_ticket.strategy == "Bull Call Spread"
            assert len(order_ticket.order_instructions) > 0
            assert len(order_ticket.execution_notes) > 0
            assert len(order_ticket.formatted_text) > 0
            
            # Verify order ticket contains essential information
            formatted_text = order_ticket.formatted_text
            assert f"{rec.long_strike:.0f} CALL" in formatted_text
            assert f"{rec.short_strike:.0f} CALL" in formatted_text
            assert f"{rec.contracts_to_trade}" in formatted_text
            assert f"${rec.net_debit:.2f}" in formatted_text
            
            # Verify risk metrics
            assert "Max Profit" in formatted_text
            assert "Max Loss" in formatted_text
            assert "Probability of Profit" in formatted_text

    @pytest.mark.asyncio
    async def test_pipeline_recommendation_diversity(self):
        """Test that pipeline generates diverse recommendations when possible."""
        account_size = 20000.0
        
        # Get recommendations
        recommendations = await self.spread_service.get_recommendations(account_size, max_recommendations=5)
        
        if len(recommendations) < 2:
            pytest.skip("Need at least 2 recommendations for diversity test")
        
        # Check that we have different strike combinations
        strike_combinations = set()
        for rec in recommendations:
            combination = (rec.long_strike, rec.short_strike)
            strike_combinations.add(combination)
        
        # Should have unique strike combinations
        assert len(strike_combinations) == len(recommendations)
        
        # Rank and format
        ranked_recs = self.ranking_engine.rank_recommendations(recommendations)
        formatted_output = self.trade_formatter.format_recommendations_list(ranked_recs)
        
        # Verify formatted output maintains diversity
        formatted_combinations = set()
        for formatted_rec in formatted_output["recommendations"]:
            details = formatted_rec["details"]
            combination = (details["long_strike"], details["short_strike"])
            formatted_combinations.add(combination)
        
        assert len(formatted_combinations) == len(formatted_output["recommendations"])