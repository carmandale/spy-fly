"""Pydantic models for market data."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Quote(BaseModel):
    """Stock quote data."""
    ticker: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: int
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    vwap: Optional[float] = None
    timestamp: datetime


class QuoteResponse(BaseModel):
    """API response for quote endpoint."""
    ticker: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: int
    timestamp: str
    market_status: str
    change: Optional[float] = None
    change_percent: Optional[float] = None
    previous_close: Optional[float] = None
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
    last: Optional[float] = None
    volume: int
    open_interest: int
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


class OptionChain(BaseModel):
    """Option chain data."""
    ticker: str
    expiration: str
    underlying_price: float
    options: List[OptionContract]


class OptionChainResponse(BaseModel):
    """API response for option chain endpoint."""
    ticker: str
    underlying_price: float
    expiration: str
    options: List[OptionContract]
    cached: bool = False
    cache_expires_at: Optional[str] = None


class Bar(BaseModel):
    """Price bar data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None


class HistoricalDataResponse(BaseModel):
    """API response for historical data endpoint."""
    ticker: str
    from_date: str
    to_date: str
    timeframe: str
    bars: List[dict]  # Simplified for JSON response
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