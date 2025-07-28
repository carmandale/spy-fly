"""Sentiment analysis endpoints."""

from fastapi import APIRouter, HTTPException, Query, Response

from app.config import settings
from app.core.exceptions import MarketDataError
from app.models.sentiment import SentimentConfig, SentimentResponse
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter
from app.services.sentiment_calculator import SentimentCalculator

router = APIRouter()

# Initialize services (in production, use dependency injection)
polygon_client = PolygonClient(
    api_key=settings.polygon_api_key, use_sandbox=settings.polygon_use_sandbox
)
cache = MarketDataCache(max_size=1000)
rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
market_service = MarketDataService(polygon_client, cache, rate_limiter)
sentiment_calculator = SentimentCalculator(market_service, cache)


@router.get("/calculate", response_model=SentimentResponse)
async def calculate_sentiment(
    force_refresh: bool = Query(False, description="Skip cache and recalculate"),
    response: Response = None,
):
    """Calculate current market sentiment score for SPY trading."""
    try:
        result = await sentiment_calculator.calculate_sentiment(
            force_refresh=force_refresh
        )

        # Convert to response format
        sentiment_response = SentimentResponse(
            score=result.score,
            decision=result.decision,
            threshold=result.threshold,
            timestamp=result.timestamp.isoformat(),
            breakdown={
                "vix": result.breakdown.vix,
                "futures": result.breakdown.futures,
                "rsi": result.breakdown.rsi,
                "ma50": result.breakdown.ma50,
                "bollinger": result.breakdown.bollinger,
                "news": result.breakdown.news,
            },
            technical_status=result.technical_status,
            cached=result.cached,
            cache_expires_at=(
                result.cache_expires_at.isoformat() if result.cache_expires_at else None
            ),
        )

        # Set cache headers
        if result.cached:
            response.headers["Cache-Control"] = (
                f"private, max-age={settings.sentiment_cache_ttl}"
            )
            response.headers["X-Cached"] = "true"
        else:
            response.headers["Cache-Control"] = "private, max-age=0"
            response.headers["X-Cached"] = "false"

        return sentiment_response

    except MarketDataError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {"code": "MARKET_DATA_ERROR", "message": str(e), "details": {}}
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "SENTIMENT_ERROR",
                    "message": f"Failed to calculate sentiment: {str(e)}",
                    "details": {},
                }
            },
        )


@router.get("/config", response_model=SentimentConfig)
async def get_sentiment_config():
    """Get current sentiment calculation configuration."""
    config = SentimentConfig(
        scoring_thresholds={
            "vix": {
                "low": settings.vix_low_threshold,
                "high": settings.vix_high_threshold,
            },
            "futures": {"bullish": settings.futures_bullish_threshold},
            "rsi": {
                "oversold": settings.rsi_oversold,
                "overbought": settings.rsi_overbought,
            },
            "bollinger": {"inner_range": settings.bollinger_inner_range},
        },
        scoring_weights={
            "vix": 1.0,
            "futures": 1.0,
            "rsi": 1.0,
            "ma50": 1.0,
            "bollinger": 1.0,
            "news": 1.0,
        },
        decision_threshold=settings.sentiment_minimum_score,
        cache_ttl=settings.sentiment_cache_ttl,
    )

    return config
