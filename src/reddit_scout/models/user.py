"""User model."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reddit_scout.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from reddit_scout.models.campaign import Campaign


class User(Base, TimestampMixin):
    """User account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Optional SuperTokens ID for future migration
    supertokens_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
