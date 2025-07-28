# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-07-27-database-schema-#7/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Schema Overview

```sql
-- Core trading and analytics tables for SPY-FLY
-- SQLite3 with SQLAlchemy ORM
```

## Table Definitions

### trades

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date DATE NOT NULL,
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('paper', 'real')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('recommended', 'skipped', 'entered', 'exited', 'stopped')),
    
    -- Entry Details
    entry_time TIMESTAMP,
    entry_sentiment_score_id INTEGER REFERENCES sentiment_scores(id),
    entry_signal_reason TEXT,
    
    -- Position Details  
    contracts INTEGER,
    max_risk DECIMAL(10, 2),
    max_reward DECIMAL(10, 2),
    probability_of_profit DECIMAL(5, 2),
    
    -- Exit Details
    exit_time TIMESTAMP,
    exit_reason VARCHAR(50),
    exit_price DECIMAL(10, 2),
    
    -- P/L Calculation
    gross_pnl DECIMAL(10, 2),
    commissions DECIMAL(10, 2),
    net_pnl DECIMAL(10, 2),
    pnl_percentage DECIMAL(10, 2),
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_date (trade_date),
    INDEX idx_status (status),
    INDEX idx_entry_sentiment (entry_sentiment_score_id)
);
```

### sentiment_scores

```sql
CREATE TABLE sentiment_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score_date DATE NOT NULL,
    score_time TIME NOT NULL,
    
    -- Overall Score
    total_score INTEGER NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('PROCEED', 'SKIP')),
    threshold INTEGER NOT NULL,
    
    -- Component Scores (stored as JSON for flexibility)
    vix_component JSON NOT NULL,
    futures_component JSON NOT NULL,
    rsi_component JSON NOT NULL,
    ma50_component JSON NOT NULL,
    bollinger_component JSON NOT NULL,
    news_component JSON NOT NULL,
    
    -- Technical Status
    technical_status JSON NOT NULL,
    
    -- Market Context
    spy_price DECIMAL(10, 2),
    market_session VARCHAR(20),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(score_date, score_time),
    INDEX idx_score_date (score_date),
    INDEX idx_decision (decision)
);
```

### trade_spreads

```sql
CREATE TABLE trade_spreads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL REFERENCES trades(id),
    
    -- Spread Details
    spread_type VARCHAR(20) NOT NULL DEFAULT 'bull_call_spread',
    expiration_date DATE NOT NULL,
    
    -- Long Leg
    long_strike DECIMAL(10, 2) NOT NULL,
    long_premium DECIMAL(10, 2) NOT NULL,
    long_iv DECIMAL(5, 2),
    long_delta DECIMAL(5, 4),
    long_gamma DECIMAL(5, 4),
    long_theta DECIMAL(5, 4),
    
    -- Short Leg
    short_strike DECIMAL(10, 2) NOT NULL,
    short_premium DECIMAL(10, 2) NOT NULL,
    short_iv DECIMAL(5, 2),
    short_delta DECIMAL(5, 4),
    short_gamma DECIMAL(5, 4),
    short_theta DECIMAL(5, 4),
    
    -- Spread Metrics
    net_debit DECIMAL(10, 2) NOT NULL,
    max_profit DECIMAL(10, 2) NOT NULL,
    max_loss DECIMAL(10, 2) NOT NULL,
    breakeven DECIMAL(10, 2) NOT NULL,
    risk_reward_ratio DECIMAL(5, 2) NOT NULL,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_trade_spreads_trade_id (trade_id)
);
```

### configuration

```sql
CREATE TABLE configuration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) NOT NULL CHECK (value_type IN ('string', 'integer', 'float', 'boolean', 'json')),
    description TEXT,
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Version tracking
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    
    UNIQUE(category, key),
    INDEX idx_category (category)
);
```

### daily_summaries

```sql
CREATE TABLE daily_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_date DATE NOT NULL UNIQUE,
    
    -- Trade Statistics
    total_trades INTEGER NOT NULL DEFAULT 0,
    winning_trades INTEGER NOT NULL DEFAULT 0,
    losing_trades INTEGER NOT NULL DEFAULT 0,
    skipped_trades INTEGER NOT NULL DEFAULT 0,
    
    -- P/L Metrics
    gross_pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    commissions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    net_pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    
    -- Cumulative Metrics
    cumulative_pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    account_value DECIMAL(10, 2),
    win_rate DECIMAL(5, 2),
    average_win DECIMAL(10, 2),
    average_loss DECIMAL(10, 2),
    
    -- Market Context
    spy_open DECIMAL(10, 2),
    spy_close DECIMAL(10, 2),
    spy_high DECIMAL(10, 2),
    spy_low DECIMAL(10, 2),
    vix_close DECIMAL(10, 2),
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_summary_date (summary_date)
);
```

## Initial Seed Data

```sql
-- Default configuration values
INSERT INTO configuration (category, key, value, value_type, description) VALUES
('risk', 'max_buying_power_percent', '5.0', 'float', 'Maximum percentage of buying power per trade'),
('risk', 'stop_loss_percent', '20.0', 'float', 'Stop loss percentage of max risk'),
('risk', 'min_risk_reward_ratio', '1.0', 'float', 'Minimum risk/reward ratio for trades'),
('sentiment', 'minimum_score', '60', 'integer', 'Minimum sentiment score to proceed'),
('alerts', 'email_enabled', 'false', 'boolean', 'Enable email notifications'),
('alerts', 'profit_target_alert', '50.0', 'float', 'Alert when profit reaches this percentage'),
('system', 'paper_trading_mode', 'true', 'boolean', 'Enable paper trading mode');
```

## Migration Notes

- All timestamps stored in UTC
- JSON columns use SQLite's JSON1 extension
- Decimal types map to REAL in SQLite but maintain precision through ORM
- Indexes created for all foreign keys and commonly queried fields
- Soft deletes implemented through status fields rather than deletion