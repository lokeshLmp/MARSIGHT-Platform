# MARSIGHT Platform

The web application and service foundation for planetary exploration research. The separate `lokeshLmp/MARSIGHT` Python research repository is outside this project and remains untouched.

## Current state

- Frontend foundation: React, TypeScript, Vite, and Tailwind CSS in `frontend/`.
- Planetary rendering engine selected: CesiumJS, after checking its official support for Mars and Moon ellipsoids. See [the projection decision](docs/map-stack.md).
- Feature status and provenance types are in `frontend/src/shared/contracts/featureStatus.ts`.
- The current interface is an early foundation. NASA imagery, elevation feeds, route analysis, and AI services are not connected. Requirements in the repository do not imply working services or live data.

## Run the frontend

```sh
cd frontend
npm install
npm run dev
```

## Project boundaries

The web client and future platform API belong here. Keep the research repository untouched. Integrate reviewed research outputs through documented API contracts; do not copy research files into this repository. Read [the module boundaries](docs/frontend-architecture.md) before adding features.

