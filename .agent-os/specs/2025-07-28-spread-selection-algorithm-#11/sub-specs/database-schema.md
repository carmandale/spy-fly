# Database Schema

This is the database schema implementation for the spec detailed in @.agent-os/specs/2025-07-28-spread-selection-algorithm-#11/spec.md

> Created: 2025-07-28
> Version: 1.0.0

## Schema Changes

### New Tables

#### spread_recommendations
Stores generated spread recommendations for analysis and caching purposes.

```sql
CREATE TABLE spread_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiration_date DATE NOT NULL,
    long_strike DECIMAL(8,2) NOT NULL,
    short_strike DECIMAL(8,2) NOT NULL,
    long_premium DECIMAL(6,4) NOT NULL,
    short_premium DECIMAL(6,4) NOT NULL,
    net_debit DECIMAL(6,4) NOT NULL,
    max_profit DECIMAL(6,4) NOT NULL,
    max_loss DECIMAL(6,4) NOT NULL,
    risk_reward_ratio DECIMAL(6,4) NOT NULL,
    probability_of_profit DECIMAL(5,4) NOT NULL,
    expected_value DECIMAL(6,4) NOT NULL,
    breakeven_price DECIMAL(8,2) NOT NULL,
    sentiment_score DECIMAL(5,4),
    sentiment_weight DECIMAL(5,4),
    spy_price_at_analysis DECIMAL(8,2) NOT NULL,
    vix_level_at_analysis DECIMAL(6,2),
    rank_position INTEGER,
    analysis_session_id VARCHAR(50),
    
    -- Indexes
    INDEX idx_expiration_date (expiration_date),
    INDEX idx_created_at (created_at),
    INDEX idx_analysis_session (analysis_session_id),
    INDEX idx_rank (rank_position)
);
```

#### spread_analysis_sessions  
Tracks each complete analysis run for performance monitoring and debugging.

```sql
CREATE TABLE spread_analysis_sessions (
    id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiration_date DATE NOT NULL,
    spy_price DECIMAL(8,2) NOT NULL,
    vix_level DECIMAL(6,2),
    sentiment_score DECIMAL(5,4),
    account_size DECIMAL(12,2),
    max_risk_percent DECIMAL(5,2),
    min_risk_reward_ratio DECIMAL(6,4),
    total_options_analyzed INTEGER,
    total_spreads_generated INTEGER,
    total_spreads_filtered INTEGER,
    recommendations_count INTEGER,
    processing_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Indexes
    INDEX idx_created_at (created_at),
    INDEX idx_expiration_date (expiration_date),
    INDEX idx_success (success)
);
```

### New Columns

#### options_data (existing table modifications)
Add columns to support spread analysis calculations.

```sql
-- Add new columns to existing options_data table
ALTER TABLE options_data ADD COLUMN delta DECIMAL(6,4);
ALTER TABLE options_data ADD COLUMN gamma DECIMAL(6,4);  
ALTER TABLE options_data ADD COLUMN theta DECIMAL(6,4);
ALTER TABLE options_data ADD COLUMN vega DECIMAL(6,4);
ALTER TABLE options_data ADD COLUMN implied_volatility DECIMAL(6,4);

-- Add index for faster strike price filtering
CREATE INDEX idx_options_strike_exp ON options_data (underlying_symbol, expiration_date, strike_price);
```

### Migration Scripts

#### Migration: Add Spread Analysis Tables

```python
"""Add spread analysis tables

Revision ID: spread_analysis_v1
Revises: a8b280f7317d
Create Date: 2025-07-28 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = 'spread_analysis_v1'
down_revision = 'a8b280f7317d'
branch_labels = None
depends_on = None

def upgrade():
    # Create spread_recommendations table
    op.create_table(
        'spread_recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('expiration_date', sa.DATE(), nullable=False),
        sa.Column('long_strike', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('short_strike', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('long_premium', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('short_premium', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('net_debit', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('max_profit', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('max_loss', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('risk_reward_ratio', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('probability_of_profit', sa.DECIMAL(precision=5, scale=4), nullable=False),
        sa.Column('expected_value', sa.DECIMAL(precision=6, scale=4), nullable=False),
        sa.Column('breakeven_price', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('sentiment_score', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('sentiment_weight', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('spy_price_at_analysis', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('vix_level_at_analysis', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('rank_position', sa.Integer(), nullable=True),
        sa.Column('analysis_session_id', sa.VARCHAR(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_expiration_date', 'spread_recommendations', ['expiration_date'])
    op.create_index('idx_created_at', 'spread_recommendations', ['created_at'])
    op.create_index('idx_analysis_session', 'spread_recommendations', ['analysis_session_id'])
    op.create_index('idx_rank', 'spread_recommendations', ['rank_position'])
    
    # Create spread_analysis_sessions table
    op.create_table(
        'spread_analysis_sessions',
        sa.Column('id', sa.VARCHAR(length=50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('expiration_date', sa.DATE(), nullable=False),
        sa.Column('spy_price', sa.DECIMAL(precision=8, scale=2), nullable=False),
        sa.Column('vix_level', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('sentiment_score', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('account_size', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('max_risk_percent', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('min_risk_reward_ratio', sa.DECIMAL(precision=6, scale=4), nullable=True),
        sa.Column('total_options_analyzed', sa.Integer(), nullable=True),
        sa.Column('total_spreads_generated', sa.Integer(), nullable=True),
        sa.Column('total_spreads_filtered', sa.Integer(), nullable=True),
        sa.Column('recommendations_count', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), server_default=sa.text('1'), nullable=True),
        sa.Column('error_message', sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for sessions table
    op.create_index('idx_created_at_sessions', 'spread_analysis_sessions', ['created_at'])
    op.create_index('idx_expiration_date_sessions', 'spread_analysis_sessions', ['expiration_date'])
    op.create_index('idx_success', 'spread_analysis_sessions', ['success'])
    
    # Add new columns to existing options_data table
    op.add_column('options_data', sa.Column('delta', sa.DECIMAL(precision=6, scale=4), nullable=True))
    op.add_column('options_data', sa.Column('gamma', sa.DECIMAL(precision=6, scale=4), nullable=True))
    op.add_column('options_data', sa.Column('theta', sa.DECIMAL(precision=6, scale=4), nullable=True))
    op.add_column('options_data', sa.Column('vega', sa.DECIMAL(precision=6, scale=4), nullable=True))
    op.add_column('options_data', sa.Column('implied_volatility', sa.DECIMAL(precision=6, scale=4), nullable=True))
    
    # Add composite index for faster queries
    op.create_index('idx_options_strike_exp', 'options_data', ['underlying_symbol', 'expiration_date', 'strike_price'])

def downgrade():
    # Drop new tables
    op.drop_table('spread_analysis_sessions')
    op.drop_table('spread_recommendations')
    
    # Remove added columns
    op.drop_column('options_data', 'implied_volatility')
    op.drop_column('options_data', 'vega')
    op.drop_column('options_data', 'theta')
    op.drop_column('options_data', 'gamma')
    op.drop_column('options_data', 'delta')
    
    # Drop added index
    op.drop_index('idx_options_strike_exp', table_name='options_data')
```

## Rationale

### Spread Recommendations Table
- **Purpose**: Cache generated recommendations to avoid recalculating identical spreads and enable performance analysis
- **Key Fields**: Complete spread metrics needed for ranking and display, plus context data for debugging
- **Performance**: Indexed by expiration date and creation time for fast retrieval of recent recommendations

### Analysis Sessions Table  
- **Purpose**: Track each complete analysis run to monitor performance, identify bottlenecks, and debug issues
- **Metrics**: Processing time, number of options analyzed, success/failure rates
- **Debugging**: Error messages and context for failed analysis runs

### Options Data Enhancements
- **Greeks Addition**: Delta, gamma, theta, vega for advanced analysis in future phases
- **Implied Volatility**: Alternative to VIX-based volatility for more precise calculations
- **Performance Index**: Composite index on symbol/expiration/strike for faster spread generation queries