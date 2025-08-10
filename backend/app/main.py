import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.config import settings
from app.core.database import Base, engine
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter
from app.services.scheduler_service import SchedulerService
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_selection_service import SpreadSelectionService
from app.services.pl_calculation_service import PLCalculationService
from app.services.pl_monitor_service import PLMonitorService
from app.services.websocket_service import WebSocketManager

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# Global scheduler service instance
scheduler_service: SchedulerService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.
    
    Handles scheduler initialization and cleanup.
    """
    global scheduler_service

    # Startup
    try:
        logger.info("Starting SPY-FLY application...")

        # Initialize services with proper dependency injection
        black_scholes = BlackScholesCalculator()

        # Initialize market data dependencies
        polygon_client = PolygonClient(
            api_key=settings.polygon_api_key,
            use_sandbox=settings.polygon_use_sandbox
        )
        cache = MarketDataCache(max_size=1000)
        rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)

        # Initialize market service with dependencies
        market_service = MarketDataService(polygon_client, cache, rate_limiter)
        sentiment_calculator = SentimentCalculator(market_service, cache)

        spread_service = SpreadSelectionService(
            black_scholes_calculator=black_scholes,
            market_service=market_service,
            sentiment_calculator=sentiment_calculator
        )

        # Initialize and start scheduler
        scheduler_service = SchedulerService(spread_selection_service=spread_service)
        await scheduler_service.start_scheduler()

        logger.info("Morning scan scheduler started successfully - next scan at 9:45 AM ET")

    except Exception as e:
        logger.error(f"Failed to start scheduler during application startup: {e}")
        # Don't crash the app if scheduler fails - it can be started manually via API

    yield

    # Shutdown
    try:
        logger.info("Shutting down SPY-FLY application...")

        if scheduler_service:
            await scheduler_service.stop_scheduler()
            logger.info("Scheduler stopped successfully")

    except Exception as e:
        logger.error(f"Error during application shutdown: {e}")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.project_name}"}
