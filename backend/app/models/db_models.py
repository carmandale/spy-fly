"""SQLAlchemy database models for market data storage."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MarketDataCache(Base):
    """Cache table for API responses with TTL management."""

    __tablename__ = "market_data_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), nullable=False, unique=True)
    data_type = Column(String(50), nullable=False)  # 'quote', 'options', 'historical'
    raw_data = Column(Text, nullable=False)  # JSON serialized response
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_cache_key", "cache_key"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_data_type", "data_type"),
    )


class SPYQuote(Base):
    """Historical SPY stock quotes for analysis and fallback."""

    __tablename__ = "spy_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, default="SPY")
    price = Column(Numeric(10, 4), nullable=False)
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    volume = Column(Integer)
    timestamp = Column(DateTime, nullable=False)
    source = Column(String(20), nullable=False, default="polygon")
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_timestamp", "timestamp"),
        Index("idx_symbol_timestamp", "symbol", "timestamp"),
    )


class OptionContract(Base):
    """Cached option chain data for SPY 0-DTE options."""

    __tablename__ = "option_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)  # Option symbol (SPY241127C00580000)
    underlying = Column(String(10), nullable=False, default="SPY")
    strike = Column(Numeric(10, 4), nullable=False)
    option_type = Column(String(4), nullable=False)  # 'call' or 'put'
    expiration_date = Column(Date, nullable=False)
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    last_price = Column(Numeric(10, 4))
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_underlying_expiration", "underlying", "expiration_date"),
        Index("idx_strike_type", "strike", "option_type"),
        Index("idx_option_timestamp", "timestamp"),
        UniqueConstraint("symbol", "timestamp", name="uq_symbol_timestamp"),
    )


class HistoricalPrice(Base):
    """Daily and intraday historical price data for technical analysis."""

    __tablename__ = "historical_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), nullable=False, default="SPY")
    date = Column(Date, nullable=False)
    timeframe = Column(String(10), nullable=False)  # 'daily', '1hour', '15min'
    open_price = Column(Numeric(10, 4), nullable=False)
    high_price = Column(Numeric(10, 4), nullable=False)
    low_price = Column(Numeric(10, 4), nullable=False)
    close_price = Column(Numeric(10, 4), nullable=False)
    volume = Column(Integer, nullable=False)
    vwap = Column(Numeric(10, 4))  # Volume Weighted Average Price
    source = Column(String(20), nullable=False, default="polygon")
    created_at = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_symbol_date", "symbol", "date"),
        Index("idx_timeframe", "timeframe"),
        UniqueConstraint(
            "symbol", "date", "timeframe", name="uq_symbol_date_timeframe"
        ),
    )


class APIRequestLog(Base):
    """Track API usage for rate limiting and debugging."""

    __tablename__ = "api_requests_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False, default="GET")
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    timestamp = Column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    __table_args__ = (
        Index("idx_log_timestamp", "timestamp"),
        Index("idx_endpoint", "endpoint"),
        Index("idx_status_code", "status_code"),
    )


class AnalysisSession(Base):
    """Track spread recommendation analysis sessions for caching and history."""

    __tablename__ = "analysis_sessions"

    id = Column(String(36), primary_key=True)  # UUID primary key
    account_size = Column(Numeric(15, 2), nullable=False)
    max_recommendations = Column(Integer, nullable=False, default=5)
    
    # Market conditions at time of analysis
    spy_price = Column(Numeric(10, 4))
    vix_level = Column(Numeric(6, 2))
    sentiment_score = Column(Numeric(4, 3))
    market_status = Column(String(20))
    
    # Analysis results
    recommendations_count = Column(Integer, nullable=False, default=0)
    avg_probability = Column(Numeric(6, 4))
    avg_expected_value = Column(Numeric(10, 4))
    total_capital_required = Column(Numeric(15, 2))
    
    # Session metadata
    user_agent = Column(String(255))
    ip_address = Column(String(45))  # IPv6 support
    request_format = Column(String(20))  # json, text, clipboard
    processing_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    expires_at = Column(DateTime)  # For cache cleanup

    # Relationship to spread recommendations
    recommendations = relationship("SpreadRecommendationRecord", back_populates="session")

    __table_args__ = (
        Index("idx_session_created_at", "created_at"),
        Index("idx_session_expires_at", "expires_at"),
        Index("idx_session_account_size", "account_size"),
    )


class SpreadRecommendationRecord(Base):
    """Store individual spread recommendations for tracking and analysis."""

    __tablename__ = "spread_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("analysis_sessions.id"), nullable=False)
    symbol = Column(String(10), nullable=False, default='SPY')
    
    # Spread details
    long_strike = Column(Numeric(10, 2), nullable=False)
    short_strike = Column(Numeric(10, 2), nullable=False)
    expiration_date = Column(Date, nullable=False)
    
    # Pricing information
    long_premium = Column(Numeric(10, 4), nullable=False)
    short_premium = Column(Numeric(10, 4), nullable=False)
    net_debit = Column(Numeric(10, 4), nullable=False)
    
    # Risk metrics
    max_risk = Column(Numeric(10, 4), nullable=False)
    max_profit = Column(Numeric(10, 4), nullable=False)
    risk_reward_ratio = Column(Numeric(8, 4), nullable=False)
    breakeven_price = Column(Numeric(10, 4), nullable=False)
    
    # Market data
    long_bid = Column(Numeric(10, 4), nullable=False)
    long_ask = Column(Numeric(10, 4), nullable=False)
    short_bid = Column(Numeric(10, 4), nullable=False)
    short_ask = Column(Numeric(10, 4), nullable=False)
    long_volume = Column(Integer, nullable=False)
    short_volume = Column(Integer, nullable=False)
    
    # Analysis results
    probability_of_profit = Column(Numeric(6, 4), nullable=False)
    expected_value = Column(Numeric(10, 4), nullable=False)
    sentiment_score = Column(Numeric(4, 3))
    ranking_score = Column(Numeric(6, 4), nullable=False)
    
    # Position sizing
    contracts_to_trade = Column(Integer, nullable=False)
    total_cost = Column(Numeric(12, 2), nullable=False)
    buying_power_used_pct = Column(Numeric(6, 4), nullable=False)
    
    # Metadata
    rank_in_session = Column(Integer, nullable=False)
    account_size = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    # Relationship to analysis session
    session = relationship("AnalysisSession", back_populates="recommendations")

    __table_args__ = (
        Index("idx_session_id", "session_id"),
        Index("idx_spread_created_at", "created_at"),
        Index("idx_spread_ranking_score", "ranking_score"),
        Index("idx_spread_probability", "probability_of_profit"),
        Index("idx_spread_strikes", "long_strike", "short_strike"),
    )


class MorningScanResult(Base):
    """Store results from scheduled morning scans for tracking and analysis."""

    __tablename__ = "morning_scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Scan execution details
    scan_time = Column(DateTime, nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    is_manual = Column(Boolean, nullable=False, default=False)
    duration_seconds = Column(Numeric(8, 2))
    
    # Scan configuration
    account_size = Column(Numeric(15, 2), nullable=False)
    
    # Results summary
    recommendations_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    
    # Scan metrics (stored as JSON)
    scan_metrics = Column(JSON)  # Contains metrics like avg_probability, high_quality_count, etc.
    
    # Metadata
    created_at = Column(DateTime, nullable=False, server_default=func.current_timestamp())

    __table_args__ = (
        Index("idx_scan_time", "scan_time"),
        Index("idx_scan_success", "success"),
        Index("idx_scan_manual", "is_manual"),
        Index("idx_scan_created_at", "created_at"),
    )
