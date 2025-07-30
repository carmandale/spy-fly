# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-30-live-pl-calculation-#28/spec.md

> Created: 2025-07-30
> Version: 1.0.0

## Endpoints

### GET /api/v1/positions/pl/current

**Purpose:** Get current P/L for all open positions
**Parameters:** None
**Response:**
```json
{
  "positions": [
    {
      "id": 1,
      "symbol": "SPY",
      "long_strike": 450,
      "short_strike": 455,
      "quantity": 5,
      "entry_value": -250.00,
      "current_value": -200.00,
      "unrealized_pl": 50.00,
      "unrealized_pl_percent": 10.0,
      "risk_percent": -10.0,
      "stop_loss_alert": false,
      "last_update": "2025-07-30T10:45:00Z"
    }
  ],
  "total_unrealized_pl": 50.00,
  "spy_price": 451.25
}
```
**Errors:** 
- 500: Database connection error

### GET /api/v1/positions/{position_id}/pl/history

**Purpose:** Get P/L history for a specific position
**Parameters:** 
- position_id (path): Position ID
- hours (query, optional): Number of hours of history (default: 24, max: 168)
**Response:**
```json
{
  "position_id": 1,
  "history": [
    {
      "timestamp": "2025-07-30T09:45:00Z",
      "unrealized_pl": 25.00,
      "unrealized_pl_percent": 5.0,
      "spy_price": 450.75,
      "current_value": -225.00
    }
  ]
}
```
**Errors:**
- 404: Position not found
- 400: Invalid hours parameter

### POST /api/v1/positions/pl/calculate

**Purpose:** Trigger immediate P/L calculation for all positions
**Parameters:** None
**Response:**
```json
{
  "success": true,
  "positions_updated": 3,
  "calculation_time_ms": 45,
  "timestamp": "2025-07-30T10:47:00Z"
}
```
**Errors:**
- 503: Market data unavailable
- 500: Calculation error

### WebSocket Extension: /api/v1/ws/price-feed

**New Message Type:** pl_update
```json
{
  "type": "pl_update",
  "position_id": 1,
  "unrealized_pl": 50.00,
  "unrealized_pl_percent": 10.0,
  "current_value": -200.00,
  "risk_percent": -10.0,
  "stop_loss_alert": false,
  "timestamp": "2025-07-30T10:45:00Z"
}
```

## Controllers

### PLCalculationService

**calculate_position_pl(position_id: int)**
- Fetch current option prices
- Calculate spread value
- Update position record
- Broadcast via WebSocket if changed

**calculate_all_positions_pl()**
- Batch calculate all open positions
- Store snapshots in database
- Trigger stop-loss alerts if needed

**get_pl_history(position_id: int, hours: int)**
- Query position_snapshots table
- Format for charting
- Include SPY price correlation

## Integration Points

### WebSocket Manager
- Subscribe to SPY price updates
- Trigger P/L recalculation on price change
- Broadcast pl_update messages to connected clients

### Scheduler Service
- Add new job: calculate_pl_snapshot
- Schedule: Every 15 minutes during market hours
- Skip weekends and holidays

### Alert Service (Future)
- Monitor stop_loss_alert_active flag
- Send notifications when triggered
- Clear alerts when position improves