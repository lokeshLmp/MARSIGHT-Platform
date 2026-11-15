"""Versioned routes for real processing of explicitly registered raster products."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict
import rasterio

from .dataset_registry import RasterDataset, get_dataset, validate_raster
from .terrain_processing import analyze_window, elevation_profile, statistics, timestamp

router = APIRouter(prefix="/api/v1/dtm", tags=["terrain processing"])


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Product(StrictModel):
    item_id: str
    collection: str
    instrument: str
    mission: str
    producer: str
    target: str
    region: str
    resolution_m_per_pixel: float
    elevation_units: str
    vertical_datum: str


class Raster(StrictModel):
    width: int
    height: int
    band_count: int
    dtype: str
    crs_wkt: str | None
    crs_linear_unit: str | None
    transform: list[float]
    resolution: list[float]
    nodata: float | None
    bounds: list[float]


class Provenance(StrictModel):
    sources: list[str]
    method: str
    processed_at: datetime
    nodata_treatment: str
    limitations: list[str]


class StatisticsResponse(StrictModel):
    product: Product
    raster: Raster
    valid_pixels: int
    nodata_pixels: int
    total_pixels: int
    minimum: float
    maximum: float
    mean: float
    population_standard_deviation: float
    algorithm: str
    parameters: dict[str, int | float]
    provenance: Provenance


class WindowResponse(StrictModel):
    product: Product
    raster: Raster
    col_off: int
    row_off: int
    width: int
    height: int
    sun_azimuth_deg: float
    sun_altitude_deg: float
    elevation: list[list[float | None]]
    slope_degrees: list[list[float | None]]
    aspect_degrees_clockwise_from_north: list[list[float | None]]
    hillshade_0_255: list[list[float | None]]
    valid_pixels: int
    nodata_pixels: int
    algorithm: str
    parameters: dict[str, int | float]
    provenance: Provenance


class ProfileSample(StrictModel):
    column: int
    row: int
    distance_crs_units: float
    elevation: float | None


class ProfileResponse(StrictModel):
    product: Product
    raster: Raster
    start_col: int
    start_row: int
    end_col: int
    end_row: int
    requested_samples: int
    samples: list[ProfileSample]
    algorithm: str
    parameters: dict[str, int | float]
    provenance: Provenance


LIMITATIONS = [
    "Only the registered HiRISE product is supported; the configured file is checked against its published dimensions, type, NoData and pixel scale.",
    "Statistics describe this product only and are not a global Mars summary.",
    "Slope/aspect use Horn 3x3 derivatives in the raster projected coordinate system; edge and incomplete NoData neighborhoods are null.",
    "Slope horizontal spacing uses the PDS 2 m/pixel map scale; local projection distortion is not corrected.",
    "Aspect is undefined on flat cells and is returned null there.",
    "Hillshade is an analytical visualization using the requested illumination angles, not a calibrated photometric product.",
    "The raster CRS reports its linear unit as unknown; profile distances are raw CRS units and must not be presented as metres without a validated conversion.",
    "No terrain-aware route cost, mission safety, or validated navigation assessment is calculated.",
]


def product_model(ds: RasterDataset) -> Product:
    return Product(item_id=ds.item_id, collection=ds.collection, instrument=ds.instrument, mission=ds.mission,
                   producer=ds.producer, target=ds.target, region=ds.region,
                   resolution_m_per_pixel=ds.resolution_m_per_pixel, elevation_units=ds.elevation_units,
                   vertical_datum=ds.vertical_datum)


def provenance(ds: RasterDataset, method: str, nodata: float | None) -> Provenance:
    treatment = f"Pixels equal to the raster NoData sentinel ({nodata!r}) and non-finite values are excluded; derivative neighborhoods containing invalid pixels are null."
    return Provenance(sources=list(ds.provenance), method=method, processed_at=timestamp(),
                      nodata_treatment=treatment, limitations=LIMITATIONS)


def _dataset(item_id: str) -> RasterDataset:
    try:
        dataset = get_dataset(item_id)
        validate_raster(dataset)
        return dataset
    except KeyError as exc:
        raise HTTPException(404, "Dataset is not in the server-side registry") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, rasterio.errors.RasterioError, OSError) as exc:
        raise HTTPException(503, "The configured scientific raster is invalid or unavailable") from exc


def _process(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (rasterio.errors.RasterioError, OSError) as exc:
        raise HTTPException(503, "The configured scientific raster could not be read") from exc


@router.get("/{item_id}/statistics", response_model=StatisticsResponse, summary="NoData-aware full-product statistics")
def product_statistics(item_id: str = Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")):
    ds = _dataset(item_id)
    result = _process(statistics, ds)
    raster = result.pop("metadata")
    return StatisticsResponse(product=product_model(ds), raster=raster, **result,
                              algorithm="Windowed Welford merge for population mean and standard deviation.",
                              parameters={"row_window_height": 256, "band": 1},
                              provenance=provenance(ds, "Windowed full-raster scan in 256-row strips; population moments merged in float64.", raster["nodata"]))


@router.get("/{item_id}/window", response_model=WindowResponse, summary="Bounded elevation and terrain-derivative window")
def terrain_window(
    item_id: str = Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"),
    col_off: int = Query(ge=0), row_off: int = Query(ge=0),
    width: int = Query(ge=1, le=512), height: int = Query(ge=1, le=512),
    sun_azimuth_deg: float = Query(default=315.0, ge=0, lt=360),
    sun_altitude_deg: float = Query(default=45.0, gt=0, le=90),
):
    ds = _dataset(item_id)
    result = _process(analyze_window, ds, col_off, row_off, width, height, sun_azimuth_deg, sun_altitude_deg)
    raster = result.pop("metadata")
    return WindowResponse(product=product_model(ds), raster=raster, col_off=col_off, row_off=row_off,
                          width=width, height=height, sun_azimuth_deg=sun_azimuth_deg,
                          sun_altitude_deg=sun_altitude_deg, **result,
                          algorithm="Horn 3x3 slope/aspect; analytical hillshade.",
                          parameters={"col_off": col_off, "row_off": row_off, "width": width, "height": height,
                                      "sun_azimuth_deg": sun_azimuth_deg, "sun_altitude_deg": sun_altitude_deg},
                          provenance=provenance(ds, "Raster window with one-pixel halo; Horn 3x3 derivatives scaled by PDS map scale; aspect clockwise from projected north; hillshade uses requested azimuth/altitude.", raster["nodata"]))


@router.get("/{item_id}/profile", response_model=ProfileResponse, summary="Sample an elevation profile between raster pixels")
def profile(
    item_id: str = Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"),
    start_col: int = Query(ge=0), start_row: int = Query(ge=0),
    end_col: int = Query(ge=0), end_row: int = Query(ge=0),
    samples: int = Query(default=256, ge=2, le=2048),
):
    ds = _dataset(item_id)
    result = _process(elevation_profile, ds, start_col, start_row, end_col, end_row, samples)
    raster = result.pop("metadata")
    return ProfileResponse(product=product_model(ds), raster=raster, start_col=start_col, start_row=start_row,
                           end_col=end_col, end_row=end_row, requested_samples=samples, **result,
                           algorithm="Nearest-pixel profile samples along a straight segment.",
                           parameters={"start_col": start_col, "start_row": start_row, "end_col": end_col,
                                       "end_row": end_row, "requested_samples": samples},
                           provenance=provenance(ds, "Nearest-pixel samples along a straight segment between pixel centres; distance uses raster CRS units.", raster["nodata"]))
