"""Discord user models."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from community_scout.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from community_scout.models.content import ContentSource, UserAlert


class DiscordUser(Base, TimestampMixin):
    """A Discord user with their monitoring configuration."""

    __tablename__ = "discord_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    discord_username: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    openrouter_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    keywords: Mapped[list["UserKeyword"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    source_threads: Mapped[list["SourceThread"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["UserAlert"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserKeyword(Base, TimestampMixin):
    """A keyword phrase to monitor for a user."""

    __tablename__ = "user_keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("discord_users.id"), nullable=False)
    phrase: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["DiscordUser"] = relationship(back_populates="keywords")
    alerts: Mapped[list["UserAlert"]] = relationship(
        back_populates="keyword", cascade="all, delete-orphan"
    )


class SourceThread(Base, TimestampMixin):
    """A Discord thread for a specific content source per user."""

    __tablename__ = "source_threads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("discord_users.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("content_sources.id"), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    user: Mapped["DiscordUser"] = relationship(back_populates="source_threads")
    source: Mapped["ContentSource"] = relationship(back_populates="threads")
