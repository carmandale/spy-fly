# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-26-polygon-api-integration-#2/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Test Coverage

### Unit Tests

**PolygonClient (test_polygon_client.py)**
- Constructor properly sets API key and base URL
- Sandbox mode uses correct endpoint
- Request headers include authentication
- HTTP errors are properly wrapped
- Retry logic works for transient failures
- Rate limit responses return appropriate errors

**MarketDataService (test_market_service.py)**
- Quote fetching returns properly formatted data
- Options chain filtering works correctly
- Historical data aggregation is accurate
- Cache hit returns cached data
- Cache miss calls Polygon client
- Service handles client errors gracefully

**Cache Layer (test_cache.py)**
- Items expire after TTL
- Cache key generation is consistent
- Cache size limits are respected
- Concurrent access is thread-safe

**Rate Limiter (test_rate_limiter.py)**
- Allows N requests per minute
- Blocks when limit exceeded
- Resets after time window
- Queue works for delayed requests

### Integration Tests

**API Endpoints (test_market_endpoints.py)**
- GET /api/v1/market/quote/SPY returns valid quote
- Invalid ticker returns 404
- Rate limit exceeded returns 429 with retry info
- Option chain endpoint filters by strike range
- Historical data respects date range limits
- Cache headers are set correctly

**Polygon API Integration (test_polygon_integration.py)**
- Real API calls work with sandbox credentials
- Response parsing handles all field types
- Network timeouts are handled gracefully
- Invalid API key returns proper error

### Feature Tests

**End-to-End Market Data Flow**
- Frontend requests quote → API → Polygon → Response displayed
- Multiple rapid requests trigger rate limiting
- Cached responses return faster than API calls
- Error states show user-friendly messages

### Mocking Requirements

- **Polygon.io API:** Mock all external API calls for unit tests
- **Network Responses:** Use httpx mock transport for controlled responses
- **Time:** Mock time.time() for cache expiration tests
- **Rate Limiter Clock:** Mock time for rate limit window tests

## Test Data

### Mock API Responses

**Quote Response:**
```json
{
  "status": "success",
  "results": {
    "T": "SPY",
    "c": 567.89,
    "h": 568.50,
    "l": 566.20,
    "o": 567.00,
    "v": 45678900,
    "vw": 567.45,
    "t": 1738234567890
  }
}
```

**Options Chain Response:**
```json
{
  "status": "success",
  "results": [
    {
      "details": {
        "contract_type": "call",
        "exercise_style": "american",
        "expiration_date": "2025-07-26",
        "strike_price": 565
      },
      "day": {
        "close": 3.28,
        "high": 3.45,
        "low": 3.10,
        "open": 3.20,
        "volume": 12500
      },
      "last_quote": {
        "ask": 3.30,
        "bid": 3.25,
        "last_updated": 1738234567890
      }
    }
  ]
}
```

## Test Configuration

### Environment Variables for Tests
```bash
POLYGON_API_KEY=test_api_key
POLYGON_USE_SANDBOX=true
POLYGON_RATE_LIMIT=5
TEST_MODE=true
```

### Pytest Fixtures

```python
@pytest.fixture
def mock_polygon_client():
    """Returns a mocked PolygonClient with preset responses"""

@pytest.fixture
def market_service():
    """Returns MarketDataService with mocked dependencies"""

@pytest.fixture
def test_cache():
    """Returns a fresh cache instance for each test"""
```

## Coverage Requirements

- Minimum 90% code coverage for all new code
- All API endpoints must have integration tests
- All error scenarios must be tested
- Performance tests for cache vs. API call speed
- Load tests for rate limiter behavior

## Performance Benchmarks

- Quote endpoint response time: < 100ms (cached), < 500ms (API call)
- Option chain response time: < 200ms (cached), < 1s (API call)
- Cache lookup time: < 1ms
- Rate limiter check: < 1ms