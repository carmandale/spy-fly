"""
Unit tests for the scheduler service module.

Tests the morning scan scheduler functionality including job scheduling,
manual scans, database logging, and error handling.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scheduler_service import SchedulerService
from app.services.spread_selection_service import SpreadSelectionService
from app.models.spread import SpreadRecommendation


@pytest.fixture
def mock_spread_service():
    """Create a mock spread selection service."""
    service = AsyncMock(spec=SpreadSelectionService)
    
    # Mock successful recommendation response
    mock_recommendation = SpreadRecommendation(
        long_strike=575.0,
        short_strike=580.0,
        long_premium=2.50,
        short_premium=1.00,
        net_debit=1.50,
        max_risk=1.50,
        max_profit=3.50,
        risk_reward_ratio=2.33,
        probability_of_profit=0.65,
        breakeven_price=576.50,
        long_bid=2.45,
        long_ask=2.55,
        short_bid=0.95,
        short_ask=1.05,
        long_volume=150,
        short_volume=200,
        expected_value=1.25,
        sentiment_score=0.75,
        ranking_score=0.80,
        timestamp=datetime.now(timezone.utc),
        contracts_to_trade=3,
        total_cost=450.0,
        buying_power_used_pct=0.045
    )
    
    service.get_recommendations.return_value = [mock_recommendation]
    return service


@pytest.fixture
def scheduler_service(mock_spread_service):
    """Create a scheduler service with mocked dependencies."""
    return SchedulerService(spread_selection_service=mock_spread_service)


class TestSchedulerServiceInitialization:
    """Test scheduler service initialization and configuration."""
    
    def test_scheduler_service_initialization(self, scheduler_service):
        """Test that scheduler service initializes correctly."""
        assert scheduler_service.spread_service is not None
        assert scheduler_service.scheduler is not None
        assert scheduler_service._is_running is False
        assert scheduler_service.scheduler.timezone.zone == 'America/New_York'
    
    def test_scheduler_configuration(self, scheduler_service):
        """Test that scheduler has correct configuration."""
        scheduler = scheduler_service.scheduler
        
        # Check timezone
        assert str(scheduler.timezone) == 'America/New_York'
        
        # Check job defaults
        assert scheduler._job_defaults['coalesce'] is False
        assert scheduler._job_defaults['max_instances'] == 1
        assert scheduler._job_defaults['misfire_grace_time'] == 300


class TestSchedulerLifecycle:
    """Test scheduler start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_scheduler_success(self, scheduler_service):
        """Test successful scheduler startup."""
        await scheduler_service.start_scheduler()
        
        assert scheduler_service._is_running is True
        
        # Check that morning scan job was added
        jobs = scheduler_service.scheduler.get_jobs()
        assert len(jobs) == 1
        
        job = jobs[0]
        assert job.id == 'morning_scan'
        assert job.name == 'Morning Market Scan'
        
        # Clean up
        await scheduler_service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, scheduler_service):
        """Test starting scheduler when already running."""
        await scheduler_service.start_scheduler()
        
        # Try to start again - should not raise error
        await scheduler_service.start_scheduler()
        
        assert scheduler_service._is_running is True
        
        # Clean up
        await scheduler_service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_success(self, scheduler_service):
        """Test successful scheduler shutdown."""
        await scheduler_service.start_scheduler()
        await scheduler_service.stop_scheduler()
        
        assert scheduler_service._is_running is False
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, scheduler_service):
        """Test stopping scheduler when not running."""
        # Should not raise error
        await scheduler_service.stop_scheduler()
        
        assert scheduler_service._is_running is False


class TestManualScan:
    """Test manual scan functionality."""
    
    @pytest.mark.asyncio
    async def test_trigger_manual_scan_success(self, scheduler_service, mock_spread_service):
        """Test successful manual scan execution."""
        result = await scheduler_service.trigger_manual_scan(account_size=100000.0)
        
        # Verify spread service was called
        mock_spread_service.get_recommendations.assert_called_once_with(
            account_size=100000.0,
            max_recommendations=10
        )
        
        # Verify result structure
        assert result['success'] is True
        assert result['account_size'] == 100000.0
        assert len(result['recommendations']) == 1
        assert 'scan_time' in result
        assert 'metrics' in result
        assert 'duration_seconds' in result
        
        # Verify metrics
        metrics = result['metrics']
        assert metrics['total_recommendations'] == 1
        assert metrics['high_quality_count'] == 1  # ranking_score > 0.7
        assert metrics['avg_probability'] == 0.65
        assert metrics['avg_risk_reward'] == 2.33
    
    @pytest.mark.asyncio
    async def test_trigger_manual_scan_empty_recommendations(self, scheduler_service, mock_spread_service):
        """Test manual scan with no recommendations."""
        mock_spread_service.get_recommendations.return_value = []
        
        result = await scheduler_service.trigger_manual_scan(account_size=50000.0)
        
        assert result['success'] is True
        assert result['account_size'] == 50000.0
        assert len(result['recommendations']) == 0
        
        # Verify metrics with empty recommendations
        metrics = result['metrics']
        assert metrics['total_recommendations'] == 0
        assert metrics['high_quality_count'] == 0
        assert metrics['avg_probability'] == 0
        assert metrics['avg_risk_reward'] == 0
    
    @pytest.mark.asyncio
    async def test_trigger_manual_scan_service_error(self, scheduler_service, mock_spread_service):
        """Test manual scan with service error."""
        mock_spread_service.get_recommendations.side_effect = Exception("Market data unavailable")
        
        result = await scheduler_service.trigger_manual_scan(account_size=100000.0)
        
        assert result['success'] is False
        assert result['error'] == "Market data unavailable"
        assert len(result['recommendations']) == 0


class TestScheduledJob:
    """Test the scheduled morning scan job."""
    
    @pytest.mark.asyncio
    async def test_morning_scan_job_success(self, scheduler_service, mock_spread_service):
        """Test successful morning scan job execution."""
        with patch.object(scheduler_service, '_log_scan_result', new_callable=AsyncMock) as mock_log, \
             patch.object(scheduler_service, '_process_scan_notifications', new_callable=AsyncMock) as mock_notify:
            
            await scheduler_service._morning_scan_job()
            
            # Verify spread service was called with default account size
            mock_spread_service.get_recommendations.assert_called_once_with(
                account_size=100000.0,
                max_recommendations=10
            )
            
            # Verify logging and notifications were called
            mock_log.assert_called_once()
            mock_notify.assert_called_once()
            
            # Check the logged result
            log_call_args = mock_log.call_args[0][0]
            assert log_call_args['success'] is True
            assert log_call_args['account_size'] == 100000.0
    
    @pytest.mark.asyncio
    async def test_morning_scan_job_error(self, scheduler_service, mock_spread_service):
        """Test morning scan job with error."""
        mock_spread_service.get_recommendations.side_effect = Exception("API timeout")
        
        with patch.object(scheduler_service, '_log_scan_result', new_callable=AsyncMock) as mock_log:
            await scheduler_service._morning_scan_job()
            
            # Verify error was logged
            mock_log.assert_called_once()
            log_call_args = mock_log.call_args[0][0]
            assert log_call_args['success'] is False
            assert log_call_args['error'] == "API timeout"


class TestDatabaseLogging:
    """Test database logging functionality."""
    
    @pytest.mark.asyncio
    async def test_log_scan_result_success(self, scheduler_service):
        """Test successful scan result logging."""
        scan_result = {
            'success': True,
            'scan_time': datetime.now(),
            'account_size': 100000.0,
            'recommendations': [{'test': 'data'}],
            'metrics': {'total_recommendations': 1},
            'duration_seconds': 2.5
        }
        
        with patch('app.services.scheduler_service.get_db') as mock_get_db, \
             patch('app.services.scheduler_service.MorningScanResult') as mock_model:
            
            mock_db = MagicMock()
            mock_get_db.return_value = iter([mock_db])
            
            await scheduler_service._log_scan_result(scan_result, is_manual=True)
            
            # Verify database operations
            mock_model.assert_called_once()
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_scan_result_database_error(self, scheduler_service):
        """Test scan result logging with database error."""
        scan_result = {
            'success': True,
            'scan_time': datetime.now(),
            'account_size': 100000.0,
            'recommendations': [],
            'metrics': {},
            'duration_seconds': 1.0
        }
        
        with patch('app.services.scheduler_service.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_db.add.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = iter([mock_db])
            
            # Should not raise exception - logging failure shouldn't break scan
            await scheduler_service._log_scan_result(scan_result, is_manual=False)
            
            mock_db.close.assert_called_once()


class TestNotificationProcessing:
    """Test notification processing for high-quality recommendations."""
    
    @pytest.mark.asyncio
    async def test_process_scan_notifications_high_quality(self, scheduler_service):
        """Test notification processing for high-quality recommendations."""
        mock_recommendation = MagicMock()
        mock_recommendation.ranking_score = 0.85  # High quality
        
        scan_result = {
            'success': True,
            'recommendations': [mock_recommendation]
        }
        
        # Currently just logs - in future would send actual notifications
        await scheduler_service._process_scan_notifications(scan_result)
        
        # No assertions needed - this is a placeholder for future notification logic
    
    @pytest.mark.asyncio
    async def test_process_scan_notifications_low_quality(self, scheduler_service):
        """Test notification processing for low-quality recommendations."""
        mock_recommendation = MagicMock()
        mock_recommendation.ranking_score = 0.50  # Low quality
        
        scan_result = {
            'success': True,
            'recommendations': [mock_recommendation]
        }
        
        await scheduler_service._process_scan_notifications(scan_result)
        
        # No notifications should be processed for low-quality recommendations
    
    @pytest.mark.asyncio
    async def test_process_scan_notifications_failed_scan(self, scheduler_service):
        """Test notification processing for failed scan."""
        scan_result = {
            'success': False,
            'recommendations': []
        }
        
        await scheduler_service._process_scan_notifications(scan_result)
        
        # No notifications should be processed for failed scans


class TestStatusAndInfo:
    """Test status and information methods."""
    
    def test_get_status_not_initialized(self):
        """Test get_status when scheduler not initialized."""
        # Create service without initializing scheduler
        service = SchedulerService(AsyncMock())
        service.scheduler = None
        
        status = service.get_status()
        assert status == {'status': 'not_initialized'}
    
    @pytest.mark.asyncio
    async def test_get_status_running(self, scheduler_service):
        """Test get_status when scheduler is running."""
        await scheduler_service.start_scheduler()
        
        status = scheduler_service.get_status()
        
        assert status['status'] == 'running'
        assert 'jobs' in status
        assert 'timezone' in status
        assert len(status['jobs']) == 1
        assert status['jobs'][0]['id'] == 'morning_scan'
        
        # Clean up
        await scheduler_service.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_get_status_stopped(self, scheduler_service):
        """Test get_status when scheduler is stopped."""
        await scheduler_service.start_scheduler()
        await scheduler_service.stop_scheduler()
        
        status = scheduler_service.get_status()
        assert status['status'] == 'stopped'
    
    @pytest.mark.asyncio
    async def test_get_next_scan_time(self, scheduler_service):
        """Test getting next scan time."""
        # When not started
        next_time = scheduler_service.get_next_scan_time()
        assert next_time is None
        
        # When started
        await scheduler_service.start_scheduler()
        next_time = scheduler_service.get_next_scan_time()
        assert next_time is not None
        
        # Clean up
        await scheduler_service.stop_scheduler()