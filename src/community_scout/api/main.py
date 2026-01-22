"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="Community Scout",
    description="Discord-first community content monitoring service",
    version="0.2.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "service": "Community Scout",
        "status": "running",
        "docs": "/docs",
    }
