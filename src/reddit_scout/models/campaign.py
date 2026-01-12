"""Campaign models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reddit_scout.models.base import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    """A monitoring campaign for a product."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    scan_frequency_minutes: Mapped[int] = mapped_column(Integer, default=60)
    discord_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="campaigns")
    subreddits: Mapped[list["CampaignSubreddit"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    keywords: Mapped[list["CampaignKeyword"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignSubreddit(Base):
    """A subreddit to monitor for a campaign."""

    __tablename__ = "campaign_subreddits"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    subreddit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="subreddits")


class CampaignKeyword(Base):
    """A keyword phrase to match for a campaign."""

    __tablename__ = "campaign_keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    phrase: Mapped[str] = mapped_column(String(255), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign: Mapped["Campaign"] = relationship(back_populates="keywords")
