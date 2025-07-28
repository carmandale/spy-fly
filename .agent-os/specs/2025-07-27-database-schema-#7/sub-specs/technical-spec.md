# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-27-database-schema-#7/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Technical Requirements

### Database Design Principles

- **Single-user focus**: Optimize for local SQLite performance, not concurrent access
- **Denormalization where appropriate**: Trade storage efficiency for query speed
- **Comprehensive audit trail**: Never delete records, use soft deletes with timestamps
- **Type safety**: Leverage SQLAlchemy's type system with Pydantic integration
- **Migration-ready**: Design with future schema evolution in mind

### Core Tables Structure

1. **trades** - Complete trade lifecycle tracking
   - Captures entry/exit signals, execution status, P/L calculations
   - Links to sentiment scores that triggered the trade
   - Supports both paper and real trades

2. **sentiment_scores** - Daily sentiment snapshots
   - Full breakdown of all 6 components (VIX, Futures, RSI, MA50, Bollinger, News)
   - Decision outcome and technical status
   - Enables backtesting and strategy optimization

3. **trade_spreads** - Option spread details
   - Strike prices, premiums, Greeks at entry
   - Position sizing and risk calculations
   - Links to parent trade record

4. **configuration** - Key-value settings store
   - User preferences (risk limits, notification settings)
   - System parameters (API keys, thresholds)
   - Version tracking for configuration changes

5. **daily_summaries** - Aggregated performance metrics
   - End-of-day P/L, win rate, trade count
   - Cumulative statistics for equity curve
   - Pre-calculated for dashboard performance

### SQLAlchemy Implementation

- Use declarative_base with proper type hints
- Implement JSON columns for flexible metadata storage
- Add database-level constraints and indexes
- Create hybrid properties for calculated fields
- Use UTC timestamps consistently

### Performance Optimizations

- Index on date fields for time-series queries
- Composite indexes for common filter combinations
- Materialized views for complex aggregations
- Connection pooling with appropriate limits

## Approach Options

**Option A: Minimal Schema**
- Pros: Simple to implement, fewer migrations needed
- Cons: Limited analytics capability, potential performance issues

**Option B: Comprehensive Schema** (Selected)
- Pros: Rich analytics, optimized queries, future-proof design
- Cons: More complex initial implementation

**Option C: NoSQL/JSON Storage**
- Pros: Flexible schema, easy iterations
- Cons: Poor query performance, no referential integrity

**Rationale:** Option B provides the best balance of functionality and performance for a trading application where historical analysis is critical.

## External Dependencies

- **SQLAlchemy 2.0+** - Modern ORM with async support
  - **Justification:** Industry standard, excellent SQLite support, type-safe queries
  
- **Alembic 1.13+** - Database migration tool
  - **Justification:** Seamlessly integrates with SQLAlchemy, handles schema evolution
  
- **python-dotenv** - Environment configuration (already in use)
  - **Justification:** Consistent configuration management