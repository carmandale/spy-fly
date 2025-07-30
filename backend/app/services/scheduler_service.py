"""
Scheduler Service for SPY-FLY trading system.

This service manages automated jobs including:
- Morning scan job that runs at 9:45 AM ET daily
- P/L snapshot job that runs every 15 minutes during market hours
"""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Optional
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.orm import Session

from app.models.db_models import MorningScanResult, Position, PositionSnapshot
from app.core.database import get_db
from app.services.spread_selection_service import SpreadSelectionService
from app.services.pl_calculation_service import PLCalculationService
from app.services.websocket_service import WebSocketManager, PLUpdate, PLPositionUpdate

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for managing scheduled jobs.
    
    This service manages:
    - Morning scan at 9:45 AM ET for trading recommendations
    - P/L snapshots every 15 minutes during market hours
    """
    
    def __init__(
        self, 
        spread_selection_service: Optional[SpreadSelectionService] = None,
        db_session: Optional[Session] = None,
        pl_service: Optional[PLCalculationService] = None,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Initialize the scheduler service.
        
        Args:
            spread_selection_service: Service for generating spread recommendations
            db_session: Database session for P/L snapshots
            pl_service: P/L calculation service
            websocket_manager: WebSocket manager for broadcasting updates
        """
        self.spread_service = spread_selection_service
        self.db_session = db_session
        self.pl_service = pl_service
        self.websocket_manager = websocket_manager
        self.scheduler = None
        self._is_running = False
        
        # Configure scheduler with timezone awareness
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,  # Run multiple instances if needed
            'max_instances': 1,  # But only one at a time
            'misfire_grace_time': 300  # 5 minutes grace period
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/New_York'  # ET timezone for market hours
        )
        
    async def start(self) -> None:
        """Start the scheduler and add scheduled jobs."""
        if self._is_running:
            logger.warning("Scheduler is already running")
            return
            
        try:
            # Add the morning scan job if spread service is available
            if self.spread_service:
                self.scheduler.add_job(
                    func=self._morning_scan_job,
                    trigger=CronTrigger(
                        hour=9,
                        minute=45,
                        day_of_week='mon-fri',
                        timezone='America/New_York'
                    ),
                    id='morning_scan',
                    name='Morning Market Scan',
                    replace_existing=True
                )
                logger.info("Morning scan job scheduled for 9:45 AM ET")
            
            # Add P/L snapshot job if P/L service is available
            if self.pl_service:
                self.scheduler.add_job(
                    func=self.calculate_pl_snapshot,
                    trigger=IntervalTrigger(
                        minutes=15,
                        timezone='America/New_York'
                    ),
                    id='pl_snapshot',
                    name='P/L Snapshot Every 15 Minutes',
                    replace_existing=True
                )
                logger.info("P/L snapshot job scheduled for every 15 minutes")
            
            # Start the scheduler
            self.scheduler.start()
            self._is_running = True
            logger.info("Scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    async def start_scheduler(self) -> None:
        """Legacy method name - delegates to start()."""
        await self.start()
    
    async def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._is_running:
            logger.warning("Scheduler is not running")
            return
            
        try:
            # Use shutdown() without wait=True for async compatibility
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            raise
    
    async def stop_scheduler(self) -> None:
        """Legacy method name - delegates to stop()."""
        await self.stop()
    
    async def trigger_manual_scan(self, account_size: float = 100000.0) -> dict[str, Any]:
        """
        Trigger a manual morning scan for testing purposes.
        
        Args:
            account_size: Account size for position sizing calculations
            
        Returns:
            Dictionary containing scan results and metadata
        """
        logger.info("Starting manual morning scan")
        
        try:
            # Execute the morning scan logic
            scan_result = await self._execute_morning_scan(account_size)
            
            # Log the manual scan
            await self._log_scan_result(scan_result, is_manual=True)
            
            logger.info(f"Manual scan completed - found {len(scan_result['recommendations'])} recommendations")
            return scan_result
            
        except Exception as e:
            logger.error(f"Manual scan failed: {e}")
            error_result = {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'scan_time': datetime.now(),
                'account_size': account_size
            }
            await self._log_scan_result(error_result, is_manual=True)
            return error_result
    
    async def _morning_scan_job(self) -> None:
        """
        Scheduled job that runs the morning market scan.
        
        This is the core scheduled job that runs at 9:45 AM ET daily.
        """
        logger.info("Starting scheduled morning scan at 9:45 AM ET")
        
        try:
            # Use default account size for automated scans
            # In production, this could be configurable per user
            default_account_size = 100000.0
            
            # Execute the morning scan
            scan_result = await self._execute_morning_scan(default_account_size)
            
            # Log the scan result to database
            await self._log_scan_result(scan_result, is_manual=False)
            
            # Send notifications if there are high-quality recommendations
            await self._process_scan_notifications(scan_result)
            
            logger.info(f"Morning scan completed - found {len(scan_result['recommendations'])} recommendations")
            
        except Exception as e:
            logger.error(f"Morning scan job failed: {e}")
            # Log the failure
            error_result = {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'scan_time': datetime.now(),
                'account_size': 100000.0
            }
            await self._log_scan_result(error_result, is_manual=False)
    
    async def _execute_morning_scan(self, account_size: float) -> dict[str, Any]:
        """
        Execute the morning scan logic.
        
        Args:
            account_size: Account size for position sizing
            
        Returns:
            Dictionary containing scan results
        """
        scan_start_time = datetime.now()
        
        try:
            # Get spread recommendations using existing service
            recommendations = await self.spread_service.get_recommendations(
                account_size=account_size,
                max_recommendations=10  # Get more for morning scan
            )
            
            # Calculate scan metrics
            scan_metrics = {
                'total_recommendations': len(recommendations),
                'high_quality_count': len([r for r in recommendations if r.ranking_score > 0.7]),
                'avg_probability': sum(r.probability_of_profit for r in recommendations) / len(recommendations) if recommendations else 0,
                'avg_risk_reward': sum(r.risk_reward_ratio for r in recommendations) / len(recommendations) if recommendations else 0,
            }
            
            return {
                'success': True,
                'recommendations': recommendations,
                'scan_time': scan_start_time,
                'account_size': account_size,
                'metrics': scan_metrics,
                'duration_seconds': (datetime.now() - scan_start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error executing morning scan: {e}")
            raise
    
    async def _log_scan_result(self, scan_result: dict[str, Any], is_manual: bool = False) -> None:
        """
        Log the scan result to the database.
        
        Args:
            scan_result: Result dictionary from morning scan
            is_manual: Whether this was a manual or scheduled scan
        """
        try:
            # Create database record of the scan
            scan_record = MorningScanResult(
                scan_time=scan_result['scan_time'],
                success=scan_result['success'],
                recommendations_count=len(scan_result['recommendations']),
                account_size=scan_result['account_size'],
                is_manual=is_manual,
                error_message=scan_result.get('error'),
                scan_metrics=scan_result.get('metrics', {}),
                duration_seconds=scan_result.get('duration_seconds', 0)
            )
            
            # Save to database
            db = next(get_db())
            try:
                db.add(scan_record)
                db.commit()
                logger.info(f"Scan result logged to database (ID: {scan_record.id})")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to log scan result to database: {e}")
            # Don't raise - logging failure shouldn't break the scan
    
    async def _process_scan_notifications(self, scan_result: dict[str, Any]) -> None:
        """
        Process notifications for high-quality scan results.
        
        Args:
            scan_result: Result dictionary from morning scan
        """
        if not scan_result['success']:
            return
            
        recommendations = scan_result['recommendations']
        high_quality_recs = [r for r in recommendations if r.ranking_score > 0.7]
        
        if high_quality_recs:
            logger.info(f"Found {len(high_quality_recs)} high-quality recommendations - notifications would be sent here")
            # TODO: Implement email/push notification logic
            # This could integrate with email service or push notification service
    
    def get_status(self) -> dict[str, Any]:
        """
        Get current scheduler status.
        
        Returns:
            Dictionary containing scheduler status information
        """
        if not self.scheduler:
            return {'status': 'not_initialized'}
            
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'status': 'running' if self._is_running else 'stopped',
            'jobs': jobs,
            'timezone': str(self.scheduler.timezone)
        }
    
    def get_next_scan_time(self) -> datetime | None:
        """
        Get the next scheduled scan time.
        
        Returns:
            Next scan time or None if not scheduled
        """
        if not self.scheduler:
            return None
            
        morning_scan_job = self.scheduler.get_job('morning_scan')
        if morning_scan_job:
            return morning_scan_job.next_run_time
            
        return None
    
    async def calculate_pl_snapshot(self) -> None:
        """
        Calculate and store P/L snapshot for all open positions.
        
        This job runs every 15 minutes during market hours to capture
        position values and broadcast updates via WebSocket.
        """
        if not self._is_market_hours():
            logger.debug("Skipping P/L snapshot - outside market hours")
            return
        
        if not self.pl_service or not self.db_session:
            logger.warning("P/L snapshot skipped - missing required services")
            return
        
        logger.debug("Starting P/L snapshot calculation")
        
        try:
            # Calculate P/L for all positions
            pl_results = await self.pl_service.calculate_all_positions_pl()
            
            if not pl_results:
                logger.debug("No positions found for P/L snapshot")
                return
            
            # Store snapshots in database
            snapshots_created = []
            positions_data = []
            has_alert = False
            
            for pl_data in pl_results:
                # Create position snapshot
                snapshot = PositionSnapshot(
                    position_id=pl_data.position_id,
                    spy_price=pl_data.spy_price,
                    current_value=pl_data.current_value,
                    unrealized_pl=pl_data.unrealized_pl,
                    unrealized_pl_percent=pl_data.unrealized_pl_percent,
                    risk_percent=pl_data.risk_percent,
                    stop_loss_triggered=pl_data.stop_loss_triggered,
                    snapshot_time=pl_data.calculation_time
                )
                
                self.db_session.add(snapshot)
                snapshots_created.append(snapshot)
                
                # Update position with latest values
                position = self.db_session.query(Position).filter_by(id=pl_data.position_id).first()
                if position:
                    position.latest_value = pl_data.current_value
                    position.latest_unrealized_pl = pl_data.unrealized_pl
                    position.latest_unrealized_pl_percent = pl_data.unrealized_pl_percent
                    position.stop_loss_alert_active = pl_data.stop_loss_triggered
                
                # Prepare WebSocket data
                position_update = PLPositionUpdate(
                    id=pl_data.position_id,
                    symbol="SPY",
                    unrealized_pl=float(pl_data.unrealized_pl),
                    unrealized_pl_percent=float(pl_data.unrealized_pl_percent),
                    current_value=float(pl_data.current_value),
                    stop_loss_alert=pl_data.stop_loss_triggered
                )
                positions_data.append(position_update)
                
                if pl_data.stop_loss_triggered:
                    has_alert = True
            
            # Commit database changes
            self.db_session.commit()
            
            # Broadcast WebSocket update if manager is available
            if self.websocket_manager and positions_data:
                total_pl = sum(float(pl.unrealized_pl) for pl in pl_results)
                spy_price = float(pl_results[0].spy_price) if pl_results else 0.0
                
                pl_update = PLUpdate(
                    positions=positions_data,
                    total_unrealized_pl=total_pl,
                    spy_price=spy_price,
                    timestamp=datetime.now().isoformat() + "Z",
                    alert=has_alert
                )
                
                await self.websocket_manager.broadcast_pl_update(pl_update)
            
            logger.info(f"P/L snapshot completed - {len(snapshots_created)} snapshots created")
            
            if has_alert:
                logger.warning("Stop-loss alerts detected in P/L snapshot")
        
        except Exception as e:
            logger.error(f"Error in P/L snapshot calculation: {e}")
            # Rollback any partial database changes
            if self.db_session:
                self.db_session.rollback()
    
    def _is_market_hours(self) -> bool:
        """
        Check if current time is during regular market hours (9:30 AM - 4:00 PM ET).
        
        Returns:
            True if during market hours, False otherwise
        """
        now = datetime.now()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if now.weekday() > 4:  # Saturday or Sunday
            return False
        
        # Get current time in ET
        current_time = now.time()
        market_open = time(9, 30)  # 9:30 AM ET
        market_close = time(16, 0)  # 4:00 PM ET
        
        return market_open <= current_time <= market_close