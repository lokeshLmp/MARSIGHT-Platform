from __future__ import annotations

import tempfile
import unittest
import os
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from backend.science_api.dataset_registry import RasterDataset
from backend.science_api.terrain_processing import analyze_window, elevation_profile, statistics

NODATA = -3.4028226550889045e38


class RasterFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        cls.path = Path(cls.temp.name) / "synthetic.tif"
        cls.data = (np.indices((7, 7))[1] * 2).astype("float32")
        cls.data[5, 5] = NODATA
        with rasterio.open(cls.path, "w", driver="GTiff", width=7, height=7, count=1,
                           dtype="float32", crs="EPSG:3857", transform=from_origin(100, 200, 2, 2),
                           nodata=NODATA) as dst:
            dst.write(cls.data, 1)
        cls.dataset = RasterDataset(
            item_id="synthetic-test", path=cls.path, collection="test", instrument="test", mission="test",
            producer="test", target="Mars", region="fixture", elevation_units="m", vertical_datum="test",
            resolution_m_per_pixel=2, provenance=("synthetic unit-test fixture",),
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_statistics_excludes_nodata(self):
        result = statistics(self.dataset)
        self.assertEqual(result["valid_pixels"], 48)
        self.assertEqual(result["nodata_pixels"], 1)
        self.assertAlmostEqual(result["minimum"], 0)
        self.assertAlmostEqual(result["maximum"], 12)
        self.assertAlmostEqual(result["mean"], float(self.data[self.data != NODATA].mean()), places=6)

    def test_assistant_context_uses_computed_raster_summaries_without_pixel_arrays(self):
        from backend.app.assistant import TerrainSummaryRequest, _collect_measured_context

        request = TerrainSummaryRequest(
            item_id="synthetic-test", col_off=1, row_off=1, width=3, height=3,
            profile_start_col=0, profile_start_row=0, profile_end_col=6, profile_end_row=6,
        )
        with patch("backend.app.assistant.get_dataset", return_value=self.dataset), \
             patch("backend.app.assistant.validate_raster"):
            measured = _collect_measured_context(request)
        self.assertEqual(measured["statistics"]["valid_pixels"], 48)
        self.assertEqual(measured["window"]["elevation"]["valid_cells"], 9)
        self.assertEqual(measured["profile"]["sample_count"], 7)
        self.assertIn("NoData", measured["provenance"]["nodata_treatment"])
        self.assertEqual(set(measured["window"]["elevation"]), {"valid_cells", "minimum", "maximum", "mean"})

    def test_horn_slope_aspect_and_hillshade(self):
        result = analyze_window(self.dataset, 1, 1, 3, 3, 270, 45)
        self.assertAlmostEqual(result["slope_degrees"][1][1], 45, places=5)
        self.assertAlmostEqual(result["aspect_degrees_clockwise_from_north"][1][1], 270, places=5)
        self.assertAlmostEqual(result["hillshade_0_255"][1][1], 255, places=4)

    def test_aspect_is_null_on_flat_surface(self):
        flat = np.full((7, 7), 12, dtype="float32")
        with rasterio.open(self.path, "r+") as dst:
            dst.write(flat, 1)
        try:
            result = analyze_window(self.dataset, 2, 2, 3, 3)
            self.assertEqual(result["slope_degrees"][1][1], 0)
            self.assertIsNone(result["aspect_degrees_clockwise_from_north"][1][1])
        finally:
            with rasterio.open(self.path, "r+") as dst:
                dst.write(self.data, 1)

    def test_edges_and_incomplete_nodata_neighborhoods_are_null(self):
        result = analyze_window(self.dataset, 0, 0, 7, 7)
        self.assertIsNone(result["slope_degrees"][0][0])
        self.assertIsNone(result["slope_degrees"][5][4])
        self.assertIsNone(result["elevation"][5][5])

    def test_window_bounds_and_sizes_are_rejected(self):
        for args in ((6, 6, 2, 2), (-1, 0, 1, 1), (0, 0, 513, 1), (0, 0, 0, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                analyze_window(self.dataset, *args)

    def test_profile_calculates_pixels_and_distance(self):
        result = elevation_profile(self.dataset, 0, 0, 6, 0, 7)
        self.assertEqual(len(result["samples"]), 7)
        self.assertEqual([p["elevation"] for p in result["samples"]], [0, 2, 4, 6, 8, 10, 12])
        self.assertEqual([p["distance_crs_units"] for p in result["samples"]], [0, 2, 4, 6, 8, 10, 12])

    def test_profile_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            elevation_profile(self.dataset, 0, 0, 7, 0, 4)
        with self.assertRaises(ValueError):
            elevation_profile(self.dataset, 0, 0, 1, 1, 1)

    def test_versioned_api_with_synthetic_raster_and_invalid_or_missing_data(self):
        from backend.science_api.dataset_registry import HIRISE_PRODUCT_ID
        from backend.science_api.terrain_routes import _dataset, product_statistics, terrain_window, profile
        from fastapi import HTTPException
        from backend.app.main import app

        api_paths = app.openapi()["paths"]
        self.assertIn("/health", api_paths)
        self.assertIn("/datasets", api_paths)
        self.assertIn("/dtm/{item_id}/metadata", api_paths)
        self.assertIn("/api/v1/dtm/{item_id}/statistics", api_paths)
        self.assertIn("/api/v1/dtm/{item_id}/window", api_paths)
        self.assertIn("/api/v1/dtm/{item_id}/profile", api_paths)
        from starlette.middleware.cors import CORSMiddleware
        cors = next(middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware)
        self.assertIn("http://localhost:5173", cors.kwargs["allow_origins"])

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MARSIGHT_DTM_PATH", None)
            with self.assertRaises(HTTPException) as missing:
                _dataset(HIRISE_PRODUCT_ID)
        self.assertEqual(missing.exception.status_code, 503)
        with patch.dict(os.environ, {"MARSIGHT_DTM_PATH": str(self.path) + ".absent"}):
            with self.assertRaises(HTTPException) as absent_file:
                _dataset(HIRISE_PRODUCT_ID)
        self.assertEqual(absent_file.exception.status_code, 503)
        self.assertNotIn("absent", absent_file.exception.detail)
        with self.assertRaises(HTTPException) as unknown:
            _dataset("NOT_REGISTERED")
        self.assertEqual(unknown.exception.status_code, 404)
        with patch.dict(os.environ, {"MARSIGHT_DTM_PATH": str(self.path)}), \
             patch("backend.science_api.terrain_routes.validate_raster"):
            with self.assertRaises(HTTPException) as invalid_size:
                terrain_window(HIRISE_PRODUCT_ID, 0, 0, 513, 1)
            stats = product_statistics(HIRISE_PRODUCT_ID)
            window = terrain_window(HIRISE_PRODUCT_ID, 0, 0, 3, 3, 315.0, 45.0)
            profile_result = profile(HIRISE_PRODUCT_ID, 0, 0, 6, 0, 7)
            with self.assertRaises(HTTPException) as outside:
                terrain_window(HIRISE_PRODUCT_ID, 6, 6, 2, 2, 315.0, 45.0)
        self.assertEqual(stats.valid_pixels, 48)
        self.assertEqual(invalid_size.exception.status_code, 422)
        self.assertEqual(stats.product.vertical_datum, "Mars 2000 Datum; metres above the Martian equipotential surface")
        self.assertIn("Welford", stats.algorithm)
        self.assertEqual(stats.parameters["row_window_height"], 256)
        self.assertEqual(window.product.item_id, HIRISE_PRODUCT_ID)
        self.assertEqual(window.parameters["sun_azimuth_deg"], 315.0)
        window_json = window.model_dump(mode="json")
        self.assertIsNone(window_json["slope_degrees"][0][0])
        self.assertNotIn(str(self.path), json.dumps(window_json, allow_nan=False))
        self.assertEqual(profile_result.requested_samples, 7)
        self.assertEqual(profile_result.parameters["start_col"], 0)
        self.assertEqual([s.elevation for s in profile_result.samples], [0, 2, 4, 6, 8, 10, 12])
        self.assertEqual(outside.exception.status_code, 422)

    @unittest.skipUnless(os.environ.get("MARSIGHT_DTM_PATH"), "Set MARSIGHT_DTM_PATH to verify the real HiRISE DTM")
    def test_real_hirise_statistics_match_verified_reference(self):
        from backend.science_api.dataset_registry import HIRISE_PRODUCT_ID
        from backend.science_api.terrain_routes import product_statistics, terrain_window, profile
        result = product_statistics(HIRISE_PRODUCT_ID)
        self.assertEqual(result.valid_pixels, 9_537_521)
        self.assertEqual(result.nodata_pixels, 1_826_582)
        self.assertEqual(result.total_pixels, 11_364_103)
        self.assertAlmostEqual(result.minimum, 2908.5302734375, places=7)
        self.assertAlmostEqual(result.maximum, 3259.0, places=7)
        self.assertAlmostEqual(result.mean, 3116.5411207628954, places=8)
        self.assertAlmostEqual(result.population_standard_deviation, 80.14356621471661, places=8)
        self.assertIn("POLAR_STEREOGRAPHIC MARS", result.raster.crs_wkt)
        self.assertEqual(result.raster.crs_linear_unit, "unknown")
        window = terrain_window(HIRISE_PRODUCT_ID, 1000, 1000, 3, 3, 315.0, 45.0)
        self.assertEqual(window.valid_pixels, 9)
        self.assertIsNotNone(window.elevation[1][1])
        self.assertIsNotNone(window.slope_degrees[1][1])
        real_profile = profile(HIRISE_PRODUCT_ID, 1000, 1000, 1010, 1000, 6)
        self.assertEqual(len(real_profile.samples), 6)
        self.assertTrue(all(sample.elevation is not None for sample in real_profile.samples))


if __name__ == "__main__":
    unittest.main()
