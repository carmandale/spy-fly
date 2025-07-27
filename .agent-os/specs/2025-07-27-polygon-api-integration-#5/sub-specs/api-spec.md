# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-27-polygon-api-integration-#5/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Endpoints

### GET /api/v1/market-data/spy/quote

**Purpose:** Retrieve current SPY stock quote with bid/ask spread and volume
**Parameters:** None
**Response:** Current SPY quote data with cache metadata
**Errors:** 503 Service Unavailable if API and cache both fail

```json
{
  "symbol": "SPY",
  "price": 450.25,
  "bid": 450.23,
  "ask": 450.27,
  "volume": 1234567,
  "timestamp": "2025-07-27T15:30:00Z",
  "cached": false,
  "cache_age_seconds": 0
}
```

### GET /api/v1/market-data/spy/options

**Purpose:** Retrieve complete 0-DTE option chain for SPY
**Parameters:** 
- `expiration` (optional): ISO date format, defaults to next 0-DTE
- `min_volume` (optional): Filter contracts with minimum volume, default 10
**Response:** Array of option contracts sorted by strike price
**Errors:** 404 Not Found if no 0-DTE options available, 503 Service Unavailable on API failure

```json
{
  "underlying": "SPY",
  "expiration_date": "2025-07-27",
  "contracts": [
    {
      "symbol": "SPY241127C00450000",
      "strike": 450.00,
      "option_type": "call",
      "bid": 2.50,
      "ask": 2.55,
      "last_price": 2.52,
      "volume": 156,
      "open_interest": 1234,
      "timestamp": "2025-07-27T15:30:00Z"
    }
  ],
  "cached": false,
  "cache_age_seconds": 0,
  "total_contracts": 42
}
```

### GET /api/v1/market-data/spy/historical

**Purpose:** Retrieve historical price data for technical analysis
**Parameters:**
- `days` (optional): Number of days to retrieve, default 30, max 90
- `timeframe` (optional): 'daily', '1hour', '15min', default 'daily'
**Response:** Array of historical price bars
**Errors:** 400 Bad Request for invalid parameters, 503 Service Unavailable on API failure

```json
{
  "symbol": "SPY",
  "timeframe": "daily",
  "bars": [
    {
      "date": "2025-07-27",
      "open": 449.50,
      "high": 451.25,
      "low": 448.75,
      "close": 450.25,
      "volume": 12345678,
      "vwap": 450.12
    }
  ],
  "cached": true,
  "cache_age_seconds": 3600,
  "total_bars": 30
}
```

### GET /api/v1/market-data/health

**Purpose:** Check Polygon.io API connectivity and rate limit status
**Parameters:** None
**Response:** API health status and rate limiting information
**Errors:** 503 Service Unavailable if API is completely unreachable

```json
{
  "polygon_api_status": "connected",
  "last_successful_request": "2025-07-27T15:29:45Z",
  "rate_limit": {
    "requests_remaining": 3,
    "reset_time": "2025-07-27T15:31:00Z",
    "requests_per_minute": 5
  },
  "cache_stats": {
    "total_entries": 156,
    "expired_entries": 12,
    "hit_rate_percentage": 78.5
  }
}
```

### POST /api/v1/market-data/cache/refresh

**Purpose:** Force refresh of cached market data
**Parameters:** 
- `data_type` (optional): 'quotes', 'options', 'historical', 'all' (default)
**Response:** Cache refresh status
**Errors:** 429 Too Many Requests if rate limit exceeded, 503 Service Unavailable on API failure

```json
{
  "refresh_status": "completed",
  "data_types_refreshed": ["quotes", "options"],
  "refresh_timestamp": "2025-07-27T15:30:00Z",
  "api_requests_made": 2,
  "rate_limit_remaining": 3
}
```

## Controllers

### MarketDataController (`app/api/v1/market_data.py`)

**Actions:**
- `get_spy_quote()` - Retrieve current SPY quote with cache fallback
- `get_spy_options()` - Fetch 0-DTE option chain with filtering
- `get_historical_data()` - Historical price data with timeframe selection
- `health_check()` - API connectivity and rate limit status
- `refresh_cache()` - Manual cache refresh with rate limit protection

**Business Logic:**
- Cache-first strategy with TTL-based expiration
- Automatic rate limit compliance with request queuing
- Graceful degradation when external API is unavailable
- Data validation using Pydantic models

**Error Handling:**
- Network timeout errors: Return cached data with staleness warning
- Authentication errors: Log error and return 503 status
- Rate limit exceeded: Queue request or return cached data
- Invalid API responses: Log error and skip malformed data

### CacheController (`app/api/v1/cache.py`)

**Actions:**
- `get_cache_stats()` - Cache performance metrics
- `cleanup_expired()` - Manual cleanup of expired entries
- `clear_cache()` - Admin function to clear all cached data

**Business Logic:**
- Automatic background cleanup of expired entries
- Cache hit rate tracking for performance monitoring
- Cache size management with LRU eviction if needed

## Background Services

### PolygonDataService (`app/services/polygon_client.py`)

**Purpose:** Core service for all Polygon.io API interactions
**Integration:** Direct integration with FastAPI dependency injection
**Methods:**
- Authentication and connection management
- Request queuing and rate limit enforcement
- Response parsing and validation
- Error handling with exponential backoff retry

### CacheManager (`app/services/cache_manager.py`)

**Purpose:** SQLite-based caching layer for all market data
**Integration:** Shared service across all controllers
**Methods:**
- TTL-based cache storage and retrieval
- Automatic cleanup of expired entries
- Cache statistics and performance monitoring
- Atomic operations for thread safety

### RateLimiter (`app/services/rate_limiter.py`)

**Purpose:** Token bucket rate limiting for API compliance
**Integration:** Middleware for all external API calls
**Methods:**
- Request rate enforcement (5 requests/minute)
- Queue management for delayed requests
- Rate limit status reporting
- Automatic reset handling

## Error Response Schema

```json
{
  "error": {
    "code": "POLYGON_API_UNAVAILABLE",
    "message": "Unable to connect to Polygon.io API",
    "details": "Connection timeout after 30 seconds",
    "fallback_used": true,
    "retry_after_seconds": 60
  },
  "timestamp": "2025-07-27T15:30:00Z",
  "request_id": "req_abc123"
}
```

## Authentication

**API Key Management:**
- Environment variable `POLYGON_API_KEY` required
- Validation on application startup
- Secure storage with no logging of actual key value
- Health check endpoint reports key validity without exposing value