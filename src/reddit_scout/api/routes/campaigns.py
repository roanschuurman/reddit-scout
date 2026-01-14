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
from reddit_scout.models import Campaign, User

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

    return templates.TemplateResponse(
        "campaigns/edit.html",
        {
            "request": request,
            "user": current_user,
            "campaign": campaign,
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
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Update campaign
    campaign.name = name.strip()
    campaign.system_prompt = system_prompt.strip()
    campaign.is_active = is_active

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
