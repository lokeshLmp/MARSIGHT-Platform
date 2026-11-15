"""Pydantic response models. Every scientific response carries a Provenance block."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class UnitsInfo(BaseModel):
    value: Optional[str] = Field(None, description="Unit string if declared by the data, otherwise null.")
    confirmed: bool = Field(..., description="True only if the unit is declared in the file or STAC metadata.")
    note: str


class CrsInfo(BaseModel):
    name: Optional[str] = None
    epsg: Optional[int] = None
    wkt: Optional[str] = None
    linear_unit: Optional[str] = None
    source: str = Field(..., description="Where this CRS information came from.")


class Provenance(BaseModel):
    source_organisation: str
    collection: Optional[str] = None
    collections: list[str] = Field(default_factory=list)
    item_id: Optional[str] = None
    asset_url: Optional[str] = None
    retrieved_at: datetime
    processing_method: str
    crs: Optional[CrsInfo] = None
    resolution: Optional[str] = None
    units: UnitsInfo
    nodata_handling: str
    limitations: list[str]
    experimental: bool = False
    sources: list[str] = Field(default_factory=list)


class AssetInfo(BaseModel):
    key: str
    title: Optional[str] = None
    media_type: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    href: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    time: datetime
    note: str = "Liveness only. External services are not contacted by this endpoint."


class DatasetItem(BaseModel):
    item_id: str
    collection: str
    title: Optional[str] = None
    footprint: Optional[dict[str, Any]] = Field(None, description="GeoJSON geometry from STAC (lon/lat).")
    bbox: Optional[list[float]] = Field(None, description="[minLon, minLat, maxLon, maxLat] degrees.")
    acquisition_date: Optional[str] = Field(None, description="Date string exactly as published in STAC.")
    acquisition_date_note: str
    mission: Optional[str] = None
    instrument: Optional[str] = None
    resolution_m: Optional[float] = Field(None, description="STAC gsd in metres, as published.")
    resolution_note: str
    crs: Optional[CrsInfo] = None
    assets: list[AssetInfo]
    stac_item_url: str
    license: Optional[str] = None
    limitations: list[str]
    provenance: Provenance


class CollectionStatus(BaseModel):
    collection: str
    status: Literal["ok", "unavailable"]
    matched: Optional[int] = Field(None, description="numberMatched reported by STAC for this query.")
    returned: int = 0
    error: Optional[str] = None


class DatasetQuery(BaseModel):
    bbox: list[float]
    collections: list[str]
    limit_per_collection: int


class DatasetsResponse(BaseModel):
    query: DatasetQuery
    collections: list[CollectionStatus]
    items: list[DatasetItem]
    coverage_note: str
    provenance: Provenance


class RasterPixelSize(BaseModel):
    x: float
    y: float
    unit: Optional[str] = Field(None, description="Linear unit of the CRS, if known.")


class RasterInfo(BaseModel):
    driver: Optional[str] = None
    width: int
    height: int
    band_count: int
    dtype: str
    crs: CrsInfo
    pixel_size: RasterPixelSize
    bounds: list[float] = Field(..., description="Left, bottom, right, top in CRS units (not degrees for projected CRS).")
    nodata: Optional[float] = None
    nodata_source: str
    tiled: Optional[bool] = None
    block_size: Optional[list[int]] = None
    overview_count: Optional[int] = None
    compression: Optional[str] = None


class VerticalReference(BaseModel):
    value: Optional[str] = None
    confirmed: bool
    documented_reference: Optional[str] = Field(
        None, description="What project documentation states; not read from this file."
    )
    note: str


class DtmMetadataResponse(BaseModel):
    item_id: str
    collection: str
    title: Optional[str] = None
    stac_item_url: str
    asset: AssetInfo
    raster: RasterInfo
    elevation_units: UnitsInfo
    vertical_reference: VerticalReference
    stac_declared: dict[str, Any] = Field(
        default_factory=dict, description="Raster properties declared by STAC, for cross-checking."
    )
    consistency_checks: list[str] = Field(default_factory=list)
    provenance: Provenance


class ErrorResponse(BaseModel):
    detail: str
