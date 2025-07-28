# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-27-database-schema-#7/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Test Coverage

### Unit Tests

**Trade Model Tests**
- Test trade creation with valid data
- Test trade status transitions (recommended → entered → exited)
- Test P/L calculations with various scenarios
- Test validation constraints (status values, trade types)
- Test relationship with sentiment scores
- Test soft delete functionality

**SentimentScore Model Tests**
- Test score creation with component breakdown
- Test JSON field serialization/deserialization
- Test unique constraint on date/time combination
- Test decision logic validation (PROCEED/SKIP)
- Test relationship with trades

**Configuration Model Tests**
- Test key-value storage with different types
- Test category grouping
- Test version incrementing on updates
- Test sensitive value handling
- Test unique constraint on category/key

**Database Service Tests**
- Test connection pooling and session management
- Test transaction rollback on errors
- Test bulk insert performance
- Test query optimization with indexes

### Integration Tests

**Trade Recording Workflow**
- Create sentiment score → Generate trade recommendation → Enter trade → Exit trade
- Verify all related records created correctly
- Test cascading updates across related tables
- Test data consistency after workflow completion

**Daily Summary Generation**
- Create multiple trades throughout day
- Run summary generation job
- Verify accurate aggregation of metrics
- Test cumulative P/L calculations
- Test handling of edge cases (no trades, all losses, etc.)

**Configuration Management**
- Update risk parameters
- Verify changes reflected in trade calculations
- Test configuration versioning
- Test rollback to previous configuration

**Historical Data Queries**
- Test date range filtering for trades
- Test performance metric calculations
- Test equity curve data generation
- Test export functionality

### Feature Tests

**End-to-End Trade Lifecycle**
- Sentiment calculation triggers trade recommendation
- User accepts recommendation
- System records entry with spread details
- Price monitoring triggers exit signal
- P/L calculated and daily summary updated

**Performance Analytics Dashboard**
- Load historical trades
- Calculate win rate, Sharpe ratio, average P/L
- Generate equity curve visualization
- Test with various data volumes (10, 100, 1000 trades)

**Data Migration Scenarios**
- Test schema upgrades with existing data
- Test data integrity during migrations
- Test rollback procedures
- Test index creation on populated tables

### Mocking Requirements

- **Market Data Service:** Mock quote responses for P/L calculations
- **Sentiment Calculator:** Mock score generation for trade testing
- **Date/Time:** Mock current time for consistent test results
- **File System:** Mock database file operations for initialization tests

## Performance Benchmarks

- Trade insertion: < 10ms per record
- Daily summary calculation: < 100ms for 250 trades
- Historical query (30 days): < 50ms
- Bulk export (1 year): < 500ms

## Error Scenarios

- Database file permissions issues
- Disk space exhaustion
- Corrupted database recovery
- Migration failure handling
- Concurrent access conflicts (future multi-user scenario)