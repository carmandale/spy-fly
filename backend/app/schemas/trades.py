"""Pydantic schemas for trade-related API operations."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TradeSpreadBase(BaseModel):
    """Base schema for trade spread data."""

    spread_type: str = Field(default="bull_call_spread")
    expiration_date: date

    # Long leg
    long_strike: Decimal = Field(decimal_places=2)
    long_premium: Decimal = Field(decimal_places=2)
    long_iv: Decimal | None = Field(None, decimal_places=2)
    long_delta: Decimal | None = Field(None, decimal_places=4)
    long_gamma: Decimal | None = Field(None, decimal_places=4)
    long_theta: Decimal | None = Field(None, decimal_places=4)

    # Short leg
    short_strike: Decimal = Field(decimal_places=2)
    short_premium: Decimal = Field(decimal_places=2)
    short_iv: Decimal | None = Field(None, decimal_places=2)
    short_delta: Decimal | None = Field(None, decimal_places=4)
    short_gamma: Decimal | None = Field(None, decimal_places=4)
    short_theta: Decimal | None = Field(None, decimal_places=4)

    # Spread metrics
    net_debit: Decimal = Field(decimal_places=2)
    max_profit: Decimal = Field(decimal_places=2)
    max_loss: Decimal = Field(decimal_places=2)
    breakeven: Decimal = Field(decimal_places=2)
    risk_reward_ratio: Decimal = Field(decimal_places=2)


class TradeSpreadCreate(TradeSpreadBase):
    """Schema for creating a new trade spread."""

    pass


class TradeSpreadResponse(TradeSpreadBase):
    """Schema for trade spread responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_id: int
    created_at: datetime


class TradeBase(BaseModel):
    """Base schema for trade data."""

    trade_date: date
    trade_type: str = Field(..., pattern="^(paper|real)$")
    status: str = Field(..., pattern="^(recommended|skipped|entered|exited|stopped)$")

    # Entry details
    entry_time: datetime | None = None
    entry_sentiment_score_id: int | None = None
    entry_signal_reason: str | None = None

    # Position details
    contracts: int | None = None
    max_risk: Decimal | None = Field(None, decimal_places=2)
    max_reward: Decimal | None = Field(None, decimal_places=2)
    probability_of_profit: Decimal | None = Field(None, decimal_places=2)

    # Exit details
    exit_time: datetime | None = None
    exit_reason: str | None = None
    exit_price: Decimal | None = Field(None, decimal_places=2)

    # P/L calculation
    gross_pnl: Decimal | None = Field(None, decimal_places=2)
    commissions: Decimal | None = Field(None, decimal_places=2)
    net_pnl: Decimal | None = Field(None, decimal_places=2)
    pnl_percentage: Decimal | None = Field(None, decimal_places=2)

    # Metadata
    notes: str | None = None


class TradeCreate(TradeBase):
    """Schema for creating a new trade."""

    spread: TradeSpreadCreate | None = None


class TradeUpdate(BaseModel):
    """Schema for updating an existing trade."""

    status: str | None = Field(
        None, pattern="^(recommended|skipped|entered|exited|stopped)$"
    )

    # Entry details
    entry_time: datetime | None = None
    entry_signal_reason: str | None = None

    # Position details
    contracts: int | None = None
    max_risk: Decimal | None = Field(None, decimal_places=2)
    max_reward: Decimal | None = Field(None, decimal_places=2)
    probability_of_profit: Decimal | None = Field(None, decimal_places=2)

    # Exit details
    exit_time: datetime | None = None
    exit_reason: str | None = None
    exit_price: Decimal | None = Field(None, decimal_places=2)

    # P/L calculation
    gross_pnl: Decimal | None = Field(None, decimal_places=2)
    commissions: Decimal | None = Field(None, decimal_places=2)
    net_pnl: Decimal | None = Field(None, decimal_places=2)
    pnl_percentage: Decimal | None = Field(None, decimal_places=2)

    # Metadata
    notes: str | None = None


class TradeResponse(TradeBase):
    """Schema for trade responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class TradeWithSpread(TradeResponse):
    """Schema for trade responses including spread data."""

    spread: TradeSpreadResponse | None = None


class TradeListResponse(BaseModel):
    """Schema for paginated trade list responses."""

    trades: list[TradeResponse]
    total: int
    skip: int
    limit: int


class TradeSummary(BaseModel):
    """Schema for trade summary statistics."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
