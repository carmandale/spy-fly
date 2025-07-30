# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-30-live-pl-calculation-#28/spec.md

> Created: 2025-07-30
> Version: 1.0.0

## Technical Requirements

### Core P/L Calculation
- Calculate current spread value using bid/ask prices for both legs
- Support mark-to-market valuation: (Short Call Bid - Long Call Ask) × 100 × Quantity
- Calculate unrealized P/L: Current Value - Entry Value
- Calculate percentage P/L: (Unrealized P/L / Max Risk) × 100
- Handle both positive (credit received) and negative (debit paid) P/L

### Real-Time Integration
- Subscribe to WebSocket price updates for SPY
- Trigger P/L recalculation on every price update
- Throttle updates to UI to prevent overwhelming (max 1 update per second)
- Maintain calculation performance under 100ms per position

### Scheduled Updates
- APScheduler job running every 15 minutes during market hours (9:30 AM - 4:00 PM ET)
- Capture P/L snapshot for all open positions
- Store snapshots in database with timestamp
- Skip updates during pre-market and after-hours

### Risk Monitoring
- Calculate risk percentage: (Unrealized P/L / Max Risk) × 100
- Trigger stop-loss alert when risk percentage <= -20%
- Maintain alert state to prevent duplicate notifications
- Clear alert state when position improves above -15% (hysteresis)

## Approach Options

**Option A: Client-Side Calculation**
- Pros: Reduced server load, instant updates, simpler architecture
- Cons: Duplicate logic, harder to maintain consistency, no historical tracking

**Option B: Server-Side Calculation with Push Updates** (Selected)
- Pros: Centralized logic, automatic history tracking, consistent calculations
- Cons: Higher server load, requires WebSocket broadcasting

**Rationale:** Server-side approach ensures consistency and enables features like scheduled snapshots and future alert integration.

## External Dependencies

- **No new dependencies required** - Leverages existing infrastructure:
  - APScheduler (already installed for morning scan)
  - WebSocket infrastructure (already implemented)
  - SQLAlchemy models (extend existing)
  - Existing market data service

## Performance Considerations

- Cache option prices for 1 minute to reduce API calls
- Batch P/L calculations for multiple positions
- Use database connection pooling for snapshot storage
- Implement circuit breaker for market data failures

## Error Handling

- Gracefully handle missing bid/ask prices (use last known values)
- Continue calculations if one position fails
- Log errors but don't crash the scheduled job
- Provide fallback P/L of 0 if calculation fails completely