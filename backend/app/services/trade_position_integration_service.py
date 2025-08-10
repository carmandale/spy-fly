"""
Trade-Position Integration Service.

This service bridges the trade execution system with the position tracking system,
automatically creating Position records when trades are executed and managing
the position lifecycle based on trade status changes.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import ServiceError
from app.models.position import Position
from app.models.trading import Trade, TradeSpread
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter
from app.services.trade_to_position_mapper import TradeToPositionMapper

logger = logging.getLogger(__name__)


def _create_market_service() -> MarketDataService:
    """Create a properly initialized MarketDataService."""
    polygon_client = PolygonClient(
        api_key=settings.polygon_api_key,
        use_sandbox=settings.polygon_use_sandbox
    )
    cache = MarketDataCache(max_size=1000)
    rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
    return MarketDataService(polygon_client, cache, rate_limiter)


class TradePositionIntegrationError(ServiceError):
    """Exception raised for trade-position integration errors."""
    pass


class TradePositionIntegrationService:
    """
    Service for integrating trade execution with position tracking.
    
    This service handles:
    - Automatic position creation when trades are executed
    - Position lifecycle management based on trade status changes
    - Data consistency between trade and position systems
    - Error handling and transaction management
    """

    def __init__(
        self,
        db: Session,
        market_service: MarketDataService | None = None,
        mapper: TradeToPositionMapper | None = None
    ):
        self.db = db
        self.market_service = market_service or _create_market_service()
        self.mapper = mapper or TradeToPositionMapper()

    async def create_position_from_trade(self, trade: Trade) -> Position | None:
        """
        Create a Position record from a Trade record.
        
        Args:
            trade: The trade record to create a position from
            
        Returns:
            The created Position record, or None if position creation is not applicable
            
        Raises:
            TradePositionIntegrationError: If position creation fails
        """
        try:
            # Only create positions for entered trades with spreads
            if trade.status != "entered":
                logger.debug(f"Skipping position creation for trade {trade.id} with status {trade.status}")
                return None

            if not trade.spread:
                logger.debug(f"Skipping position creation for trade {trade.id} - no spread data")
                return None

            # Check if position already exists for this trade
            existing_position = self.db.query(Position).filter(
                Position.symbol == "SPY",  # Assuming SPY for now
                Position.entry_date == trade.trade_date,
                Position.long_strike == trade.spread.long_strike,
                Position.short_strike == trade.spread.short_strike,
                Position.expiration_date == trade.spread.expiration_date
            ).first()

            if existing_position:
                logger.info(f"Position already exists for trade {trade.id}: position {existing_position.id}")
                return existing_position

            # Get current market data for entry conditions
            current_spy_price = await self._get_current_spy_price()
            current_vix = await self._get_current_vix()

            # Map trade data to position data
            position_data = self.mapper.map_trade_to_position(
                trade=trade,
                current_spy_price=current_spy_price,
                current_vix=current_vix
            )

            # Create the position record
            position = Position(**position_data)
            self.db.add(position)
            self.db.flush()  # Get the position ID

            logger.info(f"Created position {position.id} from trade {trade.id}")
            return position

        except Exception as e:
            logger.error(f"Failed to create position from trade {trade.id}: {str(e)}")
            raise TradePositionIntegrationError(f"Position creation failed: {str(e)}") from e

    async def update_position_from_trade(self, trade: Trade) -> Position | None:
        """
        Update an existing position based on trade status changes.
        
        Args:
            trade: The updated trade record
            
        Returns:
            The updated Position record, or None if no position exists
            
        Raises:
            TradePositionIntegrationError: If position update fails
        """
        try:
            # Find the associated position
            position = await self._find_position_for_trade(trade)
            if not position:
                logger.debug(f"No position found for trade {trade.id}")
                return None

            # Handle different trade status updates
            if trade.status == "exited":
                await self._close_position_from_trade(position, trade)
            elif trade.status == "stopped":
                await self._close_position_from_trade(position, trade, exit_reason="stop_loss")
            elif trade.status == "skipped":
                # If trade was skipped, we might want to delete the position
                # or mark it as cancelled, depending on business logic
                position.status = "cancelled"
                logger.info(f"Marked position {position.id} as cancelled due to skipped trade {trade.id}")

            self.db.flush()
            return position

        except Exception as e:
            logger.error(f"Failed to update position from trade {trade.id}: {str(e)}")
            raise TradePositionIntegrationError(f"Position update failed: {str(e)}") from e

    async def handle_trade_creation(self, trade: Trade) -> dict[str, Any]:
        """
        Handle the complete trade creation workflow including position creation.
        
        Args:
            trade: The newly created trade
            
        Returns:
            Dictionary containing trade and position information
            
        Raises:
            TradePositionIntegrationError: If the integration workflow fails
        """
        result = {
            "trade_id": trade.id,
            "position_created": False,
            "position_id": None,
            "websocket_event_sent": False
        }

        try:
            # Create position if applicable
            position = await self.create_position_from_trade(trade)

            if position:
                result["position_created"] = True
                result["position_id"] = position.id

                # Send WebSocket notification for new position
                await self._send_position_websocket_event(position, "position_created")
                result["websocket_event_sent"] = True

                logger.info(f"Successfully integrated trade {trade.id} with position {position.id}")

            return result

        except Exception as e:
            logger.error(f"Trade creation integration failed for trade {trade.id}: {str(e)}")
            raise TradePositionIntegrationError(f"Trade integration failed: {str(e)}") from e

    async def handle_trade_update(self, trade: Trade) -> dict[str, Any]:
        """
        Handle trade updates and sync changes to positions.
        
        Args:
            trade: The updated trade
            
        Returns:
            Dictionary containing update information
            
        Raises:
            TradePositionIntegrationError: If the update workflow fails
        """
        result = {
            "trade_id": trade.id,
            "position_updated": False,
            "position_id": None,
            "websocket_event_sent": False
        }

        try:
            # Update associated position
            position = await self.update_position_from_trade(trade)

            if position:
                result["position_updated"] = True
                result["position_id"] = position.id

                # Send WebSocket notification for position update
                event_type = "position_closed" if position.status == "closed" else "position_updated"
                await self._send_position_websocket_event(position, event_type)
                result["websocket_event_sent"] = True

                logger.info(f"Successfully updated position {position.id} from trade {trade.id}")

            return result

        except Exception as e:
            logger.error(f"Trade update integration failed for trade {trade.id}: {str(e)}")
            raise TradePositionIntegrationError(f"Trade update integration failed: {str(e)}") from e

    async def _find_position_for_trade(self, trade: Trade) -> Position | None:
        """Find the position associated with a trade."""
        if not trade.spread:
            return None

        return self.db.query(Position).filter(
            Position.symbol == "SPY",  # Assuming SPY for now
            Position.entry_date == trade.trade_date,
            Position.long_strike == trade.spread.long_strike,
            Position.short_strike == trade.spread.short_strike,
            Position.expiration_date == trade.spread.expiration_date,
            Position.status.in_(["open", "closed"])  # Don't match cancelled positions
        ).first()

    async def _close_position_from_trade(
        self,
        position: Position,
        trade: Trade,
        exit_reason: str = "manual_exit"
    ) -> None:
        """Close a position based on trade exit information."""
        try:
            # Update position with exit information
            position.status = "closed"
            position.exit_date = trade.trade_date
            position.exit_time = trade.exit_time or datetime.utcnow()
            position.exit_reason = exit_reason

            # Calculate exit values from trade data
            if trade.spread and trade.exit_price:
                # Use trade exit price to calculate position exit values
                # This is a simplified calculation - in practice, you'd need
                # to determine how the trade exit price maps to option premiums
                position.exit_total_value = float(trade.exit_price) * position.contracts * 100

                # Calculate realized P/L
                if position.entry_total_cost:
                    position.realized_pnl = position.exit_total_value - position.entry_total_cost
                    if position.entry_total_cost != 0:
                        position.realized_pnl_percent = (position.realized_pnl / position.entry_total_cost) * 100

            # If we have trade P/L data, use that instead
            if trade.net_pnl:
                position.realized_pnl = float(trade.net_pnl)
                if position.entry_total_cost and position.entry_total_cost != 0:
                    position.realized_pnl_percent = (position.realized_pnl / position.entry_total_cost) * 100

            logger.info(f"Closed position {position.id} with realized P/L: ${position.realized_pnl}")

        except Exception as e:
            logger.error(f"Failed to close position {position.id}: {str(e)}")
            raise

    async def _get_current_spy_price(self) -> float:
        """Get current SPY price from market service."""
        try:
            market_data = await self.market_service.get_spy_price()
            return market_data.get("price", 0.0)
        except Exception as e:
            logger.warning(f"Failed to get current SPY price: {str(e)}")
            return 0.0

    async def _get_current_vix(self) -> float | None:
        """Get current VIX level from market service."""
        try:
            vix_data = await self.market_service.get_vix_data()
            return vix_data.get("current_level")
        except Exception as e:
            logger.warning(f"Failed to get current VIX: {str(e)}")
            return None

    async def _send_position_websocket_event(self, position: Position, event_type: str) -> None:
        """Send WebSocket event for position changes."""
        try:
            # Import here to avoid circular imports
            from app.services.websocket_service import WebSocketService

            websocket_service = WebSocketService()

            # Create position event data
            event_data = {
                "type": event_type,
                "position_id": position.id,
                "symbol": position.symbol,
                "status": position.status,
                "contracts": position.contracts,
                "entry_total_cost": float(position.entry_total_cost) if position.entry_total_cost else 0.0,
                "realized_pnl": float(position.realized_pnl) if position.realized_pnl else None,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Send the event
            await websocket_service.broadcast_position_event(event_data)

            logger.debug(f"Sent WebSocket event {event_type} for position {position.id}")

        except Exception as e:
            logger.warning(f"Failed to send WebSocket event for position {position.id}: {str(e)}")
            # Don't raise - WebSocket failures shouldn't break the main workflow

    async def cleanup_orphaned_positions(self) -> int:
        """
        Clean up positions that don't have corresponding trades.
        
        Returns:
            Number of positions cleaned up
        """
        try:
            # Find positions without corresponding trades
            orphaned_positions = self.db.query(Position).filter(
                ~Position.id.in_(
                    self.db.query(Position.id)
                    .join(TradeSpread,
                          (Position.long_strike == TradeSpread.long_strike) &
                          (Position.short_strike == TradeSpread.short_strike) &
                          (Position.expiration_date == TradeSpread.expiration_date))
                    .join(Trade, TradeSpread.trade_id == Trade.id)
                    .filter(Trade.status.in_(["entered", "exited", "stopped"]))
                )
            ).all()

            count = len(orphaned_positions)

            if count > 0:
                logger.info(f"Found {count} orphaned positions for cleanup")

                for position in orphaned_positions:
                    position.status = "cancelled"
                    position.notes = (position.notes or "") + " [Auto-cancelled: no corresponding trade]"

                self.db.flush()
                logger.info(f"Cleaned up {count} orphaned positions")

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned positions: {str(e)}")
            raise TradePositionIntegrationError(f"Cleanup failed: {str(e)}") from e
