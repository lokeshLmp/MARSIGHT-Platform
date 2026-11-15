"""Platform FastAPI application combining service health, STAC metadata and terrain APIs.

No AI provider SDK or paid service is used. Raster paths are configured server-side.
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings

try:  # repository-root invocation: uvicorn backend.app.main:app
    from backend.science_api.routers import close_stac_client, router as research_router
    from backend.science_api.terrain_routes import router as terrain_router
except ModuleNotFoundError as exc:  # legacy invocation from backend/: uvicorn app.main:app
    if exc.name not in {"backend", "backend.science_api"}:
        raise
    from science_api.routers import close_stac_client, router as research_router
    from science_api.terrain_routes import router as terrain_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_):
    yield
    close_stac_client()

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=[],
)


class AiStatus(BaseModel):
    enabled: bool
    provider_requests_enabled: bool
    project_cap_usd: int


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    ai: AiStatus


@app.get("/health", response_model=HealthResponse, tags=["service"])
def health() -> HealthResponse:
    """Return local service status without contacting external providers."""
    return HealthResponse(
        status="ok",
        service="marsight-api",
        version=settings.app_version,
        ai=AiStatus(
            enabled=False,
            provider_requests_enabled=False,
            project_cap_usd=settings.claude_project_cap_usd,
        ),
    )


# Keep the platform health contract above, and add the existing STAC/header API
# plus versioned raster processing behind the same configurable service origin.
compatible_routes = APIRouter()
compatible_routes.routes.extend(route for route in research_router.routes if getattr(route, "path", None) != "/health")
app.include_router(compatible_routes)
app.include_router(terrain_router)
