"""
WebSocket service for real-time price feeds and market data updates.

This service manages WebSocket connections and broadcasts real-time SPY price
updates to connected clients with proper throttling and error handling.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Set
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.market_service import MarketDataService
from app.core.exceptions import MarketDataError

logger = logging.getLogger(__name__)


class PriceUpdate(BaseModel):
    """Model for price update messages sent via WebSocket."""
    
    type: str = "price_update"
    ticker: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    change: float | None = None
    change_percent: float | None = None
    market_status: str
    timestamp: str
    cached: bool = False


class ConnectionInfo(BaseModel):
    """Model for connection status messages."""
    
    type: str = "connection_status"
    status: str  # "connected", "disconnected", "error"
    message: str
    timestamp: str


class PLPositionUpdate(BaseModel):
    """Model for individual position P/L data in WebSocket updates."""
    
    id: int
    symbol: str
    unrealized_pl: float
    unrealized_pl_percent: float
    current_value: float
    stop_loss_alert: bool


class PLUpdate(BaseModel):
    """Model for P/L update messages sent via WebSocket."""
    
    type: str = "pl_update"
    positions: list[PLPositionUpdate]
    total_unrealized_pl: float
    spy_price: float
    timestamp: str
    alert: bool = False  # True for stop-loss alerts


@dataclass
class WebSocketConnection:
    """Container for WebSocket connection metadata."""
    
    websocket: WebSocket
    client_id: str
    connected_at: datetime
    last_ping: datetime | None = None
    subscriptions: Set[str] = None
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()


class WebSocketManager:
    """
    Manager for WebSocket connections and real-time data broadcasting.
    
    Handles multiple client connections, price update broadcasting,
    and connection lifecycle management.
    """
    
    def __init__(self, market_service: MarketDataService):
        """
        Initialize WebSocket manager.
        
        Args:
            market_service: Service for fetching market data
        """
        self.market_service = market_service
        self.connections: Dict[str, WebSocketConnection] = {}
        self.price_cache: Dict[str, PriceUpdate] = {}
        self.pl_cache: PLUpdate | None = None
        self.update_task: asyncio.Task | None = None
        self.is_running = False
        
        # Configuration
        self.update_interval = 15  # seconds between price updates
        self.price_change_threshold = 0.01  # minimum change % to trigger update
        self.ping_interval = 30  # seconds between ping/pong
        self.connection_timeout = 60  # seconds before considering connection dead
        
        # P/L update configuration
        self.pl_update_throttle = 5  # seconds between P/L updates (unless alert)
        self.last_pl_broadcast = datetime.min  # timestamp of last P/L broadcast
        self.pl_change_threshold = 1.0  # minimum $ change to trigger P/L update
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """
        Accept a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            client_id: Unique identifier for the client
        """
        await websocket.accept()
        
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id,
            connected_at=datetime.now()
        )
        
        self.connections[client_id] = connection
        logger.info(f"WebSocket client {client_id} connected. Total connections: {len(self.connections)}")
        
        # Send connection confirmation
        await self._send_to_client(client_id, ConnectionInfo(
            status="connected",
            message=f"Connected to SPY-FLY real-time feed as {client_id}",
            timestamp=datetime.now().isoformat()
        ))
        
        # Send current price if available
        if "SPY" in self.price_cache:
            await self._send_to_client(client_id, self.price_cache["SPY"])
        
        # Start update task if not running
        if not self.is_running:
            await self.start_price_updates()
    
    async def disconnect(self, client_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: Unique identifier for the client to disconnect
        """
        if client_id in self.connections:
            self.connections.pop(client_id)
            logger.info(f"WebSocket client {client_id} disconnected. Total connections: {len(self.connections)}")
            
            # Stop updates if no connections remain
            if not self.connections and self.is_running:
                await self.stop_price_updates()
    
    async def broadcast_price_update(self, ticker: str, price_data: PriceUpdate) -> None:
        """
        Broadcast price update to all connected clients.
        
        Args:
            ticker: Stock ticker symbol
            price_data: Price update data to broadcast
        """
        if not self.connections:
            return
        
        # Cache the update
        self.price_cache[ticker] = price_data
        
        # Broadcast to all connections
        disconnected_clients = []
        
        for client_id in list(self.connections.keys()):
            try:
                await self._send_to_client(client_id, price_data)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def broadcast_pl_update(self, pl_data: dict | PLUpdate) -> None:
        """
        Broadcast P/L update to all connected clients.
        
        Args:
            pl_data: P/L update data (dict or PLUpdate model)
        """
        if not self.connections:
            return
        
        # Convert dict to PLUpdate model if needed
        if isinstance(pl_data, dict):
            pl_update = PLUpdate(**pl_data)
        else:
            pl_update = pl_data
        
        # Check if we should throttle this update
        if not self._should_broadcast_pl_update(pl_update):
            return
        
        # Cache the update
        self.pl_cache = pl_update
        self.last_pl_broadcast = datetime.now()
        
        # Broadcast to all connections
        disconnected_clients = []
        
        for client_id in list(self.connections.keys()):
            try:
                await self._send_to_client(client_id, pl_update)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error sending P/L update to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
        
        if pl_update.alert:
            logger.warning(f"Stop-loss alert broadcasted to {len(self.connections)} clients")
        else:
            logger.debug(f"P/L update broadcasted to {len(self.connections)} clients")
    
    def _should_broadcast_pl_update(self, pl_update: PLUpdate) -> bool:
        """
        Determine if a P/L update should be broadcasted based on throttling rules.
        
        Args:
            pl_update: P/L update to evaluate
            
        Returns:
            True if update should be broadcasted, False if throttled
        """
        # Always broadcast alerts (stop-loss notifications)
        if pl_update.alert:
            return True
        
        # Always broadcast first P/L update
        if self.pl_cache is None:
            return True
        
        # Check throttling time
        time_since_last = (datetime.now() - self.last_pl_broadcast).total_seconds()
        if time_since_last < self.pl_update_throttle:
            return False
        
        # Check if change is significant enough
        cached_total = self.pl_cache.total_unrealized_pl
        new_total = pl_update.total_unrealized_pl
        change_amount = abs(new_total - cached_total)
        
        if change_amount >= self.pl_change_threshold:
            return True
        
        # Check if any position has a stop-loss alert change
        if self.pl_cache.positions and pl_update.positions:
            cached_positions = {p.id: p for p in self.pl_cache.positions}
            for new_pos in pl_update.positions:
                if new_pos.id in cached_positions:
                    cached_pos = cached_positions[new_pos.id]
                    if new_pos.stop_loss_alert != cached_pos.stop_loss_alert:
                        return True  # Alert status changed
        
        return False
    
    async def handle_price_update_with_pl(self, price_update: PriceUpdate, pl_service) -> None:
        """
        Handle price update and trigger P/L calculation if needed.
        
        This method integrates price updates with P/L calculations,
        triggering P/L broadcasts when SPY price changes significantly.
        
        Args:
            price_update: New SPY price data
            pl_service: P/L calculation service instance
        """
        # First broadcast the price update
        await self.broadcast_price_update("SPY", price_update)
        
        # Check if we should trigger P/L calculation
        should_calculate_pl = False
        
        if "SPY" not in self.price_cache:
            should_calculate_pl = True  # First price update
        else:
            cached_price = self.price_cache["SPY"]
            price_change_percent = abs(price_update.change_percent or 0)
            if price_change_percent >= self.price_change_threshold:
                should_calculate_pl = True  # Significant price change
        
        if should_calculate_pl:
            try:
                # Calculate P/L for all positions
                pl_results = await pl_service.calculate_all_positions_pl()
                
                if pl_results:
                    # Convert to P/L update format
                    positions_data = []
                    has_alert = False
                    
                    for pl_data in pl_results:
                        position_update = PLPositionUpdate(
                            id=pl_data.position_id,
                            symbol="SPY",  # All positions are SPY spreads
                            unrealized_pl=float(pl_data.unrealized_pl),
                            unrealized_pl_percent=float(pl_data.unrealized_pl_percent),
                            current_value=float(pl_data.current_value),
                            stop_loss_alert=pl_data.stop_loss_triggered
                        )
                        positions_data.append(position_update)
                        
                        if pl_data.stop_loss_triggered:
                            has_alert = True
                    
                    # Calculate total P/L
                    total_pl = sum(float(pl.unrealized_pl) for pl in pl_results)
                    
                    # Create P/L update
                    pl_update = PLUpdate(
                        positions=positions_data,
                        total_unrealized_pl=total_pl,
                        spy_price=price_update.price,
                        timestamp=datetime.now().isoformat() + "Z",
                        alert=has_alert
                    )
                    
                    # Broadcast P/L update
                    await self.broadcast_pl_update(pl_update)
                    
            except Exception as e:
                logger.error(f"Error calculating P/L during price update: {e}")
    
    async def _send_to_client(self, client_id: str, data: BaseModel) -> None:
        """
        Send data to a specific client.
        
        Args:
            client_id: Target client identifier
            data: Data to send (will be JSON serialized)
        """
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        
        try:
            await connection.websocket.send_text(data.model_dump_json())
        except WebSocketDisconnect:
            # Client disconnected
            raise
        except Exception as e:
            logger.error(f"Failed to send data to client {client_id}: {e}")
            raise
    
    async def start_price_updates(self) -> None:
        """Start the background task for price updates."""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_task = asyncio.create_task(self._price_update_loop())
        logger.info("Started WebSocket price update loop")
    
    async def stop_price_updates(self) -> None:
        """Stop the background task for price updates."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
        
        logger.info("Stopped WebSocket price update loop")
    
    async def _price_update_loop(self) -> None:
        """
        Background loop that fetches and broadcasts price updates.
        
        Runs continuously while there are active connections.
        """
        logger.info("WebSocket price update loop started")
        
        while self.is_running and self.connections:
            try:
                # Fetch current SPY price
                quote_response = await self.market_service.get_spy_quote()
                
                # Create price update
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
                
                # Check if we should broadcast this update
                should_broadcast = self._should_broadcast_update("SPY", price_update)
                
                if should_broadcast:
                    await self.broadcast_price_update("SPY", price_update)
                    logger.debug(f"Broadcasted SPY price update: ${price_update.price}")
                
            except MarketDataError as e:
                logger.warning(f"Market data error in WebSocket loop: {e}")
                # Send error notification to clients
                error_msg = ConnectionInfo(
                    status="error",
                    message=f"Market data temporarily unavailable: {str(e)}",
                    timestamp=datetime.now().isoformat()
                )
                
                for client_id in list(self.connections.keys()):
                    try:
                        await self._send_to_client(client_id, error_msg)
                    except Exception:
                        pass  # Client will be cleaned up naturally
            
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket price update loop: {e}")
            
            # Wait before next update
            await asyncio.sleep(self.update_interval)
        
        logger.info("WebSocket price update loop ended")
    
    def _should_broadcast_update(self, ticker: str, new_update: PriceUpdate) -> bool:
        """
        Determine if a price update should be broadcasted.
        
        Args:
            ticker: Stock ticker symbol
            new_update: New price update data
            
        Returns:
            True if update should be broadcasted, False otherwise
        """
        # Always broadcast first update
        if ticker not in self.price_cache:
            return True
        
        cached_update = self.price_cache[ticker]
        
        # Always broadcast if market status changed
        if cached_update.market_status != new_update.market_status:
            return True
        
        # Broadcast if price changed significantly
        if cached_update.price != new_update.price:
            if abs(new_update.change_percent or 0) >= self.price_change_threshold:
                return True
        
        # Broadcast if data is fresh (not cached) and some time has passed
        if not new_update.cached:
            try:
                last_update_time = datetime.fromisoformat(cached_update.timestamp.replace('Z', '+00:00'))
                if datetime.now() - last_update_time.replace(tzinfo=None) > timedelta(minutes=5):
                    return True
            except ValueError:
                # If timestamp parsing fails, broadcast anyway
                return True
        
        return False
    
    async def handle_client_message(self, client_id: str, message: str) -> None:
        """
        Handle incoming message from a WebSocket client.
        
        Args:
            client_id: Client identifier
            message: Raw message string from client
        """
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type == "ping":
                # Respond to ping with pong
                pong_msg = ConnectionInfo(
                    type="pong",
                    status="ok",
                    message="pong",
                    timestamp=datetime.now().isoformat()
                )
                await self._send_to_client(client_id, pong_msg)
            elif message_type == "subscribe":
                # Handle subscription requests (future feature)
                ticker = data.get("ticker", "SPY")
                if client_id in self.connections:
                    self.connections[client_id].subscriptions.add(ticker)
                    logger.debug(f"Client {client_id} subscribed to {ticker}")
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {client_id}: {message}")
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get current connection statistics.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "total_connections": len(self.connections),
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "cached_tickers": list(self.price_cache.keys()),
            "connections": [
                {
                    "client_id": conn.client_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "subscriptions": list(conn.subscriptions)
                }
                for conn in self.connections.values()
            ]
        }