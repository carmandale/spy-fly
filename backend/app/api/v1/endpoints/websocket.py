"""
WebSocket API endpoints for real-time price feeds and market data.
"""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.websocket_service import WebSocketManager
from app.services.market_service import MarketDataService
from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Global WebSocket manager instance
websocket_manager: WebSocketManager | None = None


class WebSocketStatsResponse(BaseModel):
    """Response model for WebSocket connection statistics."""
    
    total_connections: int
    is_running: bool
    update_interval: int
    cached_tickers: list[str]
    connections: list[dict[str, Any]]


def get_websocket_manager() -> WebSocketManager:
    """
    Get or create the global WebSocket manager instance.
    
    Returns:
        WebSocketManager instance
    """
    global websocket_manager
    
    if websocket_manager is None:
        # Create dependencies for market service with proper initialization
        polygon_client = PolygonClient(
            api_key=settings.polygon_api_key,
            use_sandbox=settings.polygon_use_sandbox
        )
        cache = MarketDataCache(max_size=1000)
        rate_limiter = RateLimiter(requests_per_minute=settings.polygon_rate_limit)
        
        market_service = MarketDataService(
            polygon_client=polygon_client,
            cache=cache,
            rate_limiter=rate_limiter
        )
        
        websocket_manager = WebSocketManager(market_service=market_service)
        logger.info("WebSocket manager initialized")
    
    return websocket_manager


@router.websocket("/price-feed")
async def websocket_price_feed(
    websocket: WebSocket,
    manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    WebSocket endpoint for real-time SPY price feeds.
    
    Clients can connect to this endpoint to receive real-time price updates
    for SPY and other market data. The connection supports:
    
    - Real-time price updates every 15 seconds or on significant price changes
    - Market status updates (open, closed, pre-market, after-hours)
    - Connection status messages and error notifications
    - Ping/pong heartbeat for connection health
    
    Message Types Sent to Client:
    - price_update: Real-time price data
    - connection_status: Connection state and error messages
    - pong: Response to client ping messages
    
    Message Types Accepted from Client:
    - ping: Heartbeat message (responds with pong)
    - subscribe: Subscribe to specific ticker (future feature)
    """
    # Generate unique client ID
    client_id = f"client_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"WebSocket connection attempt from client {client_id}")
    
    try:
        # Accept connection and register with manager
        await manager.connect(websocket, client_id)
        
        # Handle incoming messages
        while True:
            try:
                # Wait for message from client
                message = await websocket.receive_text()
                await manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                # Continue processing other messages
                continue
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected during handshake")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket handler for client {client_id}: {e}")
    finally:
        # Ensure client is properly disconnected
        await manager.disconnect(client_id)


@router.get("/stats", response_model=WebSocketStatsResponse)
async def get_websocket_stats(
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> WebSocketStatsResponse:
    """
    Get current WebSocket connection statistics.
    
    Returns information about active connections, update status,
    and configuration settings.
    
    Returns:
        WebSocketStatsResponse with connection statistics
    """
    try:
        stats = manager.get_connection_stats()
        
        return WebSocketStatsResponse(
            total_connections=stats["total_connections"],
            is_running=stats["is_running"],
            update_interval=stats["update_interval"],
            cached_tickers=stats["cached_tickers"],
            connections=stats["connections"]
        )
        
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get WebSocket statistics: {str(e)}"
        )


@router.post("/broadcast/test")
async def test_broadcast(
    message: str = "Test broadcast message",
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> dict[str, Any]:
    """
    Test endpoint to broadcast a message to all connected clients.
    
    This endpoint is useful for testing WebSocket connectivity and
    message broadcasting functionality.
    
    Args:
        message: Test message to broadcast
        
    Returns:
        Dictionary with broadcast result
    """
    try:
        from app.services.websocket_service import ConnectionInfo
        
        test_message = ConnectionInfo(
            status="test",
            message=message,
            timestamp=f"{manager.get_connection_stats()['total_connections']} clients"
        )
        
        # Broadcast to all clients
        stats = manager.get_connection_stats()
        connections_count = stats["total_connections"]
        
        if connections_count == 0:
            return {
                "success": True,
                "message": "No clients connected to broadcast to",
                "connections": 0
            }
        
        # Send test message to all clients
        for client_id in list(manager.connections.keys()):
            try:
                await manager._send_to_client(client_id, test_message)
            except Exception as e:
                logger.warning(f"Failed to send test message to client {client_id}: {e}")
        
        return {
            "success": True,
            "message": f"Test message broadcasted to {connections_count} clients",
            "connections": connections_count,
            "test_message": message
        }
        
    except Exception as e:
        logger.error(f"Error in test broadcast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to broadcast test message: {str(e)}"
        )


@router.post("/force-update")
async def force_price_update(
    manager: WebSocketManager = Depends(get_websocket_manager)
) -> dict[str, Any]:
    """
    Force an immediate price update broadcast to all connected clients.
    
    This endpoint bypasses the normal update throttling and immediately
    fetched and broadcasts the current SPY price to all clients.
    
    Returns:
        Dictionary with update result
    """
    try:
        stats = manager.get_connection_stats()
        connections_count = stats["total_connections"]
        
        if connections_count == 0:
            return {
                "success": True,
                "message": "No clients connected to update",
                "connections": 0
            }
        
        # Force fetch current price
        quote_response = await manager.market_service.get_spy_quote()
        
        # Create price update
        from app.services.websocket_service import PriceUpdate
        
        price_update = PriceUpdate(
            ticker=quote_response.ticker,
            price=quote_response.price,
            bid=quote_response.bid,
            ask=quote_response.ask,
            volume=quote_response.volume,
            change=quote_response.change,
            change_percent=quote_response.change_percent,
            market_status=quote_response.market_status,
            timestamp=quote_response.timestamp,
            cached=quote_response.cached
        )
        
        # Broadcast the update
        await manager.broadcast_price_update("SPY", price_update)
        
        return {
            "success": True,
            "message": f"Price update forced to {connections_count} clients",
            "connections": connections_count,
            "price": quote_response.price,
            "ticker": quote_response.ticker,
            "market_status": quote_response.market_status,
            "cached": quote_response.cached
        }
        
    except Exception as e:
        logger.error(f"Error forcing price update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force price update: {str(e)}"
        )