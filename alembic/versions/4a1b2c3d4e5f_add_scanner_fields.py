"""add_scanner_fields

Revision ID: 4a1b2c3d4e5f
Revises: 3339b5203673
Create Date: 2026-01-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '3339b5203673'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_scanned_at to campaigns and unique index on matches."""
    # Add last_scanned_at column to campaigns
    op.add_column('campaigns', sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=True))

    # Add unique index on (campaign_id, reddit_id) for deduplication
    op.create_index('ix_matches_campaign_reddit_id', 'matches', ['campaign_id', 'reddit_id'], unique=True)


def downgrade() -> None:
    """Remove scanner fields."""
    op.drop_index('ix_matches_campaign_reddit_id', table_name='matches')
    op.drop_column('campaigns', 'last_scanned_at')
