# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Technical Requirements

- **Performance**: Process complete SPY options chain (500-1000 options) and generate recommendations in under 10 seconds
- **Accuracy**: Black-Scholes calculations must match industry standard implementations within 0.01% tolerance
- **Risk Enforcement**: Hard-coded validation preventing any recommendation exceeding 5% buying power or below 1:1 risk/reward
- **Data Integration**: Seamless integration with existing Polygon.io API client and sentiment scoring system
- **Frontend Display**: React components to display top 3-5 recommendations with interactive sorting and copy-to-clipboard functionality
- **Error Handling**: Graceful degradation when options data is incomplete or market is closed
- **Caching**: Intelligent caching of options chain data to minimize API calls while maintaining real-time accuracy

## Approach Options

**Option A: Single-Service Monolithic Algorithm**
- Pros: Simpler architecture, faster development, easier testing, single point of responsibility
- Cons: Potential performance bottleneck, harder to scale individual components, tighter coupling

**Option B: Microservice Architecture with Separate Components** (Selected)
- Pros: Modular design, testable components, scalable performance, clear separation of concerns
- Cons: More complex architecture, additional coordination overhead

**Option C: Event-Driven Pipeline Architecture**
- Pros: Highly scalable, fault-tolerant, easy to add new filters
- Cons: Over-engineered for current needs, complex debugging, higher learning curve

**Rationale:** Option B provides the best balance of maintainability and performance for Phase 2 requirements. The modular approach allows independent testing of spread generation, filtering, and ranking while keeping complexity manageable. Each component can be optimized separately and the architecture supports future enhancements without major refactoring.

## External Dependencies

- **scipy** - For Black-Scholes option pricing model implementation
  - **Justification:** Industry-standard scientific computing library with proven financial mathematics functions, avoids reinventing complex mathematical models

- **pandas** - For efficient options chain data manipulation and filtering
  - **Justification:** Already in use for market data processing, provides vectorized operations crucial for analyzing thousands of spread combinations efficiently

- **numpy** - Mathematical operations and array processing for probability calculations
  - **Justification:** Dependency of scipy and pandas, provides fast numerical computing needed for real-time calculations

## Core Algorithm Components

### 1. Options Chain Processor
**Input:** Raw Polygon.io options data for SPY 0-DTE
**Output:** Structured DataFrame with calls sorted by strike price
**Logic:** Filter for current expiration date, validate data completeness, handle missing bid/ask spreads

### 2. Spread Combination Generator  
**Input:** Processed options chain DataFrame
**Output:** All viable bull-call-spread combinations
**Logic:** Generate combinations where long_strike < short_strike, calculate net debit, filter by liquidity requirements

### 3. Risk/Reward Filter
**Input:** Spread combinations with pricing
**Output:** Spreads meeting 1:1 minimum risk/reward and 5% buying power constraints
**Logic:** Calculate max_profit = (strike_diff - net_debit), max_loss = net_debit, filter ratio >= 1.0, apply position sizing limits

### 4. Probability Calculator
**Input:** Filtered spreads + current VIX data
**Output:** Probability of profit for each spread
**Logic:** Black-Scholes implementation using VIX/100 as volatility input, calculate probability SPY > break_even at expiration

### 5. Ranking Engine
**Input:** Spreads with probability calculations + sentiment score
**Output:** Top 3-5 recommendations ranked by expected value
**Logic:** expected_value = (probability * max_profit) - ((1-probability) * max_loss), weight by sentiment score, sort descending

### 6. Trade Formatter
**Input:** Ranked spread recommendations
**Output:** JSON formatted for frontend consumption with copy-to-clipboard order details
**Logic:** Generate human-readable descriptions, format order tickets, calculate breakeven points and profit zones