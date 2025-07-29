"""
Ranking Engine for SPY 0-DTE Bull-Call-Spread recommendations.

The RankingEngine calculates expected values and ranks spread recommendations
based on probability of profit, risk/reward ratios, and sentiment analysis.
"""

from dataclasses import dataclass
from typing import List

from app.models.spread import SpreadRecommendation


@dataclass
class RankingConfiguration:
    """Configuration for ranking algorithm weights and parameters."""
    
    # Weighting factors for ranking score calculation
    probability_weight: float = 0.4  # Weight for probability of profit
    risk_reward_weight: float = 0.3  # Weight for risk/reward ratio
    sentiment_weight: float = 0.3    # Weight for sentiment score
    
    # Risk/reward normalization parameters
    max_risk_reward_ratio: float = 5.0  # Cap for risk/reward ratio normalization
    
    def __post_init__(self):
        """Validate configuration parameters."""
        # Check that weights sum to 1.0
        total_weight = self.probability_weight + self.risk_reward_weight + self.sentiment_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        # Check that all weights are non-negative
        if any(weight < 0 for weight in [self.probability_weight, self.risk_reward_weight, self.sentiment_weight]):
            raise ValueError("All weights must be non-negative")
        
        # Check max risk/reward ratio
        if self.max_risk_reward_ratio <= 0:
            raise ValueError("Max risk/reward ratio must be positive")


class RankingEngine:
    """
    Engine for calculating expected values and ranking spread recommendations.
    
    The RankingEngine uses a weighted scoring system that combines:
    - Probability of profit from Black-Scholes calculations
    - Risk/reward ratio from spread analysis
    - Market sentiment score from technical analysis
    
    Expected value is calculated as: (probability * max_profit) - ((1-probability) * max_risk)
    """
    
    def __init__(self, config: RankingConfiguration = None):
        """
        Initialize the ranking engine with configuration.
        
        Args:
            config: RankingConfiguration object (uses defaults if None)
        """
        self.config = config or RankingConfiguration()
    
    def calculate_expected_value(
        self, 
        probability_of_profit: float, 
        max_profit: float, 
        max_risk: float
    ) -> float:
        """
        Calculate the expected value of a spread trade.
        
        Expected value = (probability * max_profit) - ((1-probability) * max_risk)
        
        Args:
            probability_of_profit: Probability of profit (0.0 to 1.0)
            max_profit: Maximum profit potential of the spread
            max_risk: Maximum risk (loss) potential of the spread
            
        Returns:
            Expected value of the trade (can be negative)
            
        Raises:
            ValueError: If probability is not between 0 and 1, or if profit/risk are negative
        """
        # Validate inputs
        if not (0.0 <= probability_of_profit <= 1.0):
            raise ValueError(f"Probability must be between 0 and 1, got {probability_of_profit}")
        
        if max_profit < 0:
            raise ValueError(f"Max profit cannot be negative, got {max_profit}")
            
        if max_risk < 0:
            raise ValueError(f"Max risk cannot be negative, got {max_risk}")
        
        # Calculate expected value
        expected_profit = probability_of_profit * max_profit
        expected_loss = (1.0 - probability_of_profit) * max_risk
        expected_value = expected_profit - expected_loss
        
        return expected_value
    
    def calculate_ranking_score(
        self,
        probability_of_profit: float,
        risk_reward_ratio: float,
        sentiment_score: float
    ) -> float:
        """
        Calculate a weighted ranking score for a spread recommendation.
        
        The score combines normalized values of:
        - Probability of profit (0.0 to 1.0)
        - Risk/reward ratio (normalized to 0.0 to 1.0, capped at max_risk_reward_ratio)
        - Sentiment score (normalized from -1.0/1.0 range to 0.0/1.0)
        
        Args:
            probability_of_profit: Probability of profit (0.0 to 1.0)
            risk_reward_ratio: Risk to reward ratio (positive value)
            sentiment_score: Market sentiment score (-1.0 to 1.0)
            
        Returns:
            Weighted ranking score (0.0 to 1.0, higher is better)
        """
        # Normalize risk/reward ratio (cap at configured maximum)
        normalized_risk_reward = min(risk_reward_ratio, self.config.max_risk_reward_ratio) / self.config.max_risk_reward_ratio
        
        # Normalize sentiment score from [-1, 1] to [0, 1]
        normalized_sentiment = (sentiment_score + 1.0) / 2.0
        
        # Calculate weighted score
        ranking_score = (
            self.config.probability_weight * probability_of_profit +
            self.config.risk_reward_weight * normalized_risk_reward +
            self.config.sentiment_weight * normalized_sentiment
        )
        
        return ranking_score
    
    def rank_recommendations(
        self, 
        recommendations: List[SpreadRecommendation]
    ) -> List[SpreadRecommendation]:
        """
        Rank a list of spread recommendations by their ranking scores.
        
        This method updates the expected_value and ranking_score fields of each
        recommendation, then sorts them by ranking score in descending order.
        
        Args:
            recommendations: List of SpreadRecommendation objects to rank
            
        Returns:
            List of recommendations sorted by ranking score (highest first)
        """
        if not recommendations:
            return []
        
        # Update expected values and ranking scores for all recommendations
        updated_recommendations = []
        
        for rec in recommendations:
            # Calculate expected value
            expected_value = self.calculate_expected_value(
                probability_of_profit=rec.probability_of_profit,
                max_profit=rec.max_profit,
                max_risk=rec.max_risk
            )
            
            # Calculate ranking score
            ranking_score = self.calculate_ranking_score(
                probability_of_profit=rec.probability_of_profit,
                risk_reward_ratio=rec.risk_reward_ratio,
                sentiment_score=rec.sentiment_score
            )
            
            # Create updated recommendation with new scores
            updated_rec = SpreadRecommendation(
                long_strike=rec.long_strike,
                short_strike=rec.short_strike,
                long_premium=rec.long_premium,
                short_premium=rec.short_premium,
                net_debit=rec.net_debit,
                max_risk=rec.max_risk,
                max_profit=rec.max_profit,
                risk_reward_ratio=rec.risk_reward_ratio,
                probability_of_profit=rec.probability_of_profit,
                breakeven_price=rec.breakeven_price,
                long_bid=rec.long_bid,
                long_ask=rec.long_ask,
                short_bid=rec.short_bid,
                short_ask=rec.short_ask,
                long_volume=rec.long_volume,
                short_volume=rec.short_volume,
                expected_value=expected_value,  # Updated
                sentiment_score=rec.sentiment_score,
                ranking_score=ranking_score,    # Updated
                timestamp=rec.timestamp,
                contracts_to_trade=rec.contracts_to_trade,
                total_cost=rec.total_cost,
                buying_power_used_pct=rec.buying_power_used_pct
            )
            
            updated_recommendations.append(updated_rec)
        
        # Sort by ranking score (highest first)
        ranked_recommendations = sorted(
            updated_recommendations, 
            key=lambda x: x.ranking_score, 
            reverse=True
        )
        
        return ranked_recommendations
    
    def get_configuration(self) -> RankingConfiguration:
        """Get current ranking configuration."""
        return self.config
    
    def update_configuration(self, config: RankingConfiguration) -> None:
        """Update ranking configuration."""
        self.config = config