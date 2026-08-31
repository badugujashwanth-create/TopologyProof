# TopologyProof

Agentic falsification of hidden deployment assumptions. TopologyProof asks which deployment assumptions a backend patch silently depends on, then produces bounded evidence and the smallest recommended falsification experiment.

## Demonstrated M1

The trusted FastAPI webhook fixture uses process-local `processed_events` state to guard durable `record_payment`. Static analysis connects membership, mutation, duplicate suppression, and the side effect. The result is a **HIGH RISK** finding with overall **REVIEW REQUIRED** and runtime **NOT EXECUTED**. Static evidence alone never produces RED.

The four-screen demo is New Analysis, Analysis Progress, Findings Dashboard, and Finding Detail / Verification Recommendation. M1 has no RUN VERIFICATION control and does not execute target code.

## Quick start (PowerShell)

```powershell
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
& .\.venv\Scripts\python.exe -m demo.webhook_dedup.materialize --destination .topologyproof\fixtures\webhook-dedup
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000
npm --prefix frontend install
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`. Copy the JSON printed by materialization into the four fields. Click **ANALYZE PATCH**. Inspect the generated `.topologyproof/runs/<RUN_ID>/` artifacts.

## Verification

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp .final-backend -p no:cacheprovider
& .\.venv\Scripts\python.exe -m ruff check backend
& .\.venv\Scripts\python.exe -m mypy backend/app
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run
npm --prefix frontend run build
Set-Location frontend; .\node_modules\.bin\playwright.cmd test --project=desktop; Set-Location ..
```

## Evidence artifacts

Each completed run persists `run.json`, `request.json`, `trajectory.jsonl`, `findings.json`, and `report.md`. JSONL records observable stages such as repository resolution, diff, symbols, context, static scan, assumption mining, finding synthesis, recommendation, verdict, and report writing; it contains no private chain-of-thought. Runtime falsification is future M2 work.

## Trust and limits

Analyzed repositories are untrusted, read-only data. TopologyProof does not run target Python, tests, scripts, package managers, hooks, binaries, or shell instructions. Secret-prone content is bounded/redacted. The deterministic offline provider is the default; live provider credentials are optional. M1 is static-first, makes no universal-safety claim, and does not execute runtime verification.
