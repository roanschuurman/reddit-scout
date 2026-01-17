"""Subreddit discovery routes."""

import asyncio
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from reddit_scout.api.deps import get_current_user
from reddit_scout.database import get_db
from reddit_scout.models import Campaign, User
from reddit_scout.scanner.client import RedditClient

router = APIRouter(prefix="/api/subreddits", tags=["subreddits"])
templates = Jinja2Templates(directory="src/reddit_scout/templates")


def _get_reddit_client() -> RedditClient:
    """Get a RedditClient instance."""
    return RedditClient()


@router.get("/search", response_class=HTMLResponse)
async def search_subreddits(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str, Query(max_length=100)] = "",
    campaign_id: Annotated[int | None, Query()] = None,
) -> HTMLResponse:
    """
    Search for subreddits by keyword.

    Returns HTML partial for HTMX consumption.
    """
    # Get existing subreddits for the campaign to mark as "already added"
    existing_subreddits: set[str] = set()
    if campaign_id:
        result = await db.execute(
            select(Campaign)
            .options(selectinload(Campaign.subreddits))
            .where(
                Campaign.id == campaign_id,
                Campaign.user_id == current_user.id,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            existing_subreddits = {s.subreddit_name for s in campaign.subreddits}

    if not q.strip():
        return templates.TemplateResponse(
            "campaigns/partials/subreddit_discovery.html",
            {
                "request": request,
                "subreddits": [],
                "query": "",
                "campaign_id": campaign_id,
                "existing_subreddits": existing_subreddits,
            },
        )

    client = _get_reddit_client()

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(
            None, lambda: client.search_subreddits(q.strip(), limit=10)
        )
    except Exception:
        return templates.TemplateResponse(
            "campaigns/partials/subreddit_discovery.html",
            {
                "request": request,
                "subreddits": [],
                "query": q,
                "campaign_id": campaign_id,
                "existing_subreddits": existing_subreddits,
                "error": "Failed to search Reddit. Please try again.",
            },
        )

    return templates.TemplateResponse(
        "campaigns/partials/subreddit_discovery.html",
        {
            "request": request,
            "subreddits": results,
            "query": q,
            "campaign_id": campaign_id,
            "existing_subreddits": existing_subreddits,
        },
    )


@router.get("/{name}/info")
async def get_subreddit_info(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Get detailed information about a specific subreddit.

    Returns subreddit metadata including subscriber count, active users,
    and description.
    """
    # Clean the name (remove r/ prefix if present)
    clean_name = name.strip().lower()
    if clean_name.startswith("r/"):
        clean_name = clean_name[2:]

    client = _get_reddit_client()

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(
        None, lambda: client.get_subreddit_info(clean_name)
    )

    if info is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Subreddit not found or not accessible"},
        )

    return JSONResponse(content=asdict(info))


@router.get("/{name}/preview", response_class=HTMLResponse)
async def get_subreddit_preview(
    request: Request,
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> HTMLResponse:
    """
    Get recent posts from a subreddit for preview.

    Returns HTML partial with recent posts.
    """
    # Clean the name (remove r/ prefix if present)
    clean_name = name.strip()
    if clean_name.lower().startswith("r/"):
        clean_name = clean_name[2:]

    client = _get_reddit_client()

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    try:
        posts = await loop.run_in_executor(
            None, lambda: client.get_subreddit_preview(clean_name, limit=limit)
        )
    except Exception:
        return templates.TemplateResponse(
            "campaigns/partials/subreddit_preview.html",
            {
                "request": request,
                "subreddit_name": clean_name,
                "posts": [],
                "error": "Failed to load preview",
            },
        )

    return templates.TemplateResponse(
        "campaigns/partials/subreddit_preview.html",
        {
            "request": request,
            "subreddit_name": clean_name,
            "posts": posts,
        },
    )
