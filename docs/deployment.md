# Render deployment guide

MARSIGHT runs as two Render services: the Vite frontend and the FastAPI backend. The root `render.yaml` defines both, the backend health check, the frontend API URL, and a single allowed frontend origin. Deploy from the connected GitHub repository and inspect the generated hostnames before relying on the configured origins; if Render assigns a different hostname, update `MARSIGHT_ALLOWED_ORIGINS` on the API service and `VITE_MARSIGHT_API_URL` on the static site to the exact deployed origins, then redeploy both.

## Frontend

From `frontend/`:

```sh
npm ci
npm test
npm run build
```

Render publishes the generated `frontend/dist/` directory as a static site. Its build-time variable must be the HTTPS origin of the deployed API (no path suffix):

```text
VITE_MARSIGHT_API_URL=https://<your-api-host>
```

The checked-in `frontend/.env.example` is for local development; do not use its localhost value in a public build.

## Backend

The Render web service installs `backend/requirements.txt` and starts Uvicorn on Render's assigned port. The process binds to `0.0.0.0` and exposes `/health` as its health check.

```sh
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

The Blueprint sets these non-secret service environment variables:

```text
MARSIGHT_ALLOWED_ORIGINS=https://<your-frontend-host>
```

`MARSIGHT_DTM_PATH` is intentionally unset: no real HiRISE raster was found in the available project data. Raster-backed statistics, windows, and profiles therefore return an explicit unavailable response. Configure this variable only after placing an approved raster on storage available to the service; do not publish static reference numbers as live processing results. The current free Render web-service plan has an ephemeral filesystem, so it is not suitable for persisting a large DTM between deploys. USGS STAC discovery and header reads also require outbound access to the configured USGS STAC service and approved asset host.

Keep frontend and API origins HTTPS, do not place API secrets in frontend variables, and do not add credentials or raster data to Git. The optional Claude feature requires `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, and `MARSIGHT_CLAUDE_ENABLED=true` on the backend only. The Blueprint leaves Claude disabled and uses `sync: false` for the secret; set the key through Render's secret prompt or dashboard, then enable the feature deliberately. The static frontend never receives the key. MARSIGHT applies a process-local limit of three assistant requests per client per minute; the Anthropic workspace monthly spending limit remains the authoritative cost cap and is not enforced by MARSIGHT itself. Render's free web service may sleep after inactivity, so the first API request may be delayed.

## Deployment smoke check

1. Open `https://<your-api-host>/health`; expect HTTP 200 and `status: "ok"`.
2. Open `https://<your-api-host>/datasets?...` with a valid bounding box and collection; expect a validated response or a clear source-unavailable response.
3. Test `GET /dtm/DTEPD_076532_0920_076203_0920_A01/metadata`.
4. With the raster configured, test `/api/v1/dtm/DTEPD_076532_0920_076203_0920_A01/statistics`, a small `/window`, and a short `/profile` request.
5. Load the deployed frontend and confirm its browser network requests reach the API without CORS errors. Confirm the application labels any unavailable or mock feature accurately.

A public demo URL is valid only after these remote checks pass. Adding `render.yaml` prepares the services but does not create them; the Blueprint must be deployed from the Render Dashboard after this repository is pushed to GitHub. Record the actual Render URLs only after the first deploy succeeds and the checks above pass.
