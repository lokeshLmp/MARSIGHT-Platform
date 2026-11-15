"""Header-only reads of remote Cloud Optimized GeoTIFFs.

Only the file header (and a few small range requests GDAL needs for it) is read. No pixel values are
decoded, and nothing is downloaded in full. rasterio is imported lazily so the API starts without it
and tests can substitute a fake reader.
"""

from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Callable
from urllib.parse import urlparse

from .config import Settings

RasterReader = Callable[[str], dict[str, Any]]


class RasterUnavailable(Exception):
    """The remote raster could not be opened (network, format or timeout)."""

    def __init__(self, message: str, timeout: bool = False):
        super().__init__(message)
        self.timeout = timeout


class AssetHostNotAllowed(Exception):
    """The asset URL is not https on an allow-listed host."""


def check_asset_url(url: str, settings: Settings) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {h.lower() for h in settings.allowed_asset_hosts}:
        raise AssetHostNotAllowed(f"Asset host '{parsed.hostname}' is not on the allow-list")


_NAME_RE = re.compile(r'^\s*(?:PROJCRS|PROJCS|GEOGCRS|GEOGCS|GEODCRS)\["([^"]+)"')


def _finite_or_none(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_raster_metadata_sync(url: str, settings: Settings) -> dict[str, Any]:
    """Open `url` via GDAL /vsicurl/ and return plain-Python header facts."""
    import rasterio  # lazy

    options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
        "GDAL_HTTP_TIMEOUT": str(int(settings.raster_http_timeout)),
        "GDAL_HTTP_CONNECTTIMEOUT": "10",
        "GDAL_HTTP_MAX_RETRY": "2",
        "GDAL_HTTP_RETRY_DELAY": "1",
    }
    try:
        with rasterio.Env(**options):
            with rasterio.open("/vsicurl/" + url) as ds:
                crs = ds.crs
                wkt = crs.to_wkt() if crs else None
                match = _NAME_RE.match(wkt) if wkt else None
                try:
                    epsg = crs.to_epsg() if crs else None
                except Exception:  # noqa: BLE001 - pyproj/GDAL can raise for IAU CRSs
                    epsg = None
                try:
                    compression = ds.compression.value if ds.compression else None
                except Exception:  # noqa: BLE001
                    compression = None
                units = tuple(u or None for u in (ds.units or ()))
                block = ds.block_shapes[0] if ds.block_shapes else None
                return {
                    "driver": ds.driver,
                    "width": ds.width,
                    "height": ds.height,
                    "band_count": ds.count,
                    "dtype": ds.dtypes[0],
                    "crs_name": match.group(1) if match else None,
                    "crs_wkt": wkt,
                    "crs_epsg": epsg,
                    "crs_linear_unit": getattr(crs, "linear_units", None) if crs else None,
                    "crs_is_projected": bool(crs.is_projected) if crs else None,
                    "res": [float(ds.res[0]), float(ds.res[1])],
                    "bounds": [float(v) for v in ds.bounds],
                    "nodata": _finite_or_none(ds.nodata),
                    "units": list(units),
                    "tiled": bool(ds.profile.get("tiled")) if ds.profile else None,
                    "block_size": [int(block[0]), int(block[1])] if block else None,
                    "overview_count": len(ds.overviews(1)),
                    "compression": compression,
                }
    except RasterUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - convert every GDAL/rasterio failure
        raise RasterUnavailable(f"Could not read raster header ({type(exc).__name__})") from exc


def make_reader(settings: Settings) -> RasterReader:
    """Reader with a wall-clock cap. The worker thread cannot be killed, but the request returns."""

    def read(url: str) -> dict[str, Any]:
        check_asset_url(url, settings)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="raster-header")
        future = executor.submit(read_raster_metadata_sync, url, settings)
        try:
            return future.result(timeout=settings.raster_total_timeout)
        except FutureTimeout as exc:
            raise RasterUnavailable("Raster header read timed out", timeout=True) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    return read
