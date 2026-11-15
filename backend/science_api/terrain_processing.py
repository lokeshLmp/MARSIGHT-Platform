"""Windowed Rasterio processing for registered planetary elevation rasters.

The processing functions contain no HTTP concerns. Slope/aspect use Horn's 3x3
finite difference; edge cells and cells adjacent to NoData are returned invalid.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

import numpy as np
import rasterio
from rasterio.windows import Window

from .dataset_registry import RasterDataset, validate_raster

MAX_WINDOW_CELLS = 65_536
MAX_WINDOW_SIDE = 512


def _open(dataset: RasterDataset):
    return rasterio.open(dataset.path)


def _valid(array: np.ndarray, nodata: float | None) -> np.ndarray:
    mask = np.isfinite(array)
    if nodata is not None:
        mask &= array != nodata
    return mask


def raster_metadata(src: rasterio.io.DatasetReader) -> dict[str, Any]:
    return {
        "width": src.width, "height": src.height, "band_count": src.count, "dtype": src.dtypes[0],
        "crs_wkt": src.crs.to_wkt() if src.crs else None,
        "crs_linear_unit": getattr(src.crs, "linear_units", None) if src.crs else None,
        "transform": list(src.transform)[:6], "resolution": [float(x) for x in src.res],
        "nodata": float(src.nodata) if src.nodata is not None else None,
        "bounds": [float(x) for x in src.bounds],
    }


def statistics(dataset: RasterDataset) -> dict[str, Any]:
    """Single-pass bounded memory statistics using mergeable population moments."""
    with _open(dataset) as src:
        count = invalid = 0
        mean = m2 = math.nan
        minimum, maximum = math.inf, -math.inf
        for row in range(0, src.height, 256):
            arr = src.read(1, window=Window(0, row, src.width, min(256, src.height-row)), masked=False)
            values = arr[_valid(arr, src.nodata)].astype(np.float64, copy=False)
            n = int(values.size)
            invalid += arr.size - n
            if not n:
                continue
            chunk_mean = float(values.mean(dtype=np.float64))
            chunk_m2 = float(np.square(values - chunk_mean).sum(dtype=np.float64))
            chunk_min, chunk_max = float(values.min()), float(values.max())
            if count == 0:
                mean, m2 = chunk_mean, chunk_m2
            else:
                delta = chunk_mean - mean
                total = count + n
                m2 += chunk_m2 + delta * delta * count * n / total
                mean += delta * n / total
            count += n
            minimum, maximum = min(minimum, chunk_min), max(maximum, chunk_max)
        if count == 0:
            raise ValueError("Raster contains no valid elevation pixels")
        return {
            "valid_pixels": count, "nodata_pixels": invalid, "minimum": minimum, "maximum": maximum,
            "mean": mean, "population_standard_deviation": math.sqrt(m2 / count), "total_pixels": count + invalid,
            "metadata": raster_metadata(src),
        }


def _derivatives(padded: np.ndarray, valid: np.ndarray, src: rasterio.io.DatasetReader, resolution_m_per_pixel: float):
    # Horn central derivatives in pixel coordinates; all 3x3 cells must be valid.
    z1, z2, z3 = padded[:-2, :-2], padded[:-2, 1:-1], padded[:-2, 2:]
    z4, z6 = padded[1:-1, :-2], padded[1:-1, 2:]
    z7, z8, z9 = padded[2:, :-2], padded[2:, 1:-1], padded[2:, 2:]
    dz_dc = ((z3 + 2*z6 + z9) - (z1 + 2*z4 + z7)) / 8.0
    dz_dr = ((z7 + 2*z8 + z9) - (z1 + 2*z2 + z3)) / 8.0
    v = valid.astype(np.uint8)
    good = sum(v[r:r + v.shape[0]-2, c:c + v.shape[1]-2] for r in range(3) for c in range(3)) == 9
    t = src.transform
    col_len, row_len = math.hypot(t.a, t.d), math.hypot(t.b, t.e)
    if min(col_len, row_len, resolution_m_per_pixel) <= 0:
        raise ValueError("Raster transform or map scale is invalid")
    col_unit = (t.a / col_len, t.d / col_len)
    row_unit = (t.b / row_len, t.e / row_len)
    basis = np.array([col_unit, row_unit], dtype=np.float64)
    if abs(float(np.linalg.det(basis))) < 1e-8:
        raise ValueError("Raster pixel axes do not define a usable local direction basis")
    inverse_basis = np.linalg.inv(basis)
    metric_col, metric_row = dz_dc / resolution_m_per_pixel, dz_dr / resolution_m_per_pixel
    dz_dx = inverse_basis[0, 0]*metric_col + inverse_basis[0, 1]*metric_row
    dz_dy = inverse_basis[1, 0]*metric_col + inverse_basis[1, 1]*metric_row
    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
    aspect = (np.degrees(np.arctan2(-dz_dx, -dz_dy)) + 360.0) % 360.0
    return slope, aspect, good


def analyze_window(dataset: RasterDataset, col_off: int, row_off: int, width: int, height: int,
                   sun_azimuth_deg: float = 315.0, sun_altitude_deg: float = 45.0) -> dict[str, Any]:
    if width <= 0 or height <= 0 or width > MAX_WINDOW_SIDE or height > MAX_WINDOW_SIDE or width * height > MAX_WINDOW_CELLS:
        raise ValueError(f"Window dimensions must be positive, at most {MAX_WINDOW_SIDE} per side and {MAX_WINDOW_CELLS} cells total")
    if not (0 <= col_off and 0 <= row_off):
        raise ValueError("Window offsets must be non-negative")
    if not (0 <= sun_azimuth_deg < 360) or not (0 < sun_altitude_deg <= 90):
        raise ValueError("Sun azimuth must be in [0, 360) and altitude in (0, 90]")
    with _open(dataset) as src:
        if col_off + width > src.width or row_off + height > src.height:
            raise ValueError("Window extends beyond raster bounds")
        # Include a one-pixel halo for derivatives; no unbounded reads.
        c0, r0 = max(0, col_off-1), max(0, row_off-1)
        c1, r1 = min(src.width, col_off+width+1), min(src.height, row_off+height+1)
        data = src.read(1, window=Window(c0, r0, c1-c0, r1-r0)).astype(np.float64)
        valid = _valid(data, src.nodata)
        inner = data[row_off-r0:row_off-r0+height, col_off-c0:col_off-c0+width]
        inner_valid = valid[row_off-r0:row_off-r0+height, col_off-c0:col_off-c0+width]
        elevation = np.where(inner_valid, inner, None)
        # Pad missing outer halo with invalid sentinels so raster edges are masked.
        pad = np.full((height+2, width+2), np.nan, dtype=np.float64)
        pad_valid = np.zeros((height+2, width+2), dtype=bool)
        # Align the clipped read into an invalid-padded one-pixel halo.
        pr0, pc0 = 1 + r0 - row_off, 1 + c0 - col_off
        pr1, pc1 = pr0 + data.shape[0], pc0 + data.shape[1]
        pad[pr0:pr1, pc0:pc1] = data
        pad_valid[pr0:pr1, pc0:pc1] = valid
        slope, aspect, derivative_valid = _derivatives(pad, pad_valid, src, dataset.resolution_m_per_pixel)
        zenith = math.radians(90.0-sun_altitude_deg)
        azimuth = math.radians(sun_azimuth_deg)
        slope_r, aspect_r = np.radians(slope), np.radians(aspect)
        shade = 255.0 * np.maximum(0.0, np.cos(zenith)*np.cos(slope_r) + np.sin(zenith)*np.sin(slope_r)*np.cos(azimuth-aspect_r))
        derivative_valid &= inner_valid
        return {
            "elevation": elevation.tolist(),
            "slope_degrees": np.where(derivative_valid, slope, None).tolist(),
            "aspect_degrees_clockwise_from_north": np.where(derivative_valid & (slope > 1e-12), aspect, None).tolist(),
            "hillshade_0_255": np.where(derivative_valid, shade, None).tolist(),
            "valid_pixels": int(inner_valid.sum()), "nodata_pixels": int(inner.size-inner_valid.sum()),
            "metadata": raster_metadata(src),
        }


def elevation_profile(dataset: RasterDataset, start_col: int, start_row: int, end_col: int, end_row: int,
                      samples: int = 256) -> dict[str, Any]:
    if samples < 2 or samples > 2048:
        raise ValueError("samples must be between 2 and 2048")
    with _open(dataset) as src:
        for col, row in ((start_col,start_row),(end_col,end_row)):
            if not (0 <= col < src.width and 0 <= row < src.height):
                raise ValueError("Profile endpoint is outside raster bounds")
        cols = np.rint(np.linspace(start_col, end_col, samples)).astype(int)
        rows = np.rint(np.linspace(start_row, end_row, samples)).astype(int)
        coords = list(dict.fromkeys((int(c), int(r)) for c, r in zip(cols, rows)))
        if len(coords) > 2048:
            raise ValueError("Profile request exceeds the sample limit")
        values = []
        distance = []
        start_x, start_y = src.transform @ (start_col + .5, start_row + .5)
        for col, row in coords:
            arr = src.read(1, window=Window(col,row,1,1))[0,0]
            valid = bool(_valid(np.asarray([arr]), src.nodata)[0])
            x,y = src.transform @ (col + .5, row + .5)
            distance.append(float(math.hypot(x-start_x, y-start_y)))
            values.append(float(arr) if valid else None)
        return {"samples": [{"column": c,"row": r,"distance_crs_units": d,"elevation": v} for (c,r),d,v in zip(coords,distance,values)],
                "metadata": raster_metadata(src)}


def timestamp() -> datetime:
    return datetime.now(timezone.utc)
