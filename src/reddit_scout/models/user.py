"""User model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reddit_scout.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User account linked to SuperTokens."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    supertokens_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="user", cascade="all, delete-orphan")
