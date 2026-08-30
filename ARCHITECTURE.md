# TopologyProof architecture

## Implemented M0 boundary

The M0 service is a FastAPI application factory in `backend/app/main.py`. `backend/app/config.py` owns validated, environment-backed settings. `backend/app/api/health.py` exposes the versioned health contract through `backend/app/api/router.py`. The M0 frontend foundation lives in `frontend/`: a Vite/React/TypeScript application with a mountable product-identity shell plus locked local install, lint, typecheck, test, and production-build tooling. It deliberately contains no product workflow or API integration.

The application is local by default: it binds to loopback, uses the `offline` provider setting, and stores future TopologyProof artifacts beneath `.topologyproof/runs`. Empty OpenAI configuration values are treated as absent secrets.

## Trust boundary

This task does not accept, inspect, execute, or modify target repositories. No analysis pipeline, runtime verification, frontend product workflow, benchmark, evaluation, fixture, or submission artifact exists in the M0 foundation.

## Package layout

- `backend/app/config.py`: server configuration and validated limits.
- `backend/app/errors.py`: typed domain error base class.
- `backend/app/api/`: versioned HTTP routes.
- `backend/app/main.py`: FastAPI application factory.
- `backend/tests/`: foundation tests.
- `frontend/`: mountable React/Vite identity shell, strict TypeScript, linting, tests, and production build tooling.
