"""
WebSocket service for real-time price feeds and market data updates.

This service manages WebSocket connections and broadcasts real-time SPY price
updates to connected clients with proper throttling and error handling.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.market_service import MarketDataService
from app.services.pl_calculation_service import PLCalculationService
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


class PLUpdate(BaseModel):
    """Model for P/L update messages sent via WebSocket."""
    
    type: str = "pl_update"
    position_id: int
    symbol: str
    contracts: int
    
    # Current P/L data
    unrealized_pnl: float
    unrealized_pnl_percent: float
    current_total_value: float
    entry_total_cost: float
    
    # Greeks and risk metrics
    position_delta: float | None = None
    position_theta: float | None = None
    daily_theta_decay: float | None = None
    
    # Alert information
    alert_triggered: bool = False
    alert_type: str | None = None
    alert_message: str | None = None
    
    # Market data
    current_spy_price: float
    market_session: str
    timestamp: str


class PortfolioPLUpdate(BaseModel):
    """Model for portfolio-level P/L update messages."""
    
    type: str = "portfolio_pl_update"
    total_positions: int
    total_unrealized_pnl: float
    total_unrealized_pnl_percent: float
    total_daily_theta: float
    current_spy_price: float
    timestamp: str
    positions: List[Dict] = []


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
    
    def __init__(
        self, 
        market_service: MarketDataService,
        pl_calculation_service: PLCalculationService | None = None
    ):
        """
        Initialize WebSocket manager.
        
        Args:
            market_service: Service for fetching market data
            pl_calculation_service: Service for P/L calculations (optional)
        """
        self.market_service = market_service
        self.pl_calculation_service = pl_calculation_service
        self.connections: Dict[str, WebSocketConnection] = {}
        self.price_cache: Dict[str, PriceUpdate] = {}
        self.pl_cache: Dict[str, PortfolioPLUpdate] = {}
        self.update_task: asyncio.Task | None = None
        self.is_running = False
        
        # Configuration
        self.update_interval = 15  # seconds between price updates
        self.price_change_threshold = 0.01  # minimum change % to trigger update
        self.ping_interval = 30  # seconds between ping/pong
        self.connection_timeout = 60  # seconds before considering connection dead
        self.pl_update_enabled = pl_calculation_service is not None
    
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
        
        # Send current P/L if available
        if "portfolio" in self.pl_cache:
            await self._send_to_client(client_id, self.pl_cache["portfolio"])
        
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
    
    async def broadcast_pl_update(self, pl_data: PortfolioPLUpdate) -> None:
        """
        Broadcast P/L update to all connected clients.
        
        Args:
            pl_data: Portfolio P/L data to broadcast
        """
        if not self.connections or not self.pl_update_enabled:
            return
        
        # Cache the update
        self.pl_cache["portfolio"] = pl_data
        
        # Broadcast to all connections
        disconnected_clients = []
        
        for client_id in list(self.connections.keys()):
            try:
                await self._send_to_client(client_id, pl_data)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error sending P/L update to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def broadcast_position_pl_update(self, position_pl_data: PLUpdate) -> None:
        """
        Broadcast individual position P/L update to all connected clients.
        
        Args:
            position_pl_data: Individual position P/L data to broadcast
        """
        if not self.connections or not self.pl_update_enabled:
            return
        
        # Broadcast to all connections
        disconnected_clients = []
        
        for client_id in list(self.connections.keys()):
            try:
                await self._send_to_client(client_id, position_pl_data)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error sending position P/L update to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
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
                
                # Calculate and broadcast P/L updates if service is available
                if self.pl_calculation_service and should_broadcast:
                    await self._calculate_and_broadcast_pl_updates(price_update.price)
                
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
    
    async def _calculate_and_broadcast_pl_updates(self, current_spy_price: float) -> None:
        """
        Calculate P/L for all open positions and broadcast updates.
        
        Args:
            current_spy_price: Current SPY price for calculations
        """
        try:
            # Calculate portfolio P/L
            portfolio_pl = await self.pl_calculation_service.calculate_portfolio_pl()
            
            if portfolio_pl["total_positions"] > 0:
                # Create portfolio P/L update message
                portfolio_update = PortfolioPLUpdate(
                    total_positions=portfolio_pl["total_positions"],
                    total_unrealized_pnl=portfolio_pl["total_unrealized_pnl"],
                    total_unrealized_pnl_percent=portfolio_pl["total_unrealized_pnl_percent"],
                    total_daily_theta=portfolio_pl["total_daily_theta"],
                    current_spy_price=current_spy_price,
                    timestamp=datetime.now().isoformat(),
                    positions=portfolio_pl["positions"]
                )
                
                # Check if we should broadcast this P/L update
                should_broadcast_pl = self._should_broadcast_pl_update(portfolio_update)
                
                if should_broadcast_pl:
                    await self.broadcast_pl_update(portfolio_update)
                    logger.debug(f"Broadcasted portfolio P/L update: ${portfolio_pl['total_unrealized_pnl']:.2f}")
                
                # Broadcast individual position updates for positions with alerts
                for position_data in portfolio_pl["positions"]:
                    if position_data.get("alert_triggered", False):
                        position_update = PLUpdate(
                            position_id=position_data["position_id"],
                            symbol=position_data["symbol"],
                            contracts=position_data["contracts"],
                            unrealized_pnl=position_data["unrealized_pnl"],
                            unrealized_pnl_percent=position_data["unrealized_pnl_percent"],
                            current_total_value=position_data["current_total_value"],
                            entry_total_cost=position_data["entry_total_cost"],
                            position_delta=position_data.get("position_delta"),
                            position_theta=position_data.get("position_theta"),
                            daily_theta_decay=position_data.get("daily_theta_decay"),
                            alert_triggered=position_data["alert_triggered"],
                            alert_type=position_data.get("alert_type"),
                            alert_message=position_data.get("alert_message"),
                            current_spy_price=current_spy_price,
                            market_session=position_data.get("market_session", "regular"),
                            timestamp=datetime.now().isoformat()
                        )
                        
                        await self.broadcast_position_pl_update(position_update)
                        logger.info(f"Broadcasted alert for position {position_data['position_id']}: {position_data.get('alert_message')}")
        
        except Exception as e:
            logger.error(f"Error calculating P/L updates: {e}")
            # Don't raise - we don't want P/L errors to break price updates
    
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
    
    def _should_broadcast_pl_update(self, new_pl_update: PortfolioPLUpdate) -> bool:
        """
        Determine if a P/L update should be broadcasted.
        
        Args:
            new_pl_update: New P/L update data
            
        Returns:
            True if update should be broadcasted, False otherwise
        """
        # Always broadcast first P/L update
        if "portfolio" not in self.pl_cache:
            return True
        
        cached_pl_update = self.pl_cache["portfolio"]
        
        # Broadcast if total P/L changed significantly (more than $10 or 1%)
        pnl_change = abs(new_pl_update.total_unrealized_pnl - cached_pl_update.total_unrealized_pnl)
        pnl_percent_change = abs(new_pl_update.total_unrealized_pnl_percent - cached_pl_update.total_unrealized_pnl_percent)
        
        if pnl_change >= 10.0 or pnl_percent_change >= 1.0:
            return True
        
        # Broadcast if number of positions changed
        if new_pl_update.total_positions != cached_pl_update.total_positions:
            return True
        
        # Broadcast if any position has alerts
        for position in new_pl_update.positions:
            if position.get("alert_triggered", False):
                return True
        
        # Broadcast every 5 minutes during market hours regardless
        try:
            time_since_last = datetime.now() - datetime.fromisoformat(cached_pl_update.timestamp.replace('Z', '+00:00'))
            if time_since_last.total_seconds() >= 300:  # 5 minutes
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
