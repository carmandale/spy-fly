"""
Pydantic schemas for position P/L endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PositionPLResponse(BaseModel):
    """Response model for a single position's P/L data."""
    id: int
    symbol: str
    long_strike: float
    short_strike: float
    quantity: int
    entry_value: float
    current_value: float
    unrealized_pl: float
    unrealized_pl_percent: float
    risk_percent: float
    stop_loss_alert: bool
    last_update: Optional[str] = None

    class Config:
        orm_mode = True


class CurrentPLResponse(BaseModel):
    """Response model for current P/L of all positions."""
    positions: List[PositionPLResponse]
    total_unrealized_pl: float
    spy_price: float


class PLHistoryItem(BaseModel):
    """Single P/L history snapshot."""
    timestamp: str
    unrealized_pl: float
    unrealized_pl_percent: float
    spy_price: float
    current_value: float


class PLHistoryResponse(BaseModel):
    """Response model for position P/L history."""
    position_id: int
    history: List[PLHistoryItem]


class CalculatePLResponse(BaseModel):
    """Response model for P/L calculation trigger."""
    success: bool
    positions_updated: int
    calculation_time_ms: int
    timestamp: str