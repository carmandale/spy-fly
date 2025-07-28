"""Trading-specific database models for SPY-FLY."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Date, Time, DateTime, 
    ForeignKey, Boolean, Text, JSON, DECIMAL,
    UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Trade(Base):
    """Trade records table for tracking all trading activity."""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)
    trade_type = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    
    # Entry Details
    entry_time = Column(DateTime(timezone=True))
    entry_sentiment_score_id = Column(Integer, ForeignKey("sentiment_scores.id"))
    entry_signal_reason = Column(Text)
    
    # Position Details
    contracts = Column(Integer)
    max_risk = Column(DECIMAL(10, 2))
    max_reward = Column(DECIMAL(10, 2))
    probability_of_profit = Column(DECIMAL(5, 2))
    
    # Exit Details
    exit_time = Column(DateTime(timezone=True))
    exit_reason = Column(String(50))
    exit_price = Column(DECIMAL(10, 2))
    
    # P/L Calculation
    gross_pnl = Column(DECIMAL(10, 2))
    commissions = Column(DECIMAL(10, 2))
    net_pnl = Column(DECIMAL(10, 2))
    pnl_percentage = Column(DECIMAL(10, 2))
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sentiment_score = relationship("SentimentScore", back_populates="trades")
    spread = relationship("TradeSpread", back_populates="trade", uselist=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(trade_type.in_(['paper', 'real']), name='check_trade_type'),
        CheckConstraint(status.in_(['recommended', 'skipped', 'entered', 'exited', 'stopped']), name='check_status'),
        Index('idx_entry_sentiment', 'entry_sentiment_score_id'),
    )


class SentimentScore(Base):
    """Sentiment scores table for storing market analysis results."""
    __tablename__ = "sentiment_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    score_date = Column(Date, nullable=False, index=True)
    score_time = Column(Time, nullable=False)
    
    # Overall Score
    total_score = Column(Integer, nullable=False)
    decision = Column(String(10), nullable=False, index=True)
    threshold = Column(Integer, nullable=False)
    
    # Component Scores (stored as JSON for flexibility)
    vix_component = Column(JSON, nullable=False)
    futures_component = Column(JSON, nullable=False)
    rsi_component = Column(JSON, nullable=False)
    ma50_component = Column(JSON, nullable=False)
    bollinger_component = Column(JSON, nullable=False)
    news_component = Column(JSON, nullable=False)
    
    # Technical Status
    technical_status = Column(JSON, nullable=False)
    
    # Market Context
    spy_price = Column(DECIMAL(10, 2))
    market_session = Column(String(20))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="sentiment_score")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('score_date', 'score_time', name='unique_score_datetime'),
        CheckConstraint(decision.in_(['PROCEED', 'SKIP']), name='check_decision'),
    )


class TradeSpread(Base):
    """Trade spreads table for option spread details."""
    __tablename__ = "trade_spreads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, index=True)
    
    # Spread Details
    spread_type = Column(String(20), nullable=False, default='bull_call_spread')
    expiration_date = Column(Date, nullable=False)
    
    # Long Leg
    long_strike = Column(DECIMAL(10, 2), nullable=False)
    long_premium = Column(DECIMAL(10, 2), nullable=False)
    long_iv = Column(DECIMAL(5, 2))
    long_delta = Column(DECIMAL(5, 4))
    long_gamma = Column(DECIMAL(5, 4))
    long_theta = Column(DECIMAL(5, 4))
    
    # Short Leg
    short_strike = Column(DECIMAL(10, 2), nullable=False)
    short_premium = Column(DECIMAL(10, 2), nullable=False)
    short_iv = Column(DECIMAL(5, 2))
    short_delta = Column(DECIMAL(5, 4))
    short_gamma = Column(DECIMAL(5, 4))
    short_theta = Column(DECIMAL(5, 4))
    
    # Spread Metrics
    net_debit = Column(DECIMAL(10, 2), nullable=False)
    max_profit = Column(DECIMAL(10, 2), nullable=False)
    max_loss = Column(DECIMAL(10, 2), nullable=False)
    breakeven = Column(DECIMAL(10, 2), nullable=False)
    risk_reward_ratio = Column(DECIMAL(5, 2), nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    trade = relationship("Trade", back_populates="spread")


class Configuration(Base):
    """Configuration table for system settings."""
    __tablename__ = "configuration"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    value_type = Column(String(20), nullable=False)
    description = Column(Text)
    is_sensitive = Column(Boolean, nullable=False, default=False)
    
    # Version tracking
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(50))
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('category', 'key', name='unique_category_key'),
        CheckConstraint(value_type.in_(['string', 'integer', 'float', 'boolean', 'json']), name='check_value_type'),
    )
    
    def get_typed_value(self):
        """Return the value converted to its proper type."""
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:  # string
            return self.value


class DailySummary(Base):
    """Daily summaries table for performance tracking."""
    __tablename__ = "daily_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    summary_date = Column(Date, nullable=False, unique=True, index=True)
    
    # Trade Statistics
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    losing_trades = Column(Integer, nullable=False, default=0)
    skipped_trades = Column(Integer, nullable=False, default=0)
    
    # P/L Metrics
    gross_pnl = Column(DECIMAL(10, 2), nullable=False, default=0)
    commissions = Column(DECIMAL(10, 2), nullable=False, default=0)
    net_pnl = Column(DECIMAL(10, 2), nullable=False, default=0)
    
    # Cumulative Metrics
    cumulative_pnl = Column(DECIMAL(10, 2), nullable=False, default=0)
    account_value = Column(DECIMAL(10, 2))
    win_rate = Column(DECIMAL(5, 2))
    average_win = Column(DECIMAL(10, 2))
    average_loss = Column(DECIMAL(10, 2))
    
    # Market Context
    spy_open = Column(DECIMAL(10, 2))
    spy_close = Column(DECIMAL(10, 2))
    spy_high = Column(DECIMAL(10, 2))
    spy_low = Column(DECIMAL(10, 2))
    vix_close = Column(DECIMAL(10, 2))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())