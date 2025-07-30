"""add_position_and_snapshot_tables_for_pl_tracking

Revision ID: 34c03e3992ef
Revises: 0657ef3b88b4
Create Date: 2025-07-30 08:18:40.316173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34c03e3992ef'
down_revision: Union[str, None] = '0657ef3b88b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False, server_default='SPY'),
        sa.Column('long_strike', sa.Numeric(10, 2), nullable=False),
        sa.Column('short_strike', sa.Numeric(10, 2), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('max_risk', sa.Numeric(10, 2), nullable=False),
        sa.Column('max_profit', sa.Numeric(10, 2), nullable=False),
        sa.Column('breakeven_price', sa.Numeric(10, 4), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('opened_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('latest_value', sa.Numeric(10, 2), nullable=True),
        sa.Column('latest_unrealized_pl', sa.Numeric(10, 2), nullable=True),
        sa.Column('latest_unrealized_pl_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('latest_update_time', sa.DateTime(), nullable=True),
        sa.Column('stop_loss_alert_active', sa.Boolean(), server_default='false'),
        sa.Column('stop_loss_alert_time', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for positions table
    op.create_index('idx_position_status', 'positions', ['status'])
    op.create_index('idx_position_symbol', 'positions', ['symbol'])
    op.create_index('idx_position_expiration', 'positions', ['expiration_date'])
    op.create_index('idx_position_opened_at', 'positions', ['opened_at'])
    
    # Create position_snapshots table
    op.create_table(
        'position_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_time', sa.DateTime(), nullable=False),
        sa.Column('spy_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('current_value', sa.Numeric(10, 2), nullable=False),
        sa.Column('unrealized_pl', sa.Numeric(10, 2), nullable=False),
        sa.Column('unrealized_pl_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('long_call_bid', sa.Numeric(10, 2), nullable=True),
        sa.Column('long_call_ask', sa.Numeric(10, 2), nullable=True),
        sa.Column('short_call_bid', sa.Numeric(10, 2), nullable=True),
        sa.Column('short_call_ask', sa.Numeric(10, 2), nullable=True),
        sa.Column('risk_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('stop_loss_triggered', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for position_snapshots table
    op.create_index('idx_position_time', 'position_snapshots', ['position_id', 'snapshot_time'])
    op.create_index('idx_snapshot_time', 'position_snapshots', ['snapshot_time'])


def downgrade() -> None:
    # Drop position_snapshots table and indexes
    op.drop_index('idx_snapshot_time', 'position_snapshots')
    op.drop_index('idx_position_time', 'position_snapshots')
    op.drop_table('position_snapshots')
    
    # Drop positions table and indexes
    op.drop_index('idx_position_opened_at', 'positions')
    op.drop_index('idx_position_expiration', 'positions')
    op.drop_index('idx_position_symbol', 'positions')
    op.drop_index('idx_position_status', 'positions')
    op.drop_table('positions')
