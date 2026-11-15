> **Archived plan:** this document records earlier development gates. The backend and frontend integration now exist in this checkout. Its older "planning only" and "current boundary" statements are historical. See [README.md](../README.md) and [deployment.md](deployment.md) for the current implementation and remaining deployment requirements.
# FastAPI backend foundation plan

## Status

Planning only. Do not create the API, install backend dependencies, make Anthropic requests, or consume API credits until the platform scaffold is committed and synchronized with its intended GitHub repository and the owner confirms the billing setup.

## Phase 0: unblock safely

1. Confirm that `work/MARSIGHT-Platform` is the canonical platform repository and reconcile it with `outputs/MARSIGHT-Platform-scaffold` (the output copy currently contains a frontend but has no visible Git metadata).
2. Confirm the intended GitHub repository, establish its remote, review the full diff, and commit/push the reviewed scaffold. The working copy currently has no commits and no remote configured, so it is not synchronized.
3. Confirm Anthropic account type and billing controls in the account owner’s Console UI. Verify the available credit is API credit (not a Claude subscription benefit), locate model availability, configure the project-level cap and disable auto-reload if offered. Keep API use disabled until the owner confirms these controls.

## Phase 1: service skeleton (after Phase 0)

- Add a `backend/` Python package using FastAPI, with dependency versions pinned in a project-local dependency file and a documented local development command.
- Add `GET /health` returning service status and API version only; it must not make network or model calls.
- Add Pydantic request/response schemas and a versioned `/api/v1` route prefix. Keep the existing frontend contracts and feature-status vocabulary authoritative; document any deliberate schema changes.
- Add configuration through environment variables, a safe `.env.example`, and startup validation. Never commit API keys or print secrets.
- Add CORS configuration limited to the local frontend origin during development; make allowed origins explicit configuration for deployment.
- Keep providers behind interfaces. The default implementation is a deterministic mock/sample provider, clearly labeled as such. No Anthropic client is initialized by default.

## Phase 2: reviewed data and analysis contracts

- Define typed contracts for planetary body, coordinates, dataset/source provenance, retrieval time, data state, limitations, and analysis results.
- Add read-only endpoints only after the corresponding source and license have been reviewed. Return provenance and limitations with every data-backed response.
- Keep route-analysis responses explicitly unvalidated for operational use until scientific methods and test datasets have been reviewed.

## Phase 3: optional AI adapter (separate owner decision)

- Treat AI as opt-in and disabled by default. Require an explicit feature flag and server-side API key before enabling the adapter.
- Use only model IDs verified in the Console at implementation time; do not assume a model based on prior notes.
- Enforce a per-request token ceiling, request timeout, bounded retries, and an application-side cumulative spend guard that fails closed. The provider-side $25 project limit remains the primary billing control; application limits are only a secondary guard.
- Show source material, model identity, generation time, and limitations to callers. Do not present generated output as validated mission advice.
- Start with a tiny, owner-approved smoke request only after synchronization and a second explicit confirmation. Record its expected cost before making it.

## Review gates

- Before implementation: canonical repo, GitHub remote, clean reviewed commit, and successful synchronization.
- Before any Anthropic request: verified API-credit account, model access, auto-reload state, project budget/cap, and owner confirmation.
- Before deployment: secrets management, origin policy, rate limits, logs without secrets, and operational ownership.

## Current boundary

The existing repository is a frontend foundation. NASA imagery, elevation feeds, route analysis, and AI services are not connected. This plan does not claim that live data or a backend exists.
