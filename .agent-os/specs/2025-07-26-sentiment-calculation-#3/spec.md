# Spec Requirements Document

> Spec: Sentiment Calculation Engine
> Created: 2025-07-26
> GitHub Issue: #3
> Status: Planning

## Overview

Implement the core sentiment scoring logic that analyzes multiple market factors to determine if conditions are favorable for SPY 0-DTE bull-call-spread trades. The engine produces a 0-100 score with a threshold of 60 to proceed with trading.

## User Stories

### Morning Scan Story

As a trader, I want the system to automatically calculate market sentiment at 9:45 AM ET, so that I can quickly know if today is suitable for trading without manual analysis.

The system should:
1. Fetch current VIX level and score accordingly
2. Check overnight futures movement
3. Calculate technical indicators (RSI, MA, Bollinger)
4. Aggregate all factors into a single score
5. Provide clear go/no-go decision with reasoning

### Sentiment Transparency Story

As a trader, I want to see the breakdown of how the sentiment score was calculated, so that I can understand which factors are contributing positively or negatively to today's decision.

The breakdown should show:
- Individual component scores
- Current values vs thresholds
- Historical context for each indicator
- Overall recommendation with confidence level

## Spec Scope

1. **Sentiment Calculator Service** - Core logic for calculating and aggregating sentiment scores
2. **VIX Integration** - Fetch current VIX level and apply scoring rules
3. **Futures Analysis** - Calculate overnight S&P 500 futures movement
4. **Technical Indicators** - Implement RSI, moving averages, and Bollinger band calculations
5. **Sentiment API Endpoint** - REST endpoint to trigger calculation and get results

## Out of Scope

- Machine learning or AI-based sentiment
- Social media sentiment analysis (Twitter/X)
- News parsing and NLP
- Intraday sentiment updates
- Historical sentiment backtesting

## Expected Deliverable

1. API endpoint `GET /api/v1/sentiment/calculate` returns sentiment score with breakdown
2. Sentiment score updates use cached market data when available
3. Clear go/no-go decision based on 60+ score threshold and bullish technicals

## Spec Documentation

- Tasks: @.agent-os/specs/2025-07-26-sentiment-calculation-#3/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-26-sentiment-calculation-#3/sub-specs/technical-spec.md
- API Specification: @.agent-os/specs/2025-07-26-sentiment-calculation-#3/sub-specs/api-spec.md
- Tests Specification: @.agent-os/specs/2025-07-26-sentiment-calculation-#3/sub-specs/tests.md