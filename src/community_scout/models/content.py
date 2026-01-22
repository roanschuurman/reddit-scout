"""Content models for HN items, user alerts, and scanner state."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from community_scout.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from community_scout.models.discord_user import DiscordUser, SourceThread, UserKeyword


class ScannerState(Base):
    """Tracks scanner progress for each content source."""

    __tablename__ = "scanner_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    last_seen_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertStatus(str, Enum):
    """Status of a user alert."""

    PENDING = "pending"
    SENT = "sent"
    DISMISSED = "dismissed"


class HNItemType(str, Enum):
    """Type of Hacker News item."""

    STORY = "story"
    COMMENT = "comment"


class ContentSource(Base):
    """A content source (e.g., hackernews, reddit)."""

    __tablename__ = "content_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    threads: Mapped[list["SourceThread"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["UserAlert"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class HNItem(Base):
    """A Hacker News item (story or comment)."""

    __tablename__ = "hn_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    hn_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    alerts: Mapped[list["UserAlert"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    @property
    def hn_url(self) -> str:
        """Get the Hacker News URL for this item."""
        return f"https://news.ycombinator.com/item?id={self.hn_id}"


class UserAlert(Base, TimestampMixin):
    """An alert for a user about a matched content item."""

    __tablename__ = "user_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("discord_users.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("hn_items.id"), nullable=False)
    keyword_id: Mapped[int] = mapped_column(ForeignKey("user_keywords.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("content_sources.id"), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=AlertStatus.PENDING.value)
    discord_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["DiscordUser"] = relationship(back_populates="alerts")
    item: Mapped["HNItem"] = relationship(back_populates="alerts")
    keyword: Mapped["UserKeyword"] = relationship(back_populates="alerts")
    source: Mapped["ContentSource"] = relationship(back_populates="alerts")
