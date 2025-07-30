"""
Tests for scheduled P/L snapshot functionality.

Tests the integration of scheduled jobs that capture P/L snapshots
every 15 minutes during market hours and store them for historical tracking.
"""

import pytest
import asyncio
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models.db_models import Position, PositionSnapshot
from app.services.pl_calculation_service import PLCalculationService, PositionPLData
from app.services.scheduler_service import SchedulerService
from app.services.websocket_service import WebSocketManager


class TestPLSnapshotScheduling:
    """Test scheduled P/L snapshot functionality."""
    
    @pytest.fixture
    def mock_market_service(self):
        """Create mock market data service."""
        mock = Mock()
        mock.get_spy_quote = AsyncMock()
        mock.get_option_quotes = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_pl_service(self):
        """Create mock P/L calculation service."""
        mock = Mock(spec=PLCalculationService)
        mock.calculate_all_positions_pl = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_websocket_manager(self, mock_market_service):
        """Create mock WebSocket manager."""
        mock = Mock(spec=WebSocketManager)
        mock.broadcast_pl_update = AsyncMock()
        return mock
    
    @pytest.fixture
    def scheduler_service(self, db, mock_pl_service, mock_websocket_manager):
        """Create scheduler service with mocked dependencies."""
        return SchedulerService(
            db_session=db,
            pl_service=mock_pl_service,
            websocket_manager=mock_websocket_manager
        )
    
    @pytest.fixture
    def sample_positions(self, db):
        """Create sample positions for testing."""
        positions = [
            Position(
                id=1,
                symbol="SPY",
                long_strike=Decimal("450.00"),
                short_strike=Decimal("455.00"),
                expiration_date=date.today(),
                quantity=5,
                entry_value=Decimal("-250.00"),
                max_risk=Decimal("500.00"),
                max_profit=Decimal("250.00"),
                breakeven_price=Decimal("452.50"),
                status="open",
                latest_value=Decimal("-200.00"),
                latest_unrealized_pl=Decimal("50.00"),
                latest_unrealized_pl_percent=Decimal("10.00"),
                stop_loss_alert_active=False
            ),
            Position(
                id=2,
                symbol="SPY",
                long_strike=Decimal("448.00"),
                short_strike=Decimal("453.00"),
                expiration_date=date.today(),
                quantity=3,
                entry_value=Decimal("-150.00"),
                max_risk=Decimal("300.00"),
                max_profit=Decimal("150.00"),
                breakeven_price=Decimal("450.50"),
                status="open",
                latest_value=Decimal("-120.00"),
                latest_unrealized_pl=Decimal("30.00"),
                latest_unrealized_pl_percent=Decimal("10.00"),
                stop_loss_alert_active=False
            )
        ]
        
        for position in positions:
            db.add(position)
        db.commit()
        
        return positions
    
    @pytest.mark.asyncio
    async def test_calculate_pl_snapshot_job_basic(self, scheduler_service, sample_positions, mock_pl_service):
        """Test basic P/L snapshot calculation job."""
        # Mock P/L calculation results
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.25"),
                current_value=Decimal("-190.00"),
                unrealized_pl=Decimal("60.00"),
                unrealized_pl_percent=Decimal("12.00"),
                risk_percent=Decimal("-12.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            ),
            PositionPLData(
                position_id=2,
                spy_price=Decimal("451.25"),
                current_value=Decimal("-110.00"),
                unrealized_pl=Decimal("40.00"),
                unrealized_pl_percent=Decimal("13.33"),
                risk_percent=Decimal("-13.33"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Execute the snapshot job
        await scheduler_service.calculate_pl_snapshot()
        
        # Verify P/L calculation was called
        mock_pl_service.calculate_all_positions_pl.assert_called_once()
        
        # Verify snapshots were created in database
        snapshots = scheduler_service.db_session.query(PositionSnapshot).all()
        assert len(snapshots) == 2
        
        # Verify snapshot data for position 1
        snapshot_1 = next(s for s in snapshots if s.position_id == 1)
        assert snapshot_1.spy_price == Decimal("451.25")
        assert snapshot_1.position_value == Decimal("-190.00")
        assert snapshot_1.unrealized_pl == Decimal("60.00")
        assert snapshot_1.unrealized_pl_percent == Decimal("12.00")
        assert snapshot_1.stop_loss_alert is False
        
        # Verify snapshot data for position 2
        snapshot_2 = next(s for s in snapshots if s.position_id == 2)
        assert snapshot_2.spy_price == Decimal("451.25")
        assert snapshot_2.position_value == Decimal("-110.00")
        assert snapshot_2.unrealized_pl == Decimal("40.00")
        assert snapshot_2.unrealized_pl_percent == Decimal("13.33")
        assert snapshot_2.stop_loss_alert is False
    
    @pytest.mark.asyncio
    async def test_pl_snapshot_with_stop_loss_alerts(self, scheduler_service, sample_positions, mock_pl_service):
        """Test P/L snapshot when stop-loss alerts are triggered."""
        # Mock P/L data with stop-loss alert
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("448.50"),
                current_value=Decimal("-350.00"),
                unrealized_pl=Decimal("-100.00"),
                unrealized_pl_percent=Decimal("-20.00"),  # Stop-loss threshold
                risk_percent=Decimal("20.00"),
                stop_loss_triggered=True,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Execute snapshot job
        await scheduler_service.calculate_pl_snapshot()
        
        # Verify snapshot captured alert status
        snapshot = scheduler_service.db_session.query(PositionSnapshot).filter_by(position_id=1).first()
        assert snapshot is not None
        assert snapshot.stop_loss_alert is True
        assert snapshot.unrealized_pl_percent == Decimal("-20.00")
        
        # Verify WebSocket broadcast was called with alert
        scheduler_service.websocket_manager.broadcast_pl_update.assert_called_once()
        call_args = scheduler_service.websocket_manager.broadcast_pl_update.call_args[0][0]
        assert call_args.alert is True
        assert call_args.positions[0].stop_loss_alert is True
    
    @pytest.mark.asyncio
    async def test_pl_snapshot_with_no_positions(self, scheduler_service, mock_pl_service):
        """Test P/L snapshot job when no positions exist."""
        # Mock empty P/L results
        mock_pl_service.calculate_all_positions_pl.return_value = []
        
        # Execute snapshot job
        await scheduler_service.calculate_pl_snapshot()
        
        # Verify P/L calculation was still called
        mock_pl_service.calculate_all_positions_pl.assert_called_once()
        
        # Verify no snapshots were created
        snapshots = scheduler_service.db_session.query(PositionSnapshot).all()
        assert len(snapshots) == 0
        
        # Verify WebSocket was not called (no data to broadcast)
        scheduler_service.websocket_manager.broadcast_pl_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_pl_snapshot_error_handling(self, scheduler_service, sample_positions, mock_pl_service):
        """Test error handling in P/L snapshot job."""
        # Mock P/L service to raise exception
        mock_pl_service.calculate_all_positions_pl.side_effect = Exception("Market data unavailable")
        
        # Execute snapshot job - should not raise exception
        try:
            await scheduler_service.calculate_pl_snapshot()
        except Exception:
            pytest.fail("calculate_pl_snapshot should handle errors gracefully")
        
        # Verify no snapshots were created due to error
        snapshots = scheduler_service.db_session.query(PositionSnapshot).all()
        assert len(snapshots) == 0
        
        # Verify WebSocket was not called due to error
        scheduler_service.websocket_manager.broadcast_pl_update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_scheduler_job_configuration(self, scheduler_service):
        """Test that P/L snapshot job is properly configured in scheduler."""
        # Start the scheduler
        await scheduler_service.start()
        
        # Verify scheduler is running
        assert scheduler_service.scheduler.running
        
        # Verify P/L snapshot job is configured
        jobs = scheduler_service.scheduler.get_jobs()
        pl_job = next((job for job in jobs if "pl_snapshot" in job.id), None)
        assert pl_job is not None
        
        # Verify job is scheduled for 15-minute intervals
        trigger = pl_job.trigger
        assert trigger.interval == timedelta(minutes=15)
        
        # Stop scheduler
        await scheduler_service.stop()
        assert not scheduler_service.scheduler.running
    
    @pytest.mark.asyncio
    async def test_market_hours_scheduling(self, scheduler_service):
        """Test that P/L snapshots only run during market hours."""
        # Mock current time as during market hours (10:30 AM ET)
        market_time = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)
        
        with patch('app.services.scheduler_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = market_time
            mock_datetime.combine = datetime.combine
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Check if time is during market hours
            is_market_hours = scheduler_service._is_market_hours()
            assert is_market_hours is True
        
        # Mock current time as outside market hours (6:00 AM ET)
        pre_market_time = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        
        with patch('app.services.scheduler_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = pre_market_time
            mock_datetime.combine = datetime.combine
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Check if time is outside market hours
            is_market_hours = scheduler_service._is_market_hours()
            assert is_market_hours is False
    
    @pytest.mark.asyncio
    async def test_pl_snapshot_websocket_integration(self, scheduler_service, sample_positions, mock_pl_service):
        """Test integration between P/L snapshot job and WebSocket broadcasting."""
        # Mock P/L calculation results
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.75"),
                current_value=Decimal("-185.00"),
                unrealized_pl=Decimal("65.00"),
                unrealized_pl_percent=Decimal("13.00"),
                risk_percent=Decimal("-13.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Execute snapshot job
        await scheduler_service.calculate_pl_snapshot()
        
        # Verify WebSocket broadcast was called
        scheduler_service.websocket_manager.broadcast_pl_update.assert_called_once()
        
        # Verify broadcast data structure
        call_args = scheduler_service.websocket_manager.broadcast_pl_update.call_args[0][0]
        assert call_args.type == "pl_update"
        assert len(call_args.positions) == 1
        assert call_args.positions[0].id == 1
        assert call_args.positions[0].unrealized_pl == 65.0
        assert call_args.spy_price == 451.75
        assert call_args.total_unrealized_pl == 65.0
        assert call_args.alert is False
    
    @pytest.mark.asyncio
    async def test_position_update_from_snapshot(self, scheduler_service, sample_positions, mock_pl_service):
        """Test that position records are updated with latest P/L data."""
        # Mock P/L calculation results
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("452.00"),
                current_value=Decimal("-180.00"),
                unrealized_pl=Decimal("70.00"),
                unrealized_pl_percent=Decimal("14.00"),
                risk_percent=Decimal("-14.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Get initial position state
        position = scheduler_service.db_session.query(Position).filter_by(id=1).first()
        original_value = position.latest_value
        original_pl = position.latest_unrealized_pl
        
        # Execute snapshot job
        await scheduler_service.calculate_pl_snapshot()
        
        # Refresh position from database
        scheduler_service.db_session.refresh(position)
        
        # Verify position was updated with new P/L values
        assert position.latest_value == Decimal("-180.00")
        assert position.latest_unrealized_pl == Decimal("70.00")
        assert position.latest_unrealized_pl_percent == Decimal("14.00")
        assert position.stop_loss_alert_active is False
        
        # Verify values actually changed
        assert position.latest_value != original_value
        assert position.latest_unrealized_pl != original_pl
    
    @pytest.mark.asyncio
    async def test_multiple_snapshots_timeline(self, scheduler_service, sample_positions, mock_pl_service):
        """Test creating multiple snapshots over time for historical tracking."""
        # First snapshot
        first_time = datetime.now()
        mock_pl_data_1 = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.00"),
                current_value=Decimal("-200.00"),
                unrealized_pl=Decimal("50.00"),
                unrealized_pl_percent=Decimal("10.00"),
                risk_percent=Decimal("-10.00"),
                stop_loss_triggered=False,
                calculation_time=first_time
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data_1
        
        await scheduler_service.calculate_pl_snapshot()
        
        # Second snapshot 15 minutes later
        second_time = first_time + timedelta(minutes=15)
        mock_pl_data_2 = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.50"),
                current_value=Decimal("-185.00"),
                unrealized_pl=Decimal("65.00"),
                unrealized_pl_percent=Decimal("13.00"),
                risk_percent=Decimal("-13.00"),
                stop_loss_triggered=False,
                calculation_time=second_time
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data_2
        
        with patch('app.services.scheduler_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = second_time
            mock_datetime.combine = datetime.combine
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            await scheduler_service.calculate_pl_snapshot()
        
        # Verify both snapshots exist
        snapshots = scheduler_service.db_session.query(PositionSnapshot).filter_by(position_id=1).order_by(PositionSnapshot.created_at).all()
        assert len(snapshots) == 2
        
        # Verify progression in P/L values
        assert snapshots[0].unrealized_pl == Decimal("50.00")
        assert snapshots[1].unrealized_pl == Decimal("65.00")
        assert snapshots[0].spy_price == Decimal("451.00")
        assert snapshots[1].spy_price == Decimal("451.50")
        
        # Verify timestamps show progression
        assert snapshots[1].created_at > snapshots[0].created_at
    
    @pytest.mark.asyncio
    async def test_concurrent_snapshot_execution(self, scheduler_service, sample_positions, mock_pl_service):
        """Test that multiple snapshot jobs don't interfere with each other."""
        # Mock P/L calculation with delay to simulate slow execution
        async def slow_pl_calculation():
            await asyncio.sleep(0.1)  # Simulate processing time
            return [
                PositionPLData(
                    position_id=1,
                    spy_price=Decimal("451.25"),
                    current_value=Decimal("-190.00"),
                    unrealized_pl=Decimal("60.00"),
                    unrealized_pl_percent=Decimal("12.00"),
                    risk_percent=Decimal("-12.00"),
                    stop_loss_triggered=False,
                    calculation_time=datetime.now()
                )
            ]
        
        mock_pl_service.calculate_all_positions_pl.side_effect = slow_pl_calculation
        
        # Execute multiple snapshot jobs concurrently
        tasks = [
            scheduler_service.calculate_pl_snapshot(),
            scheduler_service.calculate_pl_snapshot(),
            scheduler_service.calculate_pl_snapshot()
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all snapshots were created (should be 3)
        snapshots = scheduler_service.db_session.query(PositionSnapshot).all()
        assert len(snapshots) == 3
        
        # Verify P/L calculation was called for each execution
        assert mock_pl_service.calculate_all_positions_pl.call_count == 3