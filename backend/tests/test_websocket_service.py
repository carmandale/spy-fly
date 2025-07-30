"""
Tests for WebSocket service functionality.

Tests WebSocket connection management, price broadcasting, and real-time updates.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

from app.services.websocket_service import WebSocketManager, PriceUpdate, ConnectionInfo
from app.services.market_service import MarketDataService, QuoteResponse


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.accept_called = False
        
    async def accept(self):
        """Mock WebSocket accept."""
        self.accept_called = True
        
    async def send_text(self, message: str):
        """Mock sending text message."""
        if self.closed:
            raise WebSocketDisconnect(code=1000)
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000):
        """Mock WebSocket close."""
        self.closed = True


@pytest.fixture
def mock_market_service():
    """Create mock market service for testing."""
    service = Mock(spec=MarketDataService)
    service.get_spy_quote = AsyncMock(return_value=QuoteResponse(
        ticker="SPY",
        price=450.50,
        bid=450.48,
        ask=450.52,
        volume=1000000,
        change=2.50,
        change_percent=0.56,
        market_status="open",
        timestamp="2025-01-30T10:30:00Z",
        cached=False
    ))
    return service


@pytest.fixture
def websocket_manager(mock_market_service):
    """Create WebSocket manager with mock market service."""
    return WebSocketManager(market_service=mock_market_service)


@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocket manager functionality."""
    
    async def test_connect_client(self, websocket_manager):
        """Test connecting a client to WebSocket."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        await websocket_manager.connect(mock_ws, client_id)
        
        assert mock_ws.accept_called
        assert client_id in websocket_manager.connections
        assert websocket_manager.connections[client_id]["websocket"] == mock_ws
        assert websocket_manager.connections[client_id]["connected_at"] is not None
        
    async def test_disconnect_client(self, websocket_manager):
        """Test disconnecting a client from WebSocket."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        # Connect first
        await websocket_manager.connect(mock_ws, client_id)
        assert client_id in websocket_manager.connections
        
        # Then disconnect
        await websocket_manager.disconnect(client_id)
        assert client_id not in websocket_manager.connections
        
    async def test_disconnect_nonexistent_client(self, websocket_manager):
        """Test disconnecting a client that doesn't exist."""
        # Should not raise an error
        await websocket_manager.disconnect("nonexistent_client")
        
    async def test_broadcast_price_update(self, websocket_manager):
        """Test broadcasting price updates to all connected clients."""
        # Connect multiple clients
        clients = []
        for i in range(3):
            mock_ws = MockWebSocket()
            client_id = f"test_client_{i}"
            await websocket_manager.connect(mock_ws, client_id)
            clients.append((client_id, mock_ws))
        
        # Create price update
        price_update = PriceUpdate(
            ticker="SPY",
            price=451.25,
            bid=451.20,
            ask=451.30,
            volume=1500000,
            change=3.25,
            change_percent=0.72,
            market_status="open",
            timestamp="2025-01-30T10:35:00Z",
            cached=False
        )
        
        # Broadcast update
        await websocket_manager.broadcast_price_update("SPY", price_update)
        
        # Verify all clients received the message
        for client_id, mock_ws in clients:
            assert len(mock_ws.messages_sent) == 2  # Connection status + price update
            
            # Check price update message
            price_message = json.loads(mock_ws.messages_sent[1])
            assert price_message["type"] == "price_update"
            assert price_message["ticker"] == "SPY"
            assert price_message["price"] == 451.25
            assert price_message["change_percent"] == 0.72
            
    async def test_broadcast_to_disconnected_client(self, websocket_manager):
        """Test broadcasting when a client is disconnected."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        await websocket_manager.connect(mock_ws, client_id)
        
        # Simulate client disconnection
        mock_ws.closed = True
        
        price_update = PriceUpdate(
            ticker="SPY",
            price=450.00,
            change_percent=0.0,
            market_status="open",
            timestamp="2025-01-30T10:40:00Z",
            cached=False
        )
        
        # Should not raise an error
        await websocket_manager.broadcast_price_update("SPY", price_update)
        
        # Client should be removed from connections
        assert client_id not in websocket_manager.connections
        
    async def test_handle_ping_message(self, websocket_manager):
        """Test handling ping messages from clients."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        await websocket_manager.connect(mock_ws, client_id)
        
        # Send ping message
        ping_message = json.dumps({"type": "ping"})
        await websocket_manager.handle_client_message(client_id, ping_message)
        
        # Should receive pong response
        pong_message = json.loads(mock_ws.messages_sent[-1])
        assert pong_message["type"] == "pong"
        assert "timestamp" in pong_message
        
    async def test_handle_invalid_message(self, websocket_manager):
        """Test handling invalid JSON messages from clients."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        await websocket_manager.connect(mock_ws, client_id)
        
        # Send invalid JSON
        await websocket_manager.handle_client_message(client_id, "invalid json")
        
        # Should not crash - error logged but no response sent
        # Client remains connected
        assert client_id in websocket_manager.connections
        
    async def test_get_connection_stats(self, websocket_manager):
        """Test getting connection statistics."""
        # Connect a few clients
        for i in range(2):
            mock_ws = MockWebSocket()
            client_id = f"test_client_{i}"
            await websocket_manager.connect(mock_ws, client_id)
        
        stats = websocket_manager.get_connection_stats()
        
        assert stats["total_connections"] == 2
        assert stats["is_running"] is True
        assert len(stats["connections"]) == 2
        assert stats["update_interval"] == 15
        
        # Check connection details
        for conn in stats["connections"]:
            assert "client_id" in conn
            assert "connected_at" in conn
            assert "last_ping" in conn
            
    async def test_start_stop_price_updates(self, websocket_manager, mock_market_service):
        """Test starting and stopping automatic price updates."""
        # Start updates
        await websocket_manager.start_price_updates()
        assert websocket_manager.update_task is not None
        assert not websocket_manager.update_task.done()
        
        # Stop updates
        await websocket_manager.stop_price_updates()
        assert websocket_manager.update_task is None
        
    @patch("asyncio.sleep")
    async def test_price_update_loop(self, mock_sleep, websocket_manager, mock_market_service):
        """Test the automatic price update loop."""
        mock_sleep.return_value = None
        
        # Connect a client
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        await websocket_manager.connect(mock_ws, client_id)
        
        # Start updates and let it run one iteration
        update_task = asyncio.create_task(websocket_manager._price_update_loop())
        
        # Give it a moment to process
        await asyncio.sleep(0.01)
        
        # Cancel the task
        update_task.cancel()
        
        try:
            await update_task
        except asyncio.CancelledError:
            pass
        
        # Verify market service was called
        mock_market_service.get_spy_quote.assert_called()
        
        # Verify client received price update
        assert len(mock_ws.messages_sent) >= 1
        
    async def test_send_connection_status(self, websocket_manager):
        """Test sending connection status messages."""
        mock_ws = MockWebSocket()
        client_id = "test_client_1"
        
        await websocket_manager.connect(mock_ws, client_id)
        
        # Send connection status
        status = ConnectionInfo(
            status="connected",
            message="Successfully connected to price feed",
            timestamp="2025-01-30T10:45:00Z"
        )
        
        await websocket_manager._send_connection_status(client_id, status)
        
        # Check message was sent
        status_message = json.loads(mock_ws.messages_sent[-1])
        assert status_message["type"] == "connection_status"
        assert status_message["status"] == "connected"
        assert status_message["message"] == "Successfully connected to price feed"
        
    async def test_multiple_clients_price_updates(self, websocket_manager):
        """Test price updates with multiple clients."""
        clients = []
        
        # Connect 5 clients
        for i in range(5):
            mock_ws = MockWebSocket()
            client_id = f"client_{i}"
            await websocket_manager.connect(mock_ws, client_id)
            clients.append((client_id, mock_ws))
        
        # Broadcast price update
        price_update = PriceUpdate(
            ticker="SPY",
            price=452.75,
            change_percent=1.25,
            market_status="open",
            timestamp="2025-01-30T10:50:00Z",
            cached=False
        )
        
        await websocket_manager.broadcast_price_update("SPY", price_update)
        
        # All clients should receive the update
        for client_id, mock_ws in clients:
            assert len(mock_ws.messages_sent) >= 2  # At least connection + price update
            
            # Find the price update message
            price_messages = [
                json.loads(msg) for msg in mock_ws.messages_sent 
                if json.loads(msg).get("type") == "price_update"
            ]
            assert len(price_messages) == 1
            assert price_messages[0]["price"] == 452.75