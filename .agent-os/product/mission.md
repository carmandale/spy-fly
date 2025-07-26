# Product Mission

> Last Updated: 2025-07-26
> Version: 1.0.0

## Pitch

SPY-FLY is a web-based trading automation tool that helps active options traders systematically execute SPY 0-DTE bull-call-spread strategies by providing automated sentiment analysis, spread selection, and real-time P/L monitoring while maintaining strict risk management guardrails.

## Users

### Primary Customers

- **Active Options Traders**: Individual traders who regularly trade SPY 0-DTE options and want to systematize their approach
- **Trading Educators**: Professionals teaching options strategies who need a demonstration/simulation platform

### User Personas

**The Systematic Trader** (35-55 years old)
- **Role:** Independent trader or professional with discretionary account
- **Context:** Trades SPY 0-DTE spreads daily as part of income strategy
- **Pain Points:** Manual morning analysis is time-consuming, emotional bias affects decisions, hard to track performance consistently
- **Goals:** Automate routine tasks, maintain discipline, track results systematically

**The Learning Trader** (25-45 years old)
- **Role:** Part-time trader learning advanced strategies
- **Context:** Studying options strategies while maintaining day job
- **Pain Points:** Complex calculations, missing optimal entry times, paper trading is tedious
- **Goals:** Learn systematic approach, practice without real money risk, understand probability-based trading

## The Problem

### Time-Consuming Morning Routine

Active SPY 0-DTE traders spend 30-60 minutes each morning manually checking VIX levels, futures, technical indicators, and calculating spread parameters. This manual process is prone to errors and emotional bias.

**Our Solution:** Automated morning scan completes in seconds with consistent, rule-based analysis.

### Inconsistent Risk Management

Traders often deviate from their risk rules during volatile markets, taking positions too large or holding losing trades too long. Manual position sizing calculations lead to errors that compound losses.

**Our Solution:** Programmatic enforcement of 5% buying power limits and automated stop-loss alerts.

### Poor Performance Tracking

Spreadsheet-based tracking is tedious and often abandoned, making it difficult to analyze strategy performance over time or identify areas for improvement.

**Our Solution:** Automatic trade logging with equity curve visualization and exportable performance metrics.

## Differentiators

### Educational Focus

Unlike broker platforms that focus on order execution, we provide a learning environment with transparent calculations, probability models, and paper trading support. This results in traders understanding the "why" behind each trade recommendation.

### Single-Strategy Optimization

Rather than trying to support every options strategy, we optimize specifically for SPY 0-DTE bull-call-spreads. This results in a streamlined workflow that matches exactly how experienced traders approach this strategy.

### Self-Hosted Control

Unlike cloud-based services, traders maintain complete control over their data and can customize the tool to their specific rules. This results in privacy, flexibility, and no recurring subscription fees.

## Key Features

### Core Features

- **Automated Sentiment Scoring:** Multi-factor analysis combining VIX, futures, news sentiment, and technicals into actionable score
- **Smart Spread Selection:** Algorithm filters thousands of combinations to find optimal risk/reward spreads meeting strict criteria
- **Real-Time P/L Monitoring:** WebSocket-powered live updates with visual profit zones and automated alert triggers
- **Position Sizing Calculator:** Automatic contract quantity calculation based on account size and risk parameters

### Risk Management Features

- **5% Buying Power Cap:** Hard-coded maximum risk per trade based on account size
- **1:1 Risk/Reward Filter:** Only presents spreads meeting minimum profit potential
- **Stop-Loss Alerts:** Automated notifications when positions reach -20% of max risk
- **Probability Modeling:** Black-Scholes based probability of profit calculations for informed decisions

### Workflow Features

- **One-Click Recommendations:** Single button generates complete trade setup ready for broker entry
- **Copy-to-Clipboard Orders:** Formatted order tickets for quick manual execution
- **Daily Email Reports:** Automated end-of-day summaries with P/L and equity curve updates
- **Historical Performance Tracking:** Searchable database of all trades with CSV export capability