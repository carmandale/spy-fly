"""Pydantic models for sentiment analysis."""

from datetime import datetime

from pydantic import BaseModel


class ComponentScore(BaseModel):
    """Individual sentiment component score."""

    score: int
    value: float
    threshold: str | None = None
    change_percent: float | None = None
    label: str
    range: str | None = None
    position: str | None = None


class ComponentDetail(BaseModel):
    """Detailed component information."""

    component: str
    score: int
    max_score: int
    current_value: float
    scoring_rules: list[dict]
    historical_context: dict | None = None
    timestamp: datetime


class TechnicalStatus(BaseModel):
    """Technical analysis status."""

    all_bullish: bool
    details: dict[str, str]


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
    cache_expires_at: datetime | None = None


class SentimentResponse(BaseModel):
    """API response for sentiment endpoint."""

    score: int
    decision: str
    threshold: int
    timestamp: str
    breakdown: dict[str, ComponentScore]
    technical_status: TechnicalStatus
    cached: bool = False
    cache_expires_at: str | None = None


class SentimentConfig(BaseModel):
    """Sentiment calculation configuration."""

    scoring_thresholds: dict[str, dict]
    scoring_weights: dict[str, float]
    decision_threshold: int
    cache_ttl: int
