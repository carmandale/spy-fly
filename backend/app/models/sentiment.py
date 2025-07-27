"""Pydantic models for sentiment analysis."""
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class ComponentScore(BaseModel):
    """Individual sentiment component score."""
    score: int
    value: float
    threshold: Optional[str] = None
    change_percent: Optional[float] = None
    label: str
    range: Optional[str] = None
    position: Optional[str] = None
    
    
class ComponentDetail(BaseModel):
    """Detailed component information."""
    component: str
    score: int
    max_score: int
    current_value: float
    scoring_rules: list[dict]
    historical_context: Optional[dict] = None
    timestamp: datetime


class TechnicalStatus(BaseModel):
    """Technical analysis status."""
    all_bullish: bool
    details: Dict[str, str]


class SentimentBreakdown(BaseModel):
    """Breakdown of sentiment scores by component."""
    vix: ComponentScore
    futures: ComponentScore
    rsi: ComponentScore
    ma50: ComponentScore
    bollinger: ComponentScore
    news: ComponentScore


class SentimentResult(BaseModel):
    """Complete sentiment calculation result."""
    score: int
    decision: str  # "PROCEED" or "SKIP"
    threshold: int
    timestamp: datetime
    breakdown: SentimentBreakdown
    technical_status: TechnicalStatus
    cached: bool = False
    cache_expires_at: Optional[datetime] = None


class SentimentResponse(BaseModel):
    """API response for sentiment endpoint."""
    score: int
    decision: str
    threshold: int
    timestamp: str
    breakdown: Dict[str, ComponentScore]
    technical_status: TechnicalStatus
    cached: bool = False
    cache_expires_at: Optional[str] = None


class SentimentConfig(BaseModel):
    """Sentiment calculation configuration."""
    scoring_thresholds: Dict[str, dict]
    scoring_weights: Dict[str, float]
    decision_threshold: int
    cache_ttl: int