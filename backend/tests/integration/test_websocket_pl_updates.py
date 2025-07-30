"""
Tests for WebSocket P/L update broadcasting functionality.

Tests the integration of P/L calculations with WebSocket broadcasting to ensure
real-time P/L updates are properly sent to connected clients.
"""

import pytest
import json
import asyncio
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.db_models import Position
from app.services.websocket_service import WebSocketManager, PriceUpdate
from app.services.pl_calculation_service import PLCalculationService, PositionPLData


class TestWebSocketPLBroadcasting:
    """Test WebSocket P/L update broadcasting."""
    
    @pytest.fixture
    def mock_market_service(self):
        """Create mock market data service."""
        mock = Mock()
        mock.get_spy_quote = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_pl_service(self):
        """Create mock P/L calculation service."""
        mock = Mock(spec=PLCalculationService)
        mock.calculate_all_positions_pl = AsyncMock()
        return mock
    
    @pytest.fixture
    def websocket_manager(self, mock_market_service):
        """Create WebSocket manager with mocked dependencies."""
        return WebSocketManager(market_service=mock_market_service)
    
    @pytest.fixture
    def sample_position(self, db):
        """Create a sample position for testing."""
        position = Position(
            id=1,
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50"),
            status="open",
            latest_value=Decimal("-200.00"),
            latest_unrealized_pl=Decimal("50.00"),
            latest_unrealized_pl_percent=Decimal("10.00"),
            stop_loss_alert_active=False
        )
        db.add(position)
        db.commit()
        return position
    
    @pytest.mark.asyncio
    async def test_broadcast_pl_update_message_format(self, websocket_manager):
        """Test that P/L update messages have correct format."""
        # Mock WebSocket connection
        mock_websocket = Mock()
        client_id = "test_client"
        
        # Connect mock client
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Create sample P/L update data
        pl_data = {
            "type": "pl_update",
            "positions": [
                {
                    "id": 1,
                    "symbol": "SPY",
                    "unrealized_pl": 50.0,
                    "unrealized_pl_percent": 10.0,
                    "current_value": -200.0,
                    "stop_loss_alert": False
                }
            ],
            "total_unrealized_pl": 50.0,
            "spy_price": 451.25,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        # Test broadcasting P/L update
        await websocket_manager.broadcast_pl_update(pl_data)
        
        # Verify message was sent
        mock_websocket.send_text.assert_called_once()
        sent_message = mock_websocket.send_text.call_args[0][0]
        parsed_message = json.loads(sent_message)
        
        # Verify message structure
        assert parsed_message["type"] == "pl_update"
        assert "positions" in parsed_message
        assert "total_unrealized_pl" in parsed_message
        assert "spy_price" in parsed_message
        assert "timestamp" in parsed_message
        
        # Verify position data structure
        position = parsed_message["positions"][0]
        assert position["id"] == 1
        assert position["symbol"] == "SPY"
        assert position["unrealized_pl"] == 50.0
        assert position["unrealized_pl_percent"] == 10.0
        assert position["current_value"] == -200.0
        assert position["stop_loss_alert"] is False
    
    async def test_pl_update_triggered_by_price_change(self, websocket_manager, mock_pl_service):
        """Test that P/L updates are triggered when SPY price changes."""
        # Mock WebSocket connection
        mock_websocket = Mock()
        client_id = "test_client"
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Mock P/L calculation service
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.25"),
                current_value=Decimal("-190.00"),
                unrealized_pl=Decimal("60.00"),
                unrealized_pl_percent=Decimal("12.00"),
                risk_percent=Decimal("-12.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Test price update triggering P/L calculation
        price_update = PriceUpdate(
            ticker="SPY",
            price=451.25,
            bid=451.20,
            ask=451.30,
            volume=1000000,
            change=1.25,
            change_percent=0.28,
            market_status="regular",
            timestamp=datetime.now().isoformat()
        )
        
        # Simulate price update handling with P/L service integration
        await websocket_manager.handle_price_update_with_pl(price_update, mock_pl_service)
        
        # Verify P/L calculation was triggered
        mock_pl_service.calculate_all_positions_pl.assert_called_once()
        
        # Verify both price and P/L updates were sent
        assert mock_websocket.send_text.call_count >= 2
    
    async def test_pl_update_throttling(self, websocket_manager):
        """Test that P/L updates are throttled to prevent spam."""
        # Mock WebSocket connection
        mock_websocket = Mock()
        client_id = "test_client"
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Create multiple P/L updates with small changes
        base_pl_data = {
            "type": "pl_update",
            "positions": [
                {
                    "id": 1,
                    "symbol": "SPY",
                    "unrealized_pl": 50.0,
                    "unrealized_pl_percent": 10.0,
                    "current_value": -200.0,
                    "stop_loss_alert": False
                }
            ],
            "total_unrealized_pl": 50.0,
            "spy_price": 451.25,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        # Send multiple updates rapidly
        for i in range(5):
            pl_data = base_pl_data.copy()
            pl_data["positions"][0]["unrealized_pl"] = 50.0 + i * 0.1  # Small changes
            await websocket_manager.broadcast_pl_update(pl_data)
        
        # Verify throttling - should not send all 5 updates
        # (Implementation will determine exact throttling behavior)
        call_count = mock_websocket.send_text.call_count
        assert call_count < 5, "P/L updates should be throttled"
    
    async def test_stop_loss_alert_priority_update(self, websocket_manager):
        """Test that stop-loss alerts bypass throttling."""
        # Mock WebSocket connection
        mock_websocket = Mock()
        client_id = "test_client"
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Create P/L update with stop-loss alert
        pl_data_with_alert = {
            "type": "pl_update",
            "positions": [
                {
                    "id": 1,
                    "symbol": "SPY",
                    "unrealized_pl": -100.0,
                    "unrealized_pl_percent": -20.0,  # Stop-loss threshold
                    "current_value": -350.0,
                    "stop_loss_alert": True
                }
            ],
            "total_unrealized_pl": -100.0,
            "spy_price": 448.75,
            "timestamp": datetime.now().isoformat() + "Z",
            "alert": True  # Flag for priority handling
        }
        
        # Send stop-loss alert update
        await websocket_manager.broadcast_pl_update(pl_data_with_alert)
        
        # Verify immediate send (no throttling for alerts)
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message.get("alert") is True
        assert sent_message["positions"][0]["stop_loss_alert"] is True
    
    async def test_multiple_clients_pl_broadcast(self, websocket_manager):
        """Test P/L updates are sent to all connected clients."""
        # Connect multiple mock clients
        clients = []
        for i in range(3):
            mock_websocket = Mock()
            client_id = f"client_{i}"
            await websocket_manager.connect(mock_websocket, client_id)
            clients.append((client_id, mock_websocket))
        
        # Create P/L update
        pl_data = {
            "type": "pl_update",
            "positions": [
                {
                    "id": 1,
                    "symbol": "SPY",
                    "unrealized_pl": 75.0,
                    "unrealized_pl_percent": 15.0,
                    "current_value": -175.0,
                    "stop_loss_alert": False
                }
            ],
            "total_unrealized_pl": 75.0,
            "spy_price": 452.00,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        # Broadcast P/L update
        await websocket_manager.broadcast_pl_update(pl_data)
        
        # Verify all clients received the update
        for client_id, mock_websocket in clients:
            mock_websocket.send_text.assert_called()
            sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
            assert sent_message["type"] == "pl_update"
            assert sent_message["total_unrealized_pl"] == 75.0
    
    async def test_pl_update_error_handling(self, websocket_manager):
        """Test error handling when P/L updates fail."""
        # Mock WebSocket connection that will fail
        mock_websocket = Mock()
        mock_websocket.send_text.side_effect = Exception("Connection failed")
        client_id = "failing_client"
        
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Create P/L update
        pl_data = {
            "type": "pl_update",
            "positions": [],
            "total_unrealized_pl": 0.0,
            "spy_price": 451.00,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        # Should not raise exception when client fails
        try:
            await websocket_manager.broadcast_pl_update(pl_data)
        except Exception:
            pytest.fail("broadcast_pl_update should handle client errors gracefully")
        
        # Verify failing client was disconnected
        assert client_id not in websocket_manager.connections
    
    async def test_pl_update_integration_with_price_feed(self, websocket_manager, mock_pl_service):
        """Test integration between price feed and P/L updates."""
        # Mock WebSocket connection
        mock_websocket = Mock()
        client_id = "test_client"
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Mock P/L service with position data
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.50"),
                current_value=Decimal("-185.00"),
                unrealized_pl=Decimal("65.00"),
                unrealized_pl_percent=Decimal("13.00"),
                risk_percent=Decimal("-13.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.now()
            )
        ]
        mock_pl_service.calculate_all_positions_pl.return_value = mock_pl_data
        
        # Simulate the integrated workflow
        with patch.object(websocket_manager, 'pl_calculation_service', mock_pl_service):
            # Price update should trigger P/L calculation and broadcast
            price_update = PriceUpdate(
                ticker="SPY",
                price=451.50,
                bid=451.45,
                ask=451.55,
                volume=1200000,
                change=1.50,
                change_percent=0.33,
                market_status="regular",
                timestamp=datetime.now().isoformat()
            )
            
            await websocket_manager.broadcast_price_update("SPY", price_update)
            
            # Should have sent both price update and P/L update
            assert mock_websocket.send_text.call_count >= 1