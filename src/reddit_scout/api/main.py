"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="Reddit Scout",
    description="AI-powered Reddit monitoring and engagement tool",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="src/reddit_scout/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/reddit_scout/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
