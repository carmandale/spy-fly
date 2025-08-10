"""
Position management API endpoints.

Provides REST API endpoints for managing spread positions, viewing P/L data,
and accessing historical snapshots and alerts.
"""

from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.models.position import Position, PositionPLSnapshot, PLAlert
from app.services.pl_calculation_service import PLCalculationService
from app.services.market_service import MarketDataService
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter
from app.config import settings

router = APIRouter()

# Pydantic models for API requests/responses

class PositionCreate(BaseModel):
    """Model for creating a new position."""
    
    symbol: str = Field(default="SPY", description="Underlying symbol")
    position_type: str = Field(description="Type of spread position")
    contracts: int = Field(gt=0, description="Number of contracts")
    entry_date: date = Field(description="Position entry date")
    expiration_date: date = Field(description="Option expiration date")
    
    # Spread configuration
    long_strike: float = Field(description="Long option strike price")
    short_strike: float = Field(description="Short option strike price")
    
    # Entry pricing
    entry_long_premium: float = Field(description="Long option premium paid")
    entry_short_premium: float = Field(description="Short option premium received")
    entry_net_debit: float = Field(description="Net debit paid for spread")
    entry_total_cost: float = Field(description="Total cost of position")
    
    # Risk metrics
    max_profit: float = Field(description="Maximum profit potential")
    max_loss: float = Field(description="Maximum loss potential")
    breakeven_price: float = Field(description="Breakeven price")
    
    # Entry market conditions
    entry_spy_price: float = Field(description="SPY price at entry")
    entry_vix: Optional[float] = Field(None, description="VIX level at entry")
    entry_sentiment_score: Optional[float] = Field(None, description="Sentiment score at entry")
    
    # Position management
    profit_target_percent: float = Field(default=50.0, description="Profit target as % of max profit")
    stop_loss_percent: float = Field(default=20.0, description="Stop loss as % of max loss")
    
    notes: Optional[str] = Field(None, description="Optional notes")


class PositionUpdate(BaseModel):
    """Model for updating an existing position."""
    
    profit_target_percent: Optional[float] = Field(None, description="Updated profit target %")
    stop_loss_percent: Optional[float] = Field(None, description="Updated stop loss %")
    notes: Optional[str] = Field(None, description="Updated notes")


class PositionClose(BaseModel):
    """Model for closing a position."""
    
    exit_reason: str = Field(description="Reason for closing position")
    exit_long_premium: float = Field(description="Long option premium received")
    exit_short_premium: float = Field(description="Short option premium paid")
    exit_net_credit: float = Field(description="Net credit received for spread")
    exit_total_value: float = Field(description="Total value received")


class PositionResponse(BaseModel):
    """Model for position API responses."""
    
    id: int
    symbol: str
    position_type: str
    status: str
    contracts: int
    entry_date: date
    expiration_date: date
    
    # Spread configuration
    long_strike: float
    short_strike: float
    
    # Entry pricing
    entry_long_premium: float
    entry_short_premium: float
    entry_net_debit: float
    entry_total_cost: float
    
    # Risk metrics
    max_profit: float
    max_loss: float
    breakeven_price: float
    
    # Entry market conditions
    entry_spy_price: float
    entry_vix: Optional[float]
    entry_sentiment_score: Optional[float]
    
    # Exit details (if closed)
    exit_date: Optional[date]
    exit_time: Optional[datetime]
    exit_reason: Optional[str]
    exit_long_premium: Optional[float]
    exit_short_premium: Optional[float]
    exit_net_credit: Optional[float]
    exit_total_value: Optional[float]
    
    # Final P/L (if closed)
    realized_pnl: Optional[float]
    realized_pnl_percent: Optional[float]
    
    # Position management
    profit_target_percent: float
    stop_loss_percent: float
    
    # Metadata
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PLSnapshotResponse(BaseModel):
    """Model for P/L snapshot API responses."""
    
    id: int
    position_id: int
    snapshot_time: datetime
    market_session: str
    
    # Market data
    spy_price: float
    vix_level: Optional[float]
    
    # Current pricing
    current_long_premium: Optional[float]
    current_short_premium: Optional[float]
    current_net_value: Optional[float]
    current_total_value: Optional[float]
    
    # P/L calculations
    unrealized_pnl: float
    unrealized_pnl_percent: float
    
    # Greeks
    position_delta: Optional[float]
    position_gamma: Optional[float]
    position_theta: Optional[float]
    position_vega: Optional[float]
    
    # Time decay
    time_to_expiry_hours: Optional[float]
    daily_theta_decay: Optional[float]
    
    # Alert info
    alert_triggered: bool
    alert_type: Optional[str]
    
    # Data quality
    data_source: str
    calculation_method: str
    data_quality_score: Optional[float]
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """Model for alert API responses."""
    
    id: int
    position_id: int
    alert_type: str
    alert_level: str
    message: str
    
    # Alert conditions
    trigger_value: Optional[float]
    trigger_percent: Optional[float]
    threshold_value: Optional[float]
    
    # Notification status
    sent_at: Optional[datetime]
    delivery_method: Optional[str]
    delivery_status: str
    
    # Alert metadata
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CurrentPLResponse(BaseModel):
    """Model for current P/L calculation responses."""
    
    position_id: int
    symbol: str
    contracts: int
    current_spy_price: float
    time_to_expiry_hours: float
    
    # Current pricing
    current_long_premium: float
    current_short_premium: float
    current_net_value: float
    current_total_value: float
    
    # P/L calculations
    entry_total_cost: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    
    # Greeks and risk metrics
    position_delta: Optional[float]
    position_gamma: Optional[float]
    position_theta: Optional[float]
    position_vega: Optional[float]
    daily_theta_decay: Optional[float]
    
    # Alert information
    alert_triggered: bool
    alert_type: Optional[str]
    alert_message: Optional[str]
    
    # Metadata
    market_session: str
    calculation_timestamp: datetime
    data_quality_score: float


class PortfolioPLResponse(BaseModel):
    """Model for portfolio P/L responses."""
    
    total_positions: int
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    total_daily_theta: float
    current_spy_price: float
    calculation_timestamp: datetime
    positions: List[CurrentPLResponse]


# API Endpoints

@router.get("/", response_model=List[PositionResponse])
async def get_positions(
    status: Optional[str] = Query(None, description="Filter by position status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, le=1000, description="Maximum number of positions to return"),
    offset: int = Query(0, ge=0, description="Number of positions to skip"),
    db: Session = Depends(get_db)
):
    """
    Get list of positions with optional filtering.
    
    Returns paginated list of positions with optional status and symbol filtering.
    """
    query = db.query(Position)
    
    if status:
        query = query.filter(Position.status == status)
    
    if symbol:
        query = query.filter(Position.symbol == symbol)
    
    positions = query.offset(offset).limit(limit).all()
    
    return [PositionResponse.model_validate(position) for position in positions]


@router.post("/", response_model=PositionResponse)
async def create_position(
    position_data: PositionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new position.
    
    Creates a new spread position with the provided details.
    """
    # Validate position type
    valid_types = ["bull_call_spread", "bear_put_spread"]
    if position_data.position_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid position_type. Must be one of: {valid_types}"
        )
    
    # Create position
    position = Position(
        symbol=position_data.symbol,
        position_type=position_data.position_type,
        contracts=position_data.contracts,
        entry_date=position_data.entry_date,
        expiration_date=position_data.expiration_date,
        long_strike=position_data.long_strike,
        short_strike=position_data.short_strike,
        entry_long_premium=position_data.entry_long_premium,
        entry_short_premium=position_data.entry_short_premium,
        entry_net_debit=position_data.entry_net_debit,
        entry_total_cost=position_data.entry_total_cost,
        max_profit=position_data.max_profit,
        max_loss=position_data.max_loss,
        breakeven_price=position_data.breakeven_price,
        entry_spy_price=position_data.entry_spy_price,
        entry_vix=position_data.entry_vix,
        entry_sentiment_score=position_data.entry_sentiment_score,
        profit_target_percent=position_data.profit_target_percent,
        stop_loss_percent=position_data.stop_loss_percent,
        notes=position_data.notes
    )
    
    db.add(position)
    db.commit()
    db.refresh(position)
    
    return PositionResponse.model_validate(position)


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific position by ID.
    
    Returns detailed information about a single position.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return PositionResponse.model_validate(position)


@router.put("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    position_update: PositionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a position's management parameters.
    
    Updates profit target, stop loss, and notes for an existing position.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if position.status != "open":
        raise HTTPException(status_code=400, detail="Can only update open positions")
    
    # Update fields if provided
    if position_update.profit_target_percent is not None:
        position.profit_target_percent = position_update.profit_target_percent
    
    if position_update.stop_loss_percent is not None:
        position.stop_loss_percent = position_update.stop_loss_percent
    
    if position_update.notes is not None:
        position.notes = position_update.notes
    
    position.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(position)
    
    return PositionResponse.model_validate(position)


@router.post("/{position_id}/close", response_model=PositionResponse)
async def close_position(
    position_id: int,
    close_data: PositionClose,
    db: Session = Depends(get_db)
):
    """
    Close an open position.
    
    Records exit details and calculates final P/L for the position.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if position.status != "open":
        raise HTTPException(status_code=400, detail="Position is not open")
    
    # Update position with exit details
    position.status = "closed"
    position.exit_date = datetime.utcnow().date()
    position.exit_time = datetime.utcnow()
    position.exit_reason = close_data.exit_reason
    position.exit_long_premium = close_data.exit_long_premium
    position.exit_short_premium = close_data.exit_short_premium
    position.exit_net_credit = close_data.exit_net_credit
    position.exit_total_value = close_data.exit_total_value
    
    # Calculate realized P/L
    position.realized_pnl = close_data.exit_total_value - float(position.entry_total_cost)
    position.realized_pnl_percent = (position.realized_pnl / float(position.entry_total_cost)) * 100
    
    position.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(position)
    
    return PositionResponse.model_validate(position)


@router.get("/{position_id}/pl/current", response_model=CurrentPLResponse)
async def get_current_pl(
    position_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current P/L calculation for a position.
    
    Returns real-time P/L data including Greeks and alert status.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if position.status != "open":
        raise HTTPException(status_code=400, detail="Can only calculate P/L for open positions")
    
    # Initialize services (in a real app, these would be injected)
    market_service = MarketDataService()
    bs_calculator = BlackScholesCalculator()
    pl_service = PLCalculationService(market_service, bs_calculator)
    
    try:
        pl_data = await pl_service.calculate_position_pl(position, db=db)
        return CurrentPLResponse(**pl_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating P/L: {str(e)}")


@router.get("/pl/portfolio", response_model=PortfolioPLResponse)
async def get_portfolio_pl(
    db: Session = Depends(get_db)
):
    """
    Get current portfolio P/L across all open positions.
    
    Returns aggregated P/L data for all open positions.
    """
    # Initialize services (in a real app, these would be injected)
    market_service = MarketDataService()
    bs_calculator = BlackScholesCalculator()
    pl_service = PLCalculationService(market_service, bs_calculator)
    
    try:
        portfolio_data = await pl_service.calculate_portfolio_pl(db=db)
        
        # Convert position data to CurrentPLResponse objects
        positions = [CurrentPLResponse(**pos_data) for pos_data in portfolio_data["positions"]]
        
        return PortfolioPLResponse(
            total_positions=portfolio_data["total_positions"],
            total_unrealized_pnl=portfolio_data["total_unrealized_pnl"],
            total_unrealized_pnl_percent=portfolio_data["total_unrealized_pnl_percent"],
            total_daily_theta=portfolio_data["total_daily_theta"],
            current_spy_price=portfolio_data["current_spy_price"],
            calculation_timestamp=portfolio_data["calculation_timestamp"],
            positions=positions
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating portfolio P/L: {str(e)}")


@router.get("/{position_id}/snapshots", response_model=List[PLSnapshotResponse])
async def get_position_snapshots(
    position_id: int,
    limit: int = Query(100, le=1000, description="Maximum number of snapshots to return"),
    offset: int = Query(0, ge=0, description="Number of snapshots to skip"),
    db: Session = Depends(get_db)
):
    """
    Get historical P/L snapshots for a position.
    
    Returns paginated list of P/L snapshots ordered by snapshot time.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    snapshots = (
        db.query(PositionPLSnapshot)
        .filter(PositionPLSnapshot.position_id == position_id)
        .order_by(PositionPLSnapshot.snapshot_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [PLSnapshotResponse.model_validate(snapshot) for snapshot in snapshots]


@router.get("/{position_id}/alerts", response_model=List[AlertResponse])
async def get_position_alerts(
    position_id: int,
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(100, le=1000, description="Maximum number of alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip"),
    db: Session = Depends(get_db)
):
    """
    Get alerts for a position.
    
    Returns paginated list of alerts with optional acknowledgment filtering.
    """
    position = db.query(Position).filter(Position.id == position_id).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    query = db.query(PLAlert).filter(PLAlert.position_id == position_id)
    
    if acknowledged is not None:
        query = query.filter(PLAlert.is_acknowledged == acknowledged)
    
    alerts = (
        query.order_by(PLAlert.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return [AlertResponse.model_validate(alert) for alert in alerts]


@router.post("/{position_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    position_id: int,
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    Marks an alert as acknowledged to prevent further notifications.
    """
    alert = (
        db.query(PLAlert)
        .filter(PLAlert.id == alert_id, PLAlert.position_id == position_id)
        .first()
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Alert acknowledged successfully"}
