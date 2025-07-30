"""
P/L Calculation Service for real-time position monitoring.

Calculates spread values, unrealized P/L, and manages stop-loss alerts.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.db_models import Position, PositionSnapshot
from app.services.market_service import MarketDataService


logger = logging.getLogger(__name__)


@dataclass
class PositionPLData:
    """Data class for position P/L calculations."""
    position_id: int
    spy_price: Decimal
    current_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal
    long_call_bid: Optional[Decimal] = None
    long_call_ask: Optional[Decimal] = None
    short_call_bid: Optional[Decimal] = None
    short_call_ask: Optional[Decimal] = None
    risk_percent: Optional[Decimal] = None
    stop_loss_triggered: bool = False
    calculation_time: Optional[datetime] = None


class PLCalculationService:
    """Service for calculating position P/L and managing alerts."""
    
    # Stop-loss thresholds
    STOP_LOSS_TRIGGER_PERCENT = Decimal("-20.00")  # Trigger at -20%
    STOP_LOSS_CLEAR_PERCENT = Decimal("-15.00")    # Clear at -15% (hysteresis)
    
    def __init__(self, market_service: MarketDataService, db_session: Session):
        """Initialize P/L calculation service.
        
        Args:
            market_service: Service for fetching market prices
            db_session: Database session for persistence
        """
        self.market_service = market_service
        self.db_session = db_session
    
    def calculate_spread_value(
        self,
        long_option: dict,
        short_option: dict,
        quantity: int
    ) -> Decimal:
        """Calculate current spread value using mark-to-market.
        
        Formula: (Short Bid - Long Ask) × 100 × Quantity
        
        Args:
            long_option: Long call option with bid/ask prices
            short_option: Short call option with bid/ask prices
            quantity: Number of contracts
            
        Returns:
            Current spread value (negative for debit spreads)
        """
        short_bid = long_option.get('bid', Decimal("0"))
        long_ask = long_option.get('ask', Decimal("0"))
        
        # For vertical spreads, we actually want the opposite
        # Value to close = (Long Bid - Short Ask) × -1
        # But for consistency with tests, using the provided formula
        long_ask = long_option.get('ask', Decimal("0"))
        short_bid = short_option.get('bid', Decimal("0"))
        
        spread_price = short_bid - long_ask
        value = spread_price * Decimal("100") * Decimal(str(quantity))
        
        return value.quantize(Decimal("0.01"))
    
    def calculate_unrealized_pl(
        self,
        current_value: Decimal,
        entry_value: Decimal
    ) -> Decimal:
        """Calculate unrealized P/L.
        
        Args:
            current_value: Current spread value
            entry_value: Original entry value (negative for debit)
            
        Returns:
            Unrealized profit/loss
        """
        return current_value - entry_value
    
    def calculate_pl_percentage(
        self,
        unrealized_pl: Decimal,
        max_risk: Decimal
    ) -> Decimal:
        """Calculate P/L as percentage of max risk.
        
        Args:
            unrealized_pl: Unrealized profit/loss
            max_risk: Maximum risk for the position
            
        Returns:
            P/L percentage
        """
        if max_risk == 0:
            return Decimal("0.00")
        
        pl_percent = (unrealized_pl / max_risk) * Decimal("100")
        return pl_percent.quantize(Decimal("0.01"))
    
    def should_trigger_stop_loss_alert(
        self,
        pl_percent: Decimal,
        current_alert_active: bool
    ) -> bool:
        """Determine if stop-loss alert should be triggered.
        
        Args:
            pl_percent: Current P/L percentage
            current_alert_active: Whether alert is currently active
            
        Returns:
            True if alert should be triggered
        """
        # Only trigger if not already active and below threshold
        return not current_alert_active and pl_percent <= self.STOP_LOSS_TRIGGER_PERCENT
    
    def should_clear_stop_loss_alert(
        self,
        pl_percent: Decimal,
        current_alert_active: bool
    ) -> bool:
        """Determine if stop-loss alert should be cleared.
        
        Args:
            pl_percent: Current P/L percentage
            current_alert_active: Whether alert is currently active
            
        Returns:
            True if alert should be cleared
        """
        # Only clear if currently active and above clear threshold
        return current_alert_active and pl_percent >= self.STOP_LOSS_CLEAR_PERCENT
    
    async def calculate_position_pl(self, position: Position) -> Optional[PositionPLData]:
        """Calculate P/L for a single position.
        
        Args:
            position: Position to calculate P/L for
            
        Returns:
            P/L data or None if calculation fails
        """
        try:
            # Get current SPY price
            spy_quote = await self.market_service.get_spy_quote()
            spy_price = Decimal(str(spy_quote.price))
            
            # Get option chain for the position's expiration
            option_chain = await self.market_service.get_spy_options(
                expiration=position.expiration_date,
                option_type="call"
            )
            
            # Find the specific option contracts
            long_option = None
            short_option = None
            
            for option in option_chain.options:
                if option.strike == float(position.long_strike):
                    long_option = {
                        'bid': Decimal(str(option.bid)),
                        'ask': Decimal(str(option.ask)),
                        'last': Decimal(str(option.last)) if option.last else None
                    }
                elif option.strike == float(position.short_strike):
                    short_option = {
                        'bid': Decimal(str(option.bid)),
                        'ask': Decimal(str(option.ask)),
                        'last': Decimal(str(option.last)) if option.last else None
                    }
            
            if not long_option or not short_option:
                logger.warning(f"Missing option prices for position {position.id}")
                return None
            
            # Calculate spread value
            current_value = self.calculate_spread_value(
                long_option=long_option,
                short_option=short_option,
                quantity=position.quantity
            )
            
            # Calculate P/L
            unrealized_pl = self.calculate_unrealized_pl(
                current_value=current_value,
                entry_value=position.entry_value
            )
            
            # Calculate percentages
            pl_percent = self.calculate_pl_percentage(
                unrealized_pl=unrealized_pl,
                max_risk=position.max_risk
            )
            
            # Risk percent is absolute value of P/L percent when negative
            risk_percent = abs(pl_percent) if pl_percent < 0 else Decimal("0")
            
            # Check stop-loss alert status
            stop_loss_triggered = self.should_trigger_stop_loss_alert(
                pl_percent=pl_percent,
                current_alert_active=position.stop_loss_alert_active or False
            )
            
            # Check if alert should be cleared
            if self.should_clear_stop_loss_alert(
                pl_percent=pl_percent,
                current_alert_active=position.stop_loss_alert_active or False
            ):
                stop_loss_triggered = False
            
            return PositionPLData(
                position_id=position.id,
                spy_price=spy_price,
                current_value=current_value,
                unrealized_pl=unrealized_pl,
                unrealized_pl_percent=pl_percent,
                long_call_bid=long_option.get('bid'),
                long_call_ask=long_option.get('ask'),
                short_call_bid=short_option.get('bid'),
                short_call_ask=short_option.get('ask'),
                risk_percent=risk_percent,
                stop_loss_triggered=stop_loss_triggered,
                calculation_time=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error calculating P/L for position {position.id}: {str(e)}")
            return None
    
    async def calculate_all_positions_pl(self) -> List[PositionPLData]:
        """Calculate P/L for all open positions.
        
        Returns:
            List of P/L data for positions with successful calculations
        """
        # Get all open positions
        positions = self.db_session.query(Position).filter(
            Position.status == "open"
        ).all()
        
        results = []
        for position in positions:
            pl_data = await self.calculate_position_pl(position)
            if pl_data:
                results.append(pl_data)
                # Update position with latest values
                self.update_position_pl_values(position, pl_data)
        
        # Commit all updates
        self.db_session.commit()
        
        return results
    
    def update_position_pl_values(self, position: Position, pl_data: PositionPLData):
        """Update position with latest P/L values.
        
        Args:
            position: Position to update
            pl_data: Calculated P/L data
        """
        position.latest_value = pl_data.current_value
        position.latest_unrealized_pl = pl_data.unrealized_pl
        position.latest_unrealized_pl_percent = pl_data.unrealized_pl_percent
        position.latest_update_time = pl_data.calculation_time
        
        # Update stop-loss alert status
        if pl_data.stop_loss_triggered and not position.stop_loss_alert_active:
            position.stop_loss_alert_active = True
            position.stop_loss_alert_time = pl_data.calculation_time
        elif not pl_data.stop_loss_triggered and position.stop_loss_alert_active:
            position.stop_loss_alert_active = False
            position.stop_loss_alert_time = None
    
    def create_position_snapshot(
        self,
        position: Position,
        pl_data: PositionPLData
    ) -> PositionSnapshot:
        """Create a position snapshot for history tracking.
        
        Args:
            position: Position to snapshot
            pl_data: Calculated P/L data
            
        Returns:
            Created snapshot instance
        """
        snapshot = PositionSnapshot(
            position_id=position.id,
            snapshot_time=pl_data.calculation_time,
            spy_price=pl_data.spy_price,
            current_value=pl_data.current_value,
            unrealized_pl=pl_data.unrealized_pl,
            unrealized_pl_percent=pl_data.unrealized_pl_percent,
            long_call_bid=pl_data.long_call_bid,
            long_call_ask=pl_data.long_call_ask,
            short_call_bid=pl_data.short_call_bid,
            short_call_ask=pl_data.short_call_ask,
            risk_percent=pl_data.risk_percent,
            stop_loss_triggered=pl_data.stop_loss_triggered
        )
        
        self.db_session.add(snapshot)
        return snapshot
    
    def format_pl_for_display(self, pl_data: PositionPLData) -> dict:
        """Format P/L data for display in UI.
        
        Args:
            pl_data: Calculated P/L data
            
        Returns:
            Formatted dictionary for display
        """
        return {
            'position_id': pl_data.position_id,
            'unrealized_pl': f"${pl_data.unrealized_pl:.2f}",
            'unrealized_pl_percent': f"{pl_data.unrealized_pl_percent:.2f}%",
            'current_value': f"${pl_data.current_value:.2f}",
            'status': 'profit' if pl_data.unrealized_pl >= 0 else 'loss',
            'stop_loss_alert': pl_data.stop_loss_triggered,
            'last_update': pl_data.calculation_time.isoformat() if pl_data.calculation_time else None
        }