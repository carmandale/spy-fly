"""
Tests for TradeFormatter class.

The TradeFormatter is responsible for converting spread recommendations
into human-readable formats and generating copy-to-clipboard order tickets.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.models.spread import SpreadRecommendation
from app.services.trade_formatter import TradeFormatter, FormatStyle


class TestTradeFormatter:
    """Test the TradeFormatter class for human-readable output generation."""

    def test_format_recommendation_basic_text(self):
        """Test basic text formatting of a spread recommendation."""
        formatter = TradeFormatter()
        
        # Create a test recommendation
        rec = self._create_test_recommendation(
            long_strike=400.0,
            short_strike=405.0,
            net_debit=1.50,
            max_profit=3.50,
            max_risk=1.50,
            probability=0.65,
            contracts=2
        )
        
        formatted = formatter.format_recommendation(rec, style=FormatStyle.TEXT)
        
        # Check that formatted output contains key information
        assert "SPY Bull Call Spread" in formatted
        assert "400/405" in formatted  # Strike prices
        assert "$1.50" in formatted  # Net debit
        assert "65.0%" in formatted  # Probability
        assert "2.33" in formatted  # Risk/reward ratio
        assert "2 contracts" in formatted  # Position size

    def test_format_recommendation_detailed_text(self):
        """Test detailed text formatting with all metrics."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=410.0,
            short_strike=415.0,
            net_debit=2.00,
            max_profit=3.00,
            max_risk=2.00,
            probability=0.55,
            contracts=5,
            sentiment_score=0.7
        )
        
        formatted = formatter.format_recommendation(rec, style=FormatStyle.DETAILED)
        
        # Check for detailed metrics
        assert "Buy 5 SPY" in formatted
        assert "410 Call" in formatted
        assert "Sell 5 SPY" in formatted
        assert "415 Call" in formatted
        assert "Net Debit: $2.00" in formatted
        assert "Max Profit: $3.00" in formatted
        assert "Max Risk: $2.00" in formatted
        assert "Breakeven: $412.00" in formatted
        assert "Probability of Profit: 55.0%" in formatted
        assert "Expected Value: $0.75" in formatted  # (0.55 * 3) - (0.45 * 2)
        assert "Sentiment Score: 0.70" in formatted
        assert "Total Cost: $1,000.00" in formatted  # 5 * 200 * 100

    def test_format_order_ticket_basic(self):
        """Test basic order ticket generation for broker submission."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=420.0,
            short_strike=425.0,
            net_debit=1.75,
            contracts=3
        )
        
        order_ticket = formatter.format_order_ticket(rec)
        
        # Check order ticket format
        assert "BUY +3 VERTICAL SPY" in order_ticket
        assert "420/425 CALL" in order_ticket
        assert "@1.75 LMT" in order_ticket
        assert "0DTE" in order_ticket or datetime.now().strftime("%m/%d") in order_ticket

    def test_format_order_ticket_with_custom_expiry(self):
        """Test order ticket with custom expiration date."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=430.0,
            short_strike=435.0,
            net_debit=2.25,
            contracts=1
        )
        
        # Test with specific expiration date
        expiry_date = datetime(2025, 7, 30)
        order_ticket = formatter.format_order_ticket(rec, expiry_date=expiry_date)
        
        assert "BUY +1 VERTICAL SPY" in order_ticket
        assert "07/30" in order_ticket
        assert "430/435 CALL" in order_ticket
        assert "@2.25 LMT" in order_ticket

    def test_format_profit_zones(self):
        """Test profit zone calculation and formatting."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=440.0,
            short_strike=445.0,
            net_debit=2.00,
            max_profit=3.00,
            breakeven=442.00
        )
        
        profit_zones = formatter.format_profit_zones(rec)
        
        # Check profit zone descriptions
        assert "Loss Zone: Below $442.00" in profit_zones
        assert "Profit Zone: $442.00 - $445.00" in profit_zones
        assert "Max Profit Zone: Above $445.00" in profit_zones
        assert "Max Loss at/below: $440.00" in profit_zones

    def test_format_json_output(self):
        """Test JSON formatting for API responses."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=450.0,
            short_strike=455.0,
            net_debit=1.25,
            max_profit=3.75,
            max_risk=1.25,
            probability=0.72,
            contracts=4,
            sentiment_score=0.5,
            ranking_score=0.68
        )
        
        json_output = formatter.format_as_json(rec)
        
        # Check JSON structure
        assert json_output["spread_type"] == "Bull Call Spread"
        assert json_output["strikes"]["long"] == 450.0
        assert json_output["strikes"]["short"] == 455.0
        assert json_output["metrics"]["net_debit"] == 1.25
        assert json_output["metrics"]["max_profit"] == 3.75
        assert json_output["metrics"]["max_risk"] == 1.25
        assert json_output["metrics"]["risk_reward_ratio"] == 3.0
        assert json_output["probability"]["profit"] == 0.72
        assert json_output["probability"]["breakeven"] == 450.0 + 1.25
        assert json_output["position"]["contracts"] == 4
        assert json_output["position"]["total_cost"] == 500.0  # 4 * 1.25 * 100
        assert json_output["scores"]["sentiment"] == 0.5
        assert json_output["scores"]["ranking"] == 0.68
        assert json_output["order_ticket"] is not None

    def test_format_multiple_recommendations(self):
        """Test formatting multiple recommendations as a list."""
        formatter = TradeFormatter()
        
        recs = [
            self._create_test_recommendation(400, 405, 1.5, contracts=2, ranking_score=0.75),
            self._create_test_recommendation(410, 415, 2.0, contracts=3, ranking_score=0.65),
            self._create_test_recommendation(420, 425, 1.75, contracts=1, ranking_score=0.55),
        ]
        
        formatted_list = formatter.format_recommendation_list(recs, max_items=3)
        
        # Check list formatting
        assert "Top 3 SPY Bull Call Spread Recommendations" in formatted_list
        assert "#1 (Score: 0.75)" in formatted_list
        assert "#2 (Score: 0.65)" in formatted_list
        assert "#3 (Score: 0.55)" in formatted_list
        assert "400/405" in formatted_list
        assert "410/415" in formatted_list
        assert "420/425" in formatted_list

    def test_format_empty_recommendation_list(self):
        """Test formatting empty recommendation list."""
        formatter = TradeFormatter()
        
        formatted_list = formatter.format_recommendation_list([])
        
        assert "No spread recommendations meet the criteria" in formatted_list

    def test_format_with_high_precision_numbers(self):
        """Test formatting with high precision decimal numbers."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=399.50,
            short_strike=404.50,
            net_debit=1.4875,  # High precision
            max_profit=3.5125,
            probability=0.6789
        )
        
        formatted = formatter.format_recommendation(rec, style=FormatStyle.TEXT)
        
        # Check that numbers are properly rounded for display
        assert "$1.49" in formatted  # Rounded to 2 decimals for currency
        assert "67.9%" in formatted  # Rounded to 1 decimal for percentage

    def test_format_copy_friendly_output(self):
        """Test copy-to-clipboard friendly formatting."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=400.0,
            short_strike=405.0,
            net_debit=1.50,
            contracts=2
        )
        
        clipboard_text = formatter.format_for_clipboard(rec)
        
        # Check that output is clean and copyable
        assert "\t" not in clipboard_text  # No tabs
        assert "  " not in clipboard_text  # No double spaces
        assert clipboard_text.strip() == clipboard_text  # No leading/trailing whitespace
        assert "BUY +2 VERTICAL SPY" in clipboard_text

    def test_format_with_warnings(self):
        """Test formatting with risk warnings for edge cases."""
        formatter = TradeFormatter()
        
        # Low probability spread
        low_prob_rec = self._create_test_recommendation(
            long_strike=460.0,
            short_strike=465.0,
            net_debit=2.0,
            probability=0.35,  # Low probability
            contracts=10  # Large position
        )
        
        formatted = formatter.format_recommendation(
            low_prob_rec, 
            style=FormatStyle.DETAILED,
            include_warnings=True
        )
        
        assert "⚠️ WARNING" in formatted
        assert "Low probability" in formatted or "35.0%" in formatted
        
        # High cost spread
        high_cost_rec = self._create_test_recommendation(
            long_strike=400.0,
            short_strike=405.0,
            net_debit=4.50,  # High debit relative to spread width
            contracts=5
        )
        
        formatted_high_cost = formatter.format_recommendation(
            high_cost_rec,
            style=FormatStyle.DETAILED,
            include_warnings=True
        )
        
        assert "⚠️ WARNING" in formatted_high_cost
        assert "High cost" in formatted_high_cost or "90.0%" in formatted_high_cost

    def test_format_styles_consistency(self):
        """Test that all format styles produce valid output."""
        formatter = TradeFormatter()
        
        rec = self._create_test_recommendation(
            long_strike=400.0,
            short_strike=405.0,
            net_debit=2.00
        )
        
        # Test all available styles
        for style in FormatStyle:
            formatted = formatter.format_recommendation(rec, style=style)
            assert formatted is not None
            assert len(formatted) > 0
            assert "400" in formatted  # Should contain strike price

    def test_format_with_none_values(self):
        """Test formatting handles None values gracefully."""
        formatter = TradeFormatter()
        
        # Create recommendation with some None values
        rec = SpreadRecommendation(
            long_strike=400.0,
            short_strike=405.0,
            long_premium=2.0,
            short_premium=0.5,
            net_debit=1.5,
            max_risk=1.5,
            max_profit=3.5,
            risk_reward_ratio=2.33,
            probability_of_profit=0.6,
            breakeven_price=401.5,
            long_bid=1.95,
            long_ask=2.05,
            short_bid=0.45,
            short_ask=0.55,
            long_volume=None,  # None value
            short_volume=None,  # None value
            expected_value=0.8,
            sentiment_score=None,  # None value
            ranking_score=0.65,
            timestamp=datetime.now(),
            contracts_to_trade=1,
            total_cost=150.0,
            buying_power_used_pct=0.03
        )
        
        # Should format without errors (basic text format)
        formatted = formatter.format_recommendation(rec)
        assert formatted is not None
        assert "SPY Bull Call Spread" in formatted
        
        # Test detailed format to check None handling
        formatted_detailed = formatter.format_recommendation(rec, style=FormatStyle.DETAILED)
        assert formatted_detailed is not None
        assert "Sentiment Score: N/A" in formatted_detailed  # Should handle None gracefully

    def _create_test_recommendation(
        self, 
        long_strike: float,
        short_strike: float,
        net_debit: float,
        max_profit: float = None,
        max_risk: float = None,
        probability: float = 0.6,
        contracts: int = 1,
        sentiment_score: float = 0.0,
        ranking_score: float = 0.5,
        breakeven: float = None
    ) -> SpreadRecommendation:
        """Helper method to create test recommendations."""
        # Calculate derived values if not provided
        if max_risk is None:
            max_risk = net_debit
        if max_profit is None:
            max_profit = (short_strike - long_strike) - net_debit
        if breakeven is None:
            breakeven = long_strike + net_debit
            
        risk_reward_ratio = max_profit / max_risk if max_risk > 0 else 0.0
        expected_value = (probability * max_profit) - ((1 - probability) * max_risk)
        total_cost = contracts * net_debit * 100
        
        return SpreadRecommendation(
            long_strike=long_strike,
            short_strike=short_strike,
            long_premium=net_debit + 0.50,  # Arbitrary
            short_premium=0.50,
            net_debit=net_debit,
            max_risk=max_risk,
            max_profit=max_profit,
            risk_reward_ratio=risk_reward_ratio,
            probability_of_profit=probability,
            breakeven_price=breakeven,
            long_bid=net_debit + 0.45,
            long_ask=net_debit + 0.55,
            short_bid=0.45,
            short_ask=0.55,
            long_volume=1000,
            short_volume=1000,
            expected_value=expected_value,
            sentiment_score=sentiment_score,
            ranking_score=ranking_score,
            timestamp=datetime.now(),
            contracts_to_trade=contracts,
            total_cost=total_cost,
            buying_power_used_pct=total_cost / 10000  # Assume $10k account
        )


class TestTopRecommendationSelection:
    """Test top N recommendation selection and JSON formatting functionality."""

    def setup_method(self):
        """Setup test fixtures for top recommendation testing."""
        self.formatter = TradeFormatter(symbol="SPY")
        
        # Create a set of recommendations with different ranking scores for testing
        self.ranked_recommendations = [
            SpreadRecommendation(
                long_strike=470.0, short_strike=475.0, long_premium=3.0, short_premium=1.5,
                net_debit=1.5, max_risk=150.0, max_profit=350.0, risk_reward_ratio=2.33,
                probability_of_profit=0.75, breakeven_price=471.5, long_bid=2.95, long_ask=3.05,
                short_bid=1.45, short_ask=1.55, long_volume=500, short_volume=300,
                expected_value=187.5, sentiment_score=0.5, ranking_score=0.85,  # Highest rank
                timestamp=datetime(2025, 7, 28, 9, 45, 0), contracts_to_trade=3,
                total_cost=450.0, buying_power_used_pct=0.045,
            ),
            SpreadRecommendation(
                long_strike=475.0, short_strike=480.0, long_premium=2.5, short_premium=1.0,
                net_debit=1.5, max_risk=150.0, max_profit=350.0, risk_reward_ratio=2.33,
                probability_of_profit=0.65, breakeven_price=476.5, long_bid=2.45, long_ask=2.55,
                short_bid=0.95, short_ask=1.05, long_volume=200, short_volume=150,
                expected_value=102.5, sentiment_score=0.3, ranking_score=0.72,  # Second rank
                timestamp=datetime(2025, 7, 28, 9, 46, 0), contracts_to_trade=2,
                total_cost=300.0, buying_power_used_pct=0.03,
            ),
            SpreadRecommendation(
                long_strike=480.0, short_strike=485.0, long_premium=2.0, short_premium=0.8,
                net_debit=1.2, max_risk=120.0, max_profit=380.0, risk_reward_ratio=3.17,
                probability_of_profit=0.55, breakeven_price=481.2, long_bid=1.95, long_ask=2.05,
                short_bid=0.75, short_ask=0.85, long_volume=800, short_volume=600,
                expected_value=55.0, sentiment_score=0.7, ranking_score=0.68,  # Third rank
                timestamp=datetime(2025, 7, 28, 9, 47, 0), contracts_to_trade=4,
                total_cost=480.0, buying_power_used_pct=0.048,
            ),
            SpreadRecommendation(
                long_strike=485.0, short_strike=490.0, long_premium=1.8, short_premium=0.6,
                net_debit=1.2, max_risk=120.0, max_profit=380.0, risk_reward_ratio=3.17,
                probability_of_profit=0.45, breakeven_price=486.2, long_bid=1.75, long_ask=1.85,
                short_bid=0.55, short_ask=0.65, long_volume=300, short_volume=200,
                expected_value=-9.0, sentiment_score=0.1, ranking_score=0.55,  # Fourth rank
                timestamp=datetime(2025, 7, 28, 9, 48, 0), contracts_to_trade=2,
                total_cost=240.0, buying_power_used_pct=0.024,
            ),
            SpreadRecommendation(
                long_strike=490.0, short_strike=495.0, long_premium=1.5, short_premium=0.4,
                net_debit=1.1, max_risk=110.0, max_profit=390.0, risk_reward_ratio=3.55,
                probability_of_profit=0.35, breakeven_price=491.1, long_bid=1.45, long_ask=1.55,
                short_bid=0.35, short_ask=0.45, long_volume=150, short_volume=100,
                expected_value=-35.0, sentiment_score=-0.2, ranking_score=0.42,  # Fifth rank
                timestamp=datetime(2025, 7, 28, 9, 49, 0), contracts_to_trade=1,
                total_cost=110.0, buying_power_used_pct=0.011,
            ),
        ]

    def test_top_3_recommendation_selection(self):
        """Test selection of top 3 recommendations."""
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations, 
            max_count=3
        )
        
        # Should return exactly 3 recommendations
        assert len(formatted_list["recommendations"]) == 3
        assert formatted_list["summary"]["count"] == 3
        
        # Should be the top 3 by ranking score (first 3 in our pre-sorted list)
        rec1 = formatted_list["recommendations"][0]
        rec2 = formatted_list["recommendations"][1] 
        rec3 = formatted_list["recommendations"][2]
        
        # Check that we got the right strikes (which correspond to ranking order)
        assert rec1["details"]["long_strike"] == 470.0  # Highest ranking
        assert rec2["details"]["long_strike"] == 475.0  # Second ranking
        assert rec3["details"]["long_strike"] == 480.0  # Third ranking

    def test_top_5_recommendation_selection(self):
        """Test selection of top 5 recommendations."""
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations,
            max_count=5
        )
        
        # Should return all 5 available recommendations
        assert len(formatted_list["recommendations"]) == 5
        assert formatted_list["summary"]["count"] == 5

    def test_json_formatting_structure(self):
        """Test that JSON formatting includes all required fields."""
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations,
            max_count=3
        )
        
        # Check top-level structure
        required_top_level_keys = ["recommendations", "summary", "disclaimer"]
        for key in required_top_level_keys:
            assert key in formatted_list
        
        # Check each recommendation has required structure
        for rec in formatted_list["recommendations"]:
            required_rec_keys = ["id", "description", "summary", "details", "market_data", "timestamp"]
            for key in required_rec_keys:
                assert key in rec

    def test_json_summary_calculations(self):
        """Test that summary statistics are calculated correctly."""
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations,
            max_count=3
        )
        
        summary = formatted_list["summary"]
        
        # Check count
        assert summary["count"] == 3
        
        # Should have all required summary fields
        required_summary_keys = ["count", "avg_probability_of_profit", "avg_expected_value", 
                               "total_recommended_cost", "generated_at"]
        for key in required_summary_keys:
            assert key in summary
        
        # Should have generated_at timestamp in ISO format
        assert "T" in summary["generated_at"]  # ISO format check

    def test_recommendation_order_preservation(self):
        """Test that recommendation order is preserved in JSON output."""
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations,
            max_count=4
        )
        
        # Should maintain the input order (pre-sorted by ranking score)
        ranking_scores = []
        for rec in formatted_list["recommendations"]:
            ranking_scores.append(rec["details"]["ranking_score"])
        
        # Should be in descending order (highest first)
        assert ranking_scores == sorted(ranking_scores, reverse=True)
        
        # Specifically check the exact ranking scores
        assert ranking_scores == [0.85, 0.72, 0.68, 0.55]

    def test_json_serializable_output(self):
        """Test that the output is JSON serializable."""
        import json
        
        formatted_list = self.formatter.format_recommendations_list(
            self.ranked_recommendations,
            max_count=3
        )
        
        # Should be able to serialize to JSON without error
        try:
            json_string = json.dumps(formatted_list)
            assert len(json_string) > 0
            
            # Should be able to deserialize back
            deserialized = json.loads(json_string)
            assert deserialized["summary"]["count"] == 3
            
        except (TypeError, ValueError) as e:
            pytest.fail(f"JSON serialization failed: {e}")