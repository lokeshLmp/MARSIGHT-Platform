# Architecture and module boundaries

Start as a modular frontend with explicit service boundaries. Add a Python/FastAPI backend as a separate service when the first reviewed data or analysis endpoint is ready. Do not copy or import the research repository into this codebase.

- `src/app`: composition, routes, and application shell.
- `src/features`: user-facing capability modules (map, research, routes, mission workspace).
- `src/shared/contracts`: cross-feature TypeScript contracts and status/provenance types.
- `src/shared/ui`: reusable presentation components.
- `docs`: decisions, source policies, and operational notes.

Every data-backed feature should state its status, source, retrieval time where known, and limitations. Keep sample data visibly marked and never describe it as live.
