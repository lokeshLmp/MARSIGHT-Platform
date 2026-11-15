"""Runtime configuration read from environment variables.

No secrets are needed or read by this module. All values have safe defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

HIRISE_DTM_COLLECTION = "mro_hirise_socet_dtms"
CTX_DTM_COLLECTION = "mro_ctx_controlled_usgs_dtms"
SUPPORTED_COLLECTIONS = (HIRISE_DTM_COLLECTION, CTX_DTM_COLLECTION)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
)
DEFAULT_ASSET_HOSTS = ("astrogeo-ard.s3-us-west-2.amazonaws.com",)


def _csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.environ.get(name, "")
    values = tuple(v.strip() for v in raw.split(",") if v.strip())
    return values or default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    stac_url: str = "https://stac.astrogeology.usgs.gov/api"
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    # Remote raster reads are only allowed from these hosts (the STAC item is third-party input).
    allowed_asset_hosts: tuple[str, ...] = DEFAULT_ASSET_HOSTS
    stac_connect_timeout: float = 10.0
    stac_read_timeout: float = 20.0
    # GDAL network timeouts, and an overall wall-clock cap for one raster header read.
    raster_http_timeout: float = 20.0
    raster_total_timeout: float = 45.0
    user_agent: str = "MARSIGHT-backend/0.1 (research prototype)"
    collections: tuple[str, ...] = field(default=SUPPORTED_COLLECTIONS)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        stac_url=os.environ.get("MARSIGHT_STAC_URL", Settings.stac_url).rstrip("/"),
        cors_origins=_csv("MARSIGHT_CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        allowed_asset_hosts=_csv("MARSIGHT_ASSET_HOSTS", DEFAULT_ASSET_HOSTS),
        stac_connect_timeout=_float("MARSIGHT_STAC_CONNECT_TIMEOUT", 10.0),
        stac_read_timeout=_float("MARSIGHT_STAC_READ_TIMEOUT", 20.0),
        raster_http_timeout=_float("MARSIGHT_RASTER_HTTP_TIMEOUT", 20.0),
        raster_total_timeout=_float("MARSIGHT_RASTER_TOTAL_TIMEOUT", 45.0),
    )
