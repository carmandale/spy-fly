# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-27-polygon-api-integration-#5/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Technical Requirements

- **API Client Implementation:** FastAPI-compatible async HTTP client using httpx with connection pooling and timeout configuration
- **Authentication Management:** Secure API key storage using python-dotenv with validation on startup
- **Data Models:** Pydantic v2 models for all API responses ensuring type safety and validation
- **Caching Strategy:** SQLite-based cache with TTL (time-to-live) expiration for different data types
- **Rate Limiting:** Token bucket algorithm implementation respecting Polygon.io free tier limits (5 req/min)
- **Error Handling:** Custom exception hierarchy with specific handling for network, authentication, and rate limit errors
- **Logging Integration:** Structured logging using Python logging module with request/response tracking
- **Configuration Management:** Environment-based configuration with fallback defaults for development

## Approach Options

**Option A:** Direct REST API Integration with Manual Rate Limiting
- Pros: Simple implementation, full control over request timing, easy to debug
- Cons: More complex rate limiting logic, potential for blocking operations

**Option B:** Polygon Python SDK with Custom Wrapper (Selected)
- Pros: Official SDK handles authentication and rate limiting, built-in retry logic, active maintenance
- Cons: Additional dependency, less control over low-level implementation

**Option C:** Raw WebSocket Connection for Real-Time Data
- Pros: True real-time updates, lower latency for price changes
- Cons: Complex connection management, free tier limitations, overkill for Phase 1

**Rationale:** Option B provides the best balance of reliability and development speed. The official Polygon Python SDK handles authentication, rate limiting, and connection management while allowing us to add custom caching and error handling layers.

## External Dependencies

- **polygon-api-client** (>=1.12.0) - Official Polygon.io Python SDK for market data access
- **Justification:** Official SDK provides robust authentication, automatic rate limiting, and comprehensive API coverage with active maintenance

- **httpx** (>=0.24.0) - Modern async HTTP client for additional API calls if needed
- **Justification:** FastAPI-compatible async client with connection pooling and timeout support

- **aiofiles** (>=23.1.0) - Async file operations for cache management
- **Justification:** Non-blocking file I/O for SQLite cache operations in async context

- **tenacity** (>=8.2.0) - Retry logic with exponential backoff
- **Justification:** Robust retry mechanisms for handling temporary API failures

## Implementation Architecture

### API Client Module (`app/services/polygon_client.py`)

```python
class PolygonDataService:
    def __init__(self, api_key: str, cache_manager: CacheManager)
    async def get_spy_quote(self) -> SPYQuote
    async def get_option_chain(self, expiration_date: str) -> List[OptionContract]
    async def get_historical_data(self, days: int = 30) -> List[HistoricalPrice]
    async def health_check(self) -> bool
```

### Data Models (`app/models/market_data.py`)

```python
class SPYQuote(BaseModel):
    symbol: str
    price: Decimal
    bid: Decimal
    ask: Decimal
    volume: int
    timestamp: datetime

class OptionContract(BaseModel):
    symbol: str
    strike: Decimal
    option_type: Literal["call", "put"]
    expiration: date
    bid: Decimal
    ask: Decimal
    last_price: Decimal
    volume: int
    open_interest: int
```

### Cache Management (`app/services/cache_manager.py`)

```python
class CacheManager:
    def __init__(self, db_path: str)
    async def get_cached_data(self, key: str, max_age: timedelta) -> Optional[Any]
    async def set_cached_data(self, key: str, data: Any, ttl: timedelta) -> None
    async def cleanup_expired(self) -> None
```

### Rate Limiting (`app/services/rate_limiter.py`)

```python
class TokenBucketRateLimiter:
    def __init__(self, requests_per_minute: int = 5)
    async def acquire(self) -> None
    def get_wait_time(self) -> float
```

## API Endpoints Integration

### Stock Quote Endpoint
- **Polygon Endpoint:** `/v2/aggs/ticker/SPY/prev`
- **Update Frequency:** Every 15 seconds during market hours
- **Cache TTL:** 15 seconds
- **Error Handling:** Fallback to last known price with staleness warning

### Option Chain Endpoint
- **Polygon Endpoint:** `/v3/reference/options/contracts`
- **Filters:** SPY, 0-DTE expiration, active contracts only
- **Update Frequency:** Every 5 minutes during market hours
- **Cache TTL:** 5 minutes
- **Error Handling:** Use cached data up to 15 minutes old

### Historical Data Endpoint
- **Polygon Endpoint:** `/v2/aggs/ticker/SPY/range/1/day/{start}/{end}`
- **Lookback Period:** 30 calendar days
- **Update Frequency:** Once daily at 4:30 PM ET
- **Cache TTL:** 24 hours
- **Error Handling:** Graceful degradation with partial data

## Configuration Schema

```python
class PolygonConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.polygon.io"
    timeout_seconds: int = 30
    max_retries: int = 3
    requests_per_minute: int = 5
    cache_ttl_quotes: int = 15  # seconds
    cache_ttl_options: int = 300  # seconds
    cache_ttl_historical: int = 86400  # 24 hours
```