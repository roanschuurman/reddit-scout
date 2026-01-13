"""Authentication routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.api.deps import (
    SESSION_COOKIE_NAME,
    create_session_token,
    get_current_user_optional,
)
from reddit_scout.auth import hash_password, verify_password
from reddit_scout.database import get_db
from reddit_scout.models import User

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="src/reddit_scout/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> Response:
    """Display login page."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> Response:
    """Handle login form submission."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Create session
    token = create_session_token(user.id)
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect_response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return redirect_response


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> Response:
    """Display registration page."""
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
) -> Response:
    """Handle registration form submission."""
    errors: dict[str, str] = {}

    # Validate email
    if not email or "@" not in email:
        errors["email"] = "Valid email is required"

    # Validate password
    if not password or len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"

    if password != password_confirm:
        errors["password_confirm"] = "Passwords do not match"

    # Check if email already exists
    if not errors:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            errors["email"] = "Email already registered"

    if errors:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "errors": errors, "email": email},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Create user
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()

    # Create session and redirect to dashboard
    token = create_session_token(user.id)
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect_response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return redirect_response


@router.get("/logout")
async def logout(response: Response) -> Response:
    """Log out the current user."""
    redirect_response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect_response.delete_cookie(SESSION_COOKIE_NAME)
    return redirect_response
