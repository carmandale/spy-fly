# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-07-30-live-pl-calculation-#28/spec.md

> Created: 2025-07-30
> Version: 1.0.0

## Schema Changes

### New Tables

#### position_snapshots
Stores point-in-time P/L values for open positions

```sql
CREATE TABLE position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    spy_price DECIMAL(10, 2) NOT NULL,
    
    -- Current values
    current_value DECIMAL(10, 2) NOT NULL,
    unrealized_pl DECIMAL(10, 2) NOT NULL,
    unrealized_pl_percent DECIMAL(5, 2) NOT NULL,
    
    -- Individual leg values
    long_call_bid DECIMAL(10, 2),
    long_call_ask DECIMAL(10, 2),
    short_call_bid DECIMAL(10, 2),
    short_call_ask DECIMAL(10, 2),
    
    -- Risk monitoring
    risk_percent DECIMAL(5, 2) NOT NULL,
    stop_loss_triggered BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (position_id) REFERENCES positions(id),
    INDEX idx_position_time (position_id, snapshot_time),
    INDEX idx_snapshot_time (snapshot_time)
);
```

### Modified Tables

#### positions (new columns)
Add fields for real-time P/L tracking

```sql
ALTER TABLE positions ADD COLUMN latest_value DECIMAL(10, 2);
ALTER TABLE positions ADD COLUMN latest_unrealized_pl DECIMAL(10, 2);
ALTER TABLE positions ADD COLUMN latest_unrealized_pl_percent DECIMAL(5, 2);
ALTER TABLE positions ADD COLUMN latest_update_time TIMESTAMP;
ALTER TABLE positions ADD COLUMN stop_loss_alert_active BOOLEAN DEFAULT FALSE;
ALTER TABLE positions ADD COLUMN stop_loss_alert_time TIMESTAMP;
```

## Migration Strategy

1. Create new `position_snapshots` table
2. Add new columns to existing `positions` table with NULL defaults
3. Backfill latest values for any existing open positions
4. Create indexes for performance optimization

## Data Retention

- Keep all snapshots for 30 days
- Archive older snapshots to separate table if needed
- Maintain at least 5 days of data for all closed positions

## Query Patterns

### Get latest P/L for all open positions
```sql
SELECT p.*, ps.unrealized_pl, ps.risk_percent
FROM positions p
LEFT JOIN position_snapshots ps ON p.id = ps.position_id
WHERE p.status = 'open'
  AND ps.snapshot_time = (
    SELECT MAX(snapshot_time) 
    FROM position_snapshots 
    WHERE position_id = p.id
  );
```

### Get P/L history for charting
```sql
SELECT snapshot_time, unrealized_pl, spy_price
FROM position_snapshots
WHERE position_id = ?
  AND snapshot_time >= ?
ORDER BY snapshot_time ASC;
```

### Find positions needing stop-loss alerts
```sql
SELECT p.*
FROM positions p
WHERE p.status = 'open'
  AND p.latest_unrealized_pl_percent <= -20
  AND p.stop_loss_alert_active = FALSE;
```