"""Match and content summary models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reddit_scout.models.base import Base

if TYPE_CHECKING:
    from reddit_scout.models.campaign import Campaign


class MatchStatus(str, Enum):
    """Status of a match."""

    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"


class RedditType(str, Enum):
    """Type of Reddit content."""

    POST = "post"
    COMMENT = "comment"


class Match(Base):
    """A matched Reddit post or comment."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    reddit_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reddit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subreddit: Mapped[str] = mapped_column(String(255), nullable=False)
    matched_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    permalink: Mapped[str] = mapped_column(String(512), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), default=MatchStatus.PENDING.value)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discord_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="matches")
    draft_responses: Mapped[list["DraftResponse"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class DraftResponse(Base):
    """An AI-generated content summary for a match."""

    __tablename__ = "draft_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="draft_responses")
