"""
API endpoints for scheduler management and morning scan operations.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.scheduler_service import SchedulerService
from app.services.spread_selection_service import SpreadSelectionService
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.sentiment_calculator import SentimentCalculator
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter
from app.config import settings

router = APIRouter()


class ManualScanRequest(BaseModel):
    """Request model for triggering manual scans."""
    
    account_size: float = Field(
        default=100000.0,
        ge=10000,
        le=10000000,
        description="Account size for position sizing calculations"
    )


class ScanResultResponse(BaseModel):
    """Response model for scan results."""
    
    success: bool
    scan_time: datetime
    account_size: float
    recommendations_count: int
    duration_seconds: float | None = None
    error: str | None = None
    metrics: dict[str, Any] | None = None


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""
    
    status: str
    jobs: list[dict[str, Any]]
    timezone: str
    next_scan_time: datetime | None = None


# Dependency to get scheduler service
def get_scheduler_service() -> SchedulerService:
    """Create and return configured scheduler service."""
    # Create dependencies with proper initialization
    black_scholes = BlackScholesCalculator()
    
    # Initialize market data dependencies
    polygon_client = PolygonClient(
        api_key=settings.polygon_api_key, 
        use_sandbox=settings.polygon_use_sandbox
    )
    cache = MarketDataCache(max_size=1000)
    rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
    
    # Initialize services with dependencies
    market_service = MarketDataService(polygon_client, cache, rate_limiter)
    sentiment_calculator = SentimentCalculator(market_service, cache)
    
    # Create spread selection service
    spread_service = SpreadSelectionService(
        black_scholes_calculator=black_scholes,
        market_service=market_service,
        sentiment_calculator=sentiment_calculator
    )
    
    # Create and return scheduler service
    return SchedulerService(spread_selection_service=spread_service)


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> SchedulerStatusResponse:
    """
    Get current scheduler status and job information.
    
    Returns information about the scheduler state, scheduled jobs,
    and next scan time.
    """
    try:
        status_info = scheduler_service.get_status()
        next_scan_time = scheduler_service.get_next_scan_time()
        
        return SchedulerStatusResponse(
            status=status_info["status"],
            jobs=status_info["jobs"],
            timezone=status_info["timezone"],
            next_scan_time=next_scan_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


@router.post("/start")
async def start_scheduler(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> dict[str, str]:
    """
    Start the scheduler and morning scan job.
    
    This endpoint is typically called during application startup,
    but can also be used to restart the scheduler if needed.
    """
    try:
        await scheduler_service.start_scheduler()
        return {"message": "Scheduler started successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scheduler: {str(e)}"
        )


@router.post("/stop")
async def stop_scheduler(
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> dict[str, str]:
    """
    Stop the scheduler gracefully.
    
    This will stop all scheduled jobs but won't affect
    any currently running scans.
    """
    try:
        await scheduler_service.stop_scheduler()
        return {"message": "Scheduler stopped successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop scheduler: {str(e)}"
        )


@router.post("/scan/manual", response_model=ScanResultResponse)
async def trigger_manual_scan(
    request: ManualScanRequest,
    scheduler_service: SchedulerService = Depends(get_scheduler_service)
) -> ScanResultResponse:
    """
    Trigger a manual morning scan for testing or immediate analysis.
    
    This endpoint runs the same logic as the scheduled morning scan
    but can be triggered at any time for testing or immediate needs.
    
    Args:
        request: Manual scan request with account size parameter
        
    Returns:
        Scan results including recommendations count and metrics
    """
    try:
        result = await scheduler_service.trigger_manual_scan(
            account_size=request.account_size
        )
        
        return ScanResultResponse(
            success=result["success"],
            scan_time=result["scan_time"],
            account_size=result["account_size"],
            recommendations_count=len(result.get("recommendations", [])),
            duration_seconds=result.get("duration_seconds"),
            error=result.get("error"),
            metrics=result.get("metrics")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual scan failed: {str(e)}"
        )


@router.get("/scans/history")
async def get_scan_history(
    limit: int = 10,
    manual_only: bool = False
) -> dict[str, Any]:
    """
    Get history of morning scan results.
    
    Args:
        limit: Maximum number of results to return (default: 10)
        manual_only: If True, only return manual scans (default: False)
        
    Returns:
        List of historical scan results with metadata
    """
    # TODO: Implement database query to get scan history
    # This would query the MorningScanResult table with filtering
    
    return {
        "message": "Scan history endpoint - to be implemented",
        "limit": limit,
        "manual_only": manual_only,
        "results": []
    }


@router.get("/scans/latest")
async def get_latest_scan() -> dict[str, Any]:
    """
    Get the most recent scan result (scheduled or manual).
    
    Returns:
        Latest scan result with full details
    """
    # TODO: Implement database query to get latest scan
    # This would query the MorningScanResult table ordered by scan_time DESC
    
    return {
        "message": "Latest scan endpoint - to be implemented",
        "result": None
    }