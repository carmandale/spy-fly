# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-26-sentiment-calculation-#3/spec.md

> Created: 2025-07-26
> Version: 1.0.0

## Technical Requirements

- Calculate sentiment score from 0-100 based on multiple market factors
- Implement scoring rules as defined in PRD
- Use existing market data from Polygon API
- Cache calculations for 5 minutes to avoid redundant processing
- Provide detailed breakdown of score components
- Support both real-time and scheduled calculations
- Handle missing data gracefully with partial scoring

## Approach Options

**Option A:** Simple weighted sum
- Pros: Easy to implement, transparent, fast
- Cons: No interaction between factors, rigid

**Option B:** Rule-based decision tree
- Pros: Can model complex interactions, explainable
- Cons: Harder to maintain, many edge cases

**Option C:** Weighted scoring with thresholds (Selected)
- Pros: Balance of simplicity and flexibility, easy to adjust weights, clear reasoning
- Cons: May need tuning over time

**Rationale:** Weighted scoring provides transparency while allowing for future adjustments based on backtesting results.

## External Dependencies

- **pandas** - For technical indicator calculations
- **numpy** - For numerical computations
- **ta** (Technical Analysis Library) - For RSI, Bollinger bands calculations
- **Justification:** These libraries provide robust, tested implementations of technical indicators

## Sentiment Scoring Algorithm

### Score Components

| Component | Condition | Score | Weight |
|-----------|-----------|--------|---------|
| VIX Level | < 16 | 20 | 1.0 |
| | 16-20 | 10 | 1.0 |
| | > 20 | 0 | 1.0 |
| Futures Direction | > 0.1% | 20 | 1.0 |
| | 0 to 0.1% | 10 | 1.0 |
| | < 0% | 0 | 1.0 |
| RSI | 30-70 | 10 | 1.0 |
| | < 30 or > 70 | 0 | 1.0 |
| Price vs 50-MA | Above | 10 | 1.0 |
| | Below | 0 | 1.0 |
| Bollinger Position | Middle 60% | 10 | 1.0 |
| | Outer 40% | 0 | 1.0 |
| News Sentiment | Positive | 30 | 1.0 |
| | Neutral | 15 | 1.0 |
| | Negative | 0 | 1.0 |

**Total Maximum Score: 100**

### Decision Logic

```python
if total_score >= 60 and all_technicals_bullish:
    decision = "PROCEED"
else:
    decision = "SKIP"
```

### Technical Indicators Calculation

**RSI (14-period)**
```python
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

**50-Day Moving Average**
```python
def calculate_ma50(prices):
    return prices.rolling(window=50).mean().iloc[-1]
```

**Bollinger Bands (20-period, 2 std)**
```python
def calculate_bollinger_position(prices, period=20, std=2):
    ma = prices.rolling(window=period).mean()
    std_dev = prices.rolling(window=period).std()
    upper = ma + (std_dev * std)
    lower = ma - (std_dev * std)
    current = prices.iloc[-1]
    position = (current - lower) / (upper - lower)
    return position
```

## Data Flow

```
Market Data API
    ↓
┌─────────────────┐
│ Sentiment       │
│ Calculator      │
├─────────────────┤
│ - VIX Score     │
│ - Futures Score │
│ - Technical     │
│   Indicators    │
│ - News Score    │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Score           │
│ Aggregator      │
└────────┬────────┘
         ↓
┌─────────────────┐
│ Decision        │
│ Engine          │
└─────────────────┘
```

## Service Architecture

```python
class SentimentCalculator:
    def __init__(self, market_service: MarketDataService):
        self.market_service = market_service
        
    async def calculate_sentiment(self) -> SentimentResult:
        # Fetch all required data
        vix_data = await self._get_vix_data()
        futures_data = await self._get_futures_data()
        spy_history = await self._get_spy_history()
        
        # Calculate individual scores
        scores = {
            "vix": self._score_vix(vix_data),
            "futures": self._score_futures(futures_data),
            "rsi": self._score_rsi(spy_history),
            "ma50": self._score_ma50(spy_history),
            "bollinger": self._score_bollinger(spy_history),
            "news": self._score_news()  # Placeholder
        }
        
        # Aggregate and decide
        total_score = sum(scores.values())
        technicals_bullish = self._check_technicals(scores)
        
        return SentimentResult(
            score=total_score,
            decision="PROCEED" if total_score >= 60 and technicals_bullish else "SKIP",
            breakdown=scores,
            timestamp=datetime.now()
        )
```

## Caching Strategy

- Cache complete sentiment calculation for 5 minutes
- Cache individual component calculations for their respective data TTLs
- Invalidate cache on new market day
- Key format: `sentiment:spy:{date}:{component}`

## Error Handling

1. **Missing VIX Data**: Use last known value or skip component (0 score)
2. **Insufficient History**: Require minimum 50 days for MA calculation
3. **API Failures**: Return cached sentiment if available
4. **Partial Data**: Calculate with available components, note missing data

## Configuration

```python
class SentimentConfig:
    # Scoring thresholds
    VIX_LOW_THRESHOLD = 16
    VIX_HIGH_THRESHOLD = 20
    FUTURES_BULLISH_THRESHOLD = 0.001  # 0.1%
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    BOLLINGER_INNER_RANGE = 0.4  # 40% from edges
    
    # Scoring weights
    VIX_WEIGHT = 1.0
    FUTURES_WEIGHT = 1.0
    RSI_WEIGHT = 1.0
    MA50_WEIGHT = 1.0
    BOLLINGER_WEIGHT = 1.0
    NEWS_WEIGHT = 1.0
    
    # Decision threshold
    MINIMUM_SCORE = 60
    
    # Cache TTL
    SENTIMENT_CACHE_TTL = 300  # 5 minutes
```