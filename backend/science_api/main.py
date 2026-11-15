"""MARSIGHT scientific backend application.

Start the integrated platform API from the repository root:
    .\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .routers import close_stac_client, router
from .terrain_routes import router as terrain_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    close_stac_client()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="MARSIGHT scientific backend",
        version=__version__,
        description=(
            "Dataset discovery and raster metadata for Mars DTMs from the USGS Astrogeology STAC. "
            "Experimental research prototype: no response is validated for mission or safety use."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(terrain_router)
    return app


app = create_app()
