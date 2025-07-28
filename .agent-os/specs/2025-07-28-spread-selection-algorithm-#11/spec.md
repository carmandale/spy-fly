# Spec Requirements Document

> Spec: Spread Selection Algorithm for 0-DTE Bull-Call-Spreads
> Created: 2025-07-28
> GitHub Issue: #11
> Status: Planning

## Overview

Implement the core spread selection algorithm that filters and ranks SPY 0-DTE bull-call-spreads based on risk/reward criteria and probability analysis. This is the heart of the trading intelligence system that transforms raw options data into actionable trade recommendations with strict risk management guardrails.

## User Stories

### Automated Morning Scan

As a systematic trader, I want the system to automatically analyze all available SPY 0-DTE bull-call-spreads each morning, so that I can receive filtered recommendations that meet my risk criteria without spending 30-60 minutes on manual analysis.

**Detailed Workflow:** System fetches complete SPY options chain at market open, filters for 0-DTE expirations, evaluates all possible bull-call-spread combinations, applies risk/reward filters (minimum 1:1, maximum 5% buying power), calculates probability of profit using Black-Scholes, ranks spreads by expected value, and presents top 3-5 recommendations with complete trade details including strike prices, premiums, max risk/reward, and copy-to-clipboard order tickets.

### Risk-Managed Position Sizing

As a trader learning systematic approaches, I want the system to automatically calculate the correct contract quantity based on my account size and risk parameters, so that I never accidentally risk more than 5% of my buying power on a single trade.

**Detailed Workflow:** User inputs account size and risk tolerance in settings, system calculates maximum dollar risk per trade (5% of buying power), for each recommended spread calculates net debit per contract, determines maximum contracts that fit within risk limit, displays recommended position size with clear risk metrics, and prevents recommendations that would exceed limits even with minimum 1-contract position.

### Probability-Based Selection

As an active options trader, I want to see the probability of profit for each spread recommendation calculated using current market volatility, so that I can make informed decisions based on quantitative analysis rather than gut feelings.

**Detailed Workflow:** System retrieves real-time VIX data for implied volatility input, implements Black-Scholes model for options pricing, calculates probability that SPY will close above break-even point at expiration, factors in time decay and current market sentiment score, ranks spreads by probability-adjusted expected return, and displays probability percentages with confidence intervals and underlying assumptions clearly explained.

## Spec Scope

1. **Options Chain Processing** - Fetch and parse complete SPY 0-DTE options chain from Polygon.io API with real-time pricing
2. **Spread Combination Generation** - Systematically evaluate all viable bull-call-spread combinations with strike price filtering
3. **Risk/Reward Filtering** - Apply 1:1 minimum risk/reward ratio and 5% maximum buying power constraints
4. **Probability Calculations** - Implement Black-Scholes model with VIX-based volatility for probability of profit analysis  
5. **Ranking Algorithm** - Sort recommendations by expected value considering probability, risk, and current sentiment score
6. **Trade Recommendation Output** - Generate formatted trade details with copy-to-clipboard order tickets for top 3-5 spreads

## Out of Scope

- Integration with broker APIs for automatic order placement
- Support for other spread strategies (put spreads, iron condors, etc.)
- Historical backtesting functionality (reserved for Phase 4)
- Real-time P/L monitoring (reserved for Phase 3)
- Advanced Greeks calculations beyond basic Black-Scholes (delta, gamma, theta moved to should-have)

## Expected Deliverable

1. **Working Algorithm**: System processes full SPY options chain and generates 3-5 viable spread recommendations in under 10 seconds
2. **Risk Compliance**: All recommendations automatically enforce 1:1 risk/reward minimum and 5% buying power maximum with no exceptions
3. **Frontend Integration**: Recommended spreads display in React dashboard with clear risk metrics, probability scores, and actionable trade details

## Spec Documentation

- Tasks: @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/sub-specs/technical-spec.md
- Tests Specification: @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/sub-specs/tests.md