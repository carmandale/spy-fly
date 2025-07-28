"""Unit tests for trade endpoints."""
import pytest
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.trading import Trade, TradeSpread
from app.models.trade_schemas import TradeCreate, TradeUpdate, TradeResponse


class TestTradeEndpoints:
    """Test suite for trade CRUD operations."""
    
    def test_create_trade_success(self, client: TestClient, db: Session):
        """Test successful trade creation."""
        trade_data = {
            "trade_date": "2025-01-28",
            "trade_type": "paper",
            "status": "entered",
            "entry_time": "2025-01-28T10:30:00",
            "contracts": 5,
            "max_risk": 500.00,
            "max_reward": 500.00,
            "notes": "Test trade entry",
            "spread": {
                "spread_type": "bull_call_spread",
                "expiration_date": "2025-01-28",
                "long_strike": 570.00,
                "short_strike": 575.00,
                "long_premium": 2.50,
                "short_premium": 1.50,
                "net_debit": 1.00,
                "max_profit": 400.00,
                "max_loss": 100.00,
                "breakeven": 571.00,
                "risk_reward_ratio": 4.00
            }
        }
        
        response = client.post("/api/v1/trades", json=trade_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["id"] is not None
        assert data["trade_date"] == trade_data["trade_date"]
        assert data["status"] == "entered"
        assert data["contracts"] == 5
        assert float(data["spread"]["long_strike"]) == 570.00
        assert float(data["spread"]["short_strike"]) == 575.00
    
    def test_create_trade_invalid_data(self, client: TestClient):
        """Test trade creation with invalid data."""
        # Missing required fields
        trade_data = {
            "trade_date": "2025-01-28",
            "status": "entered"
        }
        
        response = client.post("/api/v1/trades", json=trade_data)
        assert response.status_code == 422
    
    def test_get_trade_by_id(self, client: TestClient, db: Session):
        """Test fetching a specific trade by ID."""
        # Create a test trade
        trade = Trade(
            trade_date=date(2025, 1, 28),
            trade_type="paper",
            status="entered",
            entry_time=datetime.now(),
            contracts=5,
            max_risk=Decimal("500.00"),
            notes="Test trade"
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        
        response = client.get(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == trade.id
        assert data["contracts"] == 5
        assert data["notes"] == "Test trade"
    
    def test_get_trade_not_found(self, client: TestClient):
        """Test fetching non-existent trade."""
        response = client.get("/api/v1/trades/99999")
        assert response.status_code == 404
    
    def test_list_trades(self, client: TestClient, db: Session):
        """Test listing trades with filters."""
        # Create test trades
        trades = [
            Trade(
                trade_date=date(2025, 1, 27),
                trade_type="paper",
                status="exited",
                net_pnl=Decimal("150.00")
            ),
            Trade(
                trade_date=date(2025, 1, 28),
                trade_type="paper", 
                status="entered",
                net_pnl=None
            ),
            Trade(
                trade_date=date(2025, 1, 28),
                trade_type="real",
                status="exited",
                net_pnl=Decimal("-50.00")
            )
        ]
        db.add_all(trades)
        db.commit()
        
        # Test listing all trades
        response = client.get("/api/v1/trades")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 3
        
        # Test filtering by date
        response = client.get("/api/v1/trades?start_date=2025-01-28")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        
        # Test filtering by status
        response = client.get("/api/v1/trades?status=exited")
        assert response.status_code == 200
        data = response.json()
        assert all(trade["status"] == "exited" for trade in data["items"])
    
    def test_update_trade(self, client: TestClient, db: Session):
        """Test updating a trade."""
        # Create a test trade
        trade = Trade(
            trade_date=date(2025, 1, 28),
            trade_type="paper",
            status="entered",
            entry_time=datetime.now(),
            contracts=5
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        
        # Update the trade
        update_data = {
            "status": "exited",
            "exit_time": "2025-01-28T15:30:00",
            "exit_reason": "profit_target",
            "gross_pnl": 400.00,
            "net_pnl": 395.00,
            "pnl_percentage": 79.00
        }
        
        response = client.patch(f"/api/v1/trades/{trade.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "exited"
        assert data["exit_reason"] == "profit_target"
        assert float(data["net_pnl"]) == 395.00
    
    def test_calculate_pnl(self, client: TestClient, db: Session):
        """Test P/L calculation for a trade."""
        # Create a test trade with spread
        trade = Trade(
            trade_date=date(2025, 1, 28),
            trade_type="paper",
            status="entered",
            contracts=5,
            max_risk=Decimal("500.00")
        )
        db.add(trade)
        db.commit()
        
        spread = TradeSpread(
            trade_id=trade.id,
            spread_type="bull_call_spread",
            expiration_date=date(2025, 1, 28),
            long_strike=Decimal("570.00"),
            short_strike=Decimal("575.00"),
            net_debit=Decimal("1.00"),
            max_profit=Decimal("400.00"),
            max_loss=Decimal("100.00"),
            breakeven=Decimal("571.00"),
            risk_reward_ratio=Decimal("4.00"),
            long_premium=Decimal("2.50"),
            short_premium=Decimal("1.50")
        )
        db.add(spread)
        db.commit()
        
        # Calculate P/L with exit price
        pnl_data = {
            "exit_price": 573.50
        }
        
        response = client.post(f"/api/v1/trades/{trade.id}/calculate-pnl", json=pnl_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "gross_pnl" in data
        assert "net_pnl" in data
        assert "pnl_percentage" in data
    
    def test_delete_trade(self, client: TestClient, db: Session):
        """Test deleting a trade."""
        # Create a test trade
        trade = Trade(
            trade_date=date(2025, 1, 28),
            trade_type="paper",
            status="skipped"
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        
        response = client.delete(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 204
        
        # Verify trade is deleted
        response = client.get(f"/api/v1/trades/{trade.id}")
        assert response.status_code == 404