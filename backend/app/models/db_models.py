"""SQLAlchemy database models for market data storage."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, 
    Numeric, Boolean, Index, UniqueConstraint
)
from sqlalchemy.sql import func

from app.core.database import Base


class MarketDataCache(Base):
    """Cache table for API responses with TTL management."""
    __tablename__ = "market_data_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False, unique=True)
    data_type = Column(String(50), nullable=False)  # 'quote', 'options', 'historical'
    raw_data = Column(Text, nullable=False)  # JSON serialized response
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    expires_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_data_type', 'data_type'),
    )


class SPYQuote(Base):
    """Historical SPY stock quotes for analysis and fallback."""
    __tablename__ = "spy_quotes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, default='SPY')
    price = Column(Numeric(10, 4), nullable=False)
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    volume = Column(Integer)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(20), nullable=False, default='polygon')
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OptionContract(Base):
    """Cached option chain data for SPY 0-DTE options."""
    __tablename__ = "option_contracts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)  # Option symbol (SPY241127C00580000)
    underlying = Column(String(10), nullable=False, default='SPY')
    strike = Column(Numeric(10, 4), nullable=False)
    option_type = Column(String(4), nullable=False)  # 'call' or 'put'
    expiration_date = Column(Date, nullable=False)
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    last_price = Column(Numeric(10, 4))
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_underlying_expiration', 'underlying', 'expiration_date'),
        Index('idx_strike_type', 'strike', 'option_type'),
        Index('idx_option_timestamp', 'timestamp'),
        UniqueConstraint('symbol', 'timestamp', name='uq_symbol_timestamp'),
    )


class HistoricalPrice(Base):
    """Daily and intraday historical price data for technical analysis."""
    __tablename__ = "historical_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, default='SPY')
    date = Column(Date, nullable=False)
    timeframe = Column(String(10), nullable=False)  # 'daily', '1hour', '15min'
    open_price = Column(Numeric(10, 4), nullable=False)
    high_price = Column(Numeric(10, 4), nullable=False)
    low_price = Column(Numeric(10, 4), nullable=False)
    close_price = Column(Numeric(10, 4), nullable=False)
    volume = Column(Integer, nullable=False)
    vwap = Column(Numeric(10, 4))  # Volume Weighted Average Price
    source = Column(String(20), nullable=False, default='polygon')
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_symbol_date', 'symbol', 'date'),
        Index('idx_timeframe', 'timeframe'),
        UniqueConstraint('symbol', 'date', 'timeframe', name='uq_symbol_date_timeframe'),
    )


class APIRequestLog(Base):
    """Track API usage for rate limiting and debugging."""
    __tablename__ = "api_requests_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False, default='GET')
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    timestamp = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_log_timestamp', 'timestamp'),
        Index('idx_endpoint', 'endpoint'),
        Index('idx_status_code', 'status_code'),
    )