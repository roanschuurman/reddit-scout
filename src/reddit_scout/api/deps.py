"""API dependencies."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.config import settings
from reddit_scout.database import get_db
from reddit_scout.models import User

# Session serializer
serializer = URLSafeTimedSerializer(settings.secret_key)
SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def create_session_token(user_id: int) -> str:
    """Create a signed session token for a user."""
    return serializer.dumps({"user_id": user_id})


def decode_session_token(token: str) -> int | None:
    """Decode a session token and return the user ID, or None if invalid."""
    try:
        data: dict[str, int] = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except BadSignature:
        return None


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> User:
    """Get the current authenticated user from session cookie."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = decode_session_token(session)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> User | None:
    """Get the current user if authenticated, or None."""
    if not session:
        return None

    user_id = decode_session_token(session)
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
