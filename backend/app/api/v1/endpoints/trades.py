"""Trade management API endpoints."""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_db
from app.models.trading import Trade, TradeSpread
from app.schemas.trades import (
    TradeCreate,
    TradeListResponse,
    TradeResponse,
    TradeSummary,
    TradeUpdate,
    TradeWithSpread,
)
from app.services.trade_position_integration_service import (
    TradePositionIntegrationService,
    TradePositionIntegrationError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=TradeListResponse)
async def get_trades(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    trade_date: date | None = None,
    status: str | None = None,
    trade_type: str | None = None,
    db: Session = Depends(get_db),
):
    """Get all trades with optional filtering."""
    query = db.query(Trade)

    # Apply filters
    if trade_date:
        query = query.filter(Trade.trade_date == trade_date)
    if status:
        query = query.filter(Trade.status == status)
    if trade_type:
        query = query.filter(Trade.trade_type == trade_type)

    # Get total count for pagination
    total = query.count()

    # Apply pagination and ordering
    trades = (
        query.order_by(Trade.trade_date.desc(), Trade.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return TradeListResponse(
        trades=[TradeResponse.model_validate(trade) for trade in trades],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=TradeSummary)
async def get_trade_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    """Get trade summary statistics."""
    query = db.query(Trade).filter(Trade.status == "exited")

    if start_date:
        query = query.filter(Trade.trade_date >= start_date)
    if end_date:
        query = query.filter(Trade.trade_date <= end_date)

    trades = query.all()

    if not trades:
        return TradeSummary(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
        )

    # Calculate statistics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.net_pnl and t.net_pnl > 0)
    losing_trades = sum(1 for t in trades if t.net_pnl and t.net_pnl < 0)

    total_pnl = sum(float(t.net_pnl) for t in trades if t.net_pnl)
    wins = [float(t.net_pnl) for t in trades if t.net_pnl and t.net_pnl > 0]
    losses = [float(t.net_pnl) for t in trades if t.net_pnl and t.net_pnl < 0]

    return TradeSummary(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=(
            round((winning_trades / total_trades) * 100, 2) if total_trades > 0 else 0.0
        ),
        total_pnl=round(total_pnl, 2),
        average_win=round(sum(wins) / len(wins), 2) if wins else 0.0,
        average_loss=round(sum(losses) / len(losses), 2) if losses else 0.0,
        largest_win=round(max(wins), 2) if wins else 0.0,
        largest_loss=round(min(losses), 2) if losses else 0.0,
    )


@router.get("/{trade_id}", response_model=TradeWithSpread)
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get a specific trade by ID."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return TradeWithSpread.model_validate(trade)


@router.post("/", response_model=TradeResponse)
async def create_trade(trade_data: TradeCreate, db: Session = Depends(get_db)):
    """Create a new trade with automatic position tracking integration."""
    try:
        # Start database transaction
        db.begin()
        
        # Create the trade
        trade = Trade(
            trade_date=trade_data.trade_date,
            trade_type=trade_data.trade_type,
            status=trade_data.status,
            entry_time=trade_data.entry_time,
            entry_sentiment_score_id=trade_data.entry_sentiment_score_id,
            entry_signal_reason=trade_data.entry_signal_reason,
            contracts=trade_data.contracts,
            max_risk=trade_data.max_risk,
            max_reward=trade_data.max_reward,
            probability_of_profit=trade_data.probability_of_profit,
            notes=trade_data.notes,
        )

        db.add(trade)
        db.flush()  # Get the trade ID

        # Create the associated spread if provided
        if trade_data.spread:
            spread = TradeSpread(
                trade_id=trade.id,
                spread_type=trade_data.spread.spread_type,
                expiration_date=trade_data.spread.expiration_date,
                long_strike=trade_data.spread.long_strike,
                long_premium=trade_data.spread.long_premium,
                long_iv=trade_data.spread.long_iv,
                long_delta=trade_data.spread.long_delta,
                long_gamma=trade_data.spread.long_gamma,
                long_theta=trade_data.spread.long_theta,
                short_strike=trade_data.spread.short_strike,
                short_premium=trade_data.spread.short_premium,
                short_iv=trade_data.spread.short_iv,
                short_delta=trade_data.spread.short_delta,
                short_gamma=trade_data.spread.short_gamma,
                short_theta=trade_data.spread.short_theta,
                net_debit=trade_data.spread.net_debit,
                max_profit=trade_data.spread.max_profit,
                max_loss=trade_data.spread.max_loss,
                breakeven=trade_data.spread.breakeven,
                risk_reward_ratio=trade_data.spread.risk_reward_ratio,
            )
            db.add(spread)
            db.flush()  # Ensure spread is available for position creation

        # Integrate with position tracking system
        integration_service = TradePositionIntegrationService(db)
        integration_result = await integration_service.handle_trade_creation(trade)
        
        # Commit the transaction
        db.commit()
        db.refresh(trade)
        
        logger.info(f"Successfully created trade {trade.id} with integration result: {integration_result}")
        
        return TradeResponse.model_validate(trade)
        
    except TradePositionIntegrationError as e:
        logger.error(f"Trade-position integration failed: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Trade creation failed due to position integration error: {str(e)}"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during trade creation: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Trade creation failed due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error during trade creation: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Trade creation failed due to unexpected error"
        )


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int, trade_data: TradeUpdate, db: Session = Depends(get_db)
):
    """Update an existing trade with position lifecycle management."""
    try:
        # Start database transaction
        db.begin()
        
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")

        # Store original status for comparison
        original_status = trade.status

        # Update trade fields
        update_data = trade_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(trade, field):
                setattr(trade, field, value)

        # Update timestamp
        trade.updated_at = datetime.utcnow()
        
        # Handle position integration if status changed
        integration_result = None
        if trade.status != original_status:
            integration_service = TradePositionIntegrationService(db)
            integration_result = await integration_service.handle_trade_update(trade)
            
            logger.info(f"Trade {trade_id} status changed from {original_status} to {trade.status}")
            logger.info(f"Position integration result: {integration_result}")

        # Commit the transaction
        db.commit()
        db.refresh(trade)
        
        return TradeResponse.model_validate(trade)
        
    except TradePositionIntegrationError as e:
        logger.error(f"Trade-position integration failed for trade {trade_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Trade update failed due to position integration error: {str(e)}"
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during trade update: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Trade update failed due to database error"
        )
    except Exception as e:
        logger.error(f"Unexpected error during trade update: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Trade update failed due to unexpected error"
        )


@router.delete("/{trade_id}")
async def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    """Delete a trade."""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    # Delete associated spread first (if exists)
    spread = db.query(TradeSpread).filter(TradeSpread.trade_id == trade_id).first()
    if spread:
        db.delete(spread)

    db.delete(trade)
    db.commit()

    return {"message": "Trade deleted successfully"}


@router.get("/recent/activity")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)
):
    """Get recent trading activity for dashboard."""
    trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(limit).all()

    return [
        {
            "id": trade.id,
            "trade_date": trade.trade_date,
            "status": trade.status,
            "trade_type": trade.trade_type,
            "net_pnl": float(trade.net_pnl) if trade.net_pnl else None,
            "created_at": trade.created_at,
        }
        for trade in trades
    ]
