"""
P/L Monitoring Service for periodic snapshot storage and alert management.

This service runs in the background to periodically calculate and store P/L snapshots,
manage alerts, and integrate with the WebSocket system for real-time updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.position import Position, PLAlert
from app.services.pl_calculation_service import PLCalculationService
from app.services.websocket_service import WebSocketManager

logger = logging.getLogger(__name__)


class PLMonitorService:
    """
    Background service for P/L monitoring and snapshot management.
    
    Handles periodic P/L calculations, snapshot storage, alert generation,
    and integration with WebSocket broadcasting.
    """
    
    def __init__(
        self,
        pl_calculation_service: PLCalculationService,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize P/L monitoring service.
        
        Args:
            pl_calculation_service: Service for P/L calculations
            websocket_manager: WebSocket manager for real-time updates (optional)
        """
        self.pl_calculation_service = pl_calculation_service
        self.websocket_manager = websocket_manager
        
        # Configuration
        self.snapshot_interval = 900  # 15 minutes between snapshots (as per roadmap spec)
        self.alert_check_interval = 60  # 1 minute between alert checks
        self.cleanup_interval = 3600  # 1 hour between cleanup tasks
        
        # State
        self.is_running = False
        self.snapshot_task: Optional[asyncio.Task] = None
        self.alert_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the P/L monitoring service."""
        if self.is_running:
            logger.warning("P/L monitoring service is already running")
            return
        
        self.is_running = True
        
        # Start background tasks
        self.snapshot_task = asyncio.create_task(self._snapshot_loop())
        self.alert_task = asyncio.create_task(self._alert_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("P/L monitoring service started")
    
    async def stop(self) -> None:
        """Stop the P/L monitoring service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all tasks
        tasks = [self.snapshot_task, self.alert_task, self.cleanup_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("P/L monitoring service stopped")
    
    async def _snapshot_loop(self) -> None:
        """
        Background loop for periodic P/L snapshot storage.
        
        Runs every snapshot_interval seconds to calculate and store P/L snapshots
        for all open positions.
        """
        logger.info("P/L snapshot loop started")
        
        while self.is_running:
            try:
                await self._store_pl_snapshots()
                
            except Exception as e:
                logger.error(f"Error in P/L snapshot loop: {e}")
            
            # Wait for next snapshot interval
            await asyncio.sleep(self.snapshot_interval)
        
        logger.info("P/L snapshot loop ended")
    
    async def _alert_loop(self) -> None:
        """
        Background loop for alert checking and notification.
        
        Runs every alert_check_interval seconds to check for alert conditions
        and send notifications.
        """
        logger.info("P/L alert loop started")
        
        while self.is_running:
            try:
                await self._check_and_send_alerts()
                
            except Exception as e:
                logger.error(f"Error in P/L alert loop: {e}")
            
            # Wait for next alert check interval
            await asyncio.sleep(self.alert_check_interval)
        
        logger.info("P/L alert loop ended")
    
    async def _cleanup_loop(self) -> None:
        """
        Background loop for data cleanup and maintenance.
        
        Runs every cleanup_interval seconds to clean up old snapshots
        and acknowledged alerts.
        """
        logger.info("P/L cleanup loop started")
        
        while self.is_running:
            try:
                await self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"Error in P/L cleanup loop: {e}")
            
            # Wait for next cleanup interval
            await asyncio.sleep(self.cleanup_interval)
        
        logger.info("P/L cleanup loop ended")
    
    async def _store_pl_snapshots(self) -> None:
        """
        Calculate and store P/L snapshots for all open positions.
        """
        db = next(get_db())
        
        try:
            # Get all open positions
            open_positions = db.query(Position).filter(Position.status == "open").all()
            
            if not open_positions:
                logger.debug("No open positions found for snapshot storage")
                return
            
            snapshots_stored = 0
            
            for position in open_positions:
                try:
                    # Calculate P/L for this position
                    pl_data = await self.pl_calculation_service.calculate_position_pl(
                        position, db=db
                    )
                    
                    # Store the snapshot
                    snapshot = await self.pl_calculation_service.store_pl_snapshot(
                        pl_data, db=db
                    )
                    
                    snapshots_stored += 1
                    logger.debug(f"Stored P/L snapshot for position {position.id}")
                    
                except Exception as e:
                    logger.error(f"Error storing snapshot for position {position.id}: {e}")
                    continue
            
            logger.info(f"Stored {snapshots_stored} P/L snapshots")
            
        finally:
            db.close()
    
    async def _check_and_send_alerts(self) -> None:
        """
        Check for alert conditions and send notifications.
        """
        db = next(get_db())
        
        try:
            # Calculate portfolio P/L to check for alerts
            portfolio_pl = await self.pl_calculation_service.calculate_portfolio_pl(db=db)
            
            if portfolio_pl["total_positions"] == 0:
                return
            
            alerts_sent = 0
            
            for position_data in portfolio_pl["positions"]:
                if position_data.get("alert_triggered", False):
                    # Create alert record
                    alert = PLAlert(
                        position_id=position_data["position_id"],
                        snapshot_id=None,  # We'll link this later if needed
                        alert_type=position_data.get("alert_type", "unknown"),
                        alert_level=self._determine_alert_level(position_data.get("alert_type")),
                        message=position_data.get("alert_message", "Alert triggered"),
                        trigger_value=position_data.get("unrealized_pnl"),
                        trigger_percent=position_data.get("unrealized_pnl_percent"),
                        delivery_method="websocket",
                        delivery_status="pending"
                    )
                    
                    db.add(alert)
                    db.commit()
                    db.refresh(alert)
                    
                    # Send WebSocket notification if manager is available
                    if self.websocket_manager:
                        from app.services.websocket_service import PLUpdate
                        
                        position_update = PLUpdate(
                            position_id=position_data["position_id"],
                            symbol=position_data["symbol"],
                            contracts=position_data["contracts"],
                            unrealized_pnl=position_data["unrealized_pnl"],
                            unrealized_pnl_percent=position_data["unrealized_pnl_percent"],
                            current_total_value=position_data["current_total_value"],
                            entry_total_cost=position_data["entry_total_cost"],
                            position_delta=position_data.get("position_delta"),
                            position_theta=position_data.get("position_theta"),
                            daily_theta_decay=position_data.get("daily_theta_decay"),
                            alert_triggered=True,
                            alert_type=position_data.get("alert_type"),
                            alert_message=position_data.get("alert_message"),
                            current_spy_price=position_data.get("current_spy_price", 0.0),
                            market_session=position_data.get("market_session", "regular"),
                            timestamp=datetime.now().isoformat()
                        )
                        
                        await self.websocket_manager.broadcast_position_pl_update(position_update)
                        
                        # Update alert delivery status
                        alert.delivery_status = "sent"
                        alert.sent_at = datetime.utcnow()
                        db.commit()
                    
                    alerts_sent += 1
                    logger.info(f"Sent alert for position {position_data['position_id']}: {position_data.get('alert_message')}")
            
            if alerts_sent > 0:
                logger.info(f"Sent {alerts_sent} P/L alerts")
                
        except Exception as e:
            logger.error(f"Error checking and sending alerts: {e}")
        finally:
            db.close()
    
    async def _cleanup_old_data(self) -> None:
        """
        Clean up old P/L snapshots and acknowledged alerts.
        """
        db = next(get_db())
        
        try:
            # Clean up snapshots older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            from app.models.position import PositionPLSnapshot
            
            old_snapshots = db.query(PositionPLSnapshot).filter(
                PositionPLSnapshot.created_at < cutoff_date
            ).count()
            
            if old_snapshots > 0:
                db.query(PositionPLSnapshot).filter(
                    PositionPLSnapshot.created_at < cutoff_date
                ).delete()
                
                logger.info(f"Cleaned up {old_snapshots} old P/L snapshots")
            
            # Clean up acknowledged alerts older than 7 days
            alert_cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            old_alerts = db.query(PLAlert).filter(
                PLAlert.is_acknowledged == True,
                PLAlert.created_at < alert_cutoff_date
            ).count()
            
            if old_alerts > 0:
                db.query(PLAlert).filter(
                    PLAlert.is_acknowledged == True,
                    PLAlert.created_at < alert_cutoff_date
                ).delete()
                
                logger.info(f"Cleaned up {old_alerts} old acknowledged alerts")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
        finally:
            db.close()
    
    def _determine_alert_level(self, alert_type: Optional[str]) -> str:
        """
        Determine alert level based on alert type.
        
        Args:
            alert_type: Type of alert
            
        Returns:
            Alert level string
        """
        if alert_type == "stop_loss":
            return "critical"
        elif alert_type == "profit_target":
            return "info"
        elif alert_type == "time_decay":
            return "warning"
        elif alert_type == "expiration_warning":
            return "warning"
        else:
            return "info"
    
    async def force_snapshot(self) -> int:
        """
        Force an immediate P/L snapshot for all open positions.
        
        Returns:
            Number of snapshots stored
        """
        logger.info("Forcing immediate P/L snapshot")
        await self._store_pl_snapshots()
        
        # Return count of open positions
        db = next(get_db())
        try:
            count = db.query(Position).filter(Position.status == "open").count()
            return count
        finally:
            db.close()
    
    async def force_alert_check(self) -> int:
        """
        Force an immediate alert check for all open positions.
        
        Returns:
            Number of alerts sent
        """
        logger.info("Forcing immediate alert check")
        await self._check_and_send_alerts()
        
        # This is a simplified return - in practice you'd track alerts sent
        return 0
