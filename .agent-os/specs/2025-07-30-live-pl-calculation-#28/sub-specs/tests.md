# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-30-live-pl-calculation-#28/spec.md

> Created: 2025-07-30
> Version: 1.0.0

## Test Coverage

### Unit Tests

**PLCalculationService**
- Test P/L calculation with positive unrealized gain
- Test P/L calculation with negative unrealized loss
- Test percentage calculation with zero max risk (edge case)
- Test stop-loss alert triggering at -20% threshold
- Test alert clearing when position improves to -15%
- Test handling of missing bid/ask prices
- Test calculation performance (< 100ms per position)

**Position Model Extensions**
- Test new column defaults and constraints
- Test relationship with position_snapshots
- Test latest P/L value updates

**PositionSnapshot Model**
- Test snapshot creation with all fields
- Test foreign key relationship to positions
- Test index performance for time-based queries

### Integration Tests

**P/L API Endpoints**
- Test GET /positions/pl/current returns all open positions
- Test GET /positions/{id}/pl/history with various time ranges
- Test POST /positions/pl/calculate triggers recalculation
- Test 404 response for non-existent position
- Test 400 response for invalid parameters

**WebSocket P/L Updates**
- Test pl_update message broadcast on price change
- Test throttling prevents message spam
- Test multiple client subscriptions receive updates
- Test disconnection handling during updates

**Scheduled P/L Snapshots**
- Test snapshot job runs every 15 minutes
- Test skips execution outside market hours
- Test handles database errors gracefully
- Test creates snapshots for all open positions

### Feature Tests

**Real-Time P/L Dashboard Flow**
- User opens position → P/L shows as $0
- SPY price increases → P/L updates to positive
- 15 minutes pass → Snapshot stored in database
- SPY price decreases → P/L updates to negative
- P/L reaches -20% → Stop-loss alert appears
- User views P/L history → Chart displays snapshots

**Stop-Loss Alert Workflow**
- Position loses 15% → No alert
- Position loses 20% → Alert triggered
- Position recovers to -18% → Alert remains
- Position recovers to -14% → Alert cleared
- Position loses 20% again → New alert triggered

### Mocking Requirements

**Market Data Service**
- Mock option chain responses with bid/ask spreads
- Mock SPY quote updates via WebSocket
- Mock connection failures for error testing

**Database Connections**
- Mock position queries for unit tests
- Mock snapshot inserts for performance tests
- Mock transaction rollbacks for error cases

**WebSocket Manager**
- Mock client connections for broadcast tests
- Mock message sending for throttling tests

## Performance Tests

### Load Testing
- Calculate P/L for 100 positions simultaneously
- Verify < 10 second total calculation time
- Test database connection pooling under load

### Real-Time Performance
- Measure WebSocket message latency
- Verify < 2 second update time to UI
- Test throttling with rapid price changes

## Test Data Requirements

### Sample Positions
```python
# Bull call spread examples
positions = [
    {
        "long_strike": 450,
        "short_strike": 455,
        "quantity": 5,
        "entry_value": -250.00,
        "max_risk": 500.00
    },
    {
        "long_strike": 448,
        "short_strike": 452,
        "quantity": 10,
        "entry_value": -400.00,
        "max_risk": 400.00
    }
]
```

### Price Scenarios
- SPY at 451: Both positions profitable
- SPY at 449: Mixed P/L results
- SPY at 446: Both positions at max loss
- Rapid changes: 450 → 452 → 449 in 1 minute