"""Trade management endpoints."""
from datetime import date
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.api import deps
from app.models.trading import Trade, TradeSpread
from app.models.trade_schemas import (
    TradeCreate, TradeUpdate, TradeResponse, TradeListResponse,
    TradePnLRequest, TradePnLResponse
)
from app.core.database import get_db

router = APIRouter()


@router.post("/", response_model=TradeResponse, status_code=201)
async def create_trade(
    trade_in: TradeCreate,
    db: Session = Depends(get_db)
):
    """Create a new trade record."""
    # Create the trade
    trade = Trade(
        trade_date=trade_in.trade_date,
        trade_type=trade_in.trade_type,
        status=trade_in.status,
        entry_time=trade_in.entry_time,
        entry_sentiment_score_id=trade_in.entry_sentiment_score_id,
        entry_signal_reason=trade_in.entry_signal_reason,
        contracts=trade_in.contracts,
        max_risk=trade_in.max_risk,
        max_reward=trade_in.max_reward,
        probability_of_profit=trade_in.probability_of_profit,
        exit_time=trade_in.exit_time,
        exit_reason=trade_in.exit_reason,
        exit_price=trade_in.exit_price,
        gross_pnl=trade_in.gross_pnl,
        commissions=trade_in.commissions,
        net_pnl=trade_in.net_pnl,
        pnl_percentage=trade_in.pnl_percentage,
        notes=trade_in.notes
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    
    # Create the spread if provided
    if trade_in.spread:
        spread = TradeSpread(
            trade_id=trade.id,
            spread_type=trade_in.spread.spread_type,
            expiration_date=trade_in.spread.expiration_date,
            long_strike=trade_in.spread.long_strike,
            short_strike=trade_in.spread.short_strike,
            long_premium=trade_in.spread.long_premium,
            short_premium=trade_in.spread.short_premium,
            net_debit=trade_in.spread.net_debit,
            max_profit=trade_in.spread.max_profit,
            max_loss=trade_in.spread.max_loss,
            breakeven=trade_in.spread.breakeven,
            risk_reward_ratio=trade_in.spread.risk_reward_ratio,
            long_iv=trade_in.spread.long_iv,
            long_delta=trade_in.spread.long_delta,
            long_gamma=trade_in.spread.long_gamma,
            long_theta=trade_in.spread.long_theta,
            short_iv=trade_in.spread.short_iv,
            short_delta=trade_in.spread.short_delta,
            short_gamma=trade_in.spread.short_gamma,
            short_theta=trade_in.spread.short_theta
        )
        db.add(spread)
        db.commit()
        db.refresh(spread)
        trade.spread = spread
    
    return trade


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific trade by ID."""
    trade = db.query(Trade).options(joinedload(Trade.spread)).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.get("/", response_model=TradeListResponse)
async def list_trades(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    status: Optional[str] = Query(None, description="Filter by status"),
    trade_type: Optional[str] = Query(None, description="Filter by trade type"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List trades with optional filters."""
    query = db.query(Trade).options(joinedload(Trade.spread))
    
    # Apply filters
    filters = []
    if start_date:
        filters.append(Trade.trade_date >= start_date)
    if end_date:
        filters.append(Trade.trade_date <= end_date)
    if status:
        filters.append(Trade.status == status)
    if trade_type:
        filters.append(Trade.trade_type == trade_type)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Order by trade date descending
    query = query.order_by(Trade.trade_date.desc(), Trade.id.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    trades = query.offset(offset).limit(per_page).all()
    
    # Calculate pages
    pages = (total + per_page - 1) // per_page
    
    return TradeListResponse(
        items=trades,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.patch("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_update: TradeUpdate,
    db: Session = Depends(get_db)
):
    """Update a trade record."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    # Update fields if provided
    update_data = trade_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trade, field, value)
    
    db.commit()
    db.refresh(trade)
    
    # Load spread relationship
    trade = db.query(Trade).options(joinedload(Trade.spread)).filter(Trade.id == trade_id).first()
    return trade


@router.post("/{trade_id}/calculate-pnl", response_model=TradePnLResponse)
async def calculate_pnl(
    trade_id: int,
    pnl_request: TradePnLRequest,
    db: Session = Depends(get_db)
):
    """Calculate P/L for a trade based on exit price."""
    trade = db.query(Trade).options(joinedload(Trade.spread)).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if not trade.spread:
        raise HTTPException(status_code=400, detail="Trade has no spread details")
    
    if not trade.contracts:
        raise HTTPException(status_code=400, detail="Trade has no contract quantity")
    
    spread = trade.spread
    exit_price = pnl_request.exit_price
    
    # Calculate intrinsic value at exit
    if exit_price <= spread.long_strike:
        # Both options expire worthless
        exit_value = Decimal("0")
    elif exit_price >= spread.short_strike:
        # Maximum profit - both options ITM
        exit_value = spread.short_strike - spread.long_strike
    else:
        # Partial profit - only long option ITM
        exit_value = exit_price - spread.long_strike
    
    # Calculate P/L
    entry_cost = spread.net_debit
    gross_pnl_per_contract = exit_value - entry_cost
    gross_pnl = gross_pnl_per_contract * trade.contracts * 100  # Convert to dollars
    
    # Calculate commissions (entry + exit)
    commissions = pnl_request.commission_per_contract * trade.contracts * 2
    
    # Net P/L
    net_pnl = gross_pnl - commissions
    
    # P/L percentage (based on max risk)
    max_risk = spread.net_debit * trade.contracts * 100
    pnl_percentage = (net_pnl / max_risk * 100) if max_risk > 0 else Decimal("0")
    
    return TradePnLResponse(
        gross_pnl=gross_pnl,
        commissions=commissions,
        net_pnl=net_pnl,
        pnl_percentage=pnl_percentage,
        exit_value=exit_value * 100  # Convert to dollars
    )


@router.delete("/{trade_id}", status_code=204)
async def delete_trade(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """Delete a trade record."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    # Delete associated spread first (if exists)
    if trade.spread:
        db.delete(trade.spread)
    
    db.delete(trade)
    db.commit()
    
    return None