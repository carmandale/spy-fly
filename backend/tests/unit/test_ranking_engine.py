"""
Tests for RankingEngine class.

The RankingEngine is responsible for calculating expected values and ranking
spread recommendations based on probability, risk/reward, and sentiment.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from app.models.spread import SpreadRecommendation
from app.services.ranking_engine import RankingEngine, RankingConfiguration


class TestRankingEngine:
    """Test the RankingEngine class for expected value calculation and ranking."""

    def test_expected_value_calculation_basic(self):
        """Test basic expected value calculation using probability and risk/reward."""
        engine = RankingEngine()
        
        # Expected value = (probability * max_profit) - ((1-probability) * max_risk)
        probability = 0.6  # 60% chance
        max_profit = 100.0  # $100 max profit
        max_risk = 50.0    # $50 max risk
        
        expected_value = engine.calculate_expected_value(
            probability_of_profit=probability,
            max_profit=max_profit,
            max_risk=max_risk
        )
        
        # Expected calculation: (0.6 * 100) - (0.4 * 50) = 60 - 20 = 40
        assert expected_value == 40.0

    def test_expected_value_calculation_negative(self):
        """Test expected value calculation when result is negative."""
        engine = RankingEngine()
        
        # Low probability scenario
        probability = 0.3  # 30% chance
        max_profit = 50.0  # $50 max profit
        max_risk = 100.0   # $100 max risk
        
        expected_value = engine.calculate_expected_value(
            probability_of_profit=probability,
            max_profit=max_profit,
            max_risk=max_risk
        )
        
        # Expected calculation: (0.3 * 50) - (0.7 * 100) = 15 - 70 = -55
        assert expected_value == -55.0

    def test_expected_value_calculation_edge_cases(self):
        """Test expected value calculation with edge cases."""
        engine = RankingEngine()
        
        # Zero probability
        assert engine.calculate_expected_value(0.0, 100.0, 50.0) == -50.0
        
        # 100% probability
        assert engine.calculate_expected_value(1.0, 100.0, 50.0) == 100.0
        
        # Zero max profit
        assert engine.calculate_expected_value(0.6, 0.0, 50.0) == -20.0
        
        # Zero max risk
        assert engine.calculate_expected_value(0.6, 100.0, 0.0) == 60.0

    def test_expected_value_with_invalid_probability(self):
        """Test expected value calculation with invalid probability values."""
        engine = RankingEngine()
        
        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            engine.calculate_expected_value(-0.1, 100.0, 50.0)
            
        with pytest.raises(ValueError, match="Probability must be between 0 and 1"):
            engine.calculate_expected_value(1.1, 100.0, 50.0)

    def test_expected_value_with_negative_values(self):
        """Test expected value calculation with negative profit/risk values."""
        engine = RankingEngine()
        
        with pytest.raises(ValueError, match="Max profit cannot be negative"):
            engine.calculate_expected_value(0.5, -10.0, 50.0)
            
        with pytest.raises(ValueError, match="Max risk cannot be negative"):
            engine.calculate_expected_value(0.5, 100.0, -10.0)

    def test_ranking_score_calculation_default_weights(self):
        """Test ranking score calculation with default weights."""
        engine = RankingEngine()
        
        probability = 0.6
        risk_reward_ratio = 2.0
        sentiment_score = 0.5
        
        ranking_score = engine.calculate_ranking_score(
            probability_of_profit=probability,
            risk_reward_ratio=risk_reward_ratio,
            sentiment_score=sentiment_score
        )
        
        # Default weights: probability=0.4, risk_reward=0.3, sentiment=0.3
        # Normalized risk_reward = min(2.0, 5.0) / 5.0 = 0.4
        # Normalized sentiment = (0.5 + 1) / 2 = 0.75
        # Score = 0.4 * 0.6 + 0.3 * 0.4 + 0.3 * 0.75 = 0.24 + 0.12 + 0.225 = 0.585
        expected_score = 0.4 * 0.6 + 0.3 * 0.4 + 0.3 * 0.75
        assert abs(ranking_score - expected_score) < 0.001

    def test_ranking_score_calculation_custom_weights(self):
        """Test ranking score calculation with custom weights."""
        config = RankingConfiguration(
            probability_weight=0.5,
            risk_reward_weight=0.2,
            sentiment_weight=0.3
        )
        engine = RankingEngine(config)
        
        probability = 0.7
        risk_reward_ratio = 3.0
        sentiment_score = -0.2
        
        ranking_score = engine.calculate_ranking_score(
            probability_of_profit=probability,
            risk_reward_ratio=risk_reward_ratio,
            sentiment_score=sentiment_score
        )
        
        # Normalized risk_reward = min(3.0, 5.0) / 5.0 = 0.6
        # Normalized sentiment = (-0.2 + 1) / 2 = 0.4
        # Score = 0.5 * 0.7 + 0.2 * 0.6 + 0.3 * 0.4 = 0.35 + 0.12 + 0.12 = 0.59
        expected_score = 0.5 * 0.7 + 0.2 * 0.6 + 0.3 * 0.4
        assert abs(ranking_score - expected_score) < 0.001

    def test_ranking_score_with_high_risk_reward_ratio(self):
        """Test ranking score calculation with high risk/reward ratio (should be capped)."""
        engine = RankingEngine()
        
        probability = 0.5
        risk_reward_ratio = 10.0  # Very high ratio, should be capped at 5.0
        sentiment_score = 0.0
        
        ranking_score = engine.calculate_ranking_score(
            probability_of_profit=probability,
            risk_reward_ratio=risk_reward_ratio,
            sentiment_score=sentiment_score
        )
        
        # Normalized risk_reward should be capped: min(10.0, 5.0) / 5.0 = 1.0
        # Normalized sentiment = (0.0 + 1) / 2 = 0.5
        # Score = 0.4 * 0.5 + 0.3 * 1.0 + 0.3 * 0.5 = 0.2 + 0.3 + 0.15 = 0.65
        expected_score = 0.4 * 0.5 + 0.3 * 1.0 + 0.3 * 0.5
        assert abs(ranking_score - expected_score) < 0.001

    def test_ranking_score_with_extreme_sentiment(self):
        """Test ranking score calculation with extreme sentiment values."""
        engine = RankingEngine()
        
        # Test with very negative sentiment
        score_negative = engine.calculate_ranking_score(
            probability_of_profit=0.5,
            risk_reward_ratio=2.0,
            sentiment_score=-1.0  # Most negative sentiment
        )
        
        # Test with very positive sentiment
        score_positive = engine.calculate_ranking_score(
            probability_of_profit=0.5,
            risk_reward_ratio=2.0,
            sentiment_score=1.0  # Most positive sentiment
        )
        
        # Positive sentiment should result in higher score
        assert score_positive > score_negative

    def test_rank_recommendations_basic_sorting(self):
        """Test basic recommendation ranking by score."""
        engine = RankingEngine()
        
        # Create test recommendations with different expected characteristics
        recommendations = [
            self._create_test_recommendation(
                long_strike=400.0, short_strike=405.0, 
                probability=0.4, max_profit=200.0, max_risk=100.0, sentiment=0.2
            ),
            self._create_test_recommendation(
                long_strike=410.0, short_strike=415.0,
                probability=0.7, max_profit=150.0, max_risk=75.0, sentiment=0.5
            ),
            self._create_test_recommendation(
                long_strike=420.0, short_strike=425.0,
                probability=0.5, max_profit=300.0, max_risk=200.0, sentiment=-0.1
            )
        ]
        
        ranked = engine.rank_recommendations(recommendations)
        
        # Verify that recommendations are sorted by ranking score (highest first)
        assert len(ranked) == 3
        for i in range(len(ranked) - 1):
            assert ranked[i].ranking_score >= ranked[i + 1].ranking_score

    def test_rank_recommendations_with_sentiment_weighting(self):
        """Test recommendation ranking heavily weighted by sentiment."""
        config = RankingConfiguration(
            probability_weight=0.1,
            risk_reward_weight=0.1,
            sentiment_weight=0.8  # Heavy sentiment weighting
        )
        engine = RankingEngine(config)
        
        # Create recommendations with different sentiment scores
        rec_high_sentiment = self._create_test_recommendation(
            long_strike=400.0, short_strike=405.0,
            probability=0.4, max_profit=100.0, max_risk=100.0, sentiment=0.9
        )
        rec_low_sentiment = self._create_test_recommendation(
            long_strike=410.0, short_strike=415.0,
            probability=0.6, max_profit=150.0, max_risk=100.0, sentiment=-0.8
        )
        
        ranked = engine.rank_recommendations([rec_high_sentiment, rec_low_sentiment])
        
        # High sentiment should rank first despite lower probability
        assert ranked[0].sentiment_score == 0.9
        assert ranked[1].sentiment_score == -0.8

    def test_rank_recommendations_with_expected_value_focus(self):
        """Test ranking when focusing on expected value differences."""
        engine = RankingEngine()
        
        # Create recommendations with clearly different expected values
        high_ev_rec = self._create_test_recommendation(
            long_strike=400.0, short_strike=405.0,
            probability=0.8, max_profit=100.0, max_risk=20.0, sentiment=0.0
        )  # Expected value: 0.8 * 100 - 0.2 * 20 = 80 - 4 = 76
        
        low_ev_rec = self._create_test_recommendation(
            long_strike=410.0, short_strike=415.0,
            probability=0.3, max_profit=50.0, max_risk=100.0, sentiment=0.0
        )  # Expected value: 0.3 * 50 - 0.7 * 100 = 15 - 70 = -55
        
        ranked = engine.rank_recommendations([low_ev_rec, high_ev_rec])
        
        # High expected value should rank first
        assert ranked[0].expected_value > ranked[1].expected_value
        assert ranked[0].ranking_score > ranked[1].ranking_score

    def test_rank_empty_recommendations_list(self):
        """Test ranking with empty recommendations list."""
        engine = RankingEngine()
        
        ranked = engine.rank_recommendations([])
        
        assert ranked == []

    def test_rank_single_recommendation(self):
        """Test ranking with single recommendation."""
        engine = RankingEngine()
        
        recommendation = self._create_test_recommendation(
            long_strike=400.0, short_strike=405.0,
            probability=0.5, max_profit=100.0, max_risk=100.0, sentiment=0.0
        )
        
        ranked = engine.rank_recommendations([recommendation])
        
        assert len(ranked) == 1
        assert ranked[0] == recommendation

    def test_configuration_validation(self):
        """Test RankingConfiguration validation."""
        # Valid configuration
        config = RankingConfiguration(
            probability_weight=0.4,
            risk_reward_weight=0.3,
            sentiment_weight=0.3
        )
        engine = RankingEngine(config)
        assert engine.config.probability_weight == 0.4

        # Invalid configuration - weights don't sum to 1.0
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            RankingConfiguration(
                probability_weight=0.5,
                risk_reward_weight=0.3,
                sentiment_weight=0.3  # Sum = 1.1
            )

        # Invalid configuration - negative weight
        with pytest.raises(ValueError, match="All weights must be non-negative"):
            RankingConfiguration(
                probability_weight=0.5,
                risk_reward_weight=-0.1,
                sentiment_weight=0.6
            )

    def _create_test_recommendation(
        self, 
        long_strike: float, 
        short_strike: float,
        probability: float,
        max_profit: float,
        max_risk: float,
        sentiment: float
    ) -> SpreadRecommendation:
        """Helper method to create test recommendations."""
        # Calculate derived values
        net_debit = max_risk
        risk_reward_ratio = max_profit / max_risk if max_risk > 0 else 0.0
        breakeven = long_strike + net_debit
        expected_value = (probability * max_profit) - ((1 - probability) * max_risk)
        
        # Use engine to calculate ranking score
        engine = RankingEngine()
        ranking_score = engine.calculate_ranking_score(
            probability_of_profit=probability,
            risk_reward_ratio=risk_reward_ratio,
            sentiment_score=sentiment
        )
        
        return SpreadRecommendation(
            long_strike=long_strike,
            short_strike=short_strike,
            long_premium=net_debit + 1.0,  # Arbitrary values for test
            short_premium=1.0,
            net_debit=net_debit,
            max_risk=max_risk,
            max_profit=max_profit,
            risk_reward_ratio=risk_reward_ratio,
            probability_of_profit=probability,
            breakeven_price=breakeven,
            long_bid=net_debit + 0.95,
            long_ask=net_debit + 1.05,
            short_bid=0.95,
            short_ask=1.05,
            long_volume=100,
            short_volume=100,
            expected_value=expected_value,
            sentiment_score=sentiment,
            ranking_score=ranking_score,
            timestamp=datetime.now(),
            contracts_to_trade=1,
            total_cost=net_debit * 100,
            buying_power_used_pct=0.02
        )