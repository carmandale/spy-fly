"""Pydantic schemas for trade-related API models."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TradeSpreadBase(BaseModel):
    """Base schema for trade spread data."""
    spread_type: str = Field(default="bull_call_spread")
    expiration_date: date
    long_strike: Decimal = Field(..., ge=0, decimal_places=2)
    short_strike: Decimal = Field(..., ge=0, decimal_places=2)
    long_premium: Decimal = Field(..., ge=0, decimal_places=2)
    short_premium: Decimal = Field(..., ge=0, decimal_places=2)
    net_debit: Decimal = Field(..., ge=0, decimal_places=2)
    max_profit: Decimal = Field(..., ge=0, decimal_places=2)
    max_loss: Decimal = Field(..., ge=0, decimal_places=2)
    breakeven: Decimal = Field(..., ge=0, decimal_places=2)
    risk_reward_ratio: Decimal = Field(..., ge=0, decimal_places=2)
    
    # Optional Greeks
    long_iv: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)
    long_delta: Optional[Decimal] = Field(None, ge=-1, le=1, decimal_places=4)
    long_gamma: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    long_theta: Optional[Decimal] = Field(None, decimal_places=4)
    short_iv: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)
    short_delta: Optional[Decimal] = Field(None, ge=-1, le=1, decimal_places=4)
    short_gamma: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    short_theta: Optional[Decimal] = Field(None, decimal_places=4)


class TradeSpreadCreate(TradeSpreadBase):
    """Schema for creating a trade spread."""
    pass


class TradeSpreadResponse(TradeSpreadBase):
    """Schema for trade spread response."""
    id: int
    trade_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TradeBase(BaseModel):
    """Base schema for trade data."""
    trade_date: date
    trade_type: str = Field(..., pattern="^(paper|real)$")
    status: str = Field(..., pattern="^(recommended|skipped|entered|exited|stopped)$")
    
    # Entry details
    entry_time: Optional[datetime] = None
    entry_sentiment_score_id: Optional[int] = None
    entry_signal_reason: Optional[str] = None
    
    # Position details
    contracts: Optional[int] = Field(None, ge=1)
    max_risk: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    max_reward: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    probability_of_profit: Optional[Decimal] = Field(None, ge=0, le=100, decimal_places=2)
    
    # Exit details
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = Field(None, max_length=50)
    exit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # P/L
    gross_pnl: Optional[Decimal] = Field(None, decimal_places=2)
    commissions: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    net_pnl: Optional[Decimal] = Field(None, decimal_places=2)
    pnl_percentage: Optional[Decimal] = Field(None, decimal_places=2)
    
    # Metadata
    notes: Optional[str] = None


class TradeCreate(TradeBase):
    """Schema for creating a trade."""
    spread: Optional[TradeSpreadCreate] = None


class TradeUpdate(BaseModel):
    """Schema for updating a trade."""
    status: Optional[str] = Field(None, pattern="^(recommended|skipped|entered|exited|stopped)$")
    
    # Exit details
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = Field(None, max_length=50)
    exit_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    
    # P/L
    gross_pnl: Optional[Decimal] = Field(None, decimal_places=2)
    commissions: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    net_pnl: Optional[Decimal] = Field(None, decimal_places=2)
    pnl_percentage: Optional[Decimal] = Field(None, decimal_places=2)
    
    notes: Optional[str] = None


class TradeResponse(TradeBase):
    """Schema for trade response."""
    id: int
    created_at: datetime
    updated_at: datetime
    spread: Optional[TradeSpreadResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class TradeListResponse(BaseModel):
    """Schema for paginated trade list response."""
    items: List[TradeResponse]
    total: int
    page: int = 1
    per_page: int = 50
    pages: int


class TradePnLRequest(BaseModel):
    """Schema for P/L calculation request."""
    exit_price: Decimal = Field(..., ge=0, decimal_places=2)
    commission_per_contract: Decimal = Field(default=Decimal("0.65"), ge=0, decimal_places=2)


class TradePnLResponse(BaseModel):
    """Schema for P/L calculation response."""
    gross_pnl: Decimal
    commissions: Decimal
    net_pnl: Decimal
    pnl_percentage: Decimal
    exit_value: Decimal