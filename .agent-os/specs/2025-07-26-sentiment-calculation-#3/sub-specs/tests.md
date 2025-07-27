# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-26-sentiment-calculation-#3/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Test Coverage

### Unit Tests

**VIX Scoring (test_vix_scoring.py)**
- Score 20 when VIX < 16
- Score 10 when VIX between 16-20
- Score 0 when VIX > 20
- Handle missing VIX data gracefully
- Validate edge cases (exactly 16, exactly 20)

**Futures Scoring (test_futures_scoring.py)**
- Score 20 when futures > 0.1%
- Score 10 when futures 0-0.1%
- Score 0 when futures negative
- Calculate percentage change correctly
- Handle pre-market vs regular hours pricing

**Technical Indicators (test_technical_indicators.py)**
- RSI calculation matches expected values
- RSI scoring (10 when 30-70, 0 otherwise)
- 50-MA calculation with various data lengths
- MA scoring (10 when above, 0 when below)
- Bollinger band position calculation
- Bollinger scoring based on position
- Handle insufficient data for indicators

**Sentiment Aggregation (test_sentiment_calculator.py)**
- Sum all component scores correctly
- Apply weights if configured
- Decision logic (PROCEED when >= 60 and technicals bullish)
- Decision logic (SKIP when < 60 or technicals bearish)
- Handle partial data scenarios
- Cache key generation

### Integration Tests

**Sentiment Calculation Flow (test_sentiment_integration.py)**
- Full calculation with all market data available
- Calculation with missing VIX data
- Calculation with insufficient historical data
- Cache hit returns same result
- Force refresh bypasses cache
- Concurrent calculations don't duplicate API calls

**API Endpoints (test_sentiment_endpoints.py)**
- GET /api/v1/sentiment/calculate returns valid response
- Force refresh parameter works correctly
- Individual component endpoints return correct data
- Invalid component name returns 404
- History endpoint respects days parameter
- Schedule endpoint creates valid schedule

### Feature Tests

**Morning Scan Workflow**
- Schedule triggers at 9:45 AM ET on weekdays
- Calculation completes within 10 seconds
- Results are cached for subsequent requests
- Email notification sent with results (if configured)

**Decision Accuracy**
- PROCEED decisions have score >= 60
- SKIP decisions have score < 60 or bearish technicals
- Technical status reflects actual indicator values
- Historical decisions are stored correctly

### Mocking Requirements

- **Market Data Service:** Mock all market data calls
- **Time:** Mock current time for schedule testing
- **VIX Data:** Mock various VIX levels for scoring tests
- **Historical Prices:** Mock 50+ days of price data for technical indicators
- **News Sentiment:** Mock as neutral for now

## Test Data

### Mock Market Data

**SPY Historical Prices (50 days):**
```python
# Generate trending up market
prices = pd.Series([
    560.0 + i * 0.3 + random.uniform(-2, 2) 
    for i in range(50)
])
```

**VIX Levels:**
```python
test_vix_levels = [
    (12.5, 20),   # Low VIX
    (18.0, 10),   # Medium VIX
    (25.0, 0),    # High VIX
    (16.0, 10),   # Edge case
    (20.0, 0),    # Edge case
]
```

**Futures Data:**
```python
test_futures = [
    {"previous_close": 5670.0, "current": 5680.0, "expected_score": 20},  # +0.18%
    {"previous_close": 5670.0, "current": 5674.0, "expected_score": 10},  # +0.07%
    {"previous_close": 5670.0, "current": 5665.0, "expected_score": 0},   # -0.09%
]
```

## Test Scenarios

### Bullish Market Scenario
```python
{
    "vix": 14.5,
    "futures_change": 0.25,
    "rsi": 55,
    "price": 568.0,
    "ma50": 562.0,
    "bollinger_position": 0.6,
    "expected_score": 80,
    "expected_decision": "PROCEED"
}
```

### Bearish Market Scenario
```python
{
    "vix": 22.5,
    "futures_change": -0.5,
    "rsi": 75,
    "price": 558.0,
    "ma50": 565.0,
    "bollinger_position": 0.9,
    "expected_score": 15,
    "expected_decision": "SKIP"
}
```

### Edge Case Scenario
```python
{
    "vix": 16.0,
    "futures_change": 0.1,
    "rsi": 70,
    "price": 565.0,
    "ma50": 565.0,
    "bollinger_position": 0.5,
    "expected_score": 50,
    "expected_decision": "SKIP"  # Below threshold
}
```

## Performance Requirements

- Sentiment calculation completes in < 2 seconds (with cached market data)
- API endpoint response time < 200ms (cached)
- Technical indicator calculations < 100ms for 50 days of data
- Can handle 100 concurrent requests

## Coverage Requirements

- Minimum 95% code coverage for sentiment calculator
- All scoring rules must have tests
- All edge cases documented and tested
- Integration tests for complete workflow
- Mock external dependencies properly