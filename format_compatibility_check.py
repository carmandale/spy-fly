#!/usr/bin/env python3
"""
Format Compatibility Check

Verify that the TradeFormatter output format matches what the frontend expects.
"""

from datetime import datetime
from backend.app.models.spread import SpreadRecommendation
from backend.app.services.trade_formatter import TradeFormatter

def create_sample_recommendation():
    """Create a sample recommendation for testing."""
    return SpreadRecommendation(
        long_strike=470.0,
        short_strike=475.0,
        long_premium=3.0,
        short_premium=1.5,
        net_debit=1.5,
        max_risk=150.0,
        max_profit=350.0,
        risk_reward_ratio=2.33,
        probability_of_profit=0.65,
        breakeven_price=471.5,
        long_bid=2.95,
        long_ask=3.05,
        short_bid=1.45,
        short_ask=1.55,
        long_volume=500,
        short_volume=300,
        expected_value=102.5,
        sentiment_score=0.35,
        ranking_score=0.75,
        timestamp=datetime.now(),
        contracts_to_trade=3,
        total_cost=450.0,
        buying_power_used_pct=0.045,
    )

def check_format_compatibility():
    """Check if TradeFormatter output can be mapped to frontend interface."""
    
    print("🔍 Checking format compatibility between backend and frontend...")
    print("=" * 60)
    
    # Create sample data
    formatter = TradeFormatter(symbol="SPY")
    rec = create_sample_recommendation()
    
    # Get formatted output
    formatted_list = formatter.format_recommendations_list([rec], max_count=1)
    
    if not formatted_list["recommendations"]:
        print("❌ No recommendations in formatted output")
        return False
    
    backend_rec = formatted_list["recommendations"][0]
    
    print("Frontend SpreadRecommendation interface expects:")
    frontend_interface = {
        "id": "string",
        "longStrike": "number", 
        "shortStrike": "number",
        "debit": "number",
        "maxProfit": "number", 
        "maxLoss": "number",
        "breakeven": "number",
        "probability": "number",
        "quantity": "number",
        "expiration": "string"
    }
    
    for field, expected_type in frontend_interface.items():
        print(f"  {field}: {expected_type}")
    
    print("\nBackend TradeFormatter produces:")
    backend_fields = {
        "id": backend_rec.get("id"),
        "description": backend_rec.get("description"),
        "summary": backend_rec.get("summary"),
        "details": backend_rec.get("details"),
        "market_data": backend_rec.get("market_data"),
        "timestamp": backend_rec.get("timestamp")
    }
    
    for field, value in backend_fields.items():
        print(f"  {field}: {type(value).__name__} = {value}")
    
    print("\n🔄 Mapping Analysis:")
    print("-" * 40)
    
    # Check if we can map backend fields to frontend interface
    mapping_success = True
    
    # Map backend details to frontend fields
    details = backend_rec.get("details", {})
    mappings = [
        ("id", backend_rec.get("id"), "✓"),
        ("longStrike", details.get("long_strike"), "✓" if details.get("long_strike") else "❌"),
        ("shortStrike", details.get("short_strike"), "✓" if details.get("short_strike") else "❌"), 
        ("debit", details.get("net_debit"), "✓" if details.get("net_debit") else "❌"),
        ("maxProfit", details.get("max_profit"), "✓" if details.get("max_profit") else "❌"),
        ("maxLoss", details.get("max_risk"), "✓" if details.get("max_risk") else "❌"),
        ("breakeven", details.get("breakeven_price"), "✓" if details.get("breakeven_price") else "❌"),
        ("probability", details.get("probability_of_profit"), "✓" if details.get("probability_of_profit") else "❌"),
        ("quantity", details.get("contracts_to_trade"), "✓" if details.get("contracts_to_trade") else "❌"),
        ("expiration", "0DTE", "✓ (hardcoded)")
    ]
    
    for frontend_field, backend_value, status in mappings:
        print(f"{status} {frontend_field}: {backend_value}")
        if status == "❌":
            mapping_success = False
    
    print(f"\n{'✅' if mapping_success else '❌'} Format Compatibility: {'PASS' if mapping_success else 'FAIL'}")
    
    if mapping_success:
        print("\n🎯 Recommended adapter function:")
        print("""
def adapt_for_frontend(backend_recommendations):
    frontend_recs = []
    for i, rec in enumerate(backend_recommendations.get("recommendations", [])):
        details = rec.get("details", {})
        adapted = {
            "id": str(rec.get("id", i + 1)),
            "longStrike": details.get("long_strike", 0),
            "shortStrike": details.get("short_strike", 0), 
            "debit": details.get("net_debit", 0),
            "maxProfit": details.get("max_profit", 0),
            "maxLoss": details.get("max_risk", 0),
            "breakeven": details.get("breakeven_price", 0),
            "probability": details.get("probability_of_profit", 0) * 100,  # Convert to percentage
            "quantity": details.get("contracts_to_trade", 0),
            "expiration": "0DTE"
        }
        frontend_recs.append(adapted)
    return frontend_recs
""")
    
    return mapping_success

if __name__ == "__main__":
    success = check_format_compatibility()
    exit(0 if success else 1)