# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Test Coverage

### Unit Tests

**SpreadSelectionService**
- Test spread combination generation with valid options chain data
- Test risk/reward filtering with various spread configurations  
- Test probability calculations using Black-Scholes model with known inputs
- Test ranking algorithm with multiple spreads and sentiment scores
- Test position sizing calculations with different account sizes
- Test error handling when options data is missing or invalid
- Test performance with large options chains (500+ options)

**BlackScholesCalculator**
- Test probability of profit calculations with known mathematical results
- Test implied volatility handling with VIX data integration
- Test edge cases (very high/low volatility, near expiration)
- Test mathematical precision against reference implementations
- Test time decay calculations throughout trading day

**SpreadGenerator**  
- Test bull-call-spread combination logic with various strike ranges
- Test filtering of invalid combinations (long_strike >= short_strike)
- Test liquidity filtering based on bid/ask spreads and volume
- Test handling of missing option pricing data
- Test performance optimization with vectorized operations

**RiskValidator**
- Test 5% buying power enforcement with edge cases
- Test 1:1 risk/reward ratio validation 
- Test position sizing calculations with fractional shares
- Test account size validation and error handling
- Test maximum risk calculations with complex spread scenarios

### Integration Tests

**Spread Recommendation API**
- Test complete recommendation flow from options data fetch to formatted output
- Test API response format and required fields validation
- Test rate limiting and caching behavior with repeated requests
- Test error responses when market is closed or data unavailable
- Test parameter validation (account size, risk settings, limits)
- Test performance requirements (< 10 second response time)

**Database Integration**
- Test storing spread recommendations with complete metadata
- Test analysis session tracking and performance metrics
- Test options data querying with new Greeks columns
- Test database migration scripts for schema changes
- Test data integrity constraints and foreign key relationships

**Frontend Integration**  
- Test React component rendering with recommendation data
- Test interactive sorting and filtering of recommendations
- Test copy-to-clipboard functionality for order tickets
- Test responsive design with mobile viewport sizes
- Test loading states and error handling for API failures

### Feature Tests

**End-to-End Spread Analysis Workflow**
- Test complete morning scan process from market data fetch to UI display
- Test user parameter customization (account size, risk tolerance)
- Test recommendation updates when market conditions change
- Test system behavior during market open, mid-day, and close
- Test handling of weekends and market holidays

**Risk Management Validation**
- Test that no recommendation exceeds 5% buying power under any conditions
- Test that all recommendations meet minimum 1:1 risk/reward ratio
- Test position sizing accuracy with various account sizes
- Test edge cases where no valid spreads meet criteria
- Test warning displays when spreads approach risk limits

**Performance and Reliability**
- Test system performance with full SPY options chain (500+ options)
- Test concurrent request handling during high load periods
- Test data accuracy compared to manual calculations
- Test system stability over extended running periods
- Test recovery from external API failures or timeouts

## Mocking Requirements

### External API Services
- **Polygon.io Options Data:** Mock complete SPY options chain responses with realistic pricing data
- **VIX Data Service:** Mock current VIX levels for volatility calculations
- **Sentiment Service:** Mock sentiment scores to test ranking algorithm weighting

### Market Data Scenarios
- **Normal Market Conditions:** Standard bid/ask spreads, reasonable volatility
- **High Volatility Days:** Elevated VIX levels, wider spreads, extreme pricing
- **Low Liquidity Conditions:** Missing bid/ask data, high spreads, low volume
- **Market Close Conditions:** Stale data, missing options, expired contracts
- **Error Conditions:** API timeouts, malformed data, authentication failures

### Time-Based Test Scenarios
- **Market Open (9:30 AM):** Fresh options data, high volatility, wide spreads
- **Mid-Day Trading (12:00 PM):** Stable conditions, normal spreads
- **Market Close (4:00 PM):** Final pricing, expiration calculations
- **After Hours:** Stale data handling, next-day preparation
- **Weekends/Holidays:** Market closed responses, error handling

### Database State Mocking
- **Clean Database State:** Fresh install with no historical data
- **Populated History:** Existing recommendations and session data for testing queries
- **Migration States:** Test database schema changes and data preservation
- **Corrupted Data:** Test error handling with invalid or incomplete database records

### Frontend Integration Mocks
- **API Response Delays:** Test loading states and timeout handling
- **Empty Result Sets:** Test UI when no valid spreads meet criteria  
- **Error Responses:** Test error message display and user guidance
- **Real-Time Updates:** Mock WebSocket-style data updates for future integration