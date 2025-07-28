"""
Data models for spread trading.

Contains data structures used throughout the spread selection
and risk management systems.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SpreadRecommendation:
    """Data structure for a spread recommendation."""

    # Spread details
    long_strike: float
    short_strike: float
    long_premium: float
    short_premium: float
    net_debit: float

    # Risk metrics
    max_risk: float
    max_profit: float
    risk_reward_ratio: float
    probability_of_profit: float
    breakeven_price: float

    # Market data
    long_bid: float
    long_ask: float
    short_bid: float
    short_ask: float
    long_volume: int
    short_volume: int

    # Analysis metadata
    expected_value: float
    sentiment_score: float
    ranking_score: float
    timestamp: datetime

    # Order execution details
    contracts_to_trade: int
    total_cost: float
    buying_power_used_pct: float
