"""Add scanner_state table.

Revision ID: 002_scanner_state
Revises: 001_initial
Create Date: 2026-01-22

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_scanner_state"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scanner_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("last_seen_id", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_scan_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name"),
    )


def downgrade() -> None:
    op.drop_table("scanner_state")
