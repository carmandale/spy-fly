# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-07-27-polygon-api-integration-#5/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Schema Changes

### New Tables

#### market_data_cache
Stores cached API responses with TTL expiration management.

```sql
CREATE TABLE market_data_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    data_type VARCHAR(50) NOT NULL,  -- 'quote', 'options', 'historical'
    raw_data TEXT NOT NULL,          -- JSON serialized response
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    INDEX idx_cache_key (cache_key),
    INDEX idx_expires_at (expires_at),
    INDEX idx_data_type (data_type)
);
```

#### spy_quotes
Historical SPY stock quotes for analysis and fallback.

```sql
CREATE TABLE spy_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL DEFAULT 'SPY',
    price DECIMAL(10,4) NOT NULL,
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    volume INTEGER,
    timestamp DATETIME NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'polygon',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_symbol_timestamp (symbol, timestamp)
);
```

#### option_contracts
Cached option chain data for SPY 0-DTE options.

```sql
CREATE TABLE option_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,        -- Option symbol (SPY241127C00580000)
    underlying VARCHAR(10) NOT NULL DEFAULT 'SPY',
    strike DECIMAL(10,4) NOT NULL,
    option_type VARCHAR(4) NOT NULL,    -- 'call' or 'put'
    expiration_date DATE NOT NULL,
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    last_price DECIMAL(10,4),
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    timestamp DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_underlying_expiration (underlying, expiration_date),
    INDEX idx_strike_type (strike, option_type),
    INDEX idx_timestamp (timestamp),
    UNIQUE(symbol, timestamp)
);
```

#### historical_prices
Daily and intraday historical price data for technical analysis.

```sql
CREATE TABLE historical_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL DEFAULT 'SPY',
    date DATE NOT NULL,
    timeframe VARCHAR(10) NOT NULL,     -- 'daily', '1hour', '15min'
    open_price DECIMAL(10,4) NOT NULL,
    high_price DECIMAL(10,4) NOT NULL,
    low_price DECIMAL(10,4) NOT NULL,
    close_price DECIMAL(10,4) NOT NULL,
    volume INTEGER NOT NULL,
    vwap DECIMAL(10,4),                 -- Volume Weighted Average Price
    source VARCHAR(20) NOT NULL DEFAULT 'polygon',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol_date (symbol, date),
    INDEX idx_timeframe (timeframe),
    UNIQUE(symbol, date, timeframe)
);
```

#### api_requests_log
Track API usage for rate limiting and debugging.

```sql
CREATE TABLE api_requests_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL DEFAULT 'GET',
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_endpoint (endpoint),
    INDEX idx_status_code (status_code)
);
```

## Schema Modifications

No modifications to existing tables are required as this is the foundational data integration feature.

## Migration Scripts

### Migration: 001_create_market_data_tables.py

```python
"""Create market data tables for Polygon.io integration

Revision ID: 001_polygon_integration
Revises: 
Create Date: 2025-07-27
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Create market_data_cache table
    op.create_table(
        'market_data_cache',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('cache_key', sa.String(255), nullable=False, unique=True),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('raw_data', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
        sa.Column('expires_at', sa.DateTime, nullable=False),
    )
    op.create_index('idx_cache_key', 'market_data_cache', ['cache_key'])
    op.create_index('idx_expires_at', 'market_data_cache', ['expires_at'])
    op.create_index('idx_data_type', 'market_data_cache', ['data_type'])

    # Create spy_quotes table
    op.create_table(
        'spy_quotes',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(10), nullable=False, default='SPY'),
        sa.Column('price', sa.Numeric(10, 4), nullable=False),
        sa.Column('bid', sa.Numeric(10, 4)),
        sa.Column('ask', sa.Numeric(10, 4)),
        sa.Column('volume', sa.Integer),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('source', sa.String(20), nullable=False, default='polygon'),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
    )
    op.create_index('idx_timestamp', 'spy_quotes', ['timestamp'])
    op.create_index('idx_symbol_timestamp', 'spy_quotes', ['symbol', 'timestamp'])

    # Create option_contracts table
    op.create_table(
        'option_contracts',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('underlying', sa.String(10), nullable=False, default='SPY'),
        sa.Column('strike', sa.Numeric(10, 4), nullable=False),
        sa.Column('option_type', sa.String(4), nullable=False),
        sa.Column('expiration_date', sa.Date, nullable=False),
        sa.Column('bid', sa.Numeric(10, 4)),
        sa.Column('ask', sa.Numeric(10, 4)),
        sa.Column('last_price', sa.Numeric(10, 4)),
        sa.Column('volume', sa.Integer, default=0),
        sa.Column('open_interest', sa.Integer, default=0),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
    )
    op.create_index('idx_underlying_expiration', 'option_contracts', ['underlying', 'expiration_date'])
    op.create_index('idx_strike_type', 'option_contracts', ['strike', 'option_type'])
    op.create_index('idx_timestamp', 'option_contracts', ['timestamp'])
    op.create_unique_constraint('uq_symbol_timestamp', 'option_contracts', ['symbol', 'timestamp'])

    # Create historical_prices table
    op.create_table(
        'historical_prices',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('symbol', sa.String(10), nullable=False, default='SPY'),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('open_price', sa.Numeric(10, 4), nullable=False),
        sa.Column('high_price', sa.Numeric(10, 4), nullable=False),
        sa.Column('low_price', sa.Numeric(10, 4), nullable=False),
        sa.Column('close_price', sa.Numeric(10, 4), nullable=False),
        sa.Column('volume', sa.Integer, nullable=False),
        sa.Column('vwap', sa.Numeric(10, 4)),
        sa.Column('source', sa.String(20), nullable=False, default='polygon'),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
    )
    op.create_index('idx_symbol_date', 'historical_prices', ['symbol', 'date'])
    op.create_index('idx_timeframe', 'historical_prices', ['timeframe'])
    op.create_unique_constraint('uq_symbol_date_timeframe', 'historical_prices', ['symbol', 'date', 'timeframe'])

    # Create api_requests_log table
    op.create_table(
        'api_requests_log',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, default='GET'),
        sa.Column('status_code', sa.Integer),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('error_message', sa.Text),
        sa.Column('timestamp', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
    )
    op.create_index('idx_timestamp', 'api_requests_log', ['timestamp'])
    op.create_index('idx_endpoint', 'api_requests_log', ['endpoint'])
    op.create_index('idx_status_code', 'api_requests_log', ['status_code'])

def downgrade():
    op.drop_table('api_requests_log')
    op.drop_table('historical_prices')
    op.drop_table('option_contracts')
    op.drop_table('spy_quotes')
    op.drop_table('market_data_cache')
```

## Data Integrity Rules

### Constraints
- Option symbols must follow standard format (SPY + YYMMDD + C/P + strike)
- Expiration dates must be valid trading days
- Prices must be positive decimal values
- Cache expiration timestamps must be in the future when created

### Foreign Key Relationships
No foreign key relationships required for this phase as tables are primarily for caching external API data.

### Performance Considerations
- Composite indexes on frequently queried columns (symbol + timestamp)
- Automatic cleanup of expired cache entries
- Partitioning considerations for high-frequency quote data (future enhancement)

## Data Retention Policy

- **market_data_cache:** Automatic cleanup of expired entries daily
- **spy_quotes:** Retain 90 days of quotes for analysis
- **option_contracts:** Retain 30 days for backtesting
- **historical_prices:** Permanent retention (low volume)
- **api_requests_log:** Retain 30 days for debugging