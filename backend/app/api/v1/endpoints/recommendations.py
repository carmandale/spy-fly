"""Spread recommendations endpoints."""

from datetime import datetime
from enum import Enum
from typing import List

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.config import settings
from app.core.exceptions import MarketDataError, RateLimitError
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.cache import MarketDataCache
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.rate_limiter import RateLimiter
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_selection_service import SpreadSelectionService
from app.services.trade_formatter import FormatStyle, TradeFormatter

router = APIRouter()


class ResponseFormat(str, Enum):
    """Supported response formats for recommendations."""
    JSON = "json"
    TEXT = "text"
    CLIPBOARD = "clipboard"


class RecommendationsSummary(BaseModel):
    """Summary statistics for recommendations."""
    total_recommendations: int = Field(..., description="Total number of recommendations returned")
    avg_probability: float = Field(..., description="Average probability of profit")
    avg_expected_value: float = Field(..., description="Average expected value")
    avg_risk_reward: float = Field(..., description="Average risk/reward ratio")
    total_capital_required: float = Field(..., description="Total capital required for all recommendations")


class RecommendationsMetadata(BaseModel):
    """Metadata about the recommendation request."""
    account_size: float = Field(..., description="Account size used for calculations")
    max_recommendations: int = Field(..., description="Maximum recommendations requested")
    format: ResponseFormat = Field(..., description="Response format used")
    generated_at: datetime = Field(..., description="Timestamp when recommendations were generated")
    market_conditions: dict = Field(..., description="Current market conditions")


class RecommendationsResponse(BaseModel):
    """Response for spread recommendations endpoint."""
    recommendations: List[dict] = Field(..., description="List of formatted recommendations")
    summary: RecommendationsSummary = Field(..., description="Summary statistics")
    metadata: RecommendationsMetadata = Field(..., description="Request metadata")
    message: str = Field(..., description="Human-readable message about the results")


# Initialize services (in production, use dependency injection)
polygon_client = PolygonClient(
    api_key=settings.polygon_api_key, use_sandbox=settings.polygon_use_sandbox
)
cache = MarketDataCache(max_size=1000)
rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
market_service = MarketDataService(polygon_client, cache, rate_limiter)

# Initialize spread selection components
black_scholes = BlackScholesCalculator()
sentiment_calculator = SentimentCalculator(market_service=market_service, cache=cache)
spread_service = SpreadSelectionService(
    black_scholes_calculator=black_scholes,
    market_service=market_service,
    sentiment_calculator=sentiment_calculator,
)

# Initialize trade formatter
trade_formatter = TradeFormatter(symbol="SPY")


@router.get("/spreads")
async def get_spread_recommendations(
    response: Response,
    account_size: float = Query(..., description="Account size for position sizing", gt=0),
    max_recommendations: int = Query(5, description="Maximum number of recommendations", ge=1, le=10),
    format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format"),
):
    """
    Get spread recommendations for SPY 0-DTE bull-call-spreads.
    
    This endpoint analyzes current market conditions and returns ranked
    spread recommendations with risk metrics, probability calculations,
    and formatted order tickets.
    """
    try:
        # Generate recommendations
        recommendations = await spread_service.get_recommendations(
            account_size=account_size,
            max_recommendations=max_recommendations
        )
        
        # Set rate limit headers
        response.headers["X-RateLimit-Limit"] = str(settings.polygon_rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limiter.get_remaining())
        response.headers["X-RateLimit-Reset"] = str(int(rate_limiter.get_reset_time()))
        
        # Handle different response formats
        if format == ResponseFormat.TEXT:
            # Return plain text format
            formatted_text = trade_formatter.format_recommendation_list(
                recommendations, max_items=max_recommendations
            )
            response.headers["Content-Type"] = "text/plain"
            response.headers["Cache-Control"] = "private, max-age=60"
            return formatted_text
            
        elif format == ResponseFormat.CLIPBOARD:
            # Return clipboard-friendly format
            if recommendations:
                clipboard_content = []
                for rec in recommendations:
                    order_ticket = trade_formatter.format_order_ticket(rec)
                    clipboard_content.append(order_ticket)
                formatted_clipboard = "\n\n".join(clipboard_content)
            else:
                formatted_clipboard = "No spread recommendations meet the current criteria."
                
            response.headers["Content-Type"] = "text/plain"
            response.headers["Cache-Control"] = "private, max-age=60"
            return formatted_clipboard
            
        else:  # JSON format (default)
            # Calculate summary statistics
            if recommendations:
                summary = RecommendationsSummary(
                    total_recommendations=len(recommendations),
                    avg_probability=sum(r.probability_of_profit for r in recommendations) / len(recommendations),
                    avg_expected_value=sum(r.expected_value for r in recommendations) / len(recommendations),
                    avg_risk_reward=sum(r.risk_reward_ratio for r in recommendations) / len(recommendations),
                    total_capital_required=sum(r.total_cost for r in recommendations),
                )
                message = f"Found {len(recommendations)} spread recommendations meeting your criteria."
                
                # Format recommendations as JSON
                formatted_recommendations = []
                for rec in recommendations:
                    json_rec = trade_formatter.format_as_json(rec)
                    formatted_recommendations.append(json_rec)
                    
            else:
                summary = RecommendationsSummary(
                    total_recommendations=0,
                    avg_probability=0.0,
                    avg_expected_value=0.0,
                    avg_risk_reward=0.0,
                    total_capital_required=0.0,
                )
                message = "No spread recommendations meet the current criteria. Try adjusting your account size or check market conditions."
                formatted_recommendations = []
            
            # Get current market conditions for metadata
            try:
                spy_quote = await market_service.get_spy_quote()
                current_sentiment = await sentiment_calculator.calculate_sentiment()
                market_conditions = {
                    "spy_price": spy_quote.price,
                    "sentiment_score": current_sentiment,
                    "market_status": getattr(spy_quote, 'market_status', 'unknown'),
                }
            except Exception:
                market_conditions = {
                    "spy_price": None,
                    "sentiment_score": None,
                    "market_status": "unknown",
                }
            
            # Create metadata
            metadata = RecommendationsMetadata(
                account_size=account_size,
                max_recommendations=max_recommendations,
                format=format,
                generated_at=datetime.now(),
                market_conditions=market_conditions,
            )
            
            # Create response
            response_data = RecommendationsResponse(
                recommendations=formatted_recommendations,
                summary=summary,
                metadata=metadata,
                message=message,
            )
            
            # Set caching headers
            response.headers["Cache-Control"] = "private, max-age=60"
            response.headers["Content-Type"] = "application/json"
            
            return response_data
        
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
                "error": {
                    "code": "MARKET_DATA_ERROR", 
                    "message": str(e), 
                    "details": {}
                }
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PARAMETERS",
                    "message": str(e),
                    "details": {
                        "account_size": account_size,
                        "max_recommendations": max_recommendations,
                    },
                }
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred while generating recommendations",
                    "details": {"error_type": type(e).__name__},
                }
            },
        )


@router.get("/spreads/{session_id}")
async def get_cached_recommendations(
    session_id: str,
    response: Response,
    format: ResponseFormat = Query(ResponseFormat.JSON, description="Response format"),
):
    """
    Retrieve previously generated recommendations by session ID.
    
    This endpoint allows retrieval of cached recommendations without
    regenerating them, useful for switching between formats.
    """
    # TODO: Implement session-based caching in Task 5.5
    raise HTTPException(
        status_code=501,
        detail={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Session-based recommendation caching not yet implemented",
                "details": {"session_id": session_id},
            }
        },
    )