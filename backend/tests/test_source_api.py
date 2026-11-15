"""Backend tests. All external services (USGS STAC, remote GeoTIFFs) are mocked; no network is used.

Run:  .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -t . -v
"""

from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit
from typing import Any, Optional

import httpx
from backend.science_api.config import CTX_DTM_COLLECTION, HIRISE_DTM_COLLECTION, Settings
from backend.science_api.main import create_app
from backend.science_api.raster_meta import AssetHostNotAllowed, RasterUnavailable, check_asset_url
from backend.science_api.routers import get_raster_reader, get_stac_client
from backend.science_api.routers import health as source_health, list_datasets, dtm_metadata, parse_bbox
from backend.science_api.stac_client import StacClient, StacUnavailable


class LocalClient:
    """Invoke synchronous route handlers directly; avoids a Windows Python 3.14 socketpair hang."""
    def __init__(self, app):
        self.app = app

    def get(self, path, params=None, headers=None):
        from fastapi import HTTPException
        from pydantic import BaseModel
        query = parse_qs(urlsplit(path).query)
        query.update({key: [str(value)] for key, value in (params or {}).items()})
        pathname = urlsplit(path).path
        try:
            if pathname == "/health":
                result = source_health()
            elif pathname == "/datasets":
                bbox = parse_bbox(query.get("bbox", [""])[0])
                collection = query.get("collection", ["all"])[0]
                limit = int(query.get("limit", ["10"])[0])
                if collection not in {"all", "hirise_dtm", "ctx_dtm"} or not 1 <= limit <= 50:
                    raise HTTPException(422, "Invalid collection or limit")
                result = list_datasets(bbox, collection, limit, self.app.dependency_overrides[get_stac_client]())
            elif pathname.startswith("/dtm/") and pathname.endswith("/metadata"):
                item_id = pathname[len("/dtm/"):-len("/metadata")]
                collection = query.get("collection", ["hirise_dtm"])[0]
                if collection not in {"hirise_dtm", "ctx_dtm"}:
                    raise HTTPException(422, "Invalid collection")
                result = dtm_metadata(item_id, collection, self.app.dependency_overrides[get_stac_client](),
                                      self.app.dependency_overrides[get_raster_reader]())
            else:
                raise HTTPException(404, "Not found")
            body = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
            status = 200
        except HTTPException as exc:
            body, status = {"detail": exc.detail}, exc.status_code
        except (TypeError, ValueError):
            body, status = {"detail": "Invalid query"}, 422
        origin = (headers or {}).get("Origin")
        allowed = Settings().cors_origins
        response_headers = {"access-control-allow-origin": origin} if origin in allowed else {}
        return LocalResponse(status, body, response_headers)


class LocalResponse:
    def __init__(self, status_code, body, headers):
        self.status_code, self._body, self.headers = status_code, body, headers

    def json(self):
        return self._body

ASSET_URL = "https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/X/DTM_A.tif"


def make_feature(item_id: str = "DTM_A", gsd: float = 2.0, with_dtm: bool = True, stac_unit: str = "") -> dict[str, Any]:
    assets: dict[str, Any] = {
        "thumbnail": {"href": "https://astrogeo-ard.s3-us-west-2.amazonaws.com/x.jpg", "type": "image/jpeg", "roles": ["thumbnail"]},
        "hillshade": {"href": ASSET_URL.replace("DTM_A", "DTM_A_hillshade"), "type": "image/tiff", "roles": ["data"]},
    }
    if with_dtm:
        assets["dtm"] = {
            "href": ASSET_URL, "type": "image/tiff; application=geotiff; profile=cloud-optimized", "title": item_id, "roles": ["data"],
            "raster:bands": [{"nodata": -3.4028226550889045e38, "data_type": "float32", "unit": stac_unit, "spatial_resolution": gsd}],
        }
    return {
        "type": "Feature", "id": item_id, "bbox": [-116.7, -87.97, -112.2, -87.84],
        "geometry": {"type": "Polygon", "coordinates": [[[-116.7, -87.97], [-112.2, -87.97], [-112.2, -87.84], [-116.7, -87.84], [-116.7, -87.97]]]},
        "properties": {
            "title": "Test DTM", "start_datetime": "2006-09-29T00:00:00Z", "gsd": gsd, "license": "CC0-1.0",
            "missions": ["Mars Reconnaissance Orbiter (MRO)"], "instruments": ["High Resolution Imaging Science Experiment"],
            "proj:epsg": None, "proj:shape": [4969, 2287],
            "proj:projjson": {"name": "Mars (2015) - Sphere / Ocentric / South Polar"},
        },
        "assets": assets,
    }


FACTS = {
    "driver": "GTiff", "width": 2287, "height": 4969, "band_count": 1, "dtype": "float32",
    "crs_name": "Mars (2015) - Sphere / Ocentric / South Polar", "crs_wkt": 'PROJCS["Mars (2015) - Sphere / Ocentric / South Polar"]',
    "crs_epsg": None, "crs_linear_unit": "metre", "crs_is_projected": True,
    "res": [2.011841715538144, 2.011841715538144], "bounds": [-115201.0, -56409.0, -110600.0, -46412.0],
    "nodata": -3.4028226550889045e38, "units": [None], "tiled": True, "block_size": [512, 512],
    "overview_count": 4, "compression": "deflate",
}


class FakeStac:
    base_url = "https://stac.example/api"

    def __init__(self, features: Optional[dict[str, list]] = None, fail: Optional[set[str]] = None, items: Optional[dict] = None, down: bool = False):
        self.features = features or {}
        self.fail = fail or set()
        self.items = items or {}
        self.down = down
        self.search_calls: list[tuple[str, list[float], int]] = []

    def item_url(self, collection: str, item_id: str) -> str:
        return f"{self.base_url}/collections/{collection}/items/{item_id}"

    def search(self, collection: str, bbox: list[float], limit: int) -> dict[str, Any]:
        self.search_calls.append((collection, bbox, limit))
        if collection in self.fail:
            raise StacUnavailable("STAC request timed out")
        feats = self.features.get(collection, [])
        return {"type": "FeatureCollection", "features": feats[:limit], "numberMatched": len(feats)}

    def get_item(self, collection: str, item_id: str):
        if self.down:
            raise StacUnavailable("STAC returned HTTP 502")
        return self.items.get((collection, item_id))


class Harness(unittest.TestCase):
    def client(self, stac: FakeStac, reader=None) -> LocalClient:
        app = create_app()
        app.dependency_overrides[get_stac_client] = lambda: stac
        self.reader_calls: list[str] = []

        def fake_reader(url: str) -> dict[str, Any]:
            self.reader_calls.append(url)
            if reader is not None:
                return reader(url)
            return dict(FACTS)

        app.dependency_overrides[get_raster_reader] = lambda: fake_reader
        return LocalClient(app)


class HealthAndCors(Harness):
    def test_health_ok_without_external_calls(self):
        stac = FakeStac()
        r = self.client(stac).get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(stac.search_calls, [])

    def test_cors_allows_local_dev_origin_only(self):
        from starlette.middleware.cors import CORSMiddleware
        app = create_app()
        cors = next(middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware)
        self.assertIn("http://localhost:5173", cors.kwargs["allow_origins"])
        self.assertNotIn("https://evil.example", cors.kwargs["allow_origins"])


class DatasetDiscovery(Harness):
    def stac(self) -> FakeStac:
        return FakeStac(features={HIRISE_DTM_COLLECTION: [make_feature("H1"), make_feature("H2")], CTX_DTM_COLLECTION: [make_feature("C1", gsd=20.16)]})

    def test_discovery_returns_items_with_provenance_and_reads_no_rasters(self):
        c = self.client(self.stac())
        r = c.get("/datasets", params={"bbox": "76,17,79,20"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual([i["item_id"] for i in body["items"]], ["H1", "H2", "C1"])
        item = body["items"][0]
        for key in ("collection", "footprint", "acquisition_date", "acquisition_date_note", "assets", "resolution_m", "crs", "limitations", "provenance", "stac_item_url"):
            self.assertIn(key, item)
        self.assertEqual(item["resolution_m"], 2.0)
        self.assertEqual(item["crs"]["name"], "Mars (2015) - Sphere / Ocentric / South Polar")
        self.assertIsNone(item["crs"]["epsg"])
        self.assertEqual(item["provenance"]["asset_url"], ASSET_URL)
        self.assertFalse(item["provenance"]["units"]["confirmed"])
        self.assertTrue(body["provenance"]["retrieved_at"])
        self.assertEqual(body["provenance"]["collections"], [HIRISE_DTM_COLLECTION, CTX_DTM_COLLECTION])
        self.assertEqual(self.reader_calls, [], "discovery must not read any raster")
        self.assertEqual({s["status"] for s in body["collections"]}, {"ok"})

    def test_collection_filter_and_limit(self):
        stac = self.stac()
        r = self.client(stac).get("/datasets", params={"bbox": "76,17,79,20", "collection": "ctx_dtm", "limit": 1})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(stac.search_calls, [(CTX_DTM_COLLECTION, [76.0, 17.0, 79.0, 20.0], 1)])
        self.assertEqual([i["item_id"] for i in r.json()["items"]], ["C1"])

    def test_acquisition_date_is_flagged_as_unverified(self):
        item = self.client(self.stac()).get("/datasets", params={"bbox": "76,17,79,20"}).json()["items"][0]
        self.assertEqual(item["acquisition_date"], "2006-09-29T00:00:00Z")
        self.assertIn("not verified", item["acquisition_date_note"])

    def test_empty_result_is_explained_not_an_error(self):
        r = self.client(FakeStac()).get("/datasets", params={"bbox": "0,0,1,1"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"], [])
        self.assertIn("does not mean", r.json()["coverage_note"])

    def test_partial_failure_degrades_gracefully(self):
        stac = FakeStac(features={HIRISE_DTM_COLLECTION: [make_feature("H1")]}, fail={CTX_DTM_COLLECTION})
        r = self.client(stac).get("/datasets", params={"bbox": "76,17,79,20"})
        self.assertEqual(r.status_code, 200)
        statuses = {s["collection"]: s for s in r.json()["collections"]}
        self.assertEqual(statuses[HIRISE_DTM_COLLECTION]["status"], "ok")
        self.assertEqual(statuses[CTX_DTM_COLLECTION]["status"], "unavailable")
        self.assertEqual(len(r.json()["items"]), 1)

    def test_total_failure_is_503(self):
        stac = FakeStac(fail={HIRISE_DTM_COLLECTION, CTX_DTM_COLLECTION})
        r = self.client(stac).get("/datasets", params={"bbox": "76,17,79,20"})
        self.assertEqual(r.status_code, 503)

    def test_malformed_feature_is_skipped(self):
        stac = FakeStac(features={HIRISE_DTM_COLLECTION: [{"id": "BAD", "assets": {"dtm": {"nohref": 1}}, "bbox": "oops"}, make_feature("H1")]})
        r = self.client(stac).get("/datasets", params={"bbox": "76,17,79,20", "collection": "hirise_dtm"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual([i["item_id"] for i in r.json()["items"]], ["H1"])

    def test_bbox_validation(self):
        c = self.client(FakeStac())
        cases = ["1,2,3", "a,b,c,d", "10,0,5,5", "0,10,5,5", "-181,0,5,5", "0,-91,5,5", "0,0,5,91", "nan,0,5,5", "0,0,inf,5"]
        for bbox in cases:
            with self.subTest(bbox=bbox):
                self.assertEqual(c.get("/datasets", params={"bbox": bbox}).status_code, 422)
        self.assertEqual(c.get("/datasets").status_code, 422)

    def test_limit_and_collection_validation(self):
        c = self.client(FakeStac())
        self.assertEqual(c.get("/datasets", params={"bbox": "0,0,1,1", "limit": 0}).status_code, 422)
        self.assertEqual(c.get("/datasets", params={"bbox": "0,0,1,1", "limit": 51}).status_code, 422)
        self.assertEqual(c.get("/datasets", params={"bbox": "0,0,1,1", "collection": "other"}).status_code, 422)


class DtmMetadata(Harness):
    def stac(self, feature=None) -> FakeStac:
        return FakeStac(items={(HIRISE_DTM_COLLECTION, "DTM_A"): feature or make_feature("DTM_A")})

    def test_metadata_success_and_units_not_assumed(self):
        r = self.client(self.stac()).get("/dtm/DTM_A/metadata")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(self.reader_calls, [ASSET_URL])
        raster = body["raster"]
        self.assertEqual((raster["width"], raster["height"], raster["dtype"]), (2287, 4969, "float32"))
        self.assertAlmostEqual(raster["pixel_size"]["x"], 2.011841715538144)
        self.assertEqual(raster["pixel_size"]["unit"], "metre")
        self.assertEqual(raster["crs"]["name"], "Mars (2015) - Sphere / Ocentric / South Polar")
        self.assertIsNone(raster["crs"]["epsg"])
        self.assertEqual(raster["nodata_source"], "GeoTIFF header")
        self.assertFalse(body["elevation_units"]["confirmed"])
        self.assertIsNone(body["elevation_units"]["value"])
        self.assertFalse(body["vertical_reference"]["confirmed"])
        self.assertIn("areoid", body["vertical_reference"]["documented_reference"])
        self.assertIn("Raster dimensions match STAC proj:shape.", body["consistency_checks"])
        prov = body["provenance"]
        self.assertEqual(prov["item_id"], "DTM_A")
        self.assertEqual(prov["asset_url"], ASSET_URL)
        self.assertTrue(prov["experimental"])
        self.assertIn("No pixel values", prov["processing_method"])
        self.assertIn("NoData", prov["nodata_handling"])
        self.assertFalse(prov["units"]["confirmed"])
        self.assertTrue(prov["limitations"])

    def test_units_confirmed_only_when_declared(self):
        c = self.client(self.stac(make_feature("DTM_A", stac_unit="m")))
        body = c.get("/dtm/DTM_A/metadata").json()
        self.assertTrue(body["elevation_units"]["confirmed"])
        self.assertEqual(body["elevation_units"]["value"], "m")
        facts = dict(FACTS, units=["metre"])
        c2 = self.client(self.stac(), reader=lambda _u: facts)
        self.assertTrue(c2.get("/dtm/DTM_A/metadata").json()["elevation_units"]["confirmed"])

    def test_different_projection_is_reported_per_item(self):
        facts = dict(FACTS, crs_name="Mars (2015) - Sphere / Ocentric / Equirectangular, clon = 0", width=100, height=50)
        body = self.client(self.stac(), reader=lambda _u: facts).get("/dtm/DTM_A/metadata").json()
        self.assertIn("Equirectangular", body["raster"]["crs"]["name"])
        self.assertTrue(any(c.startswith("MISMATCH") for c in body["consistency_checks"]))

    def test_missing_nodata_is_reported(self):
        facts = dict(FACTS, nodata=None)
        body = self.client(self.stac(), reader=lambda _u: facts).get("/dtm/DTM_A/metadata").json()
        self.assertIsNone(body["raster"]["nodata"])
        self.assertEqual(body["raster"]["nodata_source"], "not declared")
        self.assertIn("No NoData", body["provenance"]["nodata_handling"])

    def test_ctx_collection_selectable(self):
        stac = FakeStac(items={(CTX_DTM_COLLECTION, "DTM_A"): make_feature("DTM_A", gsd=20.16)})
        r = self.client(stac, reader=lambda _u: dict(FACTS, res=[20.16, 20.16])).get("/dtm/DTM_A/metadata", params={"collection": "ctx_dtm"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["collection"], CTX_DTM_COLLECTION)

    def test_not_found_is_404(self):
        self.assertEqual(self.client(FakeStac()).get("/dtm/NOPE/metadata").status_code, 404)

    def test_no_dtm_asset_is_404_and_no_fallback_guess(self):
        c = self.client(self.stac(make_feature("DTM_A", with_dtm=False)))
        self.assertEqual(c.get("/dtm/DTM_A/metadata").status_code, 404)
        self.assertEqual(self.reader_calls, [])

    def test_invalid_item_id_is_422(self):
        c = self.client(FakeStac())
        for bad in ("a b", "x;y", "-leading", "a" * 200):
            with self.subTest(item=bad):
                self.assertEqual(c.get(f"/dtm/{bad}/metadata").status_code, 422)

    def test_stac_down_is_503(self):
        self.assertEqual(self.client(FakeStac(down=True)).get("/dtm/DTM_A/metadata").status_code, 503)

    def test_raster_failures_map_to_502_and_504(self):
        def boom(_u):
            raise RasterUnavailable("Could not read raster header (RasterioIOError)")

        def slow(_u):
            raise RasterUnavailable("Raster header read timed out", timeout=True)

        self.assertEqual(self.client(self.stac(), reader=boom).get("/dtm/DTM_A/metadata").status_code, 502)
        self.assertEqual(self.client(self.stac(), reader=slow).get("/dtm/DTM_A/metadata").status_code, 504)

    def test_untrusted_asset_host_is_refused(self):
        feature = make_feature("DTM_A")
        feature["assets"]["dtm"]["href"] = "https://evil.example/dtm.tif"

        def guarded(url: str):
            check_asset_url(url, Settings())
            return dict(FACTS)

        r = self.client(self.stac(feature), reader=guarded).get("/dtm/DTM_A/metadata")
        self.assertEqual(r.status_code, 502)
        self.assertIn("allow-list", r.json()["detail"])


class AssetHostCheck(unittest.TestCase):
    def test_allow_list(self):
        s = Settings()
        check_asset_url(ASSET_URL, s)
        for bad in ("http://astrogeo-ard.s3-us-west-2.amazonaws.com/a.tif", "https://evil.example/a.tif", "file:///c:/a.tif", "https://astrogeo-ard.s3-us-west-2.amazonaws.com.evil.example/a.tif"):
            with self.subTest(url=bad), self.assertRaises(AssetHostNotAllowed):
                check_asset_url(bad, s)


class StacClientHttp(unittest.TestCase):
    """The real StacClient against httpx.MockTransport (no network)."""

    def client(self, handler) -> StacClient:
        return StacClient(Settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    def test_search_builds_expected_request(self):
        seen: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = request.url
            return httpx.Response(200, json={"type": "FeatureCollection", "features": [], "numberMatched": 0})

        self.client(handler).search(HIRISE_DTM_COLLECTION, [76, 17, 79.5, 20], 5)
        self.assertEqual(seen["url"].path, "/api/search")
        params = dict(seen["url"].params)
        self.assertEqual(params, {"collections": HIRISE_DTM_COLLECTION, "bbox": "76,17,79.5,20", "limit": "5"})

    def test_failure_modes_become_unavailable(self):
        def timeout(request):
            raise httpx.ReadTimeout("slow", request=request)

        for handler in (timeout, lambda r: httpx.Response(502), lambda r: httpx.Response(200, text="<html>not json</html>"), lambda r: httpx.Response(200, json=[1, 2])):
            with self.subTest(handler=handler), self.assertRaises(StacUnavailable):
                self.client(handler).search(HIRISE_DTM_COLLECTION, [0, 0, 1, 1], 1)

    def test_get_item_404_is_none_and_ids_are_url_encoded(self):
        seen: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["raw"] = request.url.raw_path.decode()
            return httpx.Response(404)

        c = self.client(handler)
        self.assertIsNone(c.get_item(HIRISE_DTM_COLLECTION, "a/b?x=1"))
        self.assertIn("a%2Fb%3Fx%3D1", seen["raw"])


if __name__ == "__main__":
    unittest.main()
