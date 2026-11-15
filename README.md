# MARSIGHT Platform

MARSIGHT is a modular planetary science platform with a React/Vite frontend and a separate FastAPI backend. Existing USGS STAC discovery and raster-header metadata code is integrated under `backend/science_api`; versioned raster-processing endpoints serve real results when the approved raster is configured. The research repository and its environment are not included.

## Current capabilities and status

- **EXPERIMENTAL — Mars overview globe:** CesiumJS requests the Viking VIS Global Color Mosaic through Mars Trek. It is global color imagery, not shaded relief or a HiRISE DTM visualization.
- **IMPLEMENTED — HiRISE processing API:** computes NoData-aware statistics, bounded elevation/slope/aspect/hillshade windows, and pixel-coordinate profiles for the registered DTM when configured. Terrain Explorer can request statistics and profiles and marks them LIVE only after successful responses.
- **EXPERIMENTAL — Terrain Explorer:** preserves supplied reference metadata separately from live API results. The terrain panel and route sketch remain illustrative and are not pixel-derived.
- **IMPLEMENTED — Dataset discovery and header metadata:** USGS STAC `/datasets` and `/dtm/{id}/metadata` routes preserve the existing backend behavior. The Data Provenance source register remains separate from live catalogue discovery.
- **MOCK — mission route sketch:** local waypoint drawing only. It does not calculate terrain cost, route distance, or safety.
- **OPTIONAL — Claude terrain research assistant:** on explicit user request, the backend summarizes measured statistics, a bounded real-raster window, and an optional profile. It is disabled unless both `MARSIGHT_CLAUDE_ENABLED=true` and the backend-only `ANTHROPIC_API_KEY` are configured. It does not analyze the illustrative surface and is not a route-safety assessment. Provider responses are tested with mocks; a real Claude call has not been made.

## HiRISE reference and scientific limits

The registered product is `DTEPD_076532_0920_076203_0920_A01`, a HiRISE stereo DTM from the Mars Reconnaissance Orbiter, produced by the University of Arizona for the South Polar residual cap. The PDS label provides the 2 m/pixel map scale, Mars polar stereographic projection, and elevation in metres above the Martian equipotential surface (Mars 2000 Datum). It specifies NoData bits `16#FF7FFFFB#` (float32 approximately `-3.4028226550889045e+38`). The raster is not copied into this repository. Configure its external location using `MARSIGHT_DTM_PATH`; the server-side registry exposes no filesystem paths and rejects unregistered products. The configured file is checked against published dimensions, band type, NoData value, and pixel scale.

Full-raster statistics use bounded row windows. Terrain-window reads are limited to 512 × 512 cells. Slope/aspect use Horn 3×3 finite differences with the PDS 2 m/pixel map scale; edge cells and incomplete NoData neighborhoods are null, and aspect is undefined on flat cells. Local projection distortion is not corrected. Hillshade is an analytical visualization controlled by requested illumination angles. Elevation profiles use nearest-pixel samples and report distance in raster CRS units. The raster header reports the CRS linear unit as unknown, so profile distances are not labeled metres. Responses include product metadata, method, processing timestamp, provenance, NoData treatment, and limitations. Statistics apply to this product only. No terrain-aware routing, safety assessment, or raster-backed map visualization is implemented.

## Architecture

The React application lives under `frontend/src`; the API is in `backend/`. The STAC discovery/header client remains separate from `backend/science_api/terrain_processing.py`, which provides reusable Rasterio/NumPy calculations independent of FastAPI handlers. `VITE_MARSIGHT_API_URL` configures the browser API origin. The raster path stays server-side. See [frontend boundaries](docs/frontend-architecture.md), [map-engine decision](docs/map-stack.md), and [architecture notes](docs/architecture.md).

## Run the frontend

Requires Node.js and npm.

```sh
cd frontend
npm ci
npm test
npm run build
npm run dev
```

In PowerShell, set `VITE_MARSIGHT_API_URL` in the Vite process when the API is hosted somewhere other than `http://localhost:8000`:

```powershell
$env:VITE_MARSIGHT_API_URL = 'http://localhost:8000'
npm run dev
```

## Run backend tests

After installing `backend/requirements.txt`, run from the repository root:

```sh
python -m unittest discover -s backend/tests -v
```
## Run the API

Install `backend/requirements.txt` in a Python environment with Rasterio's GDAL runtime available. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:MARSIGHT_DTM_PATH = 'D:\data\DTEPD_076532_0920_076203_0920_A01.IMG'
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

The frontend and API run as separate services. No `.env`, API key, or raster is bundled. Install `backend/requirements.txt` for the core API. Install `backend/requirements-ai.txt` only when enabling the optional Claude assistant; core application routes do not need the SDK, an API key, or a provider call. If the DTM is not configured or cannot be opened, processing and assistant endpoints return an explicit unavailable response.

### Optional Claude configuration

Set these variables only on the backend. Never define `ANTHROPIC_API_KEY` as a Vite variable or in the static frontend service.

```text
ANTHROPIC_API_KEY=<secret stored by the backend host>
ANTHROPIC_MODEL=claude-haiku-5-5
MARSIGHT_CLAUDE_ENABLED=true
```

The chosen default model is currently listed as active by Anthropic and priced at $0.10 per million input tokens and $0.50 per million output tokens for prompts up to 100,000 tokens. MARSIGHT sends compact summaries only, limits responses to 600 tokens, and limits each client to three requests per minute. The $5 monthly workspace limit is controlled in the Anthropic Console; it is not an application-enforced budget. Review [model status](https://docs.anthropic.com/en/docs/about-claude/model-deprecations) and [current pricing](https://docs.anthropic.com/en/docs/about-claude/pricing) before changing the model.

The endpoint is `POST /api/assistant/terrain-summary`. It requires the real registered raster and returns measured inputs separately from Claude's interpretation. Missing configuration or raster data does not affect the core MARSIGHT APIs. The official Anthropic Python SDK is installed from `backend/requirements-ai.txt`; this workspace currently has no network access to PyPI, so local tests use a mocked SDK client.

### Processing routes

- `GET /api/v1/dtm/{item_id}/statistics` — windowed full-product summary and valid/NoData counts.
- `GET /api/v1/dtm/{item_id}/window?col_off=…&row_off=…&width=…&height=…` — bounded elevation, slope, aspect, and hillshade arrays, with algorithm and illumination parameters returned.
- `GET /api/v1/dtm/{item_id}/profile?start_col=…&start_row=…&end_col=…&end_row=…&samples=…` — nearest-pixel elevation profile, with sampled coordinates and request parameters returned.

No route-cost or mission-safety analysis is performed.

## Deployment

See [docs/deployment.md](docs/deployment.md) for the separate frontend/API setup, required environment variables, and post-deploy smoke checks.


## License

This project is released under the MIT License. See [LICENSE](LICENSE). The research backend's original MIT license was checked and included.
