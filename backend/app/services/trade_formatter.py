"""
Trade Formatter for SPY 0-DTE Bull-Call-Spread recommendations.

The TradeFormatter converts spread recommendations into human-readable formats
suitable for display, clipboard copying, and API responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

from app.models.spread import SpreadRecommendation


class FormatStyle(Enum):
    """Available formatting styles for trade recommendations."""
    TEXT = "text"  # Basic text format
    DETAILED = "detailed"  # Detailed text with all metrics
    CLIPBOARD = "clipboard"  # Copy-friendly format
    JSON = "json"  # JSON format for API


class TradeFormatter:
    """
    Formatter for converting spread recommendations to human-readable formats.
    
    This class handles formatting spread recommendations for various outputs:
    - Human-readable text for UI display
    - Copy-to-clipboard order tickets
    - JSON format for API responses
    - Profit zone calculations and visualizations
    """
    
    def __init__(self, symbol: str = "SPY"):
        """Initialize the trade formatter.
        
        Args:
            symbol: Trading symbol (default: SPY)
        """
        self.symbol = symbol
    
    def format_recommendation(
        self, 
        recommendation: SpreadRecommendation,
        style: FormatStyle = FormatStyle.TEXT,
        include_warnings: bool = False
    ) -> str:
        """
        Format a single spread recommendation.
        
        Args:
            recommendation: SpreadRecommendation object to format
            style: Formatting style to use
            include_warnings: Whether to include risk warnings
            
        Returns:
            Formatted string representation
        """
        if style == FormatStyle.TEXT:
            return self._format_text(recommendation)
        elif style == FormatStyle.DETAILED:
            return self._format_detailed(recommendation, include_warnings)
        elif style == FormatStyle.CLIPBOARD:
            return self.format_for_clipboard(recommendation)
        elif style == FormatStyle.JSON:
            # For JSON style, convert to string representation
            json_data = self.format_as_json(recommendation)
            return str(json_data)
        else:
            return self._format_text(recommendation)
    
    def _format_text(self, rec: SpreadRecommendation) -> str:
        """Format recommendation as basic text."""
        return (
            f"SPY Bull Call Spread {self._format_strike_pair(rec.long_strike, rec.short_strike)}\n"
            f"Net Debit: ${rec.net_debit:.2f} | "
            f"Probability: {rec.probability_of_profit:.1%} | "
            f"Risk/Reward: {rec.risk_reward_ratio:.2f}:1 | "
            f"{rec.contracts_to_trade} contracts"
        )
    
    def _format_detailed(self, rec: SpreadRecommendation, include_warnings: bool = False) -> str:
        """Format recommendation with detailed metrics."""
        lines = [
            "SPY Bull Call Spread",
            "=" * 40,
            f"Buy {rec.contracts_to_trade} SPY {self._format_strike(rec.long_strike)} Call",
            f"Sell {rec.contracts_to_trade} SPY {self._format_strike(rec.short_strike)} Call",
            "",
            "Pricing & Risk Metrics:",
            f"Net Debit: ${rec.net_debit:.2f}",
            f"Max Profit: ${rec.max_profit:.2f}",
            f"Max Risk: ${rec.max_risk:.2f}",
            f"Risk/Reward Ratio: {rec.risk_reward_ratio:.2f}:1",
            "",
            "Probability & Analysis:",
            f"Breakeven: ${rec.breakeven_price:.2f}",
            f"Probability of Profit: {rec.probability_of_profit:.1%}",
            f"Expected Value: ${rec.expected_value:.2f}",
            f"Sentiment Score: {rec.sentiment_score:.2f}" if rec.sentiment_score is not None else "Sentiment Score: N/A",
            "",
            "Position Details:",
            f"Contracts: {rec.contracts_to_trade}",
            f"Total Cost: ${rec.total_cost:,.2f}",
            f"Buying Power Used: {rec.buying_power_used_pct:.1%}"
        ]
        
        # Add warnings if enabled
        if include_warnings:
            warnings = self._generate_warnings(rec)
            if warnings:
                lines.extend(["", "⚠️ WARNINGS:"] + warnings)
        
        return "\n".join(lines)
    
    def format_order_ticket(self, rec: SpreadRecommendation, expiry_date: Optional[datetime] = None) -> str:
        """
        Format recommendation as a broker-ready order ticket.
        
        Args:
            rec: SpreadRecommendation to format
            expiry_date: Expiration date (defaults to today for 0DTE)
            
        Returns:
            Order ticket string ready for copying
        """
        # Determine expiration format
        if expiry_date:
            expiry_str = expiry_date.strftime("%m/%d")
        else:
            # For 0DTE, use today's date
            expiry_str = datetime.now().strftime("%m/%d")
        
        # Format as standard vertical spread order
        return (
            f"BUY +{rec.contracts_to_trade} VERTICAL SPY "
            f"{expiry_str} "
            f"{self._format_strike_pair(rec.long_strike, rec.short_strike)} CALL "
            f"@{rec.net_debit:.2f} LMT"
        )
    
    def format_profit_zones(self, rec: SpreadRecommendation) -> str:
        """
        Format profit zone information for the spread.
        
        Args:
            rec: SpreadRecommendation to analyze
            
        Returns:
            Formatted profit zone description
        """
        lines = [
            "Profit/Loss Zones:",
            f"Max Loss at/below: ${rec.long_strike:.2f}",
            f"Loss Zone: Below ${rec.breakeven_price:.2f}",
            f"Profit Zone: ${rec.breakeven_price:.2f} - ${rec.short_strike:.2f}",
            f"Max Profit Zone: Above ${rec.short_strike:.2f}"
        ]
        
        return "\n".join(lines)
    
    def format_as_json(self, rec: SpreadRecommendation) -> Dict[str, Any]:
        """
        Format recommendation as JSON structure.
        
        Args:
            rec: SpreadRecommendation to format
            
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "spread_type": "Bull Call Spread",
            "strikes": {
                "long": rec.long_strike,
                "short": rec.short_strike
            },
            "metrics": {
                "net_debit": rec.net_debit,
                "max_profit": rec.max_profit,
                "max_risk": rec.max_risk,
                "risk_reward_ratio": rec.risk_reward_ratio
            },
            "probability": {
                "profit": rec.probability_of_profit,
                "breakeven": rec.breakeven_price
            },
            "position": {
                "contracts": rec.contracts_to_trade,
                "total_cost": rec.total_cost,
                "buying_power_pct": rec.buying_power_used_pct
            },
            "scores": {
                "expected_value": rec.expected_value,
                "sentiment": rec.sentiment_score,
                "ranking": rec.ranking_score
            },
            "order_ticket": self.format_order_ticket(rec),
            "timestamp": rec.timestamp.isoformat() if rec.timestamp else None
        }
    
    def format_recommendation_list(self, recommendations: List[SpreadRecommendation], max_items: int = 5) -> str:
        """
        Format a list of recommendations.
        
        Args:
            recommendations: List of recommendations sorted by ranking
            max_items: Maximum number to display
            
        Returns:
            Formatted list of recommendations
        """
        if not recommendations:
            return "No spread recommendations meet the criteria at this time."
        
        # Limit to max_items
        display_recs = recommendations[:max_items]
        
        lines = [f"Top {len(display_recs)} SPY Bull Call Spread Recommendations:"]
        lines.append("=" * 50)
        
        for i, rec in enumerate(display_recs, 1):
            lines.append(f"\n#{i} (Score: {rec.ranking_score:.2f})")
            lines.append(f"Spread: {self._format_strike_pair(rec.long_strike, rec.short_strike)}")
            lines.append(f"Net Debit: ${rec.net_debit:.2f} | Probability: {rec.probability_of_profit:.1%}")
            lines.append(f"Risk/Reward: {rec.risk_reward_ratio:.2f}:1 | Contracts: {rec.contracts_to_trade}")
        
        return "\n".join(lines)
    
    def format_for_clipboard(self, rec: SpreadRecommendation) -> str:
        """
        Format recommendation for clipboard copying.
        
        Args:
            rec: SpreadRecommendation to format
            
        Returns:
            Clean string suitable for clipboard
        """
        # Simple, clean format without extra spacing or special characters
        return self.format_order_ticket(rec)
    
    def _format_strike(self, strike: float) -> str:
        """Format a single strike price."""
        # Remove decimal if whole number
        if strike == int(strike):
            return str(int(strike))
        return f"{strike:.2f}"
    
    def _format_strike_pair(self, long_strike: float, short_strike: float) -> str:
        """Format a strike pair as 'long/short'."""
        return f"{self._format_strike(long_strike)}/{self._format_strike(short_strike)}"
    
    def _format_currency(self, value: float) -> str:
        """Format a value as currency."""
        return f"${value:.2f}"
    
    def _format_percentage(self, value: float) -> str:
        """Format a value as percentage."""
        return f"{value:.1%}"
    
    def _generate_warnings(self, rec: SpreadRecommendation) -> List[str]:
        """Generate risk warnings for a recommendation."""
        warnings = []
        
        # Low probability warning
        if rec.probability_of_profit < 0.40:
            warnings.append(f"Low probability of profit ({rec.probability_of_profit:.1%})")
        
        # High cost relative to spread width
        spread_width = rec.short_strike - rec.long_strike
        cost_ratio = rec.net_debit / spread_width if spread_width > 0 else 0
        if cost_ratio > 0.80:
            warnings.append(f"High cost relative to spread width ({cost_ratio:.1%})")
        
        # Large position warning
        if rec.contracts_to_trade >= 10:
            warnings.append(f"Large position size ({rec.contracts_to_trade} contracts)")
        
        # High buying power usage
        if rec.buying_power_used_pct > 0.04:  # Over 4%
            warnings.append(f"High buying power usage ({rec.buying_power_used_pct:.1%})")
        
        return warnings
    
    def format_recommendations_list(self, recommendations: List[SpreadRecommendation], max_count: int = 5) -> Dict[str, Any]:
        """
        Format a list of recommendations as JSON structure with summary.
        
        Args:
            recommendations: List of recommendations (assumed to be already sorted)
            max_count: Maximum number of recommendations to include
            
        Returns:
            Dictionary containing recommendations, summary, and disclaimer
        """
        # Select top N recommendations
        selected_recs = recommendations[:max_count]
        
        # Format each recommendation
        formatted_recs = []
        for i, rec in enumerate(selected_recs):
            formatted_rec = {
                "id": i + 1,
                "description": f"{self.symbol} {self._format_strike_pair(rec.long_strike, rec.short_strike)} Bull Call Spread",
                "summary": {
                    "net_debit": rec.net_debit,
                    "probability": rec.probability_of_profit,
                    "risk_reward_ratio": rec.risk_reward_ratio,
                    "contracts": rec.contracts_to_trade,
                    "total_cost": rec.total_cost
                },
                "details": {
                    "long_strike": rec.long_strike,
                    "short_strike": rec.short_strike,
                    "long_premium": rec.long_premium,
                    "short_premium": rec.short_premium,
                    "net_debit": rec.net_debit,
                    "max_profit": rec.max_profit,
                    "max_risk": rec.max_risk,
                    "risk_reward_ratio": rec.risk_reward_ratio,
                    "probability_of_profit": rec.probability_of_profit,
                    "breakeven_price": rec.breakeven_price,
                    "expected_value": rec.expected_value,
                    "sentiment_score": rec.sentiment_score,
                    "ranking_score": rec.ranking_score,
                    "contracts_to_trade": rec.contracts_to_trade,
                    "total_cost": rec.total_cost,
                    "buying_power_used_pct": rec.buying_power_used_pct
                },
                "market_data": {
                    "long_bid": rec.long_bid,
                    "long_ask": rec.long_ask,
                    "short_bid": rec.short_bid,
                    "short_ask": rec.short_ask,
                    "long_volume": rec.long_volume,
                    "short_volume": rec.short_volume
                },
                "timestamp": rec.timestamp.isoformat() if rec.timestamp else None
            }
            formatted_recs.append(formatted_rec)
        
        # Calculate summary statistics
        if selected_recs:
            avg_probability = sum(rec.probability_of_profit for rec in selected_recs) / len(selected_recs)
            avg_expected_value = sum(rec.expected_value for rec in selected_recs) / len(selected_recs)
            total_cost = sum(rec.total_cost for rec in selected_recs)
        else:
            avg_probability = 0.0
            avg_expected_value = 0.0
            total_cost = 0.0
        
        # Build response structure
        return {
            "recommendations": formatted_recs,
            "summary": {
                "count": len(selected_recs),
                "avg_probability_of_profit": avg_probability,
                "avg_expected_value": avg_expected_value,
                "total_recommended_cost": total_cost,
                "generated_at": datetime.now().isoformat()
            },
            "disclaimer": "These recommendations are for educational purposes only. Always verify calculations and consult with a financial advisor before trading."
        }