"""
Tests for P/L calculation API endpoints.

Tests position P/L endpoints including current values and history.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.db_models import Position, PositionSnapshot
from app.services.pl_calculation_service import PLCalculationService, PositionPLData
from app.api.deps import get_db


class TestPLEndpoints:
    """Test P/L calculation API endpoints."""
    
    @pytest.fixture
    def mock_pl_service(self):
        """Create a mock P/L calculation service."""
        mock = Mock(spec=PLCalculationService)
        return mock
    
    @pytest.fixture
    def client_with_mocks(self, mock_pl_service, db):
        """Create test client with mocked dependencies."""
        # Override dependencies
        def get_mock_pl_service():
            return mock_pl_service
        
        def get_test_db():
            return db
        
        app.dependency_overrides[get_db] = get_test_db
        # We'll need to add get_pl_service dependency later
        
        client = TestClient(app)
        yield client
        
        # Clean up
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def sample_positions(self, db):
        """Create sample positions in database."""
        positions = [
            Position(
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
            ),
            Position(
                id=2,
                symbol="SPY",
                long_strike=Decimal("460.00"),
                short_strike=Decimal("465.00"),
                expiration_date=date.today(),
                quantity=3,
                entry_value=Decimal("-150.00"),
                max_risk=Decimal("300.00"),
                max_profit=Decimal("150.00"),
                breakeven_price=Decimal("462.50"),
                status="open",
                latest_value=Decimal("-135.00"),
                latest_unrealized_pl=Decimal("15.00"),
                latest_unrealized_pl_percent=Decimal("5.00"),
                stop_loss_alert_active=False
            )
        ]
        
        for position in positions:
            db.add(position)
        db.commit()
        
        return positions
    
    @pytest.fixture
    def sample_snapshots(self, db, sample_positions):
        """Create sample position snapshots."""
        now = datetime.utcnow()
        snapshots = []
        
        # Create hourly snapshots for position 1
        for i in range(24):
            snapshot = PositionSnapshot(
                position_id=1,
                snapshot_time=now - timedelta(hours=i),
                spy_price=Decimal("451.00") - Decimal(str(i * 0.1)),
                current_value=Decimal("-200.00") - Decimal(str(i * 2)),
                unrealized_pl=Decimal("50.00") - Decimal(str(i * 2)),
                unrealized_pl_percent=Decimal("10.00") - Decimal(str(i * 0.4)),
                risk_percent=Decimal("-10.00") + Decimal(str(i * 0.4)),
                stop_loss_triggered=False
            )
            snapshots.append(snapshot)
            db.add(snapshot)
        
        db.commit()
        return snapshots
    
    def test_get_current_pl(self, client, sample_positions):
        """Test GET /api/v1/positions/pl/current endpoint."""
        response = client.get("/api/v1/positions/pl/current")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "positions" in data
        assert "total_unrealized_pl" in data
        assert "spy_price" in data
        
        # Check positions data
        positions = data["positions"]
        assert len(positions) == 2
        
        # Check first position
        pos1 = positions[0]
        assert pos1["id"] == 1
        assert pos1["symbol"] == "SPY"
        assert pos1["long_strike"] == 450.0
        assert pos1["short_strike"] == 455.0
        assert pos1["quantity"] == 5
        assert pos1["entry_value"] == -250.0
        assert pos1["current_value"] == -200.0
        assert pos1["unrealized_pl"] == 50.0
        assert pos1["unrealized_pl_percent"] == 10.0
        assert pos1["stop_loss_alert"] is False
        
        # Check total P/L
        assert data["total_unrealized_pl"] == 65.0  # 50 + 15
    
    def test_get_current_pl_no_positions(self, client):
        """Test current P/L endpoint with no open positions."""
        response = client.get("/api/v1/positions/pl/current")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["positions"] == []
        assert data["total_unrealized_pl"] == 0.0
    
    def test_get_position_pl_history(self, client, sample_snapshots):
        """Test GET /api/v1/positions/{id}/pl/history endpoint."""
        response = client.get("/api/v1/positions/1/pl/history")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["position_id"] == 1
        assert "history" in data
        
        # Default should return 24 hours of history
        history = data["history"]
        assert len(history) == 24
        
        # Check first (most recent) snapshot
        snapshot = history[0]
        assert "timestamp" in snapshot
        assert snapshot["unrealized_pl"] == 50.0
        assert snapshot["unrealized_pl_percent"] == 10.0
        assert snapshot["spy_price"] == 451.0
        assert snapshot["current_value"] == -200.0
    
    def test_get_position_pl_history_with_hours(self, client, sample_snapshots):
        """Test history endpoint with hours parameter."""
        response = client.get("/api/v1/positions/1/pl/history?hours=12")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return only 12 hours of history
        assert len(data["history"]) == 12
    
    def test_get_position_pl_history_invalid_hours(self, client):
        """Test history endpoint with invalid hours parameter."""
        # Hours too high
        response = client.get("/api/v1/positions/1/pl/history?hours=200")
        assert response.status_code == 400
        assert "Invalid hours parameter" in response.json()["detail"]
        
        # Hours too low
        response = client.get("/api/v1/positions/1/pl/history?hours=0")
        assert response.status_code == 400
        
        # Non-numeric hours
        response = client.get("/api/v1/positions/1/pl/history?hours=abc")
        assert response.status_code == 422
    
    def test_get_position_pl_history_not_found(self, client):
        """Test history endpoint with non-existent position."""
        response = client.get("/api/v1/positions/999/pl/history")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Position not found"
    
    async def test_calculate_pl(self, client_with_mocks, mock_pl_service, sample_positions):
        """Test POST /api/v1/positions/pl/calculate endpoint."""
        # Mock the calculation service
        mock_pl_data = [
            PositionPLData(
                position_id=1,
                spy_price=Decimal("451.25"),
                current_value=Decimal("-190.00"),
                unrealized_pl=Decimal("60.00"),
                unrealized_pl_percent=Decimal("12.00"),
                risk_percent=Decimal("-12.00"),
                stop_loss_triggered=False,
                calculation_time=datetime.utcnow()
            ),
            PositionPLData(
                position_id=2,
                spy_price=Decimal("451.25"),
                current_value=Decimal("-130.00"),
                unrealized_pl=Decimal("20.00"),
                unrealized_pl_percent=Decimal("6.67"),
                risk_percent=Decimal("-6.67"),
                stop_loss_triggered=False,
                calculation_time=datetime.utcnow()
            )
        ]
        
        mock_pl_service.calculate_all_positions_pl = AsyncMock(return_value=mock_pl_data)
        
        # Make request
        response = client_with_mocks.post("/api/v1/positions/pl/calculate")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response
        assert data["success"] is True
        assert data["positions_updated"] == 2
        assert "calculation_time_ms" in data
        assert "timestamp" in data
        
        # Verify service was called
        mock_pl_service.calculate_all_positions_pl.assert_called_once()
    
    async def test_calculate_pl_error(self, client_with_mocks, mock_pl_service):
        """Test calculate endpoint when calculation fails."""
        # Mock service to raise exception
        mock_pl_service.calculate_all_positions_pl = AsyncMock(
            side_effect=Exception("Market data unavailable")
        )
        
        response = client_with_mocks.post("/api/v1/positions/pl/calculate")
        
        assert response.status_code == 503
        assert "Market data unavailable" in response.json()["detail"]
    
    def test_get_current_pl_with_spy_price(self, client, sample_positions):
        """Test current P/L endpoint includes SPY price."""
        # This would need to mock the market service to provide SPY price
        response = client.get("/api/v1/positions/pl/current")
        
        assert response.status_code == 200
        data = response.json()
        
        # SPY price should be included
        assert "spy_price" in data
        # In real implementation, this would come from market service
    
    def test_position_pl_response_format(self, client, sample_positions):
        """Test that position P/L response matches expected format."""
        response = client.get("/api/v1/positions/pl/current")
        
        assert response.status_code == 200
        position = response.json()["positions"][0]
        
        # Verify all required fields are present
        required_fields = [
            "id", "symbol", "long_strike", "short_strike", "quantity",
            "entry_value", "current_value", "unrealized_pl",
            "unrealized_pl_percent", "risk_percent", "stop_loss_alert",
            "last_update"
        ]
        
        for field in required_fields:
            assert field in position
    
    def test_pl_history_ordering(self, client, sample_snapshots):
        """Test that P/L history is ordered by timestamp descending."""
        response = client.get("/api/v1/positions/1/pl/history")
        
        assert response.status_code == 200
        history = response.json()["history"]
        
        # Verify ordering - most recent first
        for i in range(1, len(history)):
            prev_time = datetime.fromisoformat(history[i-1]["timestamp"].replace("Z", "+00:00"))
            curr_time = datetime.fromisoformat(history[i]["timestamp"].replace("Z", "+00:00"))
            assert prev_time > curr_time