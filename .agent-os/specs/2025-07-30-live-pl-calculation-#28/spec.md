# Spec Requirements Document

> Spec: Live P/L Calculation for Open Positions
> Created: 2025-07-30
> GitHub Issue: #28
> Status: Planning

## Overview

Implement a real-time profit/loss calculation system that tracks the value of open spread positions throughout the trading day, providing both scheduled updates every 15 minutes and real-time updates via WebSocket price feeds.

## User Stories

### Real-Time P/L Monitoring

As an active trader, I want to see my profit/loss update in real-time, so that I can make informed decisions about when to close positions.

The system will calculate the current market value of open spread positions using real-time bid/ask prices from the WebSocket feed. When SPY price changes, the P/L will update automatically within 2 seconds. The dashboard will show both dollar amounts and percentage changes with color-coded indicators (green for profit, red for loss).

### Historical P/L Tracking

As a trader reviewing performance, I want to see how my P/L evolved throughout the day, so that I can understand the impact of time decay and price movements.

The system will store P/L snapshots every 15 minutes during market hours, creating a historical record of position performance. This data will be used to generate intraday P/L charts showing the progression from entry to current time, helping traders visualize theta decay and price impact.

### Stop-Loss Monitoring

As a risk-conscious trader, I want to be alerted when my position reaches -20% of maximum risk, so that I can exit losing trades according to my risk management rules.

The system will continuously monitor unrealized P/L against the maximum risk threshold. When a position reaches -20% of the max risk (e.g., -$100 on a $500 max risk spread), the system will trigger visual alerts on the dashboard and prepare for future email/browser notifications.

## Spec Scope

1. **P/L Calculation Engine** - Core service to calculate current spread values using option pricing
2. **Real-Time Updates** - Integration with WebSocket price feed for live P/L updates
3. **Scheduled Snapshots** - APScheduler job to capture P/L every 15 minutes during market hours
4. **Database Storage** - Tables for P/L history and position tracking
5. **Dashboard Integration** - Live P/L display with visual indicators and charts

## Out of Scope

- Email notifications for stop-loss alerts (future alert system)
- Realized P/L from closed positions (future feature)
- Tax calculations or reporting
- Multi-account support
- Options Greeks beyond basic P/L

## Expected Deliverable

1. Live P/L values updating in real-time on the dashboard as SPY price changes
2. P/L history chart showing intraday progression with 15-minute snapshots
3. Visual stop-loss indicators when positions approach -20% of max risk

## Spec Documentation

- Tasks: @.agent-os/specs/2025-07-30-live-pl-calculation-#28/tasks.md
- Technical Specification: @.agent-os/specs/2025-07-30-live-pl-calculation-#28/sub-specs/technical-spec.md
- Database Schema: @.agent-os/specs/2025-07-30-live-pl-calculation-#28/sub-specs/database-schema.md
- API Specification: @.agent-os/specs/2025-07-30-live-pl-calculation-#28/sub-specs/api-spec.md
- Tests Specification: @.agent-os/specs/2025-07-30-live-pl-calculation-#28/sub-specs/tests.md