"""Market data endpoints."""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, Response

from app.config import settings
from app.core.exceptions import MarketDataError, RateLimitError
from app.models.market import (
    HistoricalDataResponse,
    MarketStatus,
    OptionChainResponse,
    QuoteResponse,
)
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter

router = APIRouter()

# Initialize services (in production, use dependency injection)
polygon_client = PolygonClient(
    api_key=settings.polygon_api_key, use_sandbox=settings.polygon_use_sandbox
)
cache = MarketDataCache(max_size=1000)
rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
market_service = MarketDataService(polygon_client, cache, rate_limiter)


@router.get("/quote/{ticker}", response_model=QuoteResponse)
async def get_quote(ticker: str, response: Response):
    """Get real-time quote for a ticker."""
    # Currently only support SPY
    if ticker != "SPY":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_TICKER",
                    "message": "Currently only SPY is supported",
                    "details": {"ticker": ticker},
                }
            },
        )

    try:
        quote = await market_service.get_spy_quote()

        # Set cache headers
        if quote.cached:
            response.headers["Cache-Control"] = "private, max-age=60"
            response.headers["X-Cached"] = "true"
        else:
            response.headers["Cache-Control"] = "private, max-age=0"
            response.headers["X-Cached"] = "false"

        # Set rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.polygon_rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.get_remaining())
        response.headers["X-RateLimit-Reset"] = str(int(rate_limiter.get_reset_time()))

        return quote

    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "details": {
                        "retry_after": e.retry_after,
                        "limit": settings.polygon_rate_limit,
                        "window": "1m",
                    },
                }
            },
        )
    except MarketDataError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {"code": "MARKET_DATA_ERROR", "message": str(e), "details": {}}
            },
        )


@router.get("/options/{ticker}", response_model=OptionChainResponse)
async def get_options(
    ticker: str,
    response: Response,
    expiration: str = Query(
        ..., description="Option expiration date in YYYY-MM-DD format"
    ),
    option_type: str | None = Query(None, description="Filter by 'call' or 'put'"),
    strike_range: int | None = Query(
        10, description="Number of strikes above/below current price"
    ),
):
    """Get option chain for a specific expiration."""
    # Validate ticker
    if ticker != "SPY":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_TICKER",
                    "message": "Currently only SPY is supported",
                    "details": {"ticker": ticker},
                }
            },
        )

    # Parse expiration date
    try:
        exp_date = date.fromisoformat(expiration)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_DATE_FORMAT",
                    "message": "Invalid date format. Use YYYY-MM-DD",
                    "details": {"expiration": expiration},
                }
            },
        )

    # Validate option type
    if option_type and option_type not in ["call", "put"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_OPTION_TYPE",
                    "message": "Option type must be 'call' or 'put'",
                    "details": {"option_type": option_type},
                }
            },
        )

    try:
        options = await market_service.get_spy_options(
            expiration=exp_date, option_type=option_type, strike_range=strike_range
        )

        # Set cache headers
        if options.cached:
            response.headers["Cache-Control"] = "private, max-age=300"
            response.headers["X-Cached"] = "true"
        else:
            response.headers["Cache-Control"] = "private, max-age=0"
            response.headers["X-Cached"] = "false"

        return options

    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "details": {
                        "retry_after": e.retry_after,
                        "limit": settings.polygon_rate_limit,
                        "window": "1m",
                    },
                }
            },
        )
    except MarketDataError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {"code": "MARKET_DATA_ERROR", "message": str(e), "details": {}}
            },
        )


@router.get("/historical/{ticker}", response_model=HistoricalDataResponse)
async def get_historical(
    ticker: str,
    response: Response,
    from_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    to_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    timeframe: str = Query("day", description="Timeframe: minute, hour, day"),
):
    """Get historical price data."""
    # Validate ticker
    if ticker != "SPY":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_TICKER",
                    "message": "Currently only SPY is supported",
                    "details": {"ticker": ticker},
                }
            },
        )

    # Parse dates
    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_DATE_FORMAT",
                    "message": "Invalid date format. Use YYYY-MM-DD",
                    "details": {"from": from_date, "to": to_date},
                }
            },
        )

    # Validate date range
    if start > end:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_DATE_RANGE",
                    "message": "Start date must be before end date",
                    "details": {"from": from_date, "to": to_date},
                }
            },
        )

    # Validate timeframe
    if timeframe not in ["minute", "hour", "day"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_TIMEFRAME",
                    "message": "Timeframe must be 'minute', 'hour', or 'day'",
                    "details": {"timeframe": timeframe},
                }
            },
        )

    try:
        # Calculate days
        days = (end - start).days + 1

        historical = await market_service.get_historical_data(
            days=days, timeframe=timeframe
        )

        # Set cache headers
        if historical.cached:
            response.headers["Cache-Control"] = "private, max-age=3600"
            response.headers["X-Cached"] = "true"
        else:
            response.headers["Cache-Control"] = "private, max-age=0"
            response.headers["X-Cached"] = "false"

        return historical

    except RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "details": {
                        "retry_after": e.retry_after,
                        "limit": settings.polygon_rate_limit,
                        "window": "1m",
                    },
                }
            },
        )
    except MarketDataError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {"code": "MARKET_DATA_ERROR", "message": str(e), "details": {}}
            },
        )


@router.get("/status", response_model=MarketStatus)
async def get_market_status(response: Response):
    """Get market and API status."""
    now = datetime.now()

    # Determine market status
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)

    if now.weekday() >= 5:
        market_status = "closed"
        session = "weekend"
    elif now < market_open:
        market_status = "closed"
        session = "pre-market"
    elif now > market_close:
        market_status = "closed"
        session = "after-hours"
    else:
        market_status = "open"
        session = "regular"

    # Get cache stats
    cache_stats = cache.get_stats()

    status = MarketStatus(
        market_status=market_status,
        session=session,
        api_status="healthy",
        rate_limit_remaining=rate_limiter.get_remaining(),
        rate_limit_reset=datetime.fromtimestamp(
            rate_limiter.get_reset_time()
        ).isoformat(),
        cache_stats=cache_stats,
    )

    response.headers["Cache-Control"] = "private, max-age=10"

    return status
