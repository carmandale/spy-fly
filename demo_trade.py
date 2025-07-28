#!/usr/bin/env python3
"""Demo script to show trade functionality."""
import requests
from datetime import datetime
from pprint import pprint

API_BASE_URL = "http://localhost:8003/api/v1"

def demo_trade_flow():
    """Demonstrate the trade input and history functionality."""
    
    print("=== SPY-FLY Trade Demo ===\n")
    
    # 1. Create a new trade
    print("1. Creating a new paper trade...")
    trade_data = {
        "trade_date": datetime.now().strftime("%Y-%m-%d"),
        "trade_type": "paper",
        "status": "entered",
        "entry_time": datetime.now().isoformat(),
        "contracts": 5,
        "max_risk": 500.00,
        "max_reward": 500.00,
        "notes": "Demo trade - testing the new functionality",
        "spread": {
            "spread_type": "bull_call_spread",
            "expiration_date": datetime.now().strftime("%Y-%m-%d"),
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
    
    response = requests.post(f"{API_BASE_URL}/trades", json=trade_data)
    if response.status_code == 201:
        trade = response.json()
        trade_id = trade["id"]
        print(f"✓ Trade created successfully! ID: {trade_id}")
        print(f"  - Spread: {trade['spread']['long_strike']}/{trade['spread']['short_strike']}C")
        print(f"  - Net Debit: ${trade['spread']['net_debit']}")
        print(f"  - Max Risk: ${trade['max_risk']}")
    else:
        print(f"✗ Failed to create trade: {response.text}")
        return
    
    print("\n2. Listing all trades...")
    response = requests.get(f"{API_BASE_URL}/trades")
    if response.status_code == 200:
        trades = response.json()
        print(f"✓ Found {trades['total']} trades")
        for t in trades['items'][:3]:  # Show first 3
            status = t['status'].upper()
            spread = f"{t['spread']['long_strike']}/{t['spread']['short_strike']}C" if t.get('spread') else "N/A"
            print(f"  - Trade #{t['id']}: {t['trade_date']} | {status} | {spread}")
    
    print("\n3. Calculating P/L for exit at $573.50...")
    pnl_data = {
        "exit_price": 573.50,
        "commission_per_contract": 0.65
    }
    response = requests.post(f"{API_BASE_URL}/trades/{trade_id}/calculate-pnl", json=pnl_data)
    if response.status_code == 200:
        pnl = response.json()
        print(f"✓ P/L Calculated:")
        print(f"  - Gross P/L: ${pnl['gross_pnl']}")
        print(f"  - Commissions: ${pnl['commissions']}")
        print(f"  - Net P/L: ${pnl['net_pnl']}")
        print(f"  - P/L %: {pnl['pnl_percentage']}%")
    
    print("\n4. Updating trade with exit details...")
    update_data = {
        "status": "exited",
        "exit_time": datetime.now().isoformat(),
        "exit_reason": "profit_target",
        "exit_price": 573.50,
        "gross_pnl": pnl['gross_pnl'],
        "commissions": pnl['commissions'],
        "net_pnl": pnl['net_pnl'],
        "pnl_percentage": pnl['pnl_percentage']
    }
    
    response = requests.patch(f"{API_BASE_URL}/trades/{trade_id}", json=update_data)
    if response.status_code == 200:
        print(f"✓ Trade updated successfully!")
        print(f"  - Status: EXITED")
        print(f"  - Net P/L: ${update_data['net_pnl']}")
    
    print("\n5. Filtering trades by status...")
    response = requests.get(f"{API_BASE_URL}/trades?status=exited")
    if response.status_code == 200:
        trades = response.json()
        print(f"✓ Found {trades['total']} exited trades")
    
    print("\n=== Demo Complete ===")
    print("\nYou can now:")
    print("- Visit http://localhost:3003 to see the dashboard")
    print("- Click 'Record Trade' to manually input trades")
    print("- View the trade history table at the bottom")
    print("- Filter trades by date and status")

if __name__ == "__main__":
    try:
        demo_trade_flow()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure the backend is running on port 8003.")
    except Exception as e:
        print(f"Error: {e}")