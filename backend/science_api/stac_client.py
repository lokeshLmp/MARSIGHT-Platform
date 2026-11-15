"""Small synchronous client for the USGS Astrogeology STAC API.

Only the two calls MARSIGHT needs are implemented. Network failures are converted into
StacUnavailable so routes can degrade gracefully.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

import httpx

from .config import Settings


class StacUnavailable(Exception):
    """The STAC service could not be reached or returned an unusable response."""


class StacClient:
    def __init__(self, settings: Settings, client: Optional[httpx.Client] = None):
        self.base_url = settings.stac_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(settings.stac_read_timeout, connect=settings.stac_connect_timeout),
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def item_url(self, collection: str, item_id: str) -> str:
        return f"{self.base_url}/collections/{quote(collection, safe='')}/items/{quote(item_id, safe='')}"

    def _get_json(self, url: str, params: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise StacUnavailable("STAC request timed out") from exc
        except httpx.HTTPError as exc:
            raise StacUnavailable(f"STAC request failed ({type(exc).__name__})") from exc
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise StacUnavailable(f"STAC returned HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise StacUnavailable("STAC returned a non-JSON response") from exc
        if not isinstance(data, dict):
            raise StacUnavailable("STAC returned an unexpected JSON shape")
        return data

    def search(self, collection: str, bbox: list[float], limit: int) -> dict[str, Any]:
        """Bounding-box search in one collection. Returns the STAC FeatureCollection."""
        data = self._get_json(
            f"{self.base_url}/search",
            params={"collections": collection, "bbox": ",".join(f"{v:g}" for v in bbox), "limit": limit},
        )
        if data is None or "features" not in data:
            raise StacUnavailable("STAC search returned no feature list")
        return data

    def get_item(self, collection: str, item_id: str) -> Optional[dict[str, Any]]:
        """Fetch one item, or None if it does not exist in that collection."""
        return self._get_json(self.item_url(collection, item_id))
