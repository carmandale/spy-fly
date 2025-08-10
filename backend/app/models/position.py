"""Position tracking models for P/L calculation and monitoring."""

from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Position(Base):
    """Track open and closed spread positions for P/L monitoring."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Position identification
    symbol = Column(String(10), nullable=False, default="SPY")
    position_type = Column(String(20), nullable=False, default="bull_call_spread")
    status = Column(String(20), nullable=False, default="open", index=True)
    
    # Position details
    contracts = Column(Integer, nullable=False)
    entry_date = Column(Date, nullable=False, index=True)
    expiration_date = Column(Date, nullable=False)
    
    # Spread configuration
    long_strike = Column(DECIMAL(10, 2), nullable=False)
    short_strike = Column(DECIMAL(10, 2), nullable=False)
    
    # Entry pricing
    entry_long_premium = Column(DECIMAL(10, 4), nullable=False)
    entry_short_premium = Column(DECIMAL(10, 4), nullable=False)
    entry_net_debit = Column(DECIMAL(10, 4), nullable=False)
    entry_total_cost = Column(DECIMAL(12, 2), nullable=False)  # contracts * net_debit * 100
    
    # Risk metrics (calculated at entry)
    max_profit = Column(DECIMAL(10, 2), nullable=False)
    max_loss = Column(DECIMAL(10, 2), nullable=False)
    breakeven_price = Column(DECIMAL(10, 4), nullable=False)
    
    # Entry market conditions
    entry_spy_price = Column(DECIMAL(10, 4), nullable=False)
    entry_vix = Column(DECIMAL(6, 2))
    entry_sentiment_score = Column(DECIMAL(4, 3))
    
    # Exit details (null for open positions)
    exit_date = Column(Date)
    exit_time = Column(DateTime(timezone=True))
    exit_reason = Column(String(50))  # 'profit_target', 'stop_loss', 'expiration', 'manual'
    exit_long_premium = Column(DECIMAL(10, 4))
    exit_short_premium = Column(DECIMAL(10, 4))
    exit_net_credit = Column(DECIMAL(10, 4))
    exit_total_value = Column(DECIMAL(12, 2))
    
    # Final P/L (calculated on exit)
    realized_pnl = Column(DECIMAL(12, 2))
    realized_pnl_percent = Column(DECIMAL(8, 4))
    
    # Position management
    profit_target_percent = Column(DECIMAL(6, 2), default=50.0)  # % of max profit
    stop_loss_percent = Column(DECIMAL(6, 2), default=20.0)  # % of max loss
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pl_snapshots = relationship("PositionPLSnapshot", back_populates="position", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            status.in_(["open", "closed", "expired", "assigned"]),
            name="check_position_status"
        ),
        CheckConstraint(
            position_type.in_(["bull_call_spread", "bear_put_spread"]),
            name="check_position_type"
        ),
        CheckConstraint(contracts > 0, name="check_positive_contracts"),
        CheckConstraint(entry_total_cost > 0, name="check_positive_cost"),
        Index("idx_position_status_date", "status", "entry_date"),
        Index("idx_position_expiration", "expiration_date"),
        Index("idx_position_symbol_status", "symbol", "status"),
    )


class PositionPLSnapshot(Base):
    """Store P/L snapshots for positions throughout the trading day."""

    __tablename__ = "position_pl_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    
    # Snapshot timing
    snapshot_time = Column(DateTime(timezone=True), nullable=False, index=True)
    market_session = Column(String(20), nullable=False)  # 'pre_market', 'regular', 'after_hours'
    
    # Market data at snapshot time
    spy_price = Column(DECIMAL(10, 4), nullable=False)
    vix_level = Column(DECIMAL(6, 2))
    
    # Current option pricing
    current_long_premium = Column(DECIMAL(10, 4))
    current_short_premium = Column(DECIMAL(10, 4))
    current_net_value = Column(DECIMAL(10, 4))
    current_total_value = Column(DECIMAL(12, 2))
    
    # P/L calculations
    unrealized_pnl = Column(DECIMAL(12, 2), nullable=False)
    unrealized_pnl_percent = Column(DECIMAL(8, 4), nullable=False)
    
    # Greeks and risk metrics
    position_delta = Column(DECIMAL(8, 4))
    position_gamma = Column(DECIMAL(8, 4))
    position_theta = Column(DECIMAL(8, 4))  # Time decay per day
    position_vega = Column(DECIMAL(8, 4))
    
    # Time decay calculation
    time_to_expiry_hours = Column(DECIMAL(8, 2))
    daily_theta_decay = Column(DECIMAL(10, 4))  # Expected theta decay for the day
    
    # Alert status
    alert_triggered = Column(Boolean, default=False)
    alert_type = Column(String(20))  # 'profit_target', 'stop_loss', 'time_decay'
    
    # Data source and quality
    data_source = Column(String(20), default="calculated")  # 'calculated', 'market_data'
    calculation_method = Column(String(30), default="black_scholes")
    data_quality_score = Column(DECIMAL(4, 2))  # 0-100 quality score
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    position = relationship("Position", back_populates="pl_snapshots")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            market_session.in_(["pre_market", "regular", "after_hours", "closed"]),
            name="check_market_session"
        ),
        CheckConstraint(
            alert_type.in_(["profit_target", "stop_loss", "time_decay", "unusual_movement"]) | (alert_type.is_(None)),
            name="check_alert_type"
        ),
        CheckConstraint(time_to_expiry_hours >= 0, name="check_positive_time_to_expiry"),
        CheckConstraint(data_quality_score >= 0, name="check_quality_score_min"),
        CheckConstraint(data_quality_score <= 100, name="check_quality_score_max"),
        Index("idx_snapshot_position_time", "position_id", "snapshot_time"),
        Index("idx_snapshot_time", "snapshot_time"),
        Index("idx_snapshot_alert", "alert_triggered", "alert_type"),
        UniqueConstraint("position_id", "snapshot_time", name="uq_position_snapshot_time"),
    )


class PLAlert(Base):
    """Track P/L alerts and notifications sent to users."""

    __tablename__ = "pl_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("position_pl_snapshots.id"), nullable=False)
    
    # Alert details
    alert_type = Column(String(20), nullable=False)
    alert_level = Column(String(10), nullable=False, default="info")  # 'info', 'warning', 'critical'
    message = Column(Text, nullable=False)
    
    # Alert conditions
    trigger_value = Column(DECIMAL(12, 2))  # The P/L value that triggered the alert
    trigger_percent = Column(DECIMAL(8, 4))  # The P/L percentage that triggered the alert
    threshold_value = Column(DECIMAL(12, 2))  # The threshold that was crossed
    
    # Notification status
    sent_at = Column(DateTime(timezone=True))
    delivery_method = Column(String(20))  # 'websocket', 'email', 'browser'
    delivery_status = Column(String(20), default="pending")  # 'pending', 'sent', 'failed'
    
    # Alert metadata
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            alert_type.in_(["profit_target", "stop_loss", "time_decay", "unusual_movement", "expiration_warning"]),
            name="check_alert_type"
        ),
        CheckConstraint(
            alert_level.in_(["info", "warning", "critical"]),
            name="check_alert_level"
        ),
        CheckConstraint(
            delivery_method.in_(["websocket", "email", "browser", "multiple"]),
            name="check_delivery_method"
        ),
        CheckConstraint(
            delivery_status.in_(["pending", "sent", "failed", "retry"]),
            name="check_delivery_status"
        ),
        Index("idx_alert_position", "position_id"),
        Index("idx_alert_type_level", "alert_type", "alert_level"),
        Index("idx_alert_delivery_status", "delivery_status"),
        Index("idx_alert_created", "created_at"),
    )
