"""Initial schema for Community Scout.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-22

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create discord_users table
    op.create_table(
        "discord_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("discord_id", sa.String(255), nullable=False),
        sa.Column("discord_username", sa.String(255), nullable=False),
        sa.Column("channel_id", sa.String(255), nullable=False),
        sa.Column("openrouter_api_key", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discord_id"),
    )
    op.create_index("ix_discord_users_discord_id", "discord_users", ["discord_id"])

    # Create content_sources table
    op.create_table(
        "content_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Insert default content source: hackernews
    op.execute(
        "INSERT INTO content_sources (name, is_active) VALUES ('hackernews', true)"
    )

    # Create user_keywords table
    op.create_table(
        "user_keywords",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("phrase", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["discord_users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_keywords_user_id", "user_keywords", ["user_id"])

    # Create source_threads table
    op.create_table(
        "source_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["discord_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_source_threads_user_id", "source_threads", ["user_id"])

    # Create hn_items table
    op.create_table(
        "hn_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hn_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hn_id"),
    )
    op.create_index("ix_hn_items_hn_id", "hn_items", ["hn_id"])

    # Create user_alerts table
    op.create_table(
        "user_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("discord_message_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["discord_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["hn_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["keyword_id"], ["user_keywords.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_alerts_user_id", "user_alerts", ["user_id"])
    op.create_index("ix_user_alerts_status", "user_alerts", ["status"])


def downgrade() -> None:
    op.drop_table("user_alerts")
    op.drop_table("hn_items")
    op.drop_table("source_threads")
    op.drop_table("user_keywords")
    op.drop_table("content_sources")
    op.drop_table("discord_users")
