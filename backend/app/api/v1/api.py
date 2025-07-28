from fastapi import APIRouter

from app.api.v1.endpoints import health, market, sentiment, trades

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])