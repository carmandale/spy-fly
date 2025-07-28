"""Pydantic models for market data."""

from datetime import datetime

from pydantic import BaseModel


class Quote(BaseModel):
    """Stock quote data."""

    ticker: str
    price: float
    bid: float | None = None
    ask: float | None = None
    bid_size: int | None = None
    ask_size: int | None = None
    volume: int
    high: float | None = None
    low: float | None = None
    open: float | None = None
    close: float | None = None
    vwap: float | None = None
    timestamp: datetime


class QuoteResponse(BaseModel):
    """API response for quote endpoint."""

    ticker: str
    price: float
    bid: float | None = None
    ask: float | None = None
    bid_size: int | None = None
    ask_size: int | None = None
    volume: int
    timestamp: str
    market_status: str
    change: float | None = None
    change_percent: float | None = None
    previous_close: float | None = None
    cached: bool = False


class OptionContract(BaseModel):
    """Option contract details."""

    symbol: str
    type: str  # "call" or "put"
    strike: float
    expiration: str
    bid: float
    ask: float
    mid: float
    last: float | None = None
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None


class OptionChain(BaseModel):
    """Option chain data."""

    ticker: str
    expiration: str
    underlying_price: float
    options: list[OptionContract]


class OptionChainResponse(BaseModel):
    """API response for option chain endpoint."""

    ticker: str
    underlying_price: float
    expiration: str
    options: list[OptionContract]
    cached: bool = False
    cache_expires_at: str | None = None


class Bar(BaseModel):
    """Price bar data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None


class HistoricalDataResponse(BaseModel):
    """API response for historical data endpoint."""

    ticker: str
    from_date: str
    to_date: str
    timeframe: str
    bars: list[dict]  # Simplified for JSON response
    result_count: int
    cached: bool = False


class MarketStatus(BaseModel):
    """Market status information."""

    market_status: str  # "open", "closed", "pre-market", "after-hours"
    session: str
    api_status: str
    rate_limit_remaining: int
    rate_limit_reset: str
    cache_stats: dict


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict
