# Format Compatibility Analysis

## Frontend SpreadRecommendation Interface

From `Dashboard.tsx` and `RecommendedSpreadsPanel.tsx`, the frontend expects:

```typescript
interface SpreadRecommendation {
  id: string
  longStrike: number
  shortStrike: number
  debit: number
  maxProfit: number
  maxLoss: number
  breakeven: number
  probability: number  // As percentage (0-100)
  quantity: number
  expiration: string
}
```

## Backend TradeFormatter Output

From `TradeFormatter.format_recommendations_list()`, the backend produces:

```python
{
  "recommendations": [
    {
      "id": 1,  # number, not string
      "description": "SPY 470/475 Bull Call Spread",
      "summary": {
        "net_debit": 1.5,
        "probability": 0.65,  # As decimal (0-1), not percentage
        "risk_reward_ratio": 2.33,
        "contracts": 3,
        "total_cost": 450.0
      },
      "details": {
        "long_strike": 470.0,
        "short_strike": 475.0,
        "net_debit": 1.5,
        "max_profit": 350.0,
        "max_risk": 150.0,
        "breakeven_price": 471.5,
        "probability_of_profit": 0.65,  # As decimal
        "contracts_to_trade": 3,
        # ... other fields
      },
      "market_data": { ... },
      "timestamp": "2025-07-28T..."
    }
  ],
  "summary": { ... },
  "disclaimer": "..."
}
```

## Compatibility Issues ❌

1. **ID Type**: Backend uses `number`, frontend expects `string`
2. **Field Names**: Backend uses snake_case (`long_strike`), frontend expects camelCase (`longStrike`)
3. **Probability Format**: Backend uses decimal (0.65), frontend expects percentage (65)
4. **Field Mapping**: Frontend `debit` maps to backend `net_debit`
5. **Field Mapping**: Frontend `maxLoss` maps to backend `max_risk` 
6. **Missing Fields**: Backend doesn't have `expiration` field in the expected format

## Required API Adapter

An adapter function is needed in the API endpoint to transform backend format to frontend format:

```python
def adapt_recommendations_for_frontend(backend_recommendations):
    """Adapt backend TradeFormatter output to frontend SpreadRecommendation interface."""
    frontend_recs = []
    
    for rec in backend_recommendations.get("recommendations", []):
        details = rec.get("details", {})
        
        adapted = {
            "id": str(rec.get("id", 1)),  # Convert to string
            "longStrike": details.get("long_strike", 0),
            "shortStrike": details.get("short_strike", 0), 
            "debit": details.get("net_debit", 0),
            "maxProfit": details.get("max_profit", 0),
            "maxLoss": details.get("max_risk", 0),  # Note: max_risk -> maxLoss
            "breakeven": details.get("breakeven_price", 0),
            "probability": details.get("probability_of_profit", 0) * 100,  # Convert to percentage
            "quantity": details.get("contracts_to_trade", 0),
            "expiration": "0DTE"  # Hardcoded for 0-day-to-expiration
        }
        frontend_recs.append(adapted)
    
    return frontend_recs
```

## Recommendations ✅

1. **Create API Adapter**: Add the adapter function to the API endpoint that serves recommendations
2. **Update TradeFormatter**: Consider adding a `format_for_frontend()` method to TradeFormatter class
3. **Type Safety**: Ensure the adapter handles None values and type conversions properly
4. **Testing**: Add tests to verify the adapter produces the correct frontend format

## Status: NEEDS ADAPTER

The backend TradeFormatter produces comprehensive data but needs a lightweight adapter to match the frontend interface exactly. This is a common pattern in full-stack applications where the backend model is richer than the frontend needs.