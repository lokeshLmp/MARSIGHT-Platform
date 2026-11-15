"""Optional Claude assistant tests. Provider responses are mocked; no paid calls are made."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from backend.app import assistant
from backend.app.main import app
from fastapi import HTTPException, Request
from pydantic import ValidationError


ITEM_ID = "DTEPD_076532_0920_076203_0920_A01"
SECRET_SENTINEL = "never-return-this-test-key"
VALID_MEASURED = {
    "product": {"item_id": ITEM_ID, "instrument": "HiRISE", "mission": "MRO", "region": "South Polar residual cap", "elevation_units": "m", "vertical_datum": "Mars 2000 Datum"},
    "statistics": {"valid_pixels": 900, "nodata_pixels": 100, "minimum": -10.0, "maximum": 20.0, "mean": 4.0, "population_standard_deviation": 3.0},
    "window": {"pixel_bounds": {"col_off": 0, "row_off": 0, "width": 32, "height": 32}, "elevation": {"valid_cells": 900, "minimum": -1.0, "maximum": 5.0, "mean": 2.0}, "slope_degrees": {"valid_cells": 850, "minimum": 0.0, "maximum": 19.0, "mean": 3.2}, "aspect_degrees_clockwise_from_north": {"valid_cells": 830, "minimum": 5.0, "maximum": 350.0, "mean": 180.0}, "hillshade_0_255": {"valid_cells": 850, "minimum": 20.0, "maximum": 240.0, "mean": 160.0}},
    "profile": None,
    "provenance": {"sources": ["PDS product label"], "statistics_method": "windowed", "window_method": "Horn 3x3", "limitations": ["No safety assessment"], "nodata_treatment": "invalid cells excluded"},
}
MODEL_JSON = json.dumps({
    "summary": "The measured window has a modest mean slope, with some steeper cells.",
    "observations": ["Slope ranges from 0 to 19 degrees in this window."],
    "limitations": ["This is a small window, not a route assessment.", "Verify against source measurements."],
})


class FakeAsyncClient:
    response_text = MODEL_JSON
    failure: Exception | None = None
    instances: list["FakeAsyncClient"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.messages = types.SimpleNamespace(create=AsyncMock(side_effect=self._create))
        self.instances.append(self)

    async def _create(self, **kwargs):
        self.payload = kwargs
        if self.failure is not None:
            raise self.failure
        return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=self.response_text)])

    async def close(self):
        return None


class RouteResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self.body = body
        self.text = json.dumps(body)

    def json(self):
        return self.body


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        assistant.reset_rate_limit_state()
        FakeAsyncClient.instances.clear()
        FakeAsyncClient.failure = None
        FakeAsyncClient.response_text = MODEL_JSON
        self.environment = patch.dict(os.environ, {
            "MARSIGHT_CLAUDE_ENABLED": "true",
            "ANTHROPIC_API_KEY": SECRET_SENTINEL,
            "ANTHROPIC_MODEL": "claude-haiku-5-5",
        }, clear=False)
        self.environment.start()
        self.fake_sdk = types.SimpleNamespace(
            AsyncAnthropic=FakeAsyncClient,
            RateLimitError=type("RateLimitError", (Exception,), {}),
            BillingError=type("BillingError", (Exception,), {}),
            AuthenticationError=type("AuthenticationError", (Exception,), {}),
            PermissionDeniedError=type("PermissionDeniedError", (Exception,), {}),
            APITimeoutError=type("APITimeoutError", (Exception,), {}),
            APIStatusError=type("APIStatusError", (Exception,), {"__init__": lambda self, status_code, message="provider failure": (setattr(self, "status_code", status_code), Exception.__init__(self, message))[-1]}),
            APIConnectionError=type("APIConnectionError", (Exception,), {}),
        )
        self.sdk_modules = patch.dict(sys.modules, {"anthropic": self.fake_sdk})
        self.sdk_modules.start()

    def tearDown(self):
        self.sdk_modules.stop()
        self.environment.stop()
        assistant.reset_rate_limit_state()

    def post(self, body: dict):
        try:
            request_body = assistant.TerrainSummaryRequest.model_validate(body)
        except ValidationError as exc:
            return RouteResponse(422, {"detail": exc.errors(include_input=False)})

        request = Request({
            "type": "http", "method": "POST", "scheme": "http", "path": "/api/assistant/terrain-summary",
            "raw_path": b"/api/assistant/terrain-summary", "query_string": b"", "headers": [],
            "client": ("test-client", 12345), "server": ("test", 80), "root_path": "",
        })

        async def immediate_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch.object(assistant.asyncio, "to_thread", new=immediate_to_thread):
            coroutine = assistant.terrain_summary(request_body, request)
            try:
                result = coroutine.send(None)
            except StopIteration as completed:
                return RouteResponse(200, completed.value.model_dump(mode="json"))
            except HTTPException as exc:
                return RouteResponse(exc.status_code, {"detail": exc.detail})
            finally:
                coroutine.close()
        raise AssertionError("Mocked assistant route unexpectedly yielded to an event loop")

    def request_body(self):
        return {"item_id": ITEM_ID, "col_off": 0, "row_off": 0, "width": 32, "height": 32}

    def test_aspect_summary_uses_circular_mean(self):
        result = assistant._summarize_aspects([[350.0, 10.0, None]])
        self.assertAlmostEqual(result["circular_mean"], 0.0, places=7)
        self.assertEqual(result["valid_cells"], 2)

    def test_success_uses_measured_context_and_returns_separated_interpretation(self):
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["measured"], VALID_MEASURED)
        self.assertIn("slope", body["interpretation"]["observations"][0].lower())
        self.assertIn("verify", body["verification_notice"].lower())
        self.assertEqual(FakeAsyncClient.instances[0].kwargs["api_key"], SECRET_SENTINEL)
        sent = FakeAsyncClient.instances[0].payload["messages"][0]["content"]
        self.assertNotIn("raster_array", sent)
        self.assertEqual(FakeAsyncClient.instances[0].payload["max_tokens"], assistant.MAX_OUTPUT_TOKENS)
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_missing_api_key_keeps_assistant_unavailable_without_provider_call(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}), patch.object(assistant, "_collect_measured_context") as collect:
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(FakeAsyncClient.instances, [])
        collect.assert_not_called()
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_invalid_request_is_rejected_before_provider(self):
        body = self.request_body() | {"width": 65, "unexpected": "secret"}
        response = self.post(body)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(FakeAsyncClient.instances, [])

    def test_provider_failure_is_safe_and_does_not_leak_exception_text(self):
        error_type = self.fake_sdk.APIStatusError
        FakeAsyncClient.failure = error_type(500, f"provider error included {SECRET_SENTINEL}")
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 502)
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_provider_rate_limit_maps_to_429(self):
        FakeAsyncClient.failure = self.fake_sdk.RateLimitError(SECRET_SENTINEL)
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 429)
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_provider_timeout_maps_to_gateway_timeout(self):
        FakeAsyncClient.failure = self.fake_sdk.APITimeoutError(SECRET_SENTINEL)
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 504)
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_workspace_usage_limit_maps_to_payment_required_without_details(self):
        FakeAsyncClient.failure = self.fake_sdk.APIStatusError(402, f"billing details {SECRET_SENTINEL}")
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 402)
        self.assertNotIn(SECRET_SENTINEL, response.text)

    def test_application_rate_limit_blocks_fourth_request(self):
        with patch.object(assistant, "_collect_measured_context", return_value=VALID_MEASURED):
            results = [self.post(self.request_body()) for _ in range(4)]
        self.assertEqual([result.status_code for result in results], [200, 200, 200, 429])
        self.assertEqual(len(FakeAsyncClient.instances), 3)

    def test_missing_real_raster_does_not_send_reference_or_mock_to_provider(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MARSIGHT_DTM_PATH", None)
            response = self.post(self.request_body())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(FakeAsyncClient.instances, [])

    def test_health_exposes_readiness_but_never_the_secret(self):
        from backend.app.main import health

        result = health().model_dump(mode="json")
        self.assertTrue(result["ai"]["enabled"])
        self.assertEqual(result["ai"]["model"], "claude-haiku-5-5")
        self.assertEqual(result["ai"]["project_cap_usd"], 5)
        self.assertNotIn(SECRET_SENTINEL, json.dumps(result))
        self.assertIn("/api/assistant/terrain-summary", app.openapi()["paths"])
        from starlette.middleware.cors import CORSMiddleware
        cors = next(middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware)
        self.assertIn("POST", cors.kwargs["allow_methods"])
        self.assertIn("Content-Type", cors.kwargs["allow_headers"])

    def test_core_health_remains_available_without_key_or_ai_flag(self):
        from backend.app.main import health

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "", "MARSIGHT_CLAUDE_ENABLED": "false"}):
            result = health()
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.ai.enabled)


if __name__ == "__main__":
    unittest.main()
