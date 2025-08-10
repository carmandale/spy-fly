"""Add position tracking tables for P/L calculation

Revision ID: b1c2d3e4f5g6
Revises: 0657ef3b88b4
Create Date: 2025-08-09 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = '0657ef3b88b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        
        # Position identification
        sa.Column('symbol', sa.String(10), nullable=False, server_default='SPY'),
        sa.Column('position_type', sa.String(20), nullable=False, server_default='bull_call_spread'),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        
        # Position details
        sa.Column('contracts', sa.Integer(), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        
        # Spread configuration
        sa.Column('long_strike', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('short_strike', sa.DECIMAL(precision=10, scale=2), nullable=False),
        
        # Entry pricing
        sa.Column('entry_long_premium', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('entry_short_premium', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('entry_net_debit', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('entry_total_cost', sa.DECIMAL(precision=12, scale=2), nullable=False),
        
        # Risk metrics (calculated at entry)
        sa.Column('max_profit', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('max_loss', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('breakeven_price', sa.DECIMAL(precision=10, scale=4), nullable=False),
        
        # Entry market conditions
        sa.Column('entry_spy_price', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('entry_vix', sa.DECIMAL(precision=6, scale=2), nullable=True),
        sa.Column('entry_sentiment_score', sa.DECIMAL(precision=4, scale=3), nullable=True),
        
        # Exit details (null for open positions)
        sa.Column('exit_date', sa.Date(), nullable=True),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_reason', sa.String(50), nullable=True),
        sa.Column('exit_long_premium', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('exit_short_premium', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('exit_net_credit', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('exit_total_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        
        # Final P/L (calculated on exit)
        sa.Column('realized_pnl', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('realized_pnl_percent', sa.DECIMAL(precision=8, scale=4), nullable=True),
        
        # Position management
        sa.Column('profit_target_percent', sa.DECIMAL(precision=6, scale=2), server_default='50.0'),
        sa.Column('stop_loss_percent', sa.DECIMAL(precision=6, scale=2), server_default='20.0'),
        
        # Metadata
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for positions table
    op.create_index('idx_position_status_date', 'positions', ['status', 'entry_date'])
    op.create_index('idx_position_expiration', 'positions', ['expiration_date'])
    op.create_index('idx_position_symbol_status', 'positions', ['symbol', 'status'])
    op.create_index('ix_positions_status', 'positions', ['status'])
    op.create_index('ix_positions_entry_date', 'positions', ['entry_date'])
    
    # Note: Check constraints removed for SQLite compatibility
    # Application-level validation will handle data integrity
    
    # Create position_pl_snapshots table
    op.create_table(
        'position_pl_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id'), nullable=False),
        
        # Snapshot timing
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('market_session', sa.String(20), nullable=False),
        
        # Market data at snapshot time
        sa.Column('spy_price', sa.DECIMAL(precision=10, scale=4), nullable=False),
        sa.Column('vix_level', sa.DECIMAL(precision=6, scale=2), nullable=True),
        
        # Current option pricing
        sa.Column('current_long_premium', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('current_short_premium', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('current_net_value', sa.DECIMAL(precision=10, scale=4), nullable=True),
        sa.Column('current_total_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        
        # P/L calculations
        sa.Column('unrealized_pnl', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('unrealized_pnl_percent', sa.DECIMAL(precision=8, scale=4), nullable=False),
        
        # Greeks and risk metrics
        sa.Column('position_delta', sa.DECIMAL(precision=8, scale=4), nullable=True),
        sa.Column('position_gamma', sa.DECIMAL(precision=8, scale=4), nullable=True),
        sa.Column('position_theta', sa.DECIMAL(precision=8, scale=4), nullable=True),
        sa.Column('position_vega', sa.DECIMAL(precision=8, scale=4), nullable=True),
        
        # Time decay calculation
        sa.Column('time_to_expiry_hours', sa.DECIMAL(precision=8, scale=2), nullable=True),
        sa.Column('daily_theta_decay', sa.DECIMAL(precision=10, scale=4), nullable=True),
        
        # Alert status
        sa.Column('alert_triggered', sa.Boolean(), server_default='false'),
        sa.Column('alert_type', sa.String(20), nullable=True),
        
        # Data source and quality
        sa.Column('data_source', sa.String(20), server_default='calculated'),
        sa.Column('calculation_method', sa.String(30), server_default='black_scholes'),
        sa.Column('data_quality_score', sa.DECIMAL(precision=4, scale=2), nullable=True),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for position_pl_snapshots table
    op.create_index('idx_snapshot_position_time', 'position_pl_snapshots', ['position_id', 'snapshot_time'])
    op.create_index('idx_snapshot_time', 'position_pl_snapshots', ['snapshot_time'])
    op.create_index('idx_snapshot_alert', 'position_pl_snapshots', ['alert_triggered', 'alert_type'])
    op.create_index('ix_position_pl_snapshots_position_id', 'position_pl_snapshots', ['position_id'])
    
    # Note: Check constraints removed for SQLite compatibility
    # Application-level validation will handle data integrity
    
    # Add unique constraint for position_pl_snapshots
    op.create_unique_constraint(
        'uq_position_snapshot_time',
        'position_pl_snapshots',
        ['position_id', 'snapshot_time']
    )
    
    # Create pl_alerts table
    op.create_table(
        'pl_alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('position_id', sa.Integer(), sa.ForeignKey('positions.id'), nullable=False),
        sa.Column('snapshot_id', sa.Integer(), sa.ForeignKey('position_pl_snapshots.id'), nullable=False),
        
        # Alert details
        sa.Column('alert_type', sa.String(20), nullable=False),
        sa.Column('alert_level', sa.String(10), nullable=False, server_default='info'),
        sa.Column('message', sa.Text(), nullable=False),
        
        # Alert conditions
        sa.Column('trigger_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        sa.Column('trigger_percent', sa.DECIMAL(precision=8, scale=4), nullable=True),
        sa.Column('threshold_value', sa.DECIMAL(precision=12, scale=2), nullable=True),
        
        # Notification status
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_method', sa.String(20), nullable=True),
        sa.Column('delivery_status', sa.String(20), server_default='pending'),
        
        # Alert metadata
        sa.Column('is_acknowledged', sa.Boolean(), server_default='false'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for pl_alerts table
    op.create_index('idx_alert_position', 'pl_alerts', ['position_id'])
    op.create_index('idx_alert_type_level', 'pl_alerts', ['alert_type', 'alert_level'])
    op.create_index('idx_alert_delivery_status', 'pl_alerts', ['delivery_status'])
    op.create_index('idx_alert_created', 'pl_alerts', ['created_at'])
    
    # Note: Check constraints removed for SQLite compatibility
    # Application-level validation will handle data integrity


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('pl_alerts')
    op.drop_table('position_pl_snapshots')
    op.drop_table('positions')
