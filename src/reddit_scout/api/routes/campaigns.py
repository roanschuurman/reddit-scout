"""Campaign routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from reddit_scout.api.deps import get_current_user
from reddit_scout.database import get_db
from reddit_scout.models import Campaign, CampaignKeyword, CampaignSubreddit, User

# Scan frequency options (display label -> minutes)
SCAN_FREQUENCY_OPTIONS = [
    (720, "2x per day"),
    (1440, "1x per day"),
    (60, "1x per hour"),
    (30, "2x per hour"),
]

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
templates = Jinja2Templates(directory="src/reddit_scout/templates")


@router.get("", response_class=HTMLResponse)
async def list_campaigns(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> HTMLResponse:
    """List all campaigns for the current user."""
    result = await db.execute(
        select(Campaign)
        .where(Campaign.user_id == current_user.id)
        .order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    return templates.TemplateResponse(
        "campaigns/list.html",
        {"request": request, "user": current_user, "campaigns": campaigns},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_campaign_form(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> HTMLResponse:
    """Display new campaign form."""
    return templates.TemplateResponse(
        "campaigns/new.html",
        {"request": request, "user": current_user},
    )


@router.post("", response_class=HTMLResponse)
async def create_campaign(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Form()] = "",
    system_prompt: Annotated[str, Form()] = "",
    is_active: Annotated[bool, Form()] = True,
) -> Response:
    """Create a new campaign."""
    errors: dict[str, str] = {}

    # Validate name
    if not name or not name.strip():
        errors["name"] = "Campaign name is required"
    elif len(name) > 255:
        errors["name"] = "Campaign name must be 255 characters or less"

    # Validate system prompt
    if not system_prompt or not system_prompt.strip():
        errors["system_prompt"] = "System prompt is required"

    if errors:
        return templates.TemplateResponse(
            "campaigns/new.html",
            {
                "request": request,
                "user": current_user,
                "errors": errors,
                "name": name,
                "system_prompt": system_prompt,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Create campaign
    campaign = Campaign(
        user_id=current_user.id,
        name=name.strip(),
        system_prompt=system_prompt.strip(),
        is_active=is_active,
    )
    db.add(campaign)
    await db.flush()

    # Redirect to campaign detail with success message
    return RedirectResponse(
        url=f"/campaigns/{campaign.id}?created=1",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/{campaign_id}", response_class=HTMLResponse)
async def view_campaign(
    request: Request,
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    created: int = 0,
    updated: int = 0,
) -> Response:
    """View campaign details."""
    result = await db.execute(
        select(Campaign)
        .options(
            selectinload(Campaign.subreddits),
            selectinload(Campaign.keywords),
        )
        .where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()

    if campaign is None:
        return RedirectResponse(
            url="/campaigns",
            status_code=status.HTTP_302_FOUND,
        )

    return templates.TemplateResponse(
        "campaigns/detail.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign,
            "scan_frequency_options": SCAN_FREQUENCY_OPTIONS,
            "flash_success": "Campaign created successfully!" if created else (
                "Campaign updated successfully!" if updated else None
            ),
        },
    )


@router.get("/{campaign_id}/edit", response_class=HTMLResponse)
async def edit_campaign_form(
    request: Request,
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Display edit campaign form."""
    result = await db.execute(
        select(Campaign)
        .options(
            selectinload(Campaign.subreddits),
            selectinload(Campaign.keywords),
        )
        .where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()

    if campaign is None:
        return RedirectResponse(
            url="/campaigns",
            status_code=status.HTTP_302_FOUND,
        )

    return templates.TemplateResponse(
        "campaigns/edit.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign,
            "scan_frequency_options": SCAN_FREQUENCY_OPTIONS,
        },
    )


@router.post("/{campaign_id}", response_class=HTMLResponse)
async def update_campaign(
    request: Request,
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Form()] = "",
    system_prompt: Annotated[str, Form()] = "",
    is_active: Annotated[bool, Form()] = False,
    scan_frequency_minutes: Annotated[int, Form()] = 60,
    discord_channel_id: Annotated[str, Form()] = "",
) -> Response:
    """Update a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()

    if campaign is None:
        return RedirectResponse(
            url="/campaigns",
            status_code=status.HTTP_302_FOUND,
        )

    errors: dict[str, str] = {}

    # Validate name
    if not name or not name.strip():
        errors["name"] = "Campaign name is required"
    elif len(name) > 255:
        errors["name"] = "Campaign name must be 255 characters or less"

    # Validate system prompt
    if not system_prompt or not system_prompt.strip():
        errors["system_prompt"] = "System prompt is required"

    # Validate scan frequency
    valid_frequencies = [opt[0] for opt in SCAN_FREQUENCY_OPTIONS]
    if scan_frequency_minutes not in valid_frequencies:
        errors["scan_frequency_minutes"] = "Invalid scan frequency"

    if errors:
        return templates.TemplateResponse(
            "campaigns/edit.html",
            {
                "request": request,
                "user": current_user,
                "campaign": campaign,
                "errors": errors,
                "name": name,
                "system_prompt": system_prompt,
                "scan_frequency_options": SCAN_FREQUENCY_OPTIONS,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Update campaign
    campaign.name = name.strip()
    campaign.system_prompt = system_prompt.strip()
    campaign.is_active = is_active
    campaign.scan_frequency_minutes = scan_frequency_minutes
    campaign.discord_channel_id = discord_channel_id.strip() or None

    return RedirectResponse(
        url=f"/campaigns/{campaign.id}?updated=1",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/{campaign_id}/delete", response_class=HTMLResponse)
async def delete_campaign(
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete a campaign."""
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
        )
    )
    campaign = result.scalar_one_or_none()

    if campaign is not None:
        await db.delete(campaign)

    return RedirectResponse(
        url="/campaigns?deleted=1",
        status_code=status.HTTP_302_FOUND,
    )


# --- Subreddit Management ---


async def _get_campaign_for_user(
    campaign_id: int,
    user_id: int,
    db: AsyncSession,
) -> Campaign | None:
    """Helper to get a campaign owned by the user."""
    result = await db.execute(
        select(Campaign)
        .options(
            selectinload(Campaign.subreddits),
            selectinload(Campaign.keywords),
        )
        .where(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


@router.post("/{campaign_id}/subreddits", response_class=HTMLResponse)
async def add_subreddit(
    request: Request,
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    subreddit_name: Annotated[str, Form()] = "",
) -> Response:
    """Add a subreddit to a campaign."""
    campaign = await _get_campaign_for_user(campaign_id, current_user.id, db)

    if campaign is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Clean and validate subreddit name
    name = subreddit_name.strip().lower()
    # Remove r/ prefix if present
    if name.startswith("r/"):
        name = name[2:]

    error = None
    if not name:
        error = "Subreddit name is required"
    elif len(name) > 255:
        error = "Subreddit name too long"
    elif not name.replace("_", "").isalnum():
        error = "Invalid subreddit name"
    elif any(s.subreddit_name == name for s in campaign.subreddits):
        error = "Subreddit already added"

    if error:
        return templates.TemplateResponse(
            "campaigns/partials/subreddit_list.html",
            {
                "request": request,
                "campaign": campaign,
                "error": error,
            },
        )

    # Add subreddit
    subreddit = CampaignSubreddit(campaign_id=campaign.id, subreddit_name=name)
    db.add(subreddit)
    await db.flush()
    await db.refresh(campaign)

    return templates.TemplateResponse(
        "campaigns/partials/subreddit_list.html",
        {"request": request, "campaign": campaign},
    )


@router.delete("/{campaign_id}/subreddits/{subreddit_id}", response_class=HTMLResponse)
async def remove_subreddit(
    request: Request,
    campaign_id: int,
    subreddit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Remove a subreddit from a campaign."""
    campaign = await _get_campaign_for_user(campaign_id, current_user.id, db)

    if campaign is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Find and delete the subreddit
    result = await db.execute(
        select(CampaignSubreddit).where(
            CampaignSubreddit.id == subreddit_id,
            CampaignSubreddit.campaign_id == campaign_id,
        )
    )
    subreddit = result.scalar_one_or_none()

    if subreddit:
        await db.delete(subreddit)
        await db.flush()
        await db.refresh(campaign)

    return templates.TemplateResponse(
        "campaigns/partials/subreddit_list.html",
        {"request": request, "campaign": campaign},
    )


# --- Keyword Management ---


@router.post("/{campaign_id}/keywords", response_class=HTMLResponse)
async def add_keyword(
    request: Request,
    campaign_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    phrase: Annotated[str, Form()] = "",
) -> Response:
    """Add a keyword to a campaign."""
    campaign = await _get_campaign_for_user(campaign_id, current_user.id, db)

    if campaign is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Clean and validate keyword
    keyword = phrase.strip().lower()

    error = None
    if not keyword:
        error = "Keyword is required"
    elif len(keyword) > 255:
        error = "Keyword too long"
    elif any(k.phrase == keyword for k in campaign.keywords):
        error = "Keyword already added"

    if error:
        return templates.TemplateResponse(
            "campaigns/partials/keyword_list.html",
            {
                "request": request,
                "campaign": campaign,
                "error": error,
            },
        )

    # Add keyword
    kw = CampaignKeyword(campaign_id=campaign.id, phrase=keyword)
    db.add(kw)
    await db.flush()
    await db.refresh(campaign)

    return templates.TemplateResponse(
        "campaigns/partials/keyword_list.html",
        {"request": request, "campaign": campaign},
    )


@router.delete("/{campaign_id}/keywords/{keyword_id}", response_class=HTMLResponse)
async def remove_keyword(
    request: Request,
    campaign_id: int,
    keyword_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Remove a keyword from a campaign."""
    campaign = await _get_campaign_for_user(campaign_id, current_user.id, db)

    if campaign is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    # Find and delete the keyword
    result = await db.execute(
        select(CampaignKeyword).where(
            CampaignKeyword.id == keyword_id,
            CampaignKeyword.campaign_id == campaign_id,
        )
    )
    keyword = result.scalar_one_or_none()

    if keyword:
        await db.delete(keyword)
        await db.flush()
        await db.refresh(campaign)

    return templates.TemplateResponse(
        "campaigns/partials/keyword_list.html",
        {"request": request, "campaign": campaign},
    )
