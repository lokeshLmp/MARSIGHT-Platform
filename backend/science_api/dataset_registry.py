"""Server-side registry for explicitly approved local scientific rasters."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import rasterio

HIRISE_PRODUCT_ID = "DTEPD_076532_0920_076203_0920_A01"
HIRISE_COLLECTION = "mro_hirise_socet_dtms"
NODATA = -3.4028226550889045e38


@dataclass(frozen=True)
class RasterDataset:
    item_id: str
    path: Path
    collection: str
    instrument: str
    mission: str
    producer: str
    target: str
    region: str
    elevation_units: str
    vertical_datum: str
    resolution_m_per_pixel: float
    provenance: tuple[str, ...]


def get_dataset(item_id: str) -> RasterDataset:
    if item_id != HIRISE_PRODUCT_ID:
        raise KeyError("Unknown registered dataset")
    configured = os.environ.get("MARSIGHT_DTM_PATH", "").strip()
    if not configured:
        raise FileNotFoundError("The approved HiRISE DTM is not configured")
    path = Path(configured).expanduser()
    if not path.is_file():
        raise FileNotFoundError("The configured HiRISE DTM is unavailable")
    return RasterDataset(
        item_id=item_id, path=path, collection=HIRISE_COLLECTION,
        instrument="HiRISE", mission="Mars Reconnaissance Orbiter", producer="University of Arizona",
        target="Mars", region="South Polar residual cap", elevation_units="m",
        vertical_datum="Mars 2000 Datum; metres above the Martian equipotential surface",
        resolution_m_per_pixel=2.0,
        provenance=(
            "PDS product label for product identity, map scale, elevation units and vertical reference",
            "https://hirise-pds.lpl.arizona.edu/PDS/DTM/ESP/ORB_076500_076599/ESP_076532_0920_ESP_076203_0920/",
            "https://www.uahirise.org/dtm/dtm.php?ID=ESP_076532_0920",
        ),
    )


def validate_raster(dataset: RasterDataset) -> None:
    """Reject a misconfigured file instead of labeling unrelated pixels as this product."""
    with rasterio.open(dataset.path) as src:
        expected = (2287, 4969)
        if (src.width, src.height) != expected or src.count != 1 or src.dtypes[0] != "float32":
            raise ValueError("Configured raster does not match the registered product dimensions and band type")
        if src.nodata is None or float(src.nodata) != NODATA:
            raise ValueError("Configured raster NoData does not match the registered product")
        if abs(float(src.res[0]) - 2.0) > 0.05 or abs(float(src.res[1]) - 2.0) > 0.05:
            raise ValueError("Configured raster pixel size does not match the registered product")
        crs_name = src.crs.to_wkt().lower() if src.crs else ""
        if not src.crs or not src.crs.is_projected or "mars" not in crs_name or "stereographic" not in crs_name:
            raise ValueError("Configured raster CRS does not match a projected Mars polar product")
