"""API routes."""

from reddit_scout.api.routes.auth import router as auth_router
from reddit_scout.api.routes.campaigns import router as campaigns_router

__all__ = ["auth_router", "campaigns_router"]
