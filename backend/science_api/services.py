"""Turn STAC items and raster header facts into API response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .config import HIRISE_DTM_COLLECTION
from .models import (
    AssetInfo,
    CrsInfo,
    DatasetItem,
    DtmMetadataResponse,
    Provenance,
    RasterInfo,
    RasterPixelSize,
    UnitsInfo,
    VerticalReference,
)
from .provenance import (
    ACQUISITION_DATE_NOTE,
    COLLECTION_LABEL,
    RESOLUTION_NOTE,
    SOURCE_ORG,
    STAC_DOCS,
    crs_from_stac_properties,
    item_provenance,
    limitations_for,
)

DOCUMENTED_VERTICAL_REFERENCE = (
    "USGS HiRISE DTM documentation states heights are reported relative to the areoid (the Mars geoid), "
    "controlled to MOLA. The specific areoid model is not named there."
)


def _first(value: Any) -> Optional[str]:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str):
        return value
    return None


def to_asset_infos(assets: dict[str, Any]) -> list[AssetInfo]:
    return [
        AssetInfo(
            key=key,
            title=a.get("title"),
            media_type=a.get("type"),
            roles=list(a.get("roles") or []),
            href=a["href"],
        )
        for key, a in assets.items()
        if isinstance(a, dict) and a.get("href")
    ]


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def to_dataset_item(feature: dict[str, Any], collection: str, stac_item_url: str, retrieved_at: datetime) -> DatasetItem:
    props = feature.get("properties") or {}
    item_id = str(feature.get("id"))
    assets = to_asset_infos(feature.get("assets") or {})
    dtm = next((a for a in assets if a.key == "dtm"), None)
    crs = crs_from_stac_properties(props)
    resolution = _as_float(props.get("gsd"))
    date = props.get("start_datetime") or props.get("datetime")
    return DatasetItem(
        item_id=item_id,
        collection=collection,
        title=props.get("title"),
        footprint=feature.get("geometry"),
        bbox=[float(v) for v in feature["bbox"]] if feature.get("bbox") else None,
        acquisition_date=str(date) if date else None,
        acquisition_date_note=ACQUISITION_DATE_NOTE,
        mission=_first(props.get("missions")),
        instrument=_first(props.get("instruments")),
        resolution_m=resolution,
        resolution_note=RESOLUTION_NOTE,
        crs=crs,
        assets=assets,
        stac_item_url=stac_item_url,
        license=props.get("license"),
        limitations=limitations_for(collection),
        provenance=item_provenance(collection, item_id, dtm.href if dtm else None, crs, resolution, retrieved_at),
    )


def find_dtm_asset(assets: list[AssetInfo]) -> Optional[AssetInfo]:
    """The elevation raster asset: key 'dtm'. No fallback guessing among other GeoTIFFs."""
    return next((a for a in assets if a.key == "dtm"), None)


def _stac_declared(item: dict[str, Any], asset_raw: dict[str, Any]) -> dict[str, Any]:
    props = item.get("properties") or {}
    band = (asset_raw.get("raster:bands") or [{}])[0]
    return {
        "proj:shape": props.get("proj:shape"),
        "gsd": props.get("gsd"),
        "proj:epsg": props.get("proj:epsg"),
        "crs_name": (props.get("proj:projjson") or {}).get("name") if isinstance(props.get("proj:projjson"), dict) else None,
        "asset_media_type": asset_raw.get("type"),
        "raster_band": {
            k: band.get(k) for k in ("data_type", "nodata", "unit", "scale", "offset", "spatial_resolution", "statistics") if k in band
        },
    }


def _units(facts: dict[str, Any], declared: dict[str, Any]) -> UnitsInfo:
    file_units = [u for u in facts.get("units", []) if u]
    stac_unit = (declared.get("raster_band") or {}).get("unit")
    if file_units:
        return UnitsInfo(value=file_units[0], confirmed=True, note="Declared in the GeoTIFF band metadata.")
    if stac_unit:
        return UnitsInfo(value=str(stac_unit), confirmed=True, note="Declared in the STAC raster:bands metadata.")
    return UnitsInfo(
        value=None,
        confirmed=False,
        note=(
            "Elevation units are not declared in the file or in STAC. Metres is the usual convention for PDS DTMs "
            "but is not assumed here; confirm from the PDS label before computing anything."
        ),
    )


def _consistency(facts: dict[str, Any], declared: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    shape = declared.get("proj:shape")
    if isinstance(shape, list) and len(shape) == 2:
        same = shape[0] == facts["height"] and shape[1] == facts["width"]
        notes.append(
            "Raster dimensions match STAC proj:shape." if same
            else f"MISMATCH: file is {facts['height']}x{facts['width']} (rows x cols) but STAC proj:shape is {shape}."
        )
    else:
        notes.append("STAC did not declare proj:shape, so dimensions could not be cross-checked.")
    band_nodata = (declared.get("raster_band") or {}).get("nodata")
    if band_nodata is not None and facts.get("nodata") is not None:
        same = abs(float(band_nodata) - float(facts["nodata"])) <= abs(float(facts["nodata"])) * 1e-6
        notes.append("NoData value matches STAC raster:bands." if same else "MISMATCH between file NoData and STAC nodata.")
    elif facts.get("nodata") is None:
        notes.append("No NoData value is declared in the file; invalid pixels cannot be masked from metadata alone.")
    gsd = declared.get("gsd")
    if gsd is not None:
        px = facts["res"][0]
        if abs(px - float(gsd)) <= max(float(gsd), px) * 0.01:
            notes.append("Pixel size matches STAC gsd within 1%.")
        else:
            notes.append(f"Pixel size {px:g} differs from STAC gsd {gsd}; check the CRS linear unit.")
    return notes


def build_dtm_metadata(
    item: dict[str, Any],
    collection: str,
    item_id: str,
    stac_item_url: str,
    asset: AssetInfo,
    facts: dict[str, Any],
    retrieved_at: datetime,
) -> DtmMetadataResponse:
    props = item.get("properties") or {}
    raw_asset = (item.get("assets") or {}).get(asset.key, {})
    declared = _stac_declared(item, raw_asset)

    crs = CrsInfo(
        name=facts.get("crs_name"),
        epsg=facts.get("crs_epsg"),
        wkt=facts.get("crs_wkt"),
        linear_unit=facts.get("crs_linear_unit"),
        source="GeoTIFF header (read via GDAL)",
    )
    unit = crs.linear_unit if facts.get("crs_is_projected") else "degree" if facts.get("crs_is_projected") is False else None
    raster = RasterInfo(
        driver=facts.get("driver"),
        width=facts["width"],
        height=facts["height"],
        band_count=facts["band_count"],
        dtype=facts["dtype"],
        crs=crs,
        pixel_size=RasterPixelSize(x=facts["res"][0], y=facts["res"][1], unit=unit),
        bounds=facts["bounds"],
        nodata=facts.get("nodata"),
        nodata_source="GeoTIFF header" if facts.get("nodata") is not None else "not declared",
        tiled=facts.get("tiled"),
        block_size=facts.get("block_size"),
        overview_count=facts.get("overview_count"),
        compression=facts.get("compression"),
    )
    units = _units(facts, declared)
    vertical_confirmed = any("vertical" in str(k).lower() for k in props)
    vertical = VerticalReference(
        value=None,
        confirmed=False,
        documented_reference=DOCUMENTED_VERTICAL_REFERENCE if collection == HIRISE_DTM_COLLECTION else None,
        note=(
            "No vertical datum field was found in the file or STAC item."
            if not vertical_confirmed
            else "A vertical-related STAC property exists; inspect stac_declared before relying on it."
        ),
    )
    px_label = f"{raster.pixel_size.x:g} x {raster.pixel_size.y:g} {unit or 'CRS units'}"
    provenance = Provenance(
        source_organisation=SOURCE_ORG,
        collection=collection,
        item_id=item_id,
        asset_url=asset.href,
        retrieved_at=retrieved_at,
        processing_method=(
            "STAC item JSON plus a header-only read of the GeoTIFF through GDAL /vsicurl/ range requests. "
            "No pixel values were read, decoded or modified."
        ),
        crs=crs,
        resolution=px_label,
        units=units,
        nodata_handling=(
            f"NoData value {raster.nodata!r} read from the file header; masking is not applied because no pixels are read."
            if raster.nodata is not None
            else "No NoData value declared in the file; masking is not possible from metadata."
        ),
        limitations=limitations_for(collection) + [
            "Metadata only: this response contains no elevation values, slope or statistics computed by MARSIGHT.",
        ],
        experimental=True,
        sources=[stac_item_url, asset.href, STAC_DOCS.get(collection, "https://stac.astrogeology.usgs.gov/")],
    )
    return DtmMetadataResponse(
        item_id=item_id,
        collection=collection,
        title=props.get("title") or COLLECTION_LABEL.get(collection),
        stac_item_url=stac_item_url,
        asset=asset,
        raster=raster,
        elevation_units=units,
        vertical_reference=vertical,
        stac_declared=declared,
        consistency_checks=_consistency(facts, declared),
        provenance=provenance,
    )
