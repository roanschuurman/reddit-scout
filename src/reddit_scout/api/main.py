"""FastAPI application entry point."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from reddit_scout.api.deps import get_current_user, get_current_user_optional
from reddit_scout.api.routes import auth_router
from reddit_scout.models import User

app = FastAPI(
    title="Reddit Scout",
    description="AI-powered Reddit monitoring and engagement tool",
    version="0.1.0",
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    """Redirect to login for 401 errors on HTML pages."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Check if this is an HTML request (not API)
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    raise exc

# Mount static files
app.mount("/static", StaticFiles(directory="src/reddit_scout/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/reddit_scout/templates")

# Include routers
app.include_router(auth_router)


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user_optional)],
) -> HTMLResponse:
    """Home page."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "user": current_user}
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> HTMLResponse:
    """Dashboard page (requires authentication)."""
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": current_user}
    )


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
