# TopologyProof

TopologyProof is a local, evidence-driven tool for examining deployment assumptions in Git changes. This initial M0 foundation provides validated server settings, a health endpoint, and a minimal frontend identity shell only; it does not analyze repositories.

## Windows setup

Use Python 3.12 or 3.13 from PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install pip-tools==7.6.1
& .\.venv\Scripts\pip-compile.exe --no-emit-index-url --extra dev --generate-hashes --output-file requirements.lock pyproject.toml
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

## Run and verify

```powershell
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_foundation.py -v
& .\.venv\Scripts\python.exe -m ruff check backend
& .\.venv\Scripts\python.exe -m mypy backend
```

The local health check is `GET http://127.0.0.1:8000/api/v1/health`.

## Trusted webhook fixture

Create the local two-commit webhook fixture when developing or testing the later
analysis pipeline:

```powershell
& .\.venv\Scripts\python.exe -m demo.webhook_dedup.materialize --destination .topologyproof\fixtures\webhook-dedup
git -C .topologyproof\fixtures\webhook-dedup status --short
```

The command prints the repository path, base ref, candidate ref, and requirement
text as JSON. The fixture is a trusted local input for analysis tests; it is not
executed or modified by the later analysis workflow.

## Frontend foundation

Install the frontend dependencies, then start the local Vite server:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

The foundation shell is served at `http://127.0.0.1:5173`. It contains no analysis controls or API integration.

Run the frontend checks from the repository root:

```powershell
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

## Configuration

Copy `.env.example` to `.env` to override settings. The default provider is `offline`; `TOPOLOGYPROOF_OPENAI_API_KEY` and `TOPOLOGYPROOF_OPENAI_MODEL` are blank by default and are not required for the M0 health service. Artifact storage defaults to `.topologyproof/runs` and is ignored by Git.
