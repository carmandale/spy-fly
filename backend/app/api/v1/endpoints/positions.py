"""
Position P/L calculation API endpoints.

Provides endpoints for current P/L, history, and manual calculation triggers.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_db
from app.models.db_models import Position, PositionSnapshot
from app.schemas.positions import (
    PositionPLResponse,
    CurrentPLResponse,
    PLHistoryResponse,
    PLHistoryItem,
    CalculatePLResponse
)
from app.services.pl_calculation_service import PLCalculationService
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)
router = APIRouter()


def get_pl_service(db: Session = Depends(get_db)) -> PLCalculationService:
    """Get P/L calculation service instance."""
    # Import settings to get API key
    from app.config import settings
    
    # Create market data service dependencies
    polygon_client = PolygonClient(api_key=settings.polygon_api_key)
    cache = MarketDataCache()
    rate_limiter = RateLimiter()
    
    market_service = MarketDataService(
        polygon_client=polygon_client,
        cache=cache,
        rate_limiter=rate_limiter
    )
    
    return PLCalculationService(
        market_service=market_service,
        db_session=db
    )


@router.get("/pl/current", response_model=CurrentPLResponse)
async def get_current_pl(
    db: Session = Depends(get_db),
    pl_service: PLCalculationService = Depends(get_pl_service)
) -> CurrentPLResponse:
    """Get current P/L for all open positions.
    
    Returns:
        Current P/L data for all open positions with total unrealized P/L
    """
    try:
        # Get all open positions
        positions = db.query(Position).filter(Position.status == "open").all()
        
        # Get current SPY price
        market_service = pl_service.market_service
        spy_quote = await market_service.get_spy_quote()
        spy_price = float(spy_quote.price)
        
        # Build response
        position_responses = []
        total_unrealized_pl = Decimal("0")
        
        for position in positions:
            position_data = PositionPLResponse(
                id=position.id,
                symbol=position.symbol,
                long_strike=float(position.long_strike),
                short_strike=float(position.short_strike),
                quantity=position.quantity,
                entry_value=float(position.entry_value),
                current_value=float(position.latest_value) if position.latest_value else 0.0,
                unrealized_pl=float(position.latest_unrealized_pl) if position.latest_unrealized_pl else 0.0,
                unrealized_pl_percent=float(position.latest_unrealized_pl_percent) if position.latest_unrealized_pl_percent else 0.0,
                risk_percent=float(abs(position.latest_unrealized_pl_percent)) if position.latest_unrealized_pl_percent and position.latest_unrealized_pl_percent < 0 else 0.0,
                stop_loss_alert=position.stop_loss_alert_active or False,
                last_update=position.latest_update_time.isoformat() + "Z" if position.latest_update_time else None
            )
            position_responses.append(position_data)
            
            if position.latest_unrealized_pl:
                total_unrealized_pl += position.latest_unrealized_pl
        
        return CurrentPLResponse(
            positions=position_responses,
            total_unrealized_pl=float(total_unrealized_pl),
            spy_price=spy_price
        )
        
    except Exception as e:
        logger.error(f"Error getting current P/L: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection error")


@router.get("/{position_id}/pl/history", response_model=PLHistoryResponse)
async def get_position_pl_history(
    position_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
) -> PLHistoryResponse:
    """Get P/L history for a specific position.
    
    Args:
        position_id: ID of the position
        hours: Number of hours of history to return (1-168, default 24)
        
    Returns:
        P/L history snapshots for the position
    """
    # Validate hours parameter
    if hours < 1 or hours > 168:
        raise HTTPException(status_code=400, detail="Invalid hours parameter. Must be between 1 and 168.")
    
    # Check if position exists
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Get snapshots for the time period
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    snapshots = db.query(PositionSnapshot).filter(
        PositionSnapshot.position_id == position_id,
        PositionSnapshot.snapshot_time >= cutoff_time
    ).order_by(desc(PositionSnapshot.snapshot_time)).all()
    
    # Build history response
    history_items = []
    for snapshot in snapshots:
        item = PLHistoryItem(
            timestamp=snapshot.snapshot_time.isoformat() + "Z",
            unrealized_pl=float(snapshot.unrealized_pl),
            unrealized_pl_percent=float(snapshot.unrealized_pl_percent),
            spy_price=float(snapshot.spy_price),
            current_value=float(snapshot.current_value)
        )
        history_items.append(item)
    
    return PLHistoryResponse(
        position_id=position_id,
        history=history_items
    )


@router.post("/pl/calculate", response_model=CalculatePLResponse)
async def calculate_pl(
    db: Session = Depends(get_db),
    pl_service: PLCalculationService = Depends(get_pl_service)
) -> CalculatePLResponse:
    """Trigger immediate P/L calculation for all positions.
    
    Returns:
        Calculation results including number of positions updated
    """
    try:
        start_time = datetime.utcnow()
        
        # Calculate P/L for all positions
        results = await pl_service.calculate_all_positions_pl()
        
        # Calculate execution time
        end_time = datetime.utcnow()
        calculation_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return CalculatePLResponse(
            success=True,
            positions_updated=len(results),
            calculation_time_ms=calculation_time_ms,
            timestamp=end_time.isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error(f"Error calculating P/L: {str(e)}")
        if "Market data unavailable" in str(e):
            raise HTTPException(status_code=503, detail="Market data unavailable")
        else:
            raise HTTPException(status_code=500, detail="Calculation error")