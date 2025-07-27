# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-26-polygon-api-integration-#2/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Endpoints

### GET /api/v1/market/quote/{ticker}

**Purpose:** Fetch real-time quote data for a given ticker (primarily SPY)

**Parameters:**
- `ticker` (path): Stock ticker symbol (e.g., "SPY")

**Response:**
```json
{
  "ticker": "SPY",
  "price": 567.89,
  "bid": 567.87,
  "ask": 567.91,
  "bid_size": 100,
  "ask_size": 150,
  "volume": 45678900,
  "timestamp": "2025-07-26T10:30:00Z",
  "market_status": "open",
  "change": 2.34,
  "change_percent": 0.41,
  "previous_close": 565.55,
  "cached": false
}
```

**Errors:**
- 404: Ticker not found
- 429: Rate limit exceeded
- 503: Market data temporarily unavailable

### GET /api/v1/market/options/{ticker}

**Purpose:** Retrieve option chain for a specific expiration date

**Parameters:**
- `ticker` (path): Stock ticker symbol (e.g., "SPY")
- `expiration` (query): Option expiration date in YYYY-MM-DD format
- `option_type` (query, optional): Filter by "call" or "put"
- `strike_range` (query, optional): Number of strikes above/below current price (default: 10)

**Response:**
```json
{
  "ticker": "SPY",
  "underlying_price": 567.89,
  "expiration": "2025-07-26",
  "options": [
    {
      "symbol": "SPY250726C00565000",
      "type": "call",
      "strike": 565.00,
      "bid": 3.25,
      "ask": 3.30,
      "mid": 3.275,
      "last": 3.28,
      "volume": 12500,
      "open_interest": 45000,
      "implied_volatility": 0.1234,
      "delta": 0.65,
      "gamma": 0.023,
      "theta": -0.45,
      "vega": 0.12
    }
  ],
  "cached": false,
  "cache_expires_at": "2025-07-26T10:35:00Z"
}
```

**Errors:**
- 400: Invalid expiration date format
- 404: No options found for given expiration
- 429: Rate limit exceeded

### GET /api/v1/market/historical/{ticker}

**Purpose:** Get historical price data for analysis and backtesting

**Parameters:**
- `ticker` (path): Stock ticker symbol
- `from` (query): Start date in YYYY-MM-DD format
- `to` (query): End date in YYYY-MM-DD format
- `timeframe` (query, optional): "minute", "hour", "day" (default: "day")
- `limit` (query, optional): Maximum number of bars (default: 100, max: 1000)

**Response:**
```json
{
  "ticker": "SPY",
  "from": "2025-07-01",
  "to": "2025-07-26",
  "timeframe": "day",
  "bars": [
    {
      "timestamp": "2025-07-01T09:30:00Z",
      "open": 560.50,
      "high": 562.30,
      "low": 559.80,
      "close": 561.90,
      "volume": 78900000,
      "vwap": 561.15
    }
  ],
  "result_count": 26,
  "cached": true
}
```

**Errors:**
- 400: Invalid date range or timeframe
- 404: No data available for date range
- 429: Rate limit exceeded

### GET /api/v1/market/status

**Purpose:** Check market status and data availability

**Parameters:** None

**Response:**
```json
{
  "market_status": "open",
  "session": "regular",
  "api_status": "healthy",
  "rate_limit_remaining": 3,
  "rate_limit_reset": "2025-07-26T10:31:00Z",
  "cache_stats": {
    "hits": 145,
    "misses": 23,
    "size": 89,
    "max_size": 1000
  }
}
```

**Errors:**
- 503: Service temporarily unavailable

## Rate Limiting

All endpoints are subject to rate limiting based on the Polygon.io tier:

- **Free Tier:** 5 requests per minute
- **Response Headers:**
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Caching

Responses include caching information:

- `cached`: Boolean indicating if response is from cache
- `cache_expires_at`: ISO timestamp when cache entry expires
- Cache-Control headers are set appropriately

## Error Response Format

All errors follow consistent format:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded. Please try again in 45 seconds.",
    "details": {
      "retry_after": 45,
      "limit": 5,
      "window": "1m"
    }
  }
}
```