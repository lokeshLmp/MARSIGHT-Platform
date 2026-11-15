"""Provenance builders and the limitation statements attached to scientific responses.

Statements here are limited to what the STAC collections and USGS documentation say.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from .config import CTX_DTM_COLLECTION, HIRISE_DTM_COLLECTION
from .models import CrsInfo, Provenance, UnitsInfo

STAC_DOCS = {
    HIRISE_DTM_COLLECTION: "https://stac.astrogeology.usgs.gov/docs/data/mars/hirise_dtms/",
    CTX_DTM_COLLECTION: "https://stac.astrogeology.usgs.gov/docs/data/mars/ctxdtms/",
}

SOURCE_ORG = "USGS Astrogeology Science Center (STAC host/processor); products from NASA Mars Reconnaissance Orbiter"

COMMON_LIMITATIONS = [
    "Each product has its own projection, extent and resolution; never assume two products share a CRS.",
    "Elevation units are not guaranteed to be declared in file or STAC metadata. Check elevation_units.confirmed.",
    "DTMs are controlled to MOLA, so absolute accuracy is limited by MOLA (USGS: horizontal at best ~100 m).",
    "STAC datetime fields are reported as published and are not verified as the observation time.",
]

COLLECTION_LIMITATIONS: dict[str, list[str]] = {
    HIRISE_DTM_COLLECTION: [
        "Local footprints only (about 1,300 stereo products), not global coverage.",
        "Stereo matching can leave NoData gaps and edge outliers; Socet Set can leave square artefacts of ~0.5-1 m.",
        "Not guaranteed to co-register with uncontrolled HiRISE products.",
    ],
    CTX_DTM_COLLECTION: [
        "Coarser than HiRISE DTMs (roughly 20 m ground sample distance in sampled items).",
        "Generated with the Ames Stereo Pipeline and aligned to MOLA; artefacts and NoData gaps are possible.",
    ],
}

COLLECTION_LABEL = {
    HIRISE_DTM_COLLECTION: "HiRISE Socet Set DTMs",
    CTX_DTM_COLLECTION: "CTX controlled USGS DTMs",
}

ACQUISITION_DATE_NOTE = (
    "Value as published in STAC (start_datetime/datetime). It is not verified as the acquisition time: "
    "some items carry dates inconsistent with their product IDs."
)
RESOLUTION_NOTE = "STAC 'gsd' (ground sample distance) in metres as published; not measured by MARSIGHT."


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def limitations_for(collection: str) -> list[str]:
    return COLLECTION_LIMITATIONS.get(collection, []) + COMMON_LIMITATIONS


def crs_from_stac_properties(props: dict[str, Any]) -> Optional[CrsInfo]:
    """CRS as declared by the STAC projection extension, or None when not declared."""
    projjson = props.get("proj:projjson")
    name = projjson.get("name") if isinstance(projjson, dict) else None
    epsg = props.get("proj:epsg")
    if not name and not epsg and not props.get("proj:wkt2"):
        return None
    return CrsInfo(
        name=name,
        epsg=epsg if isinstance(epsg, int) else None,
        source="STAC projection extension (proj:projjson / proj:epsg)",
    )


def discovery_units() -> UnitsInfo:
    return UnitsInfo(value=None, confirmed=False, note="Discovery only: no raster values were read, so no units apply.")


def item_provenance(
    collection: str,
    item_id: str,
    asset_url: Optional[str],
    crs: Optional[CrsInfo],
    resolution_m: Optional[float],
    retrieved_at: datetime,
) -> Provenance:
    return Provenance(
        source_organisation=SOURCE_ORG,
        collection=collection,
        item_id=item_id,
        asset_url=asset_url,
        retrieved_at=retrieved_at,
        processing_method="STAC item metadata passed through unmodified; no raster pixels read.",
        crs=crs,
        resolution=f"{resolution_m:g} m (STAC gsd)" if resolution_m is not None else None,
        units=discovery_units(),
        nodata_handling="Not applicable: no raster values were read.",
        limitations=limitations_for(collection),
        experimental=False,
        sources=[STAC_DOCS.get(collection, "https://stac.astrogeology.usgs.gov/")],
    )
