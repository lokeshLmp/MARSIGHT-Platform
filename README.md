# MARSIGHT Platform

**A modular planetary science platform for discovering, exploring, and analysing Mars terrain data.**

MARSIGHT combines an interactive Mars visualization experience with a scientific data backend. It integrates USGS Astrogeology's SpatioTemporal Asset Catalog (STAC) for Mars Digital Terrain Model (DTM) discovery and provides Rasterio/NumPy-based processing for explicitly registered elevation rasters.

The platform is built with React, TypeScript, Vite, CesiumJS, Python, and FastAPI. Its architecture separates interactive visualization, scientific data discovery, raster processing, and optional AI-assisted interpretation.

**Project links**
- Frontend: https://marsight-platform-web.onrender.com
- Backend API: https://marsight-platform-api.onrender.com
- GitHub repository: https://github.com/lokeshLmp/MARSIGHT-Platform

---

## 1. Platform capabilities and implementation status

| Component | Status | Description |
|---|---|---|
| Mars overview globe | Experimental | CesiumJS displays the Viking Visual Imaging Subsystem (VIS) Global Color Mosaic through Mars Trek. This is global color imagery, not a live DTM or shaded-relief visualization. |
| USGS dataset discovery | Implemented | Searches the configured USGS STAC collections for HiRISE and CTX DTM products. |
| Raster metadata | Implemented | Retrieves and exposes metadata for discovered DTM products. |
| HiRISE raster processing | Implemented, configuration-dependent | Supports NoData-aware statistics, elevation windows, slope, aspect, analytical hillshade, and elevation profiles for the registered HiRISE product. |
| CTX raster access | Locally tested; integration pending | A real USGS CTX GeoTIFF has been opened and sampled successfully with Rasterio. It has not yet been added to the server-side processing registry. |
| Terrain Explorer | Experimental | Displays terrain-related information while distinguishing supplied reference metadata from live API results. |
| Mission route sketch | Mock / illustrative | Allows local waypoint drawing. It does not calculate terrain costs, route distances, or mission safety. |
| Claude terrain research assistant | Optional; end-to-end verification pending | Designed to interpret measured raster statistics, bounded terrain windows, and optional elevation profiles. Requires an approved registered raster and backend provider configuration. |

**Important distinction:** discovering a dataset through STAC does not mean its raster has been downloaded, registered, or processed. Live processing is available only when the corresponding approved raster is configured and passes server-side validation.

## 2. Scientific data sources

MARSIGHT uses planetary data products from the following sources:

- **USGS Astrogeology Science Center:** Mars DTM catalogue discovery and raster products.
- **HiRISE:** High-resolution stereo-derived Mars terrain products from the Mars Reconnaissance Orbiter.
- **CTX:** Context Camera-derived terrain products from the Mars Reconnaissance Orbiter.
- **Mars Trek:** Viking VIS Global Color Mosaic used for the experimental Mars overview globe.
- **Planetary Data System (PDS):** Product documentation and scientific metadata used to establish product identity and processing references.

The application currently queries these STAC collections:

- `mro_hirise_socet_dtms`
- `mro_ctx_controlled_usgs_dtms`

Dataset discovery returns catalogue metadata and asset references. It does not automatically make every discovered raster available to the processing API.

## 3. Registered HiRISE reference product

The existing server-side raster registry supports:

**Product ID:** `DTEPD_076532_0920_076203_0920_A01`

| Attribute | Value |
|---|---|
| Mission | Mars Reconnaissance Orbiter |
| Instrument | High Resolution Imaging Science Experiment (HiRISE) |
| Producer | University of Arizona |
| Target | Mars |
| Region | South Polar residual cap |
| Map scale | 2 m/pixel |
| Projection | Mars polar stereographic |
| Elevation reference | Mars 2000 Datum |
| Elevation units | Metres |
| NoData | Approximately `-3.4028226550889045e+38` (Float32) |

The product's PDS documentation is used as the reference for its map scale, elevation units, and vertical reference.

The raster itself is not bundled in this repository. Its location is configured using the backend-only environment variable:

`MARSIGHT_DTM_PATH`

The registry validates the configured raster against the expected dimensions, band count, data type, NoData value, pixel scale, and projected Mars polar CRS.

Only explicitly registered products are accepted by the scientific processing endpoints.

### CTX raster validation progress

A separate CTX product was successfully accessed and inspected locally:

`T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W`

The tested geoid-adjusted GeoTIFF returned:

- Dimensions: 1203 × 1568 pixels
- Bands: 1
- Data type: Float32
- Pixel spacing: 20 × 20 projected CRS units
- CRS: Mars 2015 Ocentric Equirectangular
- NoData: -32767
- Valid pixels in the inspected 128 × 128 sample: 16,383
- Sample minimum: approximately -2946.62
- Sample maximum: approximately -2922.71
- Sample mean: approximately -2934.73

These values are from a local raster sample, not full-product statistics. The GeoTIFF reports no explicit elevation band units, so the sample values are not labelled as verified metres.

**CTX integration is pending:** the tested product has not yet been added to `dataset_registry.py` or made available through the production terrain-processing endpoints.

## 4. Scientific processing methodology

The scientific processing module is implemented independently of the FastAPI request handlers.

### Full-raster statistics

- Processes raster data in bounded row windows.
- Excludes NoData and non-finite values.
- Calculates valid and invalid pixel counts.
- Calculates minimum, maximum, mean, and population standard deviation.
- Uses mergeable population moments with Float64 calculations.

### Terrain windows

- Reads bounded raster windows.
- Supports windows up to 512 × 512 cells.
- Calculates elevation values.
- Uses Horn's 3 × 3 finite-difference method for slope and aspect.
- Calculates analytical hillshade using configurable illumination angles.
- Returns null derivative values at raster edges and incomplete NoData neighborhoods.
- Returns null aspect values for flat cells.

### Elevation profiles

- Samples nearest raster pixels along a straight segment.
- Returns pixel coordinates, elevations, and sampled distances.
- Uses the raster affine transformation for coordinate calculations.
- Reports distances in raster CRS units rather than assuming an unverified conversion to metres.

### Scientific limitations

MARSIGHT is a terrain exploration and research platform, not a validated mission navigation system.

- Raster statistics describe the selected product, not the entire Martian surface.
- Different instruments and DTM products have different spatial resolutions and coordinate systems.
- Projection distortion is not corrected in the current derivative calculation.
- Elevation units and vertical references must be established for each registered product.
- Hillshade is an analytical visualization, not a calibrated photometric observation.
- No terrain-aware route optimization, hazard classification, or mission safety assessment is implemented.
- The experimental globe imagery is not a substitute for raster-backed terrain visualization.

API responses include raster metadata, algorithm descriptions, processing timestamps, provenance, NoData treatment, and applicable limitations.

## 5. Architecture and technology stack

### Frontend

- React
- TypeScript
- Vite
- CesiumJS
- JavaScript / CSS

### Backend

- Python
- FastAPI
- Rasterio
- GDAL
- NumPy
- Pydantic

### Data and scientific infrastructure

- USGS Astrogeology STAC
- HiRISE and CTX Mars DTM products
- Planetary coordinate reference systems
- GeoTIFF raster processing

### Optional AI integration

- Anthropic Python SDK
- Claude terrain research assistant
- Server-side measured-data interpretation

### Deployment

- Render Web Service for the FastAPI backend
- Render Static Site for the frontend
- Environment-based configuration for API URLs, raster locations, and optional provider credentials

The frontend and backend are deployed separately.

See:
- [Frontend architecture](docs/frontend-architecture.md)
- [Map stack decision](docs/map-stack.md)
- [Architecture notes](docs/architecture.md)
- [Deployment guide](docs/deployment.md)

## 6. Repository structure

```text
MARSIGHT-Platform/
│
├── frontend/
│   └── src/
│       └── React application and visualization
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── assistant.py
│   │
│   ├── science_api/
│   │   ├── dataset_registry.py
│   │   ├── terrain_processing.py
│   │   └── terrain_routes.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── requirements-ai.txt
│
├── docs/
│   ├── architecture.md
│   ├── frontend-architecture.md
│   ├── map-stack.md
│   └── deployment.md
│
├── LICENSE
└── README.md
```

## 7. Installation and local development

### Prerequisites

- Node.js and npm
- Python 3.12 recommended
- A Python environment with compatible Rasterio/GDAL dependencies

### Frontend

From the repository root:

```bash
cd frontend
npm ci
npm test
npm run build
npm run dev
```

The development server starts the Vite frontend.

If the backend is hosted at a different address, configure the API origin before starting Vite.

PowerShell:

```powershell
$env:VITE_MARSIGHT_API_URL = "http://localhost:8000"
npm run dev
```

### Backend

From the repository root:

```powershell
python -m venv .venv

.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

The API documentation is available at:

`http://localhost:8000/docs`

### Configure the registered HiRISE raster

Set the path to an approved local raster file:

```powershell
$env:MARSIGHT_DTM_PATH = "D:\data\DTEPD_076532_0920_076203_0920_A01.IMG"
```

The path must point to a file accessible from the backend process. An S3 or HTTPS URL cannot be substituted directly for this local-file configuration.

The raster is not included in the repository.

### Backend tests

From the repository root:

```powershell
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

### Optional Claude dependency

Install the additional dependency only when enabling the optional AI assistant:

```powershell
.venv\Scripts\python.exe -m pip install -r backend\requirements-ai.txt
```

The core API does not require the Anthropic SDK or an API key.

## 8. Optional Claude terrain research assistant

MARSIGHT includes an optional endpoint for AI-assisted interpretation of measured terrain information.

**Endpoint:**

`POST /api/assistant/terrain-summary`

The backend prepares a compact evidence package containing:

- Registered product metadata
- Full-product raster statistics
- A bounded elevation and terrain-derivative window
- An optional elevation profile
- Data provenance and scientific limitations

Claude receives these measured results and generates an interpretation separately from the numerical measurements.

### Configuration

The following variables belong exclusively to the backend service:

```text
ANTHROPIC_API_KEY=<backend secret>
ANTHROPIC_MODEL=claude-haiku-5-5
MARSIGHT_CLAUDE_ENABLED=true
```

Never expose `ANTHROPIC_API_KEY` through Vite, frontend environment variables, or browser code.

The feature requires both explicit enablement and a valid backend API key. It also requires an approved registered raster for the requested product.

### Usage limitations

- Provider requests are rate-limited to three per client per minute.
- The configured response limit is 600 output tokens.
- Only compact measured summaries are sent to the provider.
- Claude interpretations are not replacements for scientific validation.
- No route safety or mission survival assessment is produced.
- A project spending limit must be configured in the Anthropic Console; the application does not independently enforce the monthly spending cap.

The application keeps measured values and AI-generated interpretations in separate response fields.

## 9. API endpoints

### Health and discovery

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Backend health and optional AI configuration status |
| `/datasets` | GET | Search supported USGS STAC DTM collections |
| `/dtm/{item_id}/metadata` | GET | Retrieve DTM asset metadata |

Dataset discovery requires a bounding box:

```text
GET /datasets?collection=all&limit=2&bbox=-180,-90,180,90
```

Supported collection values:

- `all`
- `hirise_dtm`
- `ctx_dtm`

### Scientific processing

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/dtm/{item_id}/statistics` | GET | Full-product NoData-aware statistics |
| `/api/v1/dtm/{item_id}/window` | GET | Bounded elevation, slope, aspect, and hillshade |
| `/api/v1/dtm/{item_id}/profile` | GET | Nearest-pixel elevation profile |

### Optional AI

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/assistant/terrain-summary` | POST | AI interpretation of measured raster analysis |

The processing endpoints accept only products explicitly registered and validated by the backend. STAC discovery alone does not authorize raster processing.

## 10. Deployment

MARSIGHT uses two independent Render services:

**Frontend Static Site**

- Repository: `lokeshLmp/MARSIGHT-Platform`
- Service: `marsight-platform-web`
- URL: https://marsight-platform-web.onrender.com

**Backend Web Service**

- Repository: `lokeshLmp/MARSIGHT-Platform`
- Service: `marsight-platform-api`
- URL: https://marsight-platform-api.onrender.com

The frontend uses `VITE_MARSIGHT_API_URL` to communicate with the backend.

The backend stores sensitive configuration and any approved raster path server-side. A raster must actually exist within the backend service's accessible filesystem before processing endpoints can use it.

For complete deployment instructions and smoke tests, see [docs/deployment.md](docs/deployment.md).

## 11. Security and configuration

- API keys are stored as backend secrets.
- Raster filesystem paths are not exposed to frontend clients.
- Only explicitly registered datasets are accepted for scientific processing.
- API request models validate input and reject unexpected fields.
- Terrain window dimensions and assistant output are bounded.
- Optional AI functionality is separated from core scientific API functionality.

Do not commit `.env` files, provider secrets, private raster files, or locally generated virtual environments.

## 12. License

This project is released under the **MIT License**.

See [LICENSE](LICENSE) for the complete license text.

The original research backend's MIT license has been checked and included.

---

**MARSIGHT — Exploring the Martian surface through planetary data, scientific computation, and interactive visualization.**
