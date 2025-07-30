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
    pass


def downgrade() -> None:
    pass
