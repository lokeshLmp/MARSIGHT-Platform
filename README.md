# MARSIGHT Platform

MARSIGHT is a modular planetary science platform with a React/Vite frontend and a separate FastAPI backend. Existing USGS STAC discovery and raster-header metadata code is integrated under `backend/science_api`; versioned raster-processing endpoints serve real results when the approved raster is configured. The research repository and its environment are not included.

## Current capabilities and status

- **EXPERIMENTAL — Mars overview globe:** CesiumJS requests the Viking VIS Global Color Mosaic through Mars Trek. It is global color imagery, not shaded relief or a HiRISE DTM visualization.
- **IMPLEMENTED — HiRISE processing API:** computes NoData-aware statistics, bounded elevation/slope/aspect/hillshade windows, and pixel-coordinate profiles for the registered DTM when configured. Terrain Explorer can request statistics and profiles and marks them LIVE only after successful responses.
- **EXPERIMENTAL — Terrain Explorer:** preserves supplied reference metadata separately from live API results. The terrain panel and route sketch remain illustrative and are not pixel-derived.
- **IMPLEMENTED — Dataset discovery and header metadata:** USGS STAC `/datasets` and `/dtm/{id}/metadata` routes preserve the existing backend behavior. The Data Provenance source register remains separate from live catalogue discovery.
- **MOCK — mission route sketch:** local waypoint drawing only. It does not calculate terrain cost, route distance, or safety.
- **PLANNED — mission assistant and operational analysis:** no assistant, validated routing, or safety assessment is connected.

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

The frontend and API run as separate services. No `.env`, API key, raster, AI service, or paid infrastructure is bundled. If the DTM is not configured or cannot be opened, processing endpoints return an explicit unavailable response.

### Processing routes

- `GET /api/v1/dtm/{item_id}/statistics` — windowed full-product summary and valid/NoData counts.
- `GET /api/v1/dtm/{item_id}/window?col_off=…&row_off=…&width=…&height=…` — bounded elevation, slope, aspect, and hillshade arrays, with algorithm and illumination parameters returned.
- `GET /api/v1/dtm/{item_id}/profile?start_col=…&start_row=…&end_col=…&end_row=…&samples=…` — nearest-pixel elevation profile, with sampled coordinates and request parameters returned.

No route-cost or mission-safety analysis is performed.

## Deployment

See [docs/deployment.md](docs/deployment.md) for the separate frontend/API setup, required environment variables, and post-deploy smoke checks.


## License

This project is released under the MIT License. See [LICENSE](LICENSE). The research backend's original MIT license was checked and included.
