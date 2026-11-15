"""HTTP endpoints."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from . import __version__
from .config import CTX_DTM_COLLECTION, HIRISE_DTM_COLLECTION, SUPPORTED_COLLECTIONS, Settings, get_settings
from .models import (
    CollectionStatus,
    DatasetQuery,
    DatasetsResponse,
    DtmMetadataResponse,
    ErrorResponse,
    HealthResponse,
    Provenance,
)
from .provenance import SOURCE_ORG, STAC_DOCS, discovery_units, now_utc
from .raster_meta import AssetHostNotAllowed, RasterReader, RasterUnavailable, make_reader
from .services import build_dtm_metadata, find_dtm_asset, to_asset_infos, to_dataset_item
from .stac_client import StacClient, StacUnavailable

router = APIRouter()

CollectionChoice = Literal["all", "hirise_dtm", "ctx_dtm"]
_COLLECTION_BY_CHOICE = {"hirise_dtm": (HIRISE_DTM_COLLECTION,), "ctx_dtm": (CTX_DTM_COLLECTION,), "all": SUPPORTED_COLLECTIONS}
_ITEM_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,159}$")

_stac_singleton: dict[str, StacClient] = {}


def get_stac_client(settings: Settings = Depends(get_settings)) -> StacClient:
    if "client" not in _stac_singleton:
        _stac_singleton["client"] = StacClient(settings)
    return _stac_singleton["client"]


def get_raster_reader(settings: Settings = Depends(get_settings)) -> RasterReader:
    return make_reader(settings)


def close_stac_client() -> None:
    client = _stac_singleton.pop("client", None)
    if client:
        client.close()


def parse_bbox(bbox: Annotated[str, Query(description="minLon,minLat,maxLon,maxLat in degrees (east-positive, -180..180).")]) -> list[float]:
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(422, "bbox must have exactly four comma-separated numbers: minLon,minLat,maxLon,maxLat")
    try:
        values = [float(p) for p in parts]
    except ValueError:
        raise HTTPException(422, "bbox values must be numbers") from None
    min_lon, min_lat, max_lon, max_lat = values
    if any(v != v or v in (float("inf"), float("-inf")) for v in values):
        raise HTTPException(422, "bbox values must be finite")
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise HTTPException(422, "longitudes must be within -180..180 (east-positive)")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise HTTPException(422, "latitudes must be within -90..90")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(422, "bbox must satisfy minLon < maxLon and minLat < maxLat (boxes crossing the antimeridian are not supported)")
    return values


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="marsight-backend", version=__version__, time=now_utc())


@router.get(
    "/datasets",
    response_model=DatasetsResponse,
    responses={503: {"model": ErrorResponse}},
    tags=["datasets"],
    summary="Discover DTM products intersecting a bounding box",
)
def list_datasets(
    bbox: Annotated[list[float], Depends(parse_bbox)],
    collection: Annotated[CollectionChoice, Query(description="Which DTM collection(s) to search.")] = "all",
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum items returned per collection.")] = 10,
    stac: StacClient = Depends(get_stac_client),
) -> DatasetsResponse:
    retrieved_at = now_utc()
    collections = _COLLECTION_BY_CHOICE[collection]
    statuses: list[CollectionStatus] = []
    items = []
    for cid in collections:
        try:
            result = stac.search(cid, bbox, limit)
        except StacUnavailable as exc:
            statuses.append(CollectionStatus(collection=cid, status="unavailable", error=str(exc)))
            continue
        features = result.get("features") or []
        for feature in features:
            try:
                items.append(to_dataset_item(feature, cid, stac.item_url(cid, str(feature.get("id"))), retrieved_at))
            except (KeyError, TypeError, ValueError):
                continue  # skip a malformed STAC feature rather than failing the whole query
        matched = result.get("numberMatched")
        statuses.append(CollectionStatus(
            collection=cid, status="ok", matched=matched if isinstance(matched, int) else None, returned=len(features)
        ))
    if all(s.status == "unavailable" for s in statuses):
        raise HTTPException(503, "The USGS STAC service is unavailable: " + "; ".join(s.error or "" for s in statuses))

    ok = [s for s in statuses if s.status == "ok"]
    zero = [s.collection for s in ok if s.matched == 0 or (s.matched is None and s.returned == 0)]
    note = (
        "Results are products whose footprint intersects the box. An empty collection means no catalogued product in "
        "that collection covers this area; it does not mean the area cannot be observed."
        + (f" No products found in: {', '.join(zero)}." if zero else "")
    )
    provenance = Provenance(
        source_organisation=SOURCE_ORG,
        collections=list(collections),
        retrieved_at=retrieved_at,
        processing_method="Bounding-box STAC /search per collection; item metadata passed through. No rasters downloaded.",
        resolution=None,
        units=discovery_units(),
        nodata_handling="Not applicable: no raster values were read.",
        limitations=[
            "Footprints and metadata are as published by USGS STAC and are not independently verified.",
            "Per-item CRS and resolution appear only when STAC declares them.",
            "Items returned are capped by 'limit'; check each collection's 'matched' count.",
        ],
        experimental=False,
        sources=[STAC_DOCS[c] for c in collections] + [f"{stac.base_url}/search"],
    )
    return DatasetsResponse(
        query=DatasetQuery(bbox=bbox, collections=list(collections), limit_per_collection=limit),
        collections=statuses,
        items=items,
        coverage_note=note,
        provenance=provenance,
    )


@router.get(
    "/dtm/{item_id}/metadata",
    response_model=DtmMetadataResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
    tags=["datasets"],
    summary="Raster metadata for one DTM (header-only read)",
)
def dtm_metadata(
    item_id: Annotated[str, Path(description="STAC item ID, e.g. DTEPD_076532_0920_076203_0920_A01")],
    collection: Annotated[Literal["hirise_dtm", "ctx_dtm"], Query(description="Collection containing the item.")] = "hirise_dtm",
    stac: StacClient = Depends(get_stac_client),
    read_raster: RasterReader = Depends(get_raster_reader),
) -> DtmMetadataResponse:
    if not _ITEM_ID.match(item_id):
        raise HTTPException(422, "item_id contains unsupported characters")
    collection_id = _COLLECTION_BY_CHOICE[collection][0]
    retrieved_at = now_utc()
    try:
        item = stac.get_item(collection_id, item_id)
    except StacUnavailable as exc:
        raise HTTPException(503, f"The USGS STAC service is unavailable: {exc}") from exc
    if item is None:
        raise HTTPException(404, f"Item '{item_id}' was not found in collection '{collection_id}'")

    asset = find_dtm_asset(to_asset_infos(item.get("assets") or {}))
    if asset is None:
        raise HTTPException(404, f"Item '{item_id}' has no 'dtm' asset; this endpoint reads elevation rasters only")
    try:
        facts = read_raster(asset.href)
    except AssetHostNotAllowed as exc:
        raise HTTPException(502, f"Refusing to read asset: {exc}") from exc
    except RasterUnavailable as exc:
        raise HTTPException(504 if exc.timeout else 502, f"The DTM raster could not be read: {exc}") from exc
    try:
        return build_dtm_metadata(item, collection_id, item_id, stac.item_url(collection_id, item_id), asset, facts, retrieved_at)
    except (KeyError, TypeError, IndexError) as exc:
        raise HTTPException(502, "The raster header was missing expected fields") from exc
