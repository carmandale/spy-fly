# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-29-trade-execution-checklist-#20/spec.md

> Created: 2025-07-29
> Version: 1.0.0

## Endpoints

### GET /api/execution/validate/{recommendation_id}

**Purpose:** Validate a spread recommendation for execution readiness
**Parameters:** 
- `recommendation_id` (path): UUID of the spread recommendation to validate
**Response:** JSON object with validation results and any blocking issues
**Errors:** 404 if recommendation not found, 422 if validation fails

```json
{
  "is_valid": true,
  "recommendation_id": "123e4567-e89b-12d3-a456-426614174000",
  "validation_results": {
    "position_sizing": {
      "valid": true,
      "buying_power_used": 0.045,
      "max_allowed": 0.05,
      "message": "Position size within limits"
    },
    "risk_reward": {
      "valid": true,
      "ratio": 1.2,
      "min_required": 1.0,
      "message": "Risk/reward ratio acceptable"
    },
    "market_conditions": {
      "valid": true,
      "market_open": true,
      "last_update": "2025-07-29T14:30:00Z",
      "message": "Market open and data current"
    },
    "spread_structure": {
      "valid": true,
      "long_strike": 550.0,
      "short_strike": 551.0,
      "expiration": "2025-07-29",
      "message": "Valid bull call spread structure"
    }
  },
  "warnings": [],
  "errors": []
}
```

### POST /api/execution/format-order

**Purpose:** Generate formatted order ticket for broker entry
**Parameters:** Request body with recommendation ID and broker format preference
**Response:** Formatted order text optimized for clipboard copy
**Errors:** 400 if invalid parameters, 422 if recommendation fails validation

**Request Body:**
```json
{
  "recommendation_id": "123e4567-e89b-12d3-a456-426614174000",
  "broker_format": "interactive_brokers",
  "account_size": 10000.00,
  "custom_quantity": null
}
```

**Response:**
```json
{
  "formatted_order": "BUY +1 SPY 29JUL25 550 CALL\nSELL -1 SPY 29JUL25 551 CALL\n@ NET DEBIT 0.65 LMT\nDAY ORDER",
  "broker_format": "interactive_brokers",
  "order_details": {
    "strategy": "Bull Call Spread",
    "symbol": "SPY",
    "expiration": "29JUL25",
    "long_strike": 550.0,
    "short_strike": 551.0,
    "quantity": 1,
    "net_debit": 0.65,
    "max_risk": 65.00,
    "max_profit": 35.00,
    "break_even": 550.65
  },
  "execution_notes": [
    "Verify SPY is trading above 550.65 at entry",
    "Set stop loss at 20% of max risk ($13.00)",
    "Target profit at 50% of max gain ($17.50)"
  ]
}
```

### GET /api/execution/brokers

**Purpose:** List supported broker formats for order generation
**Parameters:** None
**Response:** Array of supported broker configurations
**Errors:** None (always returns available formats)

```json
{
  "brokers": [
    {
      "id": "interactive_brokers",
      "name": "Interactive Brokers",
      "description": "TWS and mobile app compatible format",
      "sample_format": "BUY +1 SPY CALL, SELL -1 SPY CALL @ NET DEBIT"
    },
    {
      "id": "td_ameritrade", 
      "name": "TD Ameritrade",
      "description": "Think or Swim platform format", 
      "sample_format": "SPY_072925C550/SPY_072925C551 +1/-1 NET 0.65"
    },
    {
      "id": "etrade",
      "name": "E*TRADE",
      "description": "Power E*TRADE and mobile format",
      "sample_format": "SPY Jul29'25 550/551 Call Spread BUY 1 @ 0.65"
    }
  ]
}
```

## Controllers

### ExecutionController
**Location:** `/app/api/execution/router.py`
**Responsibilities:**
- Handle HTTP requests for all execution-related endpoints
- Validate request parameters and format responses
- Integrate with execution services for business logic
- Provide comprehensive error handling with user-friendly messages

**Key Actions:**
- `validate_recommendation()`: Coordinate comprehensive validation checks
- `format_order_ticket()`: Generate broker-specific order formatting  
- `list_broker_formats()`: Return available broker format options

### ExecutionService
**Location:** `/app/api/execution/services.py`
**Responsibilities:**
- Core business logic for order validation and formatting
- Integration with existing position sizing and risk management services
- Template-based broker format generation
- Real-time market condition checks

**Key Methods:**
- `validate_spread_for_execution()`: Comprehensive spread validation
- `generate_order_ticket()`: Create formatted order text
- `check_market_conditions()`: Verify market is open and data is current
- `calculate_execution_metrics()`: Generate break-even, risk, and profit data

## Database Integration

**Tables Used:**
- `spread_recommendations`: Read recommendation details for validation and formatting
- `user_settings`: Read broker preferences and account size for position sizing
- `execution_log`: Write execution attempts and validation results for audit trail

**New Tables Required:**
```sql
CREATE TABLE execution_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL,
    broker_format TEXT NOT NULL,
    formatted_order TEXT NOT NULL,
    validation_passed BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recommendation_id) REFERENCES spread_recommendations (id)
);
```

## Error Handling

**Validation Errors (422):**
- Position size exceeds 5% buying power limit
- Risk/reward ratio below 1:1 minimum  
- Market closed or data stale
- Invalid spread structure

**Client Errors (400):**
- Invalid recommendation ID format
- Unsupported broker format
- Missing required parameters

**Server Errors (500):**
- Database connection failures
- External API unavailable (market data)
- Template rendering errors