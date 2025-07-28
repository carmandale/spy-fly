# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Endpoints

### GET /api/v1/spreads/recommendations

**Purpose:** Get top-ranked SPY 0-DTE bull-call-spread recommendations based on current market conditions
**Parameters:** 
- `account_size` (optional, float): Account buying power for position sizing, defaults to $10,000
- `max_risk_percent` (optional, float): Maximum risk percentage, defaults to 5.0, range 1.0-10.0
- `min_risk_reward_ratio` (optional, float): Minimum risk/reward ratio, defaults to 1.0
- `limit` (optional, int): Maximum number of recommendations, defaults to 5, max 10

**Response:** 
```json
{
  "recommendations": [
    {
      "id": "spy-bull-call-spread-1",
      "long_strike": 580.0,
      "short_strike": 585.0,
      "long_premium": 2.45,
      "short_premium": 0.95,
      "net_debit": 1.50,
      "max_profit": 3.50,
      "max_loss": 1.50,
      "risk_reward_ratio": 2.33,
      "probability_of_profit": 0.65,
      "expected_value": 0.775,
      "breakeven_price": 581.50,
      "recommended_contracts": 3,
      "total_risk": 450.0,
      "sentiment_weight": 0.75,
      "order_ticket": "BUY 3 SPY 580/585 Bull Call Spread for 1.50 debit",
      "expiration_date": "2025-07-28",
      "time_to_expiry_minutes": 390
    }
  ],
  "market_context": {
    "spy_price": 578.25,
    "vix_level": 14.2,
    "sentiment_score": 0.75,
    "options_chain_timestamp": "2025-07-28T09:45:00Z",
    "total_spreads_analyzed": 156
  },
  "metadata": {
    "generated_at": "2025-07-28T09:45:15Z",
    "processing_time_ms": 1250,
    "account_size_used": 10000.0,
    "filters_applied": {
      "min_risk_reward_ratio": 1.0,
      "max_risk_percent": 5.0,
      "expiration_date": "2025-07-28"
    }
  }
}
```

**Errors:** 
- 400: Invalid parameters or market closed
- 429: Rate limit exceeded for options data API
- 503: Options data temporarily unavailable

### POST /api/v1/spreads/analyze

**Purpose:** Analyze a specific spread combination provided by the user
**Parameters:** JSON body with spread details
```json
{
  "long_strike": 580.0,
  "short_strike": 585.0,
  "account_size": 10000.0
}
```

**Response:** 
```json
{
  "analysis": {
    "long_premium": 2.45,
    "short_premium": 0.95,
    "net_debit": 1.50,
    "max_profit": 3.50,
    "max_loss": 1.50,
    "risk_reward_ratio": 2.33,
    "probability_of_profit": 0.65,
    "expected_value": 0.775,
    "breakeven_price": 581.50,
    "recommended_contracts": 3,
    "total_risk": 450.0,
    "meets_criteria": true,
    "criteria_check": {
      "min_risk_reward": true,
      "max_buying_power": true,
      "liquidity_adequate": true
    }
  }
}
```

**Errors:**
- 400: Invalid strike prices or missing required fields
- 404: No options data available for specified strikes

### GET /api/v1/spreads/options-chain

**Purpose:** Get current SPY 0-DTE options chain data used for spread analysis
**Parameters:** None

**Response:**
```json
{
  "options_chain": [
    {
      "strike": 580.0,
      "call_bid": 2.40,
      "call_ask": 2.50,
      "call_last": 2.45,
      "call_volume": 150,
      "call_open_interest": 1200,
      "delta": 0.52,
      "expiration_date": "2025-07-28"
    }
  ],
  "metadata": {
    "underlying_price": 578.25,
    "expiration_date": "2025-07-28",
    "time_to_expiry_minutes": 390,
    "total_strikes": 45,
    "data_timestamp": "2025-07-28T09:45:00Z"
  }
}
```

## Controllers

### SpreadRecommendationController

**Actions:**
- `get_recommendations()`: Orchestrate full spread analysis pipeline
- `analyze_specific_spread()`: Validate and analyze user-provided spread
- `get_options_chain()`: Return cached or fresh options data

**Business Logic:**
- Coordinate between options chain processor, spread generator, and ranking engine
- Apply user-specified filters and risk parameters
- Handle caching of options data to minimize API calls
- Validate user inputs and enforce business rules

**Error Handling:**
- Graceful degradation when options data is stale or incomplete
- Rate limiting protection for external API calls
- Input validation with detailed error messages
- Fallback responses when market is closed

### Risk Management Integration

**Position Sizing Logic:**
- Calculate maximum contracts based on account size and risk percentage
- Enforce hard limits preventing risk parameter violations
- Validate spread meets minimum criteria before including in results

**Market Data Validation:**
- Ensure options chain data is current (< 5 minutes old during market hours)
- Verify bid/ask spreads are reasonable (< 10% wide)
- Handle missing or invalid option prices gracefully