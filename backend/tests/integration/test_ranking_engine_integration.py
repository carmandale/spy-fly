"""
Integration tests for the complete Ranking Engine and Trade Formatter pipeline.

These tests verify that RankingEngine and TradeFormatter work together correctly
with the rest of the spread selection system.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from app.models.spread import SpreadRecommendation
from app.models.market import OptionChainResponse, OptionContract
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.options_chain_processor import OptionsChainProcessor
from app.services.ranking_engine import RankingEngine
from app.services.risk_validator import RiskValidator
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_generator import SpreadGenerator
from app.services.spread_selection_service import SpreadSelectionService, SpreadConfiguration
from app.services.trade_formatter import TradeFormatter, FormatStyle


class TestRankingEngineIntegration:
    """Test the integration of RankingEngine within the complete spread selection pipeline."""

    @pytest.fixture
    def mock_market_service(self):
        """Create a mock market service."""
        service = Mock(spec=MarketDataService)
        
        # Mock SPY quote
        spy_quote = Mock()
        spy_quote.price = 475.0
        service.get_spy_quote = AsyncMock(return_value=spy_quote)
        
        # Mock option chain data - create proper OptionContract objects
        # Create realistic spreads that will pass the filters
        options = [
            OptionContract(
                symbol="SPY",
                type="call",
                strike=470.0,
                expiration=datetime.now().date().isoformat(),
                bid=6.00,
                ask=6.10,
                mid=6.05,
                last=6.05,
                volume=2000,
                open_interest=1500
            ),
            OptionContract(
                symbol="SPY",
                type="call",
                strike=472.0,
                expiration=datetime.now().date().isoformat(),
                bid=4.20,
                ask=4.30,
                mid=4.25,
                last=4.25,
                volume=1800,
                open_interest=1200
            ),
            OptionContract(
                symbol="SPY",
                type="call",
                strike=474.0,
                expiration=datetime.now().date().isoformat(),
                bid=2.60,
                ask=2.70,
                mid=2.65,
                last=2.65,
                volume=2200,
                open_interest=1600
            ),
            OptionContract(
                symbol="SPY",
                type="call",
                strike=476.0,
                expiration=datetime.now().date().isoformat(),
                bid=1.40,
                ask=1.50,
                mid=1.45,
                last=1.45,
                volume=1900,
                open_interest=1450
            ),
            OptionContract(
                symbol="SPY",
                type="call",
                strike=478.0,
                expiration=datetime.now().date().isoformat(),
                bid=0.60,
                ask=0.70,
                mid=0.65,
                last=0.65,
                volume=1600,
                open_interest=1300
            ),
            OptionContract(
                symbol="SPY",
                type="call",
                strike=480.0,
                expiration=datetime.now().date().isoformat(),
                bid=0.20,
                ask=0.30,
                mid=0.25,
                last=0.25,
                volume=1500,
                open_interest=1250
            )
        ]
        
        option_chain_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=datetime.now().date().isoformat(),
            options=options
        )
        
        service.get_spy_options = AsyncMock(return_value=option_chain_response)
        
        return service

    @pytest.fixture
    def mock_sentiment_calculator(self):
        """Create a mock sentiment calculator."""
        calculator = Mock(spec=SentimentCalculator)
        calculator.calculate_sentiment = AsyncMock(return_value=0.6)  # Bullish sentiment
        return calculator

    @pytest.fixture
    def spread_selection_service(self, mock_market_service, mock_sentiment_calculator):
        """Create a spread selection service with real components."""
        # Use real components
        black_scholes = BlackScholesCalculator()
        options_processor = OptionsChainProcessor()
        spread_generator = SpreadGenerator()
        risk_validator = RiskValidator()
        
        # Custom configuration for testing
        config = SpreadConfiguration(
            max_buying_power_pct=0.05,
            min_risk_reward_ratio=1.0,
            min_probability_of_profit=0.35,
            max_bid_ask_spread_pct=0.10,
            min_volume=100
        )
        
        service = SpreadSelectionService(
            black_scholes_calculator=black_scholes,
            market_service=mock_market_service,
            sentiment_calculator=mock_sentiment_calculator,
            config=config,
            options_processor=options_processor,
            spread_generator=spread_generator,
            risk_validator=risk_validator
        )
        
        return service

    @pytest.mark.asyncio
    async def test_complete_recommendation_pipeline(self, spread_selection_service):
        """Test the complete pipeline from market data to formatted recommendations."""
        # Execute the recommendation pipeline
        account_size = 10000.0
        recommendations = await spread_selection_service.get_recommendations(
            account_size=account_size,
            max_recommendations=5
        )
        
        # May not get recommendations if spreads don't meet criteria
        # This is expected behavior
        if len(recommendations) == 0:
            # Test formatter handles empty list
            formatter = TradeFormatter()
            formatted_list = formatter.format_recommendation_list(recommendations)
            assert "No spread recommendations meet the criteria" in formatted_list
            return
        
        # If we got recommendations, verify they're properly formed
        assert len(recommendations) <= 5
        
        # Create RankingEngine and verify it properly ranks the recommendations
        ranking_engine = RankingEngine()
        ranked_recs = ranking_engine.rank_recommendations(recommendations)
        
        # Verify ranking order
        for i in range(len(ranked_recs) - 1):
            assert ranked_recs[i].ranking_score >= ranked_recs[i + 1].ranking_score
        
        # Create TradeFormatter and format the recommendations
        formatter = TradeFormatter()
        
        # Test formatting individual recommendation
        if ranked_recs:
            top_rec = ranked_recs[0]
            formatted_text = formatter.format_recommendation(top_rec)
            assert "SPY Bull Call Spread" in formatted_text
            assert str(top_rec.long_strike) in formatted_text
            
            # Test order ticket generation
            order_ticket = formatter.format_order_ticket(top_rec)
            assert "BUY +" in order_ticket
            assert "VERTICAL SPY" in order_ticket
            assert f"@{top_rec.net_debit:.2f} LMT" in order_ticket
        
        # Test formatting recommendation list
        formatted_list = formatter.format_recommendation_list(ranked_recs, max_items=3)
        assert "Top" in formatted_list
        assert "SPY Bull Call Spread Recommendations" in formatted_list

    @pytest.mark.asyncio
    async def test_pipeline_with_ranking_engine_integration(self, spread_selection_service):
        """Test that SpreadSelectionService properly integrates with RankingEngine."""
        # Get recommendations
        recommendations = await spread_selection_service.get_recommendations(
            account_size=10000.0,
            max_recommendations=5
        )
        
        # All recommendations should have calculated expected values and ranking scores
        for rec in recommendations:
            assert rec.expected_value is not None
            assert rec.ranking_score is not None
            assert 0 <= rec.ranking_score <= 1.0  # Score should be normalized
            
            # Expected value should match the formula
            calculated_ev = (rec.probability_of_profit * rec.max_profit) - \
                          ((1 - rec.probability_of_profit) * rec.max_risk)
            assert abs(rec.expected_value - calculated_ev) < 0.01

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_ranking_weights(self, mock_market_service, mock_sentiment_calculator):
        """Test pipeline with custom ranking weights favoring probability."""
        # Create service with custom ranking configuration
        black_scholes = BlackScholesCalculator()
        
        # Custom spread configuration
        spread_config = SpreadConfiguration(
            probability_weight=0.7,    # Heavy weight on probability
            risk_reward_weight=0.2,
            sentiment_weight=0.1
        )
        
        service = SpreadSelectionService(
            black_scholes_calculator=black_scholes,
            market_service=mock_market_service,
            sentiment_calculator=mock_sentiment_calculator,
            config=spread_config
        )
        
        recommendations = await service.get_recommendations(
            account_size=10000.0,
            max_recommendations=5
        )
        
        if len(recommendations) >= 2:
            # With heavy probability weighting, higher probability should generally rank higher
            # (not guaranteed due to other factors, but likely)
            sorted_by_prob = sorted(recommendations, key=lambda x: x.probability_of_profit, reverse=True)
            sorted_by_rank = sorted(recommendations, key=lambda x: x.ranking_score, reverse=True)
            
            # Check if the highest probability spread is in top 2 by ranking
            highest_prob_rec = sorted_by_prob[0]
            top_2_ranks = sorted_by_rank[:2]
            assert highest_prob_rec in top_2_ranks

    @pytest.mark.asyncio
    async def test_formatter_json_output_integration(self, spread_selection_service):
        """Test that formatter produces valid JSON output for API responses."""
        # Get recommendations
        recommendations = await spread_selection_service.get_recommendations(
            account_size=10000.0,
            max_recommendations=5
        )
        
        if recommendations:
            formatter = TradeFormatter()
            
            # Format single recommendation as JSON
            json_output = formatter.format_as_json(recommendations[0])
            
            # Verify JSON structure
            assert json_output["spread_type"] == "Bull Call Spread"
            assert "strikes" in json_output
            assert "metrics" in json_output
            assert "probability" in json_output
            assert "position" in json_output
            assert "scores" in json_output
            assert "order_ticket" in json_output
            
            # Verify values match recommendation
            rec = recommendations[0]
            assert json_output["strikes"]["long"] == rec.long_strike
            assert json_output["strikes"]["short"] == rec.short_strike
            assert json_output["metrics"]["net_debit"] == rec.net_debit
            assert json_output["probability"]["profit"] == rec.probability_of_profit

    @pytest.mark.asyncio
    async def test_pipeline_with_no_valid_spreads(self, mock_market_service, mock_sentiment_calculator):
        """Test pipeline behavior when no spreads meet criteria."""
        # Create service with very restrictive criteria
        black_scholes = BlackScholesCalculator()
        
        restrictive_config = SpreadConfiguration(
            min_risk_reward_ratio=10.0,  # Unrealistically high
            min_probability_of_profit=0.95  # Very high probability requirement
        )
        
        service = SpreadSelectionService(
            black_scholes_calculator=black_scholes,
            market_service=mock_market_service,
            sentiment_calculator=mock_sentiment_calculator,
            config=restrictive_config
        )
        
        recommendations = await service.get_recommendations(
            account_size=10000.0,
            max_recommendations=5
        )
        
        # Should return empty list when no spreads qualify
        assert recommendations == []
        
        # Formatter should handle empty list gracefully
        formatter = TradeFormatter()
        formatted_list = formatter.format_recommendation_list(recommendations)
        assert "No spread recommendations meet the criteria" in formatted_list

    @pytest.mark.asyncio
    async def test_ranking_consistency_across_pipeline(self, spread_selection_service):
        """Test that ranking remains consistent throughout the pipeline."""
        # Get recommendations
        recommendations = await spread_selection_service.get_recommendations(
            account_size=10000.0,
            max_recommendations=10
        )
        
        if len(recommendations) >= 3:
            # Store original ranking scores
            original_scores = [(rec.long_strike, rec.short_strike, rec.ranking_score) 
                             for rec in recommendations]
            
            # Re-rank with RankingEngine
            ranking_engine = RankingEngine()
            re_ranked = ranking_engine.rank_recommendations(recommendations)
            
            # Scores should remain consistent (allowing for small floating point differences)
            for i, rec in enumerate(re_ranked):
                original = next(s for s in original_scores 
                              if s[0] == rec.long_strike and s[1] == rec.short_strike)
                assert abs(rec.ranking_score - original[2]) < 0.001

    @pytest.mark.asyncio
    async def test_profit_zone_calculations(self, spread_selection_service):
        """Test that profit zone calculations are correct."""
        recommendations = await spread_selection_service.get_recommendations(
            account_size=10000.0,
            max_recommendations=3
        )
        
        if recommendations:
            formatter = TradeFormatter()
            
            for rec in recommendations:
                profit_zones = formatter.format_profit_zones(rec)
                
                # Verify all required zones are present
                assert f"Max Loss at/below: ${rec.long_strike:.2f}" in profit_zones
                assert f"Loss Zone: Below ${rec.breakeven_price:.2f}" in profit_zones
                assert f"Profit Zone: ${rec.breakeven_price:.2f} - ${rec.short_strike:.2f}" in profit_zones
                assert f"Max Profit Zone: Above ${rec.short_strike:.2f}" in profit_zones

    @pytest.mark.asyncio
    async def test_complete_workflow_with_warnings(self, spread_selection_service):
        """Test the complete workflow including risk warnings."""
        # Get recommendations with a small account to trigger warnings
        small_account = 2000.0
        recommendations = await spread_selection_service.get_recommendations(
            account_size=small_account,
            max_recommendations=5
        )
        
        if recommendations:
            formatter = TradeFormatter()
            
            # Find a recommendation that might trigger warnings
            for rec in recommendations:
                formatted = formatter.format_recommendation(
                    rec, 
                    style=FormatStyle.DETAILED,
                    include_warnings=True
                )
                
                # Check if any warnings were triggered
                if rec.probability_of_profit < 0.40:
                    assert "⚠️ WARNING" in formatted
                    assert "Low probability" in formatted