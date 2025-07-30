"""
Tests for WebSocket API endpoints.

Tests WebSocket endpoint connectivity, stats API, and broadcast functionality.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.main import app
from app.services.websocket_service import WebSocketManager


@pytest.fixture
def client():
    """Create test client for API endpoints."""
    return TestClient(app)


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager for testing."""
    manager = Mock(spec=WebSocketManager)
    manager.connections = {}
    manager.get_connection_stats = Mock(return_value={
        "total_connections": 2,
        "is_running": True,
        "update_interval": 15,
        "cached_tickers": ["SPY"],
        "connections": [
            {
                "client_id": "client_1",
                "connected_at": "2025-01-30T10:30:00Z",
                "last_ping": "2025-01-30T10:35:00Z"
            },
            {
                "client_id": "client_2", 
                "connected_at": "2025-01-30T10:32:00Z",
                "last_ping": "2025-01-30T10:36:00Z"
            }
        ]
    })
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.handle_client_message = AsyncMock()
    manager.broadcast_price_update = AsyncMock()
    manager._send_to_client = AsyncMock()
    
    # Mock market service for force update
    manager.market_service = Mock()
    manager.market_service.get_spy_quote = AsyncMock(return_value=Mock(
        ticker="SPY",
        price=451.25,
        bid=451.20,
        ask=451.30,
        volume=1500000,
        change=2.75,
        change_percent=0.61,
        market_status="open",
        timestamp="2025-01-30T10:40:00Z",
        cached=False
    ))
    
    return manager


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints."""
    
    def test_websocket_stats_endpoint(self, client, mock_websocket_manager):
        """Test getting WebSocket connection statistics."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.get("/api/v1/ws/stats")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_connections"] == 2
            assert data["is_running"] is True
            assert data["update_interval"] == 15
            assert data["cached_tickers"] == ["SPY"]
            assert len(data["connections"]) == 2
            
            # Check connection details
            conn = data["connections"][0]
            assert "client_id" in conn
            assert "connected_at" in conn
            assert "last_ping" in conn
            
    def test_websocket_stats_error_handling(self, client):
        """Test WebSocket stats endpoint error handling."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", side_effect=Exception("Service unavailable")):
            response = client.get("/api/v1/ws/stats")
            
            assert response.status_code == 500
            assert "Failed to get WebSocket statistics" in response.json()["detail"]
            
    def test_test_broadcast_endpoint(self, client, mock_websocket_manager):
        """Test the test broadcast endpoint."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.post("/api/v1/ws/broadcast/test?message=Hello%20World")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Test message broadcasted to 2 clients" in data["message"]
            assert data["connections"] == 2
            assert data["test_message"] == "Hello World"
            
    def test_test_broadcast_no_clients(self, client, mock_websocket_manager):
        """Test test broadcast when no clients are connected."""
        mock_websocket_manager.get_connection_stats.return_value = {
            "total_connections": 0,
            "is_running": True,
            "update_interval": 15,
            "cached_tickers": [],
            "connections": []
        }
        
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.post("/api/v1/ws/broadcast/test")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "No clients connected to broadcast to" in data["message"]
            assert data["connections"] == 0
            
    def test_test_broadcast_error_handling(self, client):
        """Test test broadcast endpoint error handling."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", side_effect=Exception("Broadcast failed")):
            response = client.post("/api/v1/ws/broadcast/test")
            
            assert response.status_code == 500
            assert "Failed to broadcast test message" in response.json()["detail"]
            
    def test_force_price_update_endpoint(self, client, mock_websocket_manager):
        """Test the force price update endpoint."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.post("/api/v1/ws/force-update")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Price update forced to 2 clients" in data["message"]
            assert data["connections"] == 2
            assert data["price"] == 451.25
            assert data["ticker"] == "SPY"
            assert data["market_status"] == "open"
            assert data["cached"] is False
            
            # Verify market service was called
            mock_websocket_manager.market_service.get_spy_quote.assert_called_once()
            
            # Verify broadcast was called
            mock_websocket_manager.broadcast_price_update.assert_called_once()
            
    def test_force_price_update_no_clients(self, client, mock_websocket_manager):
        """Test force price update when no clients are connected."""
        mock_websocket_manager.get_connection_stats.return_value = {
            "total_connections": 0,
            "is_running": True,
            "update_interval": 15,
            "cached_tickers": [],
            "connections": []
        }
        
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.post("/api/v1/ws/force-update")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "No clients connected to update" in data["message"]
            assert data["connections"] == 0
            
            # Market service should not be called
            mock_websocket_manager.market_service.get_spy_quote.assert_not_called()
            
    def test_force_price_update_error_handling(self, client, mock_websocket_manager):
        """Test force price update endpoint error handling."""
        mock_websocket_manager.market_service.get_spy_quote.side_effect = Exception("Market data unavailable")
        
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            response = client.post("/api/v1/ws/force-update")
            
            assert response.status_code == 500
            assert "Failed to force price update" in response.json()["detail"]


class TestWebSocketConnection:
    """Test WebSocket connection functionality using TestClient."""
    
    def test_websocket_connection_basic(self, client, mock_websocket_manager):
        """Test basic WebSocket connection."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            with client.websocket_connect("/api/v1/ws/price-feed") as websocket:
                # Connection should be established successfully
                # Mock manager connect should be called
                mock_websocket_manager.connect.assert_called_once()
                
    def test_websocket_send_ping(self, client, mock_websocket_manager):
        """Test sending ping message over WebSocket."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", return_value=mock_websocket_manager):
            with client.websocket_connect("/api/v1/ws/price-feed") as websocket:
                # Send ping message
                websocket.send_text(json.dumps({"type": "ping"}))
                
                # Should handle the message
                mock_websocket_manager.handle_client_message.assert_called()
                
    def test_websocket_connection_manager_error(self, client):
        """Test WebSocket connection when manager initialization fails."""
        with patch("app.api.v1.endpoints.websocket.get_websocket_manager", side_effect=Exception("Manager failed")):
            # Should handle the error gracefully
            try:
                with client.websocket_connect("/api/v1/ws/price-feed") as websocket:
                    pass
            except Exception:
                # Exception expected due to manager failure
                pass


@pytest.mark.asyncio 
class TestWebSocketEndpointIntegration:
    """Integration tests for WebSocket endpoints."""
    
    async def test_websocket_manager_singleton(self):
        """Test that WebSocket manager is properly managed as singleton."""
        from app.api.v1.endpoints.websocket import get_websocket_manager
        
        # Reset global manager
        import app.api.v1.endpoints.websocket as ws_module
        ws_module.websocket_manager = None
        
        # Get manager twice
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        
        # Should be the same instance
        assert manager1 is manager2
        assert manager1.market_service is not None
        
    async def test_websocket_endpoint_documentation(self):
        """Test that WebSocket endpoint has proper documentation."""
        from app.api.v1.endpoints.websocket import websocket_price_feed
        
        # Check docstring exists and contains key information
        assert websocket_price_feed.__doc__ is not None
        doc = websocket_price_feed.__doc__
        
        assert "real-time SPY price feeds" in doc
        assert "price_update" in doc
        assert "connection_status" in doc
        assert "ping" in doc