"""FastAPI dashboard backend for the AI Content Fabric Platform."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from platform.web.routes import episodes, characters, prompts, analytics

app = FastAPI(
    title="AI Content Fabric Platform",
    description="Local platform service for content generation with scheduled tasks and trend monitoring",
    version="0.1.0",
)

# Mount API routes
app.include_router(episodes.router, prefix="/api/episodes", tags=["Episodes"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
app.include_router(prompts.router, prefix="/api/prompts", tags=["Prompts"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])

# Mount static files for frontend dashboard
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


@app.get("/api/health")
async def health_check():
    """Platform health check endpoint."""
    return {"status": "ok", "service": "ai-content-fabric"}
