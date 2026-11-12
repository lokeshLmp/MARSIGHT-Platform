# MARSIGHT frontend module boundaries

The first frontend is a modular application, not a microfrontend fleet. Keep domain features isolated and let the application shell compose them.

- `frontend/src/app`: application composition and navigation.
- `frontend/src/features`: user-facing capability modules such as maps, research, routes, and mission workspaces.
- `frontend/src/shared/contracts`: typed cross-feature contracts, status, provenance, and limitations.
- `frontend/src/shared/ui`: reusable presentation components.
- `docs`: architecture decisions, data-source review, and product limitations.

A future FastAPI service may provide documented endpoints for reviewed datasets and analyses. The current `requirements.txt` lists dependencies only; it does not indicate that API endpoints, science processing, or data feeds are implemented.

Every data-backed feature should identify its state, source, retrieval time when known, and limitations. Clearly label sample or prototype content. Never imply live NASA connections or validated operational recommendations without evidence and implementation.

