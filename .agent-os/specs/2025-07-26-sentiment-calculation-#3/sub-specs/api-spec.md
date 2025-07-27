# API Specification

This is the API specification for the spec detailed in @.agent-os/specs/2025-07-26-sentiment-calculation-#3/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Endpoints

### GET /api/v1/sentiment/calculate

**Purpose:** Calculate current market sentiment score for SPY trading

**Parameters:**
- `force_refresh` (query, optional): Skip cache and recalculate (default: false)

**Response:**
```json
{
  "score": 72,
  "decision": "PROCEED",
  "threshold": 60,
  "timestamp": "2025-07-26T09:45:00Z",
  "breakdown": {
    "vix": {
      "score": 20,
      "value": 14.5,
      "threshold": "< 16",
      "label": "Low volatility (bullish)"
    },
    "futures": {
      "score": 20,
      "value": 0.35,
      "change_percent": 0.35,
      "label": "Positive overnight (bullish)"
    },
    "rsi": {
      "score": 10,
      "value": 55.2,
      "range": "30-70",
      "label": "Neutral (healthy)"
    },
    "ma50": {
      "score": 10,
      "current_price": 567.89,
      "ma50": 562.34,
      "position": "above",
      "label": "Above 50-MA (bullish)"
    },
    "bollinger": {
      "score": 10,
      "position": 0.65,
      "band_width": 8.5,
      "label": "Middle range (neutral)"
    },
    "news": {
      "score": 2,
      "sentiment": "neutral",
      "label": "Neutral market sentiment"
    }
  },
  "technical_status": {
    "all_bullish": true,
    "details": {
      "trend": "up",
      "momentum": "positive",
      "volatility": "low"
    }
  },
  "cached": false,
  "cache_expires_at": "2025-07-26T09:50:00Z"
}
```

**Errors:**
- 503: Unable to fetch required market data
- 500: Calculation error

### GET /api/v1/sentiment/components/{component}

**Purpose:** Get individual sentiment component calculation

**Parameters:**
- `component` (path): Component name (vix, futures, rsi, ma50, bollinger, news)

**Response (VIX example):**
```json
{
  "component": "vix",
  "score": 20,
  "max_score": 20,
  "current_value": 14.5,
  "scoring_rules": [
    {"range": "< 16", "score": 20, "active": true},
    {"range": "16-20", "score": 10, "active": false},
    {"range": "> 20", "score": 0, "active": false}
  ],
  "historical_context": {
    "current": 14.5,
    "avg_30d": 16.2,
    "avg_90d": 17.8,
    "percentile": 25
  },
  "timestamp": "2025-07-26T09:45:00Z"
}
```

**Errors:**
- 404: Invalid component name
- 503: Component data unavailable

### GET /api/v1/sentiment/history

**Purpose:** Get historical sentiment scores

**Parameters:**
- `days` (query, optional): Number of days to retrieve (default: 7, max: 30)

**Response:**
```json
{
  "history": [
    {
      "date": "2025-07-26",
      "score": 72,
      "decision": "PROCEED",
      "components": {
        "vix": 20,
        "futures": 20,
        "rsi": 10,
        "ma50": 10,
        "bollinger": 10,
        "news": 2
      }
    },
    {
      "date": "2025-07-25",
      "score": 45,
      "decision": "SKIP",
      "components": {
        "vix": 0,
        "futures": 10,
        "rsi": 10,
        "ma50": 10,
        "bollinger": 0,
        "news": 15
      }
    }
  ],
  "summary": {
    "total_days": 7,
    "proceed_days": 4,
    "skip_days": 3,
    "avg_score": 58.5,
    "success_rate": 0.571
  }
}
```

**Errors:**
- 400: Invalid days parameter

### POST /api/v1/sentiment/schedule

**Purpose:** Schedule sentiment calculation for specific time

**Request Body:**
```json
{
  "time": "09:45",
  "timezone": "America/New_York",
  "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "enabled": true
}
```

**Response:**
```json
{
  "schedule_id": "daily-morning-scan",
  "status": "active",
  "next_run": "2025-07-27T09:45:00-04:00",
  "configuration": {
    "time": "09:45",
    "timezone": "America/New_York",
    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "enabled": true
  }
}
```

**Errors:**
- 400: Invalid schedule configuration
- 409: Schedule already exists

### GET /api/v1/sentiment/config

**Purpose:** Get current sentiment calculation configuration

**Response:**
```json
{
  "scoring_thresholds": {
    "vix": {
      "low": 16,
      "high": 20
    },
    "futures": {
      "bullish": 0.001
    },
    "rsi": {
      "oversold": 30,
      "overbought": 70
    },
    "bollinger": {
      "inner_range": 0.4
    }
  },
  "scoring_weights": {
    "vix": 1.0,
    "futures": 1.0,
    "rsi": 1.0,
    "ma50": 1.0,
    "bollinger": 1.0,
    "news": 1.0
  },
  "decision_threshold": 60,
  "cache_ttl": 300
}
```

## Rate Limiting

Sentiment endpoints share the same rate limit as market data endpoints:
- Uses cached market data when available
- Sentiment calculation itself doesn't count against Polygon rate limit
- Force refresh may trigger multiple API calls

## Caching

- Sentiment calculations are cached for 5 minutes
- Individual components may have different cache TTLs
- Use `force_refresh=true` to bypass cache

## WebSocket Events (Future Enhancement)

```json
{
  "event": "sentiment_update",
  "data": {
    "score": 72,
    "decision": "PROCEED",
    "timestamp": "2025-07-26T09:45:00Z"
  }
}
```