"""Add spread recommendations and analysis sessions tables

Revision ID: 0657ef3b88b4
Revises: a8b280f7317d
Create Date: 2025-07-29 04:25:27.349014

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0657ef3b88b4'
down_revision: Union[str, None] = 'a8b280f7317d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create analysis_sessions table
    op.create_table(
        'analysis_sessions',
        sa.Column('id', sa.String(36), primary_key=True),  # UUID
        sa.Column('account_size', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_recommendations', sa.Integer(), nullable=False, server_default='5'),
        
        # Market conditions at time of analysis
        sa.Column('spy_price', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('vix_level', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('sentiment_score', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('market_status', sa.String(20), nullable=True),
        
        # Analysis results
        sa.Column('recommendations_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_probability', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('avg_expected_value', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('total_capital_required', sa.Numeric(precision=15, scale=2), nullable=True),
        
        # Session metadata
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 support
        sa.Column('request_format', sa.String(20), nullable=True),  # json, text, clipboard
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),  # For cache cleanup
    )
    
    # Create analysis_sessions indexes
    op.create_index('idx_session_created_at', 'analysis_sessions', ['created_at'])
    op.create_index('idx_session_expires_at', 'analysis_sessions', ['expires_at'])
    op.create_index('idx_session_account_size', 'analysis_sessions', ['account_size'])
    
    # Create spread_recommendations table
    op.create_table(
        'spread_recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('symbol', sa.String(10), nullable=False, server_default='SPY'),
        
        # Spread details
        sa.Column('long_strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('short_strike', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=False),
        
        # Pricing information
        sa.Column('long_premium', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('short_premium', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('net_debit', sa.Numeric(precision=10, scale=4), nullable=False),
        
        # Risk metrics
        sa.Column('max_risk', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('max_profit', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('risk_reward_ratio', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('breakeven_price', sa.Numeric(precision=10, scale=4), nullable=False),
        
        # Market data
        sa.Column('long_bid', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('long_ask', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('short_bid', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('short_ask', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('long_volume', sa.Integer(), nullable=False),
        sa.Column('short_volume', sa.Integer(), nullable=False),
        
        # Analysis results
        sa.Column('probability_of_profit', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('expected_value', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('sentiment_score', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('ranking_score', sa.Numeric(precision=6, scale=4), nullable=False),
        
        # Position sizing
        sa.Column('contracts_to_trade', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('buying_power_used_pct', sa.Numeric(precision=6, scale=4), nullable=False),
        
        # Metadata
        sa.Column('rank_in_session', sa.Integer(), nullable=False),
        sa.Column('account_size', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        
        # Foreign key relationship
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        
        # Check constraints (PostgreSQL style - SQLite will ignore)
        sa.CheckConstraint('long_strike < short_strike', name='chk_spread_strikes'),
        sa.CheckConstraint('net_debit > 0', name='chk_spread_net_debit'),
        sa.CheckConstraint('probability_of_profit >= 0 AND probability_of_profit <= 1', name='chk_spread_probability'),
        sa.CheckConstraint('contracts_to_trade > 0', name='chk_spread_contracts'),
    )
    
    # Create spread_recommendations indexes
    op.create_index('idx_session_id', 'spread_recommendations', ['session_id'])
    op.create_index('idx_spread_created_at', 'spread_recommendations', ['created_at'])
    op.create_index('idx_spread_ranking_score', 'spread_recommendations', ['ranking_score'])
    op.create_index('idx_spread_probability', 'spread_recommendations', ['probability_of_profit'])
    op.create_index('idx_spread_strikes', 'spread_recommendations', ['long_strike', 'short_strike'])


def downgrade() -> None:
    # Drop spread_recommendations table and its indexes
    op.drop_index('idx_spread_strikes', 'spread_recommendations')
    op.drop_index('idx_spread_probability', 'spread_recommendations')
    op.drop_index('idx_spread_ranking_score', 'spread_recommendations')
    op.drop_index('idx_spread_created_at', 'spread_recommendations')
    op.drop_index('idx_session_id', 'spread_recommendations')
    op.drop_table('spread_recommendations')
    
    # Drop analysis_sessions table and its indexes
    op.drop_index('idx_session_account_size', 'analysis_sessions')
    op.drop_index('idx_session_expires_at', 'analysis_sessions')
    op.drop_index('idx_session_created_at', 'analysis_sessions')
    op.drop_table('analysis_sessions')
