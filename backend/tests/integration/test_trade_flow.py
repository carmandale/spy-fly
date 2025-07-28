"""Integration test for complete trade flow."""
import pytest
from datetime import datetime, date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.trading import Trade, TradeSpread


def test_complete_trade_flow(client: TestClient, db: Session):
    """Test the complete flow of creating, listing, and updating a trade."""
    
    # 1. Create a new trade
    trade_data = {
        "trade_date": "2025-01-28",
        "trade_type": "paper",
        "status": "entered",
        "entry_time": "2025-01-28T10:30:00",
        "contracts": 5,
        "max_risk": 500.00,
        "max_reward": 500.00,
        "notes": "Integration test trade",
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
    created_trade = response.json()
    trade_id = created_trade["id"]
    
    # 2. Get the created trade
    response = client.get(f"/api/v1/trades/{trade_id}")
    assert response.status_code == 200
    fetched_trade = response.json()
    assert fetched_trade["id"] == trade_id
    assert fetched_trade["notes"] == "Integration test trade"
    
    # 3. List trades to verify it appears
    response = client.get("/api/v1/trades")
    assert response.status_code == 200
    trade_list = response.json()
    assert any(t["id"] == trade_id for t in trade_list["items"])
    
    # 4. Calculate P/L for exit
    pnl_data = {
        "exit_price": 573.50,
        "commission_per_contract": 0.65
    }
    response = client.post(f"/api/v1/trades/{trade_id}/calculate-pnl", json=pnl_data)
    assert response.status_code == 200
    pnl_result = response.json()
    
    # Expected calculations:
    # Exit value: 573.50 - 570 = 3.50 per share
    # Gross P/L: (3.50 - 1.00) * 5 * 100 = $1250
    # Commissions: 0.65 * 5 * 2 = $6.50
    # Net P/L: $1250 - $6.50 = $1243.50
    assert float(pnl_result["gross_pnl"]) == 1250.00
    assert float(pnl_result["commissions"]) == 6.50
    assert float(pnl_result["net_pnl"]) == 1243.50
    
    # 5. Update trade with exit details
    update_data = {
        "status": "exited",
        "exit_time": "2025-01-28T15:30:00",
        "exit_reason": "profit_target",
        "exit_price": 573.50,
        "gross_pnl": pnl_result["gross_pnl"],
        "commissions": pnl_result["commissions"],
        "net_pnl": pnl_result["net_pnl"],
        "pnl_percentage": pnl_result["pnl_percentage"]
    }
    
    response = client.patch(f"/api/v1/trades/{trade_id}", json=update_data)
    assert response.status_code == 200
    updated_trade = response.json()
    assert updated_trade["status"] == "exited"
    assert float(updated_trade["net_pnl"]) == 1243.50
    
    # 6. Filter trades by status
    response = client.get("/api/v1/trades?status=exited")
    assert response.status_code == 200
    exited_trades = response.json()
    assert any(t["id"] == trade_id for t in exited_trades["items"])
    
    # 7. Clean up - delete the trade
    response = client.delete(f"/api/v1/trades/{trade_id}")
    assert response.status_code == 204
    
    # Verify deletion
    response = client.get(f"/api/v1/trades/{trade_id}")
    assert response.status_code == 404