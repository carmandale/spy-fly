"""Sentiment calculation service."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

from app.config import settings
from app.models.sentiment import (
    ComponentScore, SentimentResult, SentimentBreakdown,
    TechnicalStatus
)
from app.services.market_service import MarketDataService
from app.services.cache import MarketDataCache
from app.core.exceptions import MarketDataError


def score_vix(vix_value: Optional[float]) -> ComponentScore:
    """Score VIX level."""
    if vix_value is None:
        return ComponentScore(
            score=0,
            value=0,
            threshold="N/A",
            label="VIX data unavailable"
        )
    
    if vix_value < settings.vix_low_threshold:
        score = 20
        threshold = f"< {settings.vix_low_threshold}"
        label = "Low volatility (bullish)"
    elif vix_value <= settings.vix_high_threshold:
        score = 10
        threshold = f"{settings.vix_low_threshold}-{settings.vix_high_threshold}"
        label = "Medium volatility (neutral)"
    else:
        score = 0
        threshold = f"> {settings.vix_high_threshold}"
        label = "High volatility (bearish)"
    
    return ComponentScore(
        score=score,
        value=vix_value,
        threshold=threshold,
        label=label
    )


def score_futures(current: Optional[float], previous_close: Optional[float]) -> ComponentScore:
    """Score S&P 500 futures movement."""
    if current is None or previous_close is None:
        return ComponentScore(
            score=0,
            value=0,
            change_percent=0,
            label="Futures data unavailable"
        )
    
    change_percent = ((current - previous_close) / previous_close) * 100
    
    if change_percent >= settings.futures_bullish_threshold * 100:
        score = 20
        label = "Positive overnight (bullish)"
    elif change_percent > 0:
        score = 10
        label = "Slightly positive (neutral)"
    else:
        score = 0
        label = "Negative overnight (bearish)"
    
    return ComponentScore(
        score=score,
        value=current,
        change_percent=round(change_percent, 3),
        label=label
    )


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return 50.0  # Neutral if insufficient data
    
    rsi_indicator = RSIIndicator(close=prices, window=period)
    rsi = rsi_indicator.rsi()
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def score_rsi(rsi_value: Optional[float]) -> ComponentScore:
    """Score RSI indicator."""
    if rsi_value is None:
        return ComponentScore(
            score=0,
            value=50,
            range="N/A",
            label="RSI unavailable"
        )
    
    if settings.rsi_oversold < rsi_value < settings.rsi_overbought:
        score = 10
        label = "Neutral (healthy)"
    elif rsi_value <= settings.rsi_oversold:
        score = 0
        label = "Oversold (caution)"
    else:
        score = 0
        label = "Overbought (caution)"
    
    return ComponentScore(
        score=score,
        value=rsi_value,
        range=f"{settings.rsi_oversold}-{settings.rsi_overbought}",
        label=label
    )


def score_ma50(current_price: float, ma50: float) -> ComponentScore:
    """Score price vs 50-day moving average."""
    if current_price > ma50:
        score = 10
        position = "above"
        label = "Above 50-MA (bullish)"
    else:
        score = 0
        position = "below"
        label = "Below 50-MA (bearish)"
    
    return ComponentScore(
        score=score,
        value=current_price,
        position=position,
        label=label
    )


def calculate_bollinger_position(prices: pd.Series, period: int = 20, std_dev: int = 2) -> float:
    """Calculate position within Bollinger bands (0 = lower band, 1 = upper band)."""
    if len(prices) < period:
        return 0.5  # Middle if insufficient data
    
    bb = BollingerBands(close=prices, window=period, window_dev=std_dev)
    upper = bb.bollinger_hband()
    lower = bb.bollinger_lband()
    
    current = prices.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    
    if upper_val == lower_val:
        return 0.5
    
    position = (current - lower_val) / (upper_val - lower_val)
    return max(0, min(1, position))  # Clamp to 0-1


def score_bollinger(position: Optional[float]) -> ComponentScore:
    """Score Bollinger band position."""
    if position is None:
        return ComponentScore(
            score=0,
            value=0.5,
            label="Bollinger bands unavailable"
        )
    
    # Score 10 if in middle 60% (0.2 to 0.8)
    if settings.bollinger_inner_range / 2 <= position <= 1 - (settings.bollinger_inner_range / 2):
        score = 10
        label = "Middle range (neutral)"
    elif position < settings.bollinger_inner_range / 2:
        score = 0
        label = "Near lower band (oversold)"
    else:
        score = 0
        label = "Near upper band (overbought)"
    
    return ComponentScore(
        score=score,
        value=round(position, 3),
        label=label
    )


def score_news() -> ComponentScore:
    """Placeholder for news sentiment scoring."""
    # TODO: Implement actual news sentiment analysis
    return ComponentScore(
        score=15,
        value=0,
        label="Neutral market sentiment"
    )


class SentimentCalculator:
    """Service for calculating market sentiment."""
    
    def __init__(self, market_service: MarketDataService, cache: MarketDataCache):
        self.market_service = market_service
        self.cache = cache
    
    async def calculate_sentiment(self, force_refresh: bool = False) -> SentimentResult:
        """Calculate overall market sentiment."""
        cache_key = self.cache.generate_key(
            "sentiment",
            "SPY",
            date=datetime.now().date().isoformat()
        )
        
        # Check cache unless force refresh
        if not force_refresh:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                result = SentimentResult(**cached_result)
                result.cached = True
                return result
        
        try:
            # Fetch required market data
            vix_data = await self._get_vix_data()
            futures_data = await self._get_futures_data()
            spy_history = await self._get_spy_history()
            
            # Calculate technical indicators
            prices = pd.Series([bar["close"] for bar in spy_history["bars"]])
            rsi_value = calculate_rsi(prices) if len(prices) >= 15 else None
            ma50_value = prices.rolling(window=50).mean().iloc[-1] if len(prices) >= 50 else None
            bollinger_position = calculate_bollinger_position(prices) if len(prices) >= 20 else None
            
            # Score each component
            vix_score = score_vix(vix_data.get("value"))
            futures_score = score_futures(
                futures_data.get("current"),
                futures_data.get("previous_close")
            )
            rsi_score = score_rsi(rsi_value)
            ma50_score = score_ma50(prices.iloc[-1], ma50_value) if ma50_value else ComponentScore(
                score=0, value=0, label="Insufficient data for MA50"
            )
            bollinger_score = score_bollinger(bollinger_position)
            news_score = score_news()
            
            # Create breakdown
            breakdown = SentimentBreakdown(
                vix=vix_score,
                futures=futures_score,
                rsi=rsi_score,
                ma50=ma50_score,
                bollinger=bollinger_score,
                news=news_score
            )
            
            # Calculate total score
            total_score = (
                vix_score.score +
                futures_score.score +
                rsi_score.score +
                ma50_score.score +
                bollinger_score.score +
                news_score.score
            )
            
            # Determine technical status
            technicals_bullish = (
                ma50_score.score > 0 and  # Above MA50
                rsi_score.score > 0 and    # RSI in healthy range
                bollinger_score.score > 0   # Not at extremes
            )
            
            technical_status = TechnicalStatus(
                all_bullish=technicals_bullish,
                details={
                    "trend": "up" if ma50_score.score > 0 else "down",
                    "momentum": "positive" if rsi_score.score > 0 else "extreme",
                    "volatility": "low" if vix_score.score == 20 else "elevated"
                }
            )
            
            # Make decision
            decision = "PROCEED" if (
                total_score >= settings.sentiment_minimum_score and
                technicals_bullish
            ) else "SKIP"
            
            result = SentimentResult(
                score=total_score,
                decision=decision,
                threshold=settings.sentiment_minimum_score,
                timestamp=datetime.now(),
                breakdown=breakdown,
                technical_status=technical_status,
                cached=False
            )
            
            # Cache the result
            self.cache.set(
                cache_key,
                result.model_dump(),
                ttl=settings.sentiment_cache_ttl
            )
            
            return result
            
        except Exception as e:
            raise MarketDataError(f"Failed to calculate sentiment: {str(e)}")
    
    async def _get_vix_data(self) -> Dict[str, Any]:
        """Get VIX data (placeholder for now)."""
        # TODO: Implement actual VIX data fetching
        # For now, return mock data
        return {"value": 15.5}
    
    async def _get_futures_data(self) -> Dict[str, Any]:
        """Get S&P 500 futures data (placeholder for now)."""
        # TODO: Implement actual futures data fetching
        # For now, return mock data
        return {
            "current": 5680.0,
            "previous_close": 5670.0
        }
    
    async def _get_spy_history(self) -> Dict[str, Any]:
        """Get SPY historical data for technical analysis."""
        # Get 60 days of history to ensure we have enough for 50-MA
        historical = await self.market_service.get_historical_data(days=60)
        return historical.model_dump()