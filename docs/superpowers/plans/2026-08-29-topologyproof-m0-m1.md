# TopologyProof M0 + M1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible M0 foundation and the complete credential-free M1 webhook-deduplication vertical slice from local Git input through static/semantic analysis, API, UI, trajectory, report, and executed browser evidence.

**Architecture:** A single FastAPI process runs an explicit typed pipeline and stores atomic JSON/JSONL/Markdown run artifacts outside analyzed repositories. A React/Vite client uses versioned HTTP contracts and real polling state. Git-object reads, deterministic AST analysis, an offline semantic provider, and validated evidence form the required path; the OpenAI Responses API adapter is isolated and credential-gated.

**Tech Stack:** Python 3.13, FastAPI 0.141.1, Pydantic 2.13.5, OpenAI Python 3.6.0, pytest 9.1.1, Ruff 0.16.5, mypy 2.3.1, React 19.2.8, TypeScript 5.9.3, Vite 8.2.2, Vitest 4.1.11, Playwright 1.62.1, npm 11 with `package-lock.json`.

**Spec:** `docs/superpowers/specs/2026-08-29-topologyproof-design.md`

## Global Constraints

- Implement M0 and M1 only; runtime topology verification, additional families, benchmarks, evaluation UI, and submission artifacts remain absent.
- Support Python `>=3.12,<3.14` and Node `>=22.12.0`; verification uses local Python 3.13.7 and Node 24.15.0.
- Use a standard `.venv`, a hash-pinned `requirements.lock` for offline/dev dependencies, and a committed npm lockfile; install the optional `live` extra only for OpenAI-adapter tests or live-provider use; `uv` is not required.
- Analyze only local Git repositories, read source from Git objects, never check out or write to the target, and never execute target code or instructions.
- Invoke Git with `shell=False`, resolved commit IDs, timeouts, output limits, global/system configuration disabled, and optional locks disabled.
- Keep exactly five topology wire values: `replica_count`, `request_routing`, `restart_recovery`, `concurrency`, `state_locality`.
- Default to the deterministic `offline` provider. `openai` is allowed only when a server-side key and model are configured; no key enters an API request, artifact, log, fixture, or browser bundle.
- Every Python function and method receives a one-line docstring. TypeScript exported functions and components receive concise TSDoc where their contract is not obvious from the type.
- Keep the frontend dark, mobile-first, technical-workbench styled with ink/slate surfaces, cool-blue structure, amber uncertainty, red risk, and restrained green scoped-success states.
- Use native `fetch`, History API, React state, Python AST, stdlib subprocess/path/file primitives, and CSS before adding dependencies.
- Each implementation task uses red-green-refactor, ends with targeted verification, gets specification-conformance review followed by code-quality review, and lands as one logical commit.
- The controller updates `docs/status/m0-m1-goal-contract.md` only after named evidence exists; code presence alone leaves a criterion `NOT-VERIFIED`.

## Goal Contract Coverage Map

Every approved M0/M1 criterion has an implementation and evidence owner. The ledger remains NOT-VERIFIED until Task 15 records executed results.

| Criterion | Implementation tasks | Evidence gate |
|---|---|---|
| GC-01 | Tasks 1, 2, 14 | Install/start commands, tooling checks, and PowerShell verification script. |
| GC-02 | Tasks 5, 6, 12 | Git resolution tests, hostile-input tests, and target before/after state. |
| GC-03 | Task 6 | Real two-commit fixture diff, changed paths, and changed-symbol assertions. |
| GC-04 | Task 7 | Positive mutable-state signal and cache-only negative test. |
| GC-05 | Task 7 | Context provenance, call expansion, secret exclusion, and budget tests. |
| GC-06 | Task 8 | Fake/offline provider, mocked OpenAI contract, uncertainty, and failure tests. |
| GC-07 | Task 9 | Pydantic finding validation and candidate-blob evidence checks. |
| GC-08 | Tasks 11, 12 | API tests plus live Uvicorn/httpx smoke for every endpoint and error class. |
| GC-09 | Task 13 | UI tests and desktop/mobile Playwright flow with real API state. |
| GC-10 | Task 10 | JSONL trajectory ordering and deterministic Markdown report tests. |
| GC-11 | Tasks 8, 12 | Credential-free suite, offline run, and explicit provider-unavailable test. |
| GC-12 | Tasks 5, 7, 8, 12 | Shell/traversal/symlink/secret/limit/non-execution security suite. |
| GC-13 | Task 15 | Full backend/frontend tests, lint, typecheck, builds, smoke, browser, and scan sequence. |
| GC-14 | Tasks 14, 15 | Diff review, secret scan, forbidden-token scan, and unavailable-control check. |

## Locked Dependency Set

Python direct pins in `pyproject.toml`:

```toml
dependencies = [
  "fastapi==0.141.1",
  "httpx==0.28.1",
  "pydantic==2.13.5",
  "pydantic-settings==2.15.0",
  "uvicorn==0.52.4",
]

[project.optional-dependencies]
live = [
  "openai==3.6.0",
]
dev = [
  "mypy==2.3.1",
  "pytest==9.1.1",
  "pytest-cov==7.1.0",
  "ruff==0.16.5",
]
```

Frontend direct pins in `frontend/package.json`:

```json
{
  "dependencies": {
    "react": "19.2.8",
    "react-dom": "19.2.8"
  },
  "devDependencies": {
    "@eslint/js": "10.0.1",
    "@playwright/test": "1.62.1",
    "@testing-library/jest-dom": "7.0.1",
    "@testing-library/react": "16.3.3",
    "@testing-library/user-event": "14.6.6",
    "@types/node": "26.4.0",
    "@types/react": "19.2.18",
    "@types/react-dom": "19.2.5",
    "@vitejs/plugin-react": "6.1.1",
    "eslint": "10.9.1",
    "eslint-plugin-react-hooks": "7.1.1",
    "eslint-plugin-react-refresh": "0.5.5",
    "jsdom": "30.0.1",
    "typescript": "5.9.3",
    "typescript-eslint": "8.68.0",
    "vite": "8.2.2",
    "vitest": "4.1.11"
  }
}
```

TypeScript 5.9.3 is intentionally pinned because it is the released stable compiler range supported by the selected Vite, Vitest, and `typescript-eslint` peer dependencies; the previously planned 7.0.2 value is not an installable peer-compatible release for this dependency set.

## File and Responsibility Map

### Root and documentation

- `.gitattributes` â€” text normalization without changing target repositories.
- `.gitignore` â€” credentials, virtual environments, Node output, Playwright output, and `.topologyproof/` artifacts.
- `.env.example` â€” safe setting names with offline defaults and blank secrets/model.
- `pyproject.toml` â€” Python package metadata, direct pins, pytest/Ruff/mypy configuration.
- `requirements.lock` â€” generated transitive Python lock with hashes.
- `README.md` â€” Windows-first install, run, fixture, verification, and provider instructions.
- `ARCHITECTURE.md` â€” implemented M0/M1 boundaries and trust model.
- `docs/status/m0-m1-goal-contract.md` â€” GC-01 through GC-14 evidence ledger.
- `.github/workflows/ci.yml` â€” deterministic backend, frontend, and browser jobs without secrets.
- `scripts/verify.ps1` â€” one-command local milestone verification.

### Backend application

- `backend/__init__.py`, `backend/app/__init__.py` â€” package markers.
- `backend/app/config.py` â€” validated settings and named limits.
- `backend/app/errors.py` â€” typed domain error and FastAPI mapping.
- `backend/app/main.py` â€” application factory, CORS, exception handlers, router composition, restart cleanup.
- `backend/app/schemas/common.py` â€” enums and common diagnostics.
- `backend/app/schemas/evidence.py` â€” checked source locations.
- `backend/app/schemas/repository.py` â€” request, snapshot, diff, path, preview, and changed-symbol contracts.
- `backend/app/schemas/analysis.py` â€” context, static signal, mining input, hypothesis, and batch contracts.
- `backend/app/schemas/findings.py` â€” recommendation, finding, finding list, and overall verdict contracts.
- `backend/app/schemas/runs.py` â€” run state, stages, trajectory, report, and API status contracts.
- `backend/app/schemas/__init__.py` â€” stable schema exports.
- `backend/app/ingestion/git_client.py` â€” bounded shell-free Git execution and blob/tree operations.
- `backend/app/ingestion/service.py` â€” request/ref resolution, diff loading, changed paths, preview.
- `backend/app/ingestion/symbols.py` â€” diff-hunk-aware Python symbol detection.
- `backend/app/context/python_graph.py` â€” AST name uses, enclosing functions, imports, direct callees.
- `backend/app/context/builder.py` â€” prioritized bounded context selection and secret-file exclusion.
- `backend/app/static_analysis/mutable_state.py` â€” deterministic module mutable-collection signals and use facts.
- `backend/app/agents/assumption_miner/provider.py` â€” provider protocol, registry, and provider errors.
- `backend/app/agents/assumption_miner/offline.py` â€” deterministic webhook correctness-chain inference.
- `backend/app/agents/assumption_miner/redaction.py` â€” bounded provider payload and secret-pattern redaction.
- `backend/app/agents/assumption_miner/openai_provider.py` â€” structured Responses API adapter.
- `backend/app/findings/synthesizer.py` â€” evidence validation and stable finding construction.
- `backend/app/findings/verdicts.py` â€” finding/overall verdict rules.
- `backend/app/verification/policy.py` â€” recommendation normalization only; no executor.
- `backend/app/trajectories/recorder.py` â€” per-run monotonic JSONL events.
- `backend/app/reports/generator.py` â€” deterministic Markdown report.
- `backend/app/runs/store.py` â€” atomic per-run artifact store and startup interruption cleanup.
- `backend/app/runs/orchestrator.py` â€” explicit stage pipeline and failure transitions.
- `backend/app/runs/executor.py` â€” background/inline executor boundary.
- `backend/app/api/health.py` â€” health route.
- `backend/app/api/analyses.py` â€” preview, create, status, findings, detail, trajectory, report routes.
- `backend/app/api/dependencies.py` â€” application dependency container.
- `backend/app/api/router.py` â€” `/api/v1` route composition.
- Every backend subpackage above receives an `__init__.py` package marker.

### Demo fixture

- `demo/webhook_dedup/base/app/main.py` â€” base FastAPI route without deduplication.
- `demo/webhook_dedup/base/app/payments.py` â€” unchanged durable SQLite side effect.
- `demo/webhook_dedup/candidate/app/main.py` â€” candidate route with process-local deduplication.
- `demo/webhook_dedup/candidate/app/payments.py` â€” identical durable side effect.
- `demo/webhook_dedup/ticket.txt` â€” idempotency requirement without evaluator label.
- `demo/webhook_dedup/materialize.py` â€” trusted two-commit temporary repository builder.

### Backend tests

- `backend/tests/conftest.py` â€” settings, API client, artifact root, and materialized fixture fixtures.
- `backend/tests/helpers/git_repo.py` â€” trusted test-only Git helpers.
- `backend/tests/test_foundation.py` â€” health/settings baseline.
- `backend/tests/schemas/test_contracts.py` â€” contract validation and exact taxonomy.
- `backend/tests/demo/test_materialize.py` â€” genuine two-commit fixture behavior.
- `backend/tests/ingestion/test_git_client.py` â€” bounded execution, hostile refs, blob reads, no target writes.
- `backend/tests/ingestion/test_service.py` â€” resolution, diff, summary, errors, limits.
- `backend/tests/ingestion/test_symbols.py` â€” changed Python symbols and syntax diagnostics.
- `backend/tests/context/test_builder.py` â€” provenance, call expansion, budgets, secret exclusion.
- `backend/tests/static_analysis/test_mutable_state.py` â€” mutable signals and non-finding separation.
- `backend/tests/agents/test_offline_provider.py` â€” complete chain, cache-only negative, uncertainty.
- `backend/tests/agents/test_openai_provider.py` â€” mocked structured output, refusal, timeout, missing configuration.
- `backend/tests/agents/test_redaction.py` â€” key/file/source redaction and size bound.
- `backend/tests/findings/test_synthesizer.py` â€” evidence line/blob validation and stable IDs.
- `backend/tests/findings/test_verdicts.py` â€” RED/YELLOW/GREEN labels and threshold.
- `backend/tests/verification/test_policy.py` â€” recommendation only and no runtime capability.
- `backend/tests/trajectories/test_recorder.py` â€” real ordered events and safe summaries.
- `backend/tests/reports/test_generator.py` â€” stable report sections/ordering/limitations.
- `backend/tests/runs/test_store.py` â€” atomic files, traversal rejection, interrupted run cleanup.
- `backend/tests/runs/test_orchestrator.py` â€” stages, provider failure, artifact publication.
- `backend/tests/api/test_analyses.py` â€” endpoint statuses, polling, not-ready, errors.
- `backend/tests/integration/test_offline_vertical_slice.py` â€” full fixture-to-report pipeline.
- `backend/tests/integration/test_live_api.py` â€” real Uvicorn process and HTTP smoke.
- `backend/tests/security/test_trust_boundary.py` â€” command injection, symlink/worktree, secrets, and non-execution regression suite.

### Frontend

- `frontend/package.json`, `frontend/package-lock.json` â€” scripts, exact direct pins, transitive lock.
- `frontend/index.html` â€” Vite entry document.
- `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json` â€” strict TypeScript.
- `frontend/vite.config.ts`, `frontend/vitest.config.ts`, `frontend/eslint.config.js` â€” build/test/lint configuration.
- `frontend/playwright.config.ts` â€” real backend/frontend servers and desktop/mobile projects.
- `frontend/src/main.tsx` â€” React root.
- `frontend/src/App.tsx` â€” native-history route switch for the four M1 screens.
- `frontend/src/styles.css` â€” responsive workbench theme and component styles.
- `frontend/src/api/types.ts` â€” API wire contracts matching Pydantic serialization.
- `frontend/src/api/client.ts` â€” typed `fetch` calls and `ApiError`.
- `frontend/src/hooks/useRoute.ts` â€” History API routing.
- `frontend/src/hooks/useAnalysis.ts` â€” real status polling and cleanup.
- `frontend/src/components/AppShell.tsx` â€” product frame/navigation without evaluation link.
- `frontend/src/components/ErrorNotice.tsx` â€” accessible error rendering.
- `frontend/src/components/StageTimeline.tsx` â€” eight real stages.
- `frontend/src/components/VerdictBanner.tsx` â€” scoped verdict display.
- `frontend/src/components/TopologyPanel.tsx` â€” all five dimensions with affected state.
- `frontend/src/components/EvidenceBlock.tsx` â€” exact file/line/symbol/excerpt.
- `frontend/src/pages/NewAnalysisPage.tsx` â€” preview and submission form.
- `frontend/src/pages/AnalysisProgressPage.tsx` â€” real polling/failure/completion navigation.
- `frontend/src/pages/FindingsDashboardPage.tsx` â€” counts, verdict, empty/error states.
- `frontend/src/pages/FindingDetailPage.tsx` â€” engineering explanation and recommendation without execution control.
- `frontend/src/test/setup.ts` â€” DOM matchers and cleanup.
- `frontend/src/test/render.tsx` â€” injected API/render helpers.
- `frontend/src/api/client.test.ts` â€” success/error wire handling.
- `frontend/src/pages/NewAnalysisPage.test.tsx` â€” validation, preview, submit states.
- `frontend/src/pages/AnalysisProgressPage.test.tsx` â€” stage/poll/failure states.
- `frontend/src/pages/FindingsDashboardPage.test.tsx` â€” risk and empty states.
- `frontend/src/pages/FindingDetailPage.test.tsx` â€” evidence/dimensions/recommendation and absent execution button.
- `frontend/e2e/global-setup.ts` â€” materialize trusted fixture before browser tests.
- `frontend/e2e/topologyproof.spec.ts` â€” desktop/mobile critical flow plus console/network assertions.

---

### Task 1: M0 Python Foundation and Health Contract

**Files:**
- Create: `.gitattributes`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `requirements.lock`
- Create: `README.md`
- Create: `ARCHITECTURE.md`
- Create: `docs/status/m0-m1-goal-contract.md`
- Create: `backend/__init__.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/errors.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_foundation.py`

**Interfaces:**
- Produces: `Settings`, `get_settings() -> Settings`, `TopologyProofError`, `create_app(settings: Settings | None = None) -> FastAPI`, `GET /api/v1/health`.
- Consumes: Approved settings defaults and GC ledger from the design specification.

- [ ] **Step 1: Write failing settings and health tests**

```python
def test_settings_default_to_offline_and_loopback(tmp_path: Path) -> None:
    settings = Settings(artifact_root=tmp_path / "runs")
    assert settings.provider == ProviderName.OFFLINE
    assert settings.api_host == "127.0.0.1"
    assert settings.openai_api_key is None


def test_health_returns_service_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "service": "topologyproof",
        "status": "ok",
        "version": "0.1.0",
    }
```

- [ ] **Step 2: Run the tests and confirm the missing-module failure**

Run:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install pip-tools==7.6.1
& .\.venv\Scripts\pip-compile.exe --no-emit-index-url --extra dev --generate-hashes --output-file requirements.lock pyproject.toml
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_foundation.py -v
```

Expected: collection fails because `backend.app.config` and `backend.app.main` do not exist.

- [ ] **Step 3: Implement the smallest validated foundation**

Implement `Settings` with `SettingsConfigDict(env_prefix="TOPOLOGYPROOF_", env_file=".env", extra="forbid")`, design-spec limits, `SecretStr | None` for the key, blank model/key normalized to `None`, and loopback/CORS defaults. Implement the health router and application factory:

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the configured TopologyProof API application."""
    resolved = settings or get_settings()
    application = FastAPI(title=resolved.app_name, version=resolved.app_version)
    application.state.settings = resolved
    application.include_router(api_router, prefix="/api/v1")
    return application
```

Create the initial GC ledger with all fourteen criteria `NOT-VERIFIED`, `.env.example` with `TOPOLOGYPROOF_PROVIDER=offline` and blank OpenAI values, and documentation that describes only commands that exist in this task.

- [ ] **Step 4: Generate the lock and verify the foundation**

Run:

```powershell
& .\.venv\Scripts\pip-compile.exe --no-emit-index-url --extra dev --generate-hashes --output-file requirements.lock pyproject.toml
& .\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
& .\.venv\Scripts\python.exe -m pip install --no-deps -e .
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_foundation.py -v
& .\.venv\Scripts\python.exe -m ruff check backend
& .\.venv\Scripts\python.exe -m mypy backend
```

Expected: all commands exit `0`; the health test reports `200` and the exact body above.

- [ ] **Step 5: Review and commit M0 Python foundation**

```powershell
git diff --check
git add .gitattributes .gitignore .env.example pyproject.toml requirements.lock README.md ARCHITECTURE.md docs/status backend
git commit -m "chore: establish Python project foundation"
```

### Task 2: M0 React/Vite/TypeScript Foundation

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/package-lock.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/eslint.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/App.test.tsx`
- Modify: `README.md`
- Modify: `docs/status/m0-m1-goal-contract.md`

**Interfaces:**
- Produces: Vite app at `http://127.0.0.1:5173`, strict TypeScript, scripts `dev`, `build`, `lint`, `typecheck`, and `test`; minimal mountable `App` shell only.
- Consumes: the workbench visual direction from Task 1/spec. It does not implement product screens, API calls, navigation, analysis data, progress, findings, evaluation, or unavailable controls.

- [ ] **Step 1: Invoke `frontend-skill`, then write the failing foundation test**

```tsx
it("renders the minimal product identity without product functionality", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "TopologyProof" })).toBeVisible();
  expect(screen.getByText("Agentic Falsification of Hidden Deployment Assumptions")).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Install exact dependencies and confirm the test fails**

Run:

```powershell
Set-Location frontend
npm install
npm test -- --run src/App.test.tsx
Set-Location ..
```

Expected: test fails because `App` and test setup are not implemented.

- [ ] **Step 3: Implement the minimal app shell and tool configuration**

Use the exact dependency object in this plan, strict compiler settings (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`), `jsdom`, and accessible landmark markup. Define restrained dark engineering-workspace tokens in `styles.css` and no component library. Do not add route shells or fake data; the four M1 screens belong to Task 13 and the Evaluation Dashboard belongs to M7.

```tsx
export function App(): React.JSX.Element {
  return (
    <main className="app-shell">
      <p className="eyebrow">Deployment assumption verification</p>
      <h1>TopologyProof</h1>
      <p>Agentic Falsification of Hidden Deployment Assumptions</p>
    </main>
  );
}
```

- [ ] **Step 4: Verify frontend foundation and production build**

Run:

```powershell
Set-Location frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
Set-Location ..
```

Expected: all commands exit `0` and Vite writes `frontend/dist/`.

- [ ] **Step 5: Record M0 evidence and commit**

Update GC-01 to `PARTIAL` with the exact install/test/build commands; full clean-startup evidence is deferred to Task 15.

```powershell
git add frontend README.md docs/status/m0-m1-goal-contract.md
git commit -m "chore: establish React project foundation"
```

### Task 3: Typed Domain and API Contracts

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/evidence.py`
- Create: `backend/app/schemas/repository.py`
- Create: `backend/app/schemas/analysis.py`
- Create: `backend/app/schemas/findings.py`
- Create: `backend/app/schemas/runs.py`
- Create: `backend/tests/schemas/__init__.py`
- Create: `backend/tests/schemas/test_contracts.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- Produces: `ProviderName`, `TopologyDimension`, `Severity`, `FindingVerdict`, `OverallVerdict`, `RunStatus`, `AnalysisStage`, `TrajectoryAction`, `RepositoryRefRequest`, `AnalysisRequest`, `RepositorySnapshot`, `ChangedPath`, `DiffSummary`, `DiffArtifact`, `ChangedSymbol`, `EvidenceLocation`, `ContextItem`, `StaticSignal`, `AssumptionMiningInput`, `AssumptionHypothesis`, `HypothesisBatch`, `VerificationRecommendation`, `Finding`, `AnalysisRun`, `TrajectoryEvent`, `ReportArtifact`.
- Consumes: Limits and provider defaults from `Settings`.

- [ ] **Step 1: Write failing contract tests**

```python
def test_taxonomy_has_exactly_five_wire_values() -> None:
    assert {dimension.value for dimension in TopologyDimension} == {
        "replica_count",
        "request_routing",
        "restart_recovery",
        "concurrency",
        "state_locality",
    }


def test_analysis_request_rejects_relative_path_and_blank_text(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest(
            repo_path=Path("relative"),
            ticket=" ",
            base_ref="main",
            candidate_ref=" ",
            provider=ProviderName.OFFLINE,
        )


def test_finding_requires_checked_evidence() -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate(valid_finding_data | {"evidence": []})
```

- [ ] **Step 2: Confirm missing-contract failures**

Run: `& .\.venv\Scripts\python.exe -m pytest backend/tests/schemas/test_contracts.py -v`

Expected: collection fails on missing schema imports.

- [ ] **Step 3: Implement strict Pydantic models and enums**

Use `ConfigDict(extra="forbid", frozen=True)` for immutable analysis artifacts, one-based positive lines, `0 <= confidence <= 1`, unique non-empty dimensions/evidence, canonical POSIX evidence paths, commit IDs matching `^[0-9a-f]{40,64}$`, and stripped non-blank text. Define the eight stage enum values exactly as the spec.

```python
class TopologyDimension(StrEnum):
    """Name a supported deployment-topology axis."""

    REPLICA_COUNT = "replica_count"
    REQUEST_ROUTING = "request_routing"
    RESTART_RECOVERY = "restart_recovery"
    CONCURRENCY = "concurrency"
    STATE_LOCALITY = "state_locality"
```

- [ ] **Step 4: Verify schemas, lint, and type checking**

Run:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/schemas/test_contracts.py -v
& .\.venv\Scripts\python.exe -m ruff check backend/app/schemas backend/tests/schemas
& .\.venv\Scripts\python.exe -m mypy backend/app/schemas
```

Expected: all commands exit `0`.

- [ ] **Step 5: Commit schema contracts**

```powershell
git add backend/app/config.py backend/app/schemas backend/tests/schemas
git commit -m "feat: define analysis domain contracts"
```

### Task 4: Reproducible Webhook Git Fixture

**Files:**
- Create: `demo/__init__.py`
- Create: `demo/webhook_dedup/__init__.py`
- Create: `demo/webhook_dedup/base/app/main.py`
- Create: `demo/webhook_dedup/base/app/payments.py`
- Create: `demo/webhook_dedup/candidate/app/main.py`
- Create: `demo/webhook_dedup/candidate/app/payments.py`
- Create: `demo/webhook_dedup/ticket.txt`
- Create: `demo/webhook_dedup/materialize.py`
- Create: `backend/tests/helpers/__init__.py`
- Create: `backend/tests/helpers/git_repo.py`
- Create: `backend/tests/demo/__init__.py`
- Create: `backend/tests/demo/test_materialize.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `MaterializedFixture(repo_path: Path, base_ref: str, candidate_ref: str, ticket: str)` and `materialize_fixture(destination: Path) -> MaterializedFixture`; the fixture also exposes `analysis_request() -> AnalysisRequest`, `request_json() -> dict[str, object]`, and `context_inputs()` test helpers; CLI prints JSON containing the four serialized fields.
- Consumes: trusted source snapshots under `demo/webhook_dedup/`; Git executable from `PATH` only in the trusted materializer.

- [ ] **Step 1: Write the failing materializer test**

```python
def test_materializer_creates_clean_two_commit_repository(tmp_path: Path) -> None:
    fixture = materialize_fixture(tmp_path / "fixture")
    assert fixture.repo_path.is_absolute()
    assert run_git(fixture.repo_path, "rev-list", "--count", "HEAD") == "2"
    assert run_git(fixture.repo_path, "status", "--porcelain") == ""
    diff = run_git(fixture.repo_path, "diff", fixture.base_ref, fixture.candidate_ref)
    assert "processed_events" in diff
    assert "unsafe" not in fixture.ticket.casefold()
```

- [ ] **Step 2: Confirm the materializer import fails**

Run: `& .\.venv\Scripts\python.exe -m pytest backend/tests/demo/test_materialize.py -v`

Expected: collection fails because `demo.webhook_dedup.materialize` does not exist.

- [ ] **Step 3: Implement the trusted fixture and source snapshots**

The base route always calls `record_payment`. The candidate adds `processed_events: set[str] = set()`, a membership guard, the same call, and `processed_events.add(event.event_id)`. `payments.py` uses stdlib SQLite to make the durability semantics explicit but is never executed by TopologyProof. The materializer copies base, initializes Git, commits with fixture-local identity, overlays candidate, commits again, and never embeds an evaluator label.

```python
def materialize_fixture(destination: Path) -> MaterializedFixture:
    """Create the trusted webhook fixture as a clean two-commit Git repository."""
    destination.mkdir(parents=True, exist_ok=False)
    _copy_snapshot(BASE_SOURCE, destination)
    _git(destination, "init")
    _git(destination, "config", "user.name", "TopologyProof Fixture")
    _git(destination, "config", "user.email", "fixture@topologyproof.local")
    _git(destination, "add", ".")
    _git(destination, "commit", "-m", "base webhook behavior")
    base_commit = _git(destination, "rev-parse", "HEAD")
    _copy_snapshot(CANDIDATE_SOURCE, destination)
    _git(destination, "add", ".")
    _git(destination, "commit", "-m", "prevent duplicate webhook processing")
    candidate_commit = _git(destination, "rev-parse", "HEAD")
    return MaterializedFixture(destination.resolve(), base_commit, candidate_commit, TICKET)
```

- [ ] **Step 4: Verify reproducibility and clean target state**

Run:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/demo/test_materialize.py -v
& .\.venv\Scripts\python.exe -m demo.webhook_dedup.materialize --destination .topologyproof\fixtures\manual
git -C .topologyproof\fixtures\manual status --short
```

Expected: tests pass, CLI emits valid JSON, and fixture status is empty.

- [ ] **Step 5: Commit the fixture**

```powershell
git add demo backend/tests/helpers backend/tests/demo README.md
git commit -m "test: add reproducible webhook Git fixture"
```


### Task 5: Bounded Shell-Free Git Client

Files:
- Create: backend/app/ingestion/__init__.py
- Create: backend/app/ingestion/git_client.py
- Create: backend/tests/ingestion/__init__.py
- Create: backend/tests/ingestion/test_git_client.py

Interfaces:
- Produces GitClient(root: Path, settings: Settings), GitCommandResult, resolve_commit(ref: str) -> str, read_blob(commit_id: str, path: PurePosixPath) -> str, list_tree(commit_id: str) -> tuple[TreeEntry, ...], and diff(base_commit: str, candidate_commit: str) -> str.
- Consumes Settings and TopologyProofError from Tasks 1 and 3.
- Every subprocess uses shell=False, a fixed git executable, --no-optional-locks, controlled Git configuration, bounded output, and timeout.

- [ ] Step 1: Write failing security/blob tests

    def test_option_like_ref_is_rejected(client):
        with pytest.raises(TopologyProofError, match="invalid_git_ref"):
            client.resolve_commit("--upload-pack=evil")

    def test_blob_read_does_not_mutate_target(client, fixture):
        before = snapshot_worktree(fixture.repo_path)
        assert "processed_events" in client.read_blob(
            fixture.candidate_ref, PurePosixPath("app/main.py")
        )
        assert snapshot_worktree(fixture.repo_path) == before

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/ingestion/test_git_client.py -v
Expected: collection fails because backend.app.ingestion.git_client does not exist.

- [ ] Step 3: Implement the bounded client

Use subprocess.run with an argument list, cwd set to the canonical root, shell=False, check=False, capture_output=True, text=True, the configured timeout, and a controlled environment. Reject blank, NUL-containing, and option-like refs. Resolve refs to full commit IDs before diff/blob operations. Reject absolute or parent-traversing Git paths and map timeout, non-zero exit, binary blob, and limit failures to typed domain errors.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/ingestion/test_git_client.py -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/ingestion backend/tests/ingestion
    & .\.venv\Scripts\python.exe -m mypy backend/app/ingestion
Expected: all commands exit 0 and the target worktree remains unchanged.

- [ ] Step 5: Commit

    git add backend/app/ingestion backend/tests/ingestion
    git commit -m "feat: add bounded read-only Git client"

### Task 6: Repository Intake, Diff Summary, and Changed Symbols

Files:
- Create: backend/app/ingestion/service.py
- Create: backend/app/ingestion/symbols.py
- Create: backend/tests/ingestion/test_service.py
- Create: backend/tests/ingestion/test_symbols.py

Interfaces:
- Produces RepositoryIntake.resolve(request: AnalysisRequest) -> RepositorySnapshot, load_diff(snapshot: RepositorySnapshot) -> DiffArtifact, preview(request: RepositoryRefRequest) -> AnalysisPreview, and ChangedSymbolDetector.detect(snapshot, diff) -> tuple[ChangedSymbol, ...].
- Consumes GitClient from Task 5 and repository schemas from Task 3.
- Preview and analysis reuse the same resolution and diff methods.

- [ ] Step 1: Write failing fixture tests

    def test_fixture_intake_resolves_refs_diff_and_symbols(intake, fixture):
        request = fixture.analysis_request()
        snapshot = intake.resolve(request)
        diff = intake.load_diff(snapshot)
        symbols = ChangedSymbolDetector().detect(snapshot, diff)
        assert snapshot.base_commit != snapshot.candidate_commit
        assert diff.summary.changed_file_count == 2
        assert any(symbol.name == "processed_events" for symbol in symbols)

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/ingestion/test_service.py backend/tests/ingestion/test_symbols.py -v
Expected: collection fails because RepositoryIntake and ChangedSymbolDetector do not exist.

- [ ] Step 3: Implement intake and symbols

Canonicalize and validate the repository root, resolve refs, parse bounded name-status and unified diff output, enforce MAX_DIFF_BYTES and MAX_CHANGED_FILES, and read candidate blobs through GitClient. Parse changed Python blobs with ast.parse and detect definitions/assignment targets intersecting changed hunk lines. Syntax errors become diagnostics.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/ingestion/test_service.py backend/tests/ingestion/test_symbols.py -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/ingestion backend/tests/ingestion
    & .\.venv\Scripts\python.exe -m mypy backend/app/ingestion
Expected: all commands exit 0 and invalid repositories, refs, oversized diffs, and syntax errors produce specified outcomes.

- [ ] Step 5: Commit

    git add backend/app/ingestion backend/tests/ingestion
    git commit -m "feat: implement repository intake and symbol detection"

### Task 7: Provenance-Bounded Context and Deterministic Static Signals

Files:
- Create: backend/app/context/__init__.py
- Create: backend/app/context/python_graph.py
- Create: backend/app/context/builder.py
- Create: backend/app/static_analysis/__init__.py
- Create: backend/app/static_analysis/mutable_state.py
- Create: backend/tests/context/__init__.py
- Create: backend/tests/context/test_builder.py
- Create: backend/tests/static_analysis/__init__.py
- Create: backend/tests/static_analysis/test_mutable_state.py

Interfaces:
- Produces PythonGraph.build(items), ContextBuilder.build(request, snapshot, diff, symbols) -> tuple[ContextItem, ...], and MutableStateScanner.scan(snapshot, diff, context) -> tuple[StaticSignal, ...].
- Consumes intake outputs from Task 6.
- Source is read from candidate Git blobs; secret-prone files and binaries are excluded.

- [ ] Step 1: Write failing context/signal tests

    def test_context_reaches_route_state_and_side_effect(builder, fixture):
        items = builder.build(*fixture.context_inputs())
        assert any(item.path.as_posix() == "app/main.py" for item in items)
        assert any("record_payment" in item.excerpt for item in items)
        assert all(item.commit == fixture.candidate_ref for item in items)

    def test_cache_only_global_is_signal_not_finding(cache_only_input):
        signals = MutableStateScanner().scan(*cache_only_input)
        assert signals[0].kind == "module_mutable_collection"
        assert signals[0].facts["correctness_link"] is False

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/context backend/tests/static_analysis -v
Expected: collection fails because context and static-analysis modules do not exist.

- [ ] Step 3: Implement bounded AST graph and scanner

Index imports, definitions, name uses, enclosing functions, direct callees, membership tests, and mutations. Select changed symbols first, then state references, route/helper code, one-hop side-effect callees, related tests, lifecycle/deployment files, and related shared-state use. Detect module-level set, dict, and list literals, comprehensions, and constructors; emit facts and exact evidence without severity or verdict.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/context backend/tests/static_analysis -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/context backend/app/static_analysis backend/tests/context backend/tests/static_analysis
    & .\.venv\Scripts\python.exe -m mypy backend/app/context backend/app/static_analysis
Expected: all commands exit 0; secret exclusion and context-limit tests pass and cache-only state is not promoted.

- [ ] Step 5: Commit

    git add backend/app/context backend/app/static_analysis backend/tests/context backend/tests/static_analysis
    git commit -m "feat: add bounded context and static state signals"

### Task 8: Provider Boundary, Offline Reasoning, Redaction, and OpenAI Adapter

Files:
- Create: backend/app/agents/__init__.py
- Create: backend/app/agents/assumption_miner/__init__.py
- Create: backend/app/agents/assumption_miner/provider.py
- Create: backend/app/agents/assumption_miner/offline.py
- Create: backend/app/agents/assumption_miner/redaction.py
- Create: backend/app/agents/assumption_miner/openai_provider.py
- Create: backend/tests/agents/__init__.py
- Create: backend/tests/agents/test_offline_provider.py
- Create: backend/tests/agents/test_openai_provider.py
- Create: backend/tests/agents/test_redaction.py

Interfaces:
- Produces AssumptionProvider.mine(input: AssumptionMiningInput) -> HypothesisBatch, OfflineWebhookProvider, FakeAssumptionProvider, Redactor.redact(text) -> RedactedText, and ProviderRegistry.get(name).
- Consumes context/signals from Task 7 and settings/schemas from Tasks 1 and 3.
- Offline is the default; OpenAI is credential-gated and never required for deterministic tests.

- [ ] Step 1: Write failing provider tests

    def test_offline_provider_requires_complete_webhook_chain(offline_input):
        batch = OfflineWebhookProvider().mine(offline_input)
        hypothesis = batch.hypotheses[0]
        assert hypothesis.correctness_property.startswith("One event identifier")
        assert {dimension.value for dimension in hypothesis.topology_dimensions} >= {
            "replica_count", "request_routing", "restart_recovery", "state_locality"
        }

    def test_missing_openai_configuration_is_typed(settings_without_key):
        with pytest.raises(ProviderUnavailableError, match="missing_openai_configuration"):
            OpenAIProvider(settings_without_key).mine(valid_input)

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/agents -v
Expected: collection fails because provider modules do not exist.

- [ ] Step 3: Implement providers

Require mutable-state, membership/mutation, route, and side-effect evidence before the offline provider emits a hypothesis. Implement fake injection, bounded redaction, secret-prone filename exclusion, and provider error mapping. Implement the OpenAI adapter using the current official structured-output API, mocked transport tests, timeout handling, and no raw prompt/response logging. Treat repository text as quoted evidence, never instructions.

For the OpenAI adapter test only, install the optional live extra after the default lock is green: `& .\.venv\Scripts\python.exe -m pip install --no-deps openai==3.6.0`. Keep the offline provider and all deterministic tests independent of that package and any key.

- [ ] Step 4: Verify without credentials

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/agents -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/agents backend/tests/agents
    & .\.venv\Scripts\python.exe -m mypy backend/app/agents
Expected: all commands exit 0; mocked provider responses validate and no secret appears in payloads.

- [ ] Step 5: Commit

    git add backend/app/agents backend/tests/agents
    git commit -m "feat: add deterministic assumption provider boundary"

### Task 9: Finding Synthesis, Verdicts, and Verification Recommendations

Files:
- Create: backend/app/findings/__init__.py
- Create: backend/app/findings/synthesizer.py
- Create: backend/app/findings/verdicts.py
- Create: backend/app/verification/__init__.py
- Create: backend/app/verification/policy.py
- Create: backend/tests/findings/__init__.py
- Create: backend/tests/findings/test_synthesizer.py
- Create: backend/tests/findings/test_verdicts.py
- Create: backend/tests/verification/__init__.py
- Create: backend/tests/verification/test_policy.py

Interfaces:
- Produces FindingSynthesizer.synthesize(snapshot, hypotheses), VerdictPolicy.finding_verdict(finding), VerdictPolicy.overall(findings, runtime=None), and VerificationPolicy.recommend(finding).
- Consumes hypotheses from Task 8 and blob/evidence access from Task 5.
- Policy emits recommendations only; no runtime executor is created.

- [ ] Step 1: Write failing finding/verdict tests

    def test_invalid_candidate_line_is_rejected(snapshot, hypothesis):
        with pytest.raises(TopologyProofError, match="invalid_evidence_location"):
            FindingSynthesizer().synthesize(snapshot, [hypothesis.model_copy(update={"evidence": [invalid_line_evidence]})])

    def test_webhook_high_risk_is_review_required(webhook_finding):
        assert VerdictPolicy().finding_verdict(webhook_finding) == FindingVerdict.HIGH_RISK
        assert VerdictPolicy().overall([webhook_finding]).label == (
            "REVIEW REQUIRED"
        )

    def test_recommendation_has_no_execution_control(webhook_finding):
        recommendation = VerificationPolicy().recommend(webhook_finding)
        assert recommendation.worth_running is True
        assert not hasattr(recommendation, "execute")

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/findings backend/tests/verification -v
Expected: collection fails because finding, verdict, and policy modules do not exist.

- [ ] Step 3: Implement synthesis and policy

Validate candidate blob paths, lines, excerpts, dimensions, confidence, and all required finding fields. Construct deterministic run-local IDs. Apply HIGH_CONFIDENCE_THRESHOLD and the exact RED/YELLOW/GREEN labels. Emit only the M1 webhook recommendation for one-replica baseline and two-replica cross-worker challenge.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/findings backend/tests/verification -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/findings backend/app/verification backend/tests/findings backend/tests/verification
    & .\.venv\Scripts\python.exe -m mypy backend/app/findings backend/app/verification
Expected: all commands exit 0; invalid evidence is rejected and no runtime executor exists.

- [ ] Step 5: Commit

    git add backend/app/findings backend/app/verification backend/tests/findings backend/tests/verification
    git commit -m "feat: synthesize topology findings and verdicts"

### Task 10: Trajectories, Atomic Run Artifacts, and Reports

Files:
- Create: backend/app/trajectories/__init__.py
- Create: backend/app/trajectories/recorder.py
- Create: backend/app/reports/__init__.py
- Create: backend/app/reports/generator.py
- Create: backend/app/runs/__init__.py
- Create: backend/app/runs/store.py
- Create: backend/tests/trajectories/__init__.py
- Create: backend/tests/trajectories/test_recorder.py
- Create: backend/tests/reports/__init__.py
- Create: backend/tests/reports/test_generator.py
- Create: backend/tests/runs/__init__.py
- Create: backend/tests/runs/test_store.py

Interfaces:
- Produces TrajectoryRecorder.append(event), RunStore.create/read/publish_findings/publish_report/mark_interrupted, and ReportGenerator.render(run, findings, trajectory) -> ReportArtifact.
- Consumes run/finding/report schemas from Task 3 and verdicts from Task 9.
- Writes only below the TopologyProof-owned artifact root; per-run writes are locked and atomically replaced.

- [ ] Step 1: Write failing artifact tests

    def test_trajectory_steps_are_monotonic(recorder):
        assert recorder.append(event("repository_loaded")).step == 1
        assert recorder.append(event("diff_parsed")).step == 2

    def test_run_store_rejects_traversal_and_publishes_report(store):
        with pytest.raises(TopologyProofError, match="invalid_run_id"):
            store.read("..\\outside")
        store.publish_report(valid_run_id, "# report")
        assert store.report_path(valid_run_id).read_text(encoding="utf-8") == "# report"

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/trajectories backend/tests/reports backend/tests/runs -v
Expected: collection fails because recorder, report generator, and run store do not exist.

- [ ] Step 3: Implement safe artifacts

Persist run.json, request.json, trajectory.jsonl, findings.json, and report.md with UTF-8 stable ordering. Bound summaries, emit only observable actions, and use temporary sibling files plus os.replace. Mark queued/running runs as failed with restart_interruption on startup. Keep report sections and finding order deterministic.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/trajectories backend/tests/reports backend/tests/runs -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app/trajectories backend/app/reports backend/app/runs backend/tests/trajectories backend/tests/reports backend/tests/runs
    & .\.venv\Scripts\python.exe -m mypy backend/app/trajectories backend/app/reports backend/app/runs
Expected: all commands exit 0; traversal is rejected and hidden reasoning is not persisted.

- [ ] Step 5: Commit

    git add backend/app/trajectories backend/app/reports backend/app/runs backend/tests/trajectories backend/tests/reports backend/tests/runs
    git commit -m "feat: persist safe trajectories and reports"

### Task 11: Explicit Orchestrator and FastAPI Analysis API

Files:
- Create: backend/app/runs/orchestrator.py
- Create: backend/app/runs/executor.py
- Create: backend/app/api/dependencies.py
- Create: backend/app/api/analyses.py
- Modify: backend/app/api/router.py
- Modify: backend/app/main.py
- Create: backend/tests/runs/test_orchestrator.py
- Create: backend/tests/api/__init__.py
- Create: backend/tests/api/test_analyses.py
- Modify: backend/tests/conftest.py

Interfaces:
- Produces AnalysisOrchestrator.run(run_id, request) -> None, InProcessExecutor.submit(run_id, request) -> None, all versioned preview/create/status/findings/detail/trajectory/report routes in the approved API, and test helpers wait_for_run(client, run_id, expected_status) and submit_and_wait(client, fixture).
- Consumes stage interfaces from Tasks 5 through 10 through an injected ApplicationContainer.
- Create validates repository/provider/refs synchronously, returns 202, then background work emits real stages from diff loading through report publication.

- [ ] Step 1: Write failing orchestration/API tests

    def test_create_analysis_returns_202_and_completes(client, fixture):
        response = client.post("/api/v1/analyses", json=fixture.request_json())
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        wait_for_run(client, run_id, expected_status="completed")
        assert client.get(f"/api/v1/analyses/{run_id}/findings").status_code == 200

    def test_missing_repository_returns_structured_400(client):
        response = client.post("/api/v1/analyses", json={
            "repo_path": "C:\\\\missing",
            "ticket": "x",
            "base_ref": "a",
            "candidate_ref": "b",
        })
        assert response.status_code == 400
        assert response.json()["code"] == "repository_not_found"

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/runs/test_orchestrator.py backend/tests/api/test_analyses.py -v
Expected: collection or route tests fail because the orchestrator and analysis routes do not exist.

- [ ] Step 3: Implement orchestration and routes

Compose dependencies once. Persist each successful stage and trajectory event. Map domain errors to the specified 400, 408, 409, 413, 422, 503, and 404 statuses. Return 409 for findings/report before publication. Keep route handlers thin and keep all analysis logic in services.

- [ ] Step 4: Verify

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests/runs/test_orchestrator.py backend/tests/api/test_analyses.py -v
    & .\.venv\Scripts\python.exe -m ruff check backend/app backend/tests/api backend/tests/runs
    & .\.venv\Scripts\python.exe -m mypy backend/app
Expected: all commands exit 0; a real fixture reaches completed and publishes findings, trajectory, and report.

- [ ] Step 5: Commit

    git add backend/app/runs backend/app/api backend/tests/runs/test_orchestrator.py backend/tests/api
    git commit -m "feat: expose the analysis pipeline through FastAPI"

### Task 12: Backend Integration, Live HTTP Smoke, and Security Tests

Files:
- Create: backend/tests/integration/__init__.py
- Create: backend/tests/integration/test_offline_vertical_slice.py
- Create: backend/tests/integration/test_live_api.py
- Create: backend/tests/security/__init__.py
- Create: backend/tests/security/test_trust_boundary.py
- Modify: backend/tests/conftest.py

Interfaces:
- Produces executable evidence for GC-02 through GC-08 and GC-10 through GC-12; test-only run_uvicorn_subprocess(settings) -> RunningServer.
- Consumes the complete pipeline from Tasks 1 through 11.
- Must not execute target Python, tests, hooks, Docker files, package managers, or binaries.

- [ ] Step 1: Write failing full-flow/security tests

    def test_offline_fixture_produces_finding_report_and_trajectory(client, fixture):
        run_id = submit_and_wait(client, fixture)
        finding = client.get(f"/api/v1/analyses/{run_id}/findings").json()["findings"][0]
        assert finding["verdict"] == "high-risk"
        assert finding["evidence"][0]["line"] > 0
        assert "processed_events" in client.get(
            f"/api/v1/analyses/{run_id}/report"
        ).text

    def test_target_is_not_mutated_or_executed(client, malicious_target):
        before = snapshot_worktree(malicious_target)
        run_id = submit_and_wait(client, malicious_target)
        assert client.get(f"/api/v1/analyses/{run_id}").json()["status"] == "completed"
        assert snapshot_worktree(malicious_target) == before

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/integration backend/tests/security -v
Expected: tests fail until the complete pipeline and live process fixtures are wired.

- [ ] Step 3: Implement test-only live process and trust-boundary fixtures

Start Uvicorn on an ephemeral loopback port and use httpx to submit/poll the real API. Capture target hashes/status before and after. Exercise hostile refs, traversal, symlink escape, secret redaction, oversized inputs, provider failure, and repository text that attempts to issue commands.

- [ ] Step 4: Verify backend evidence

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests -v --cov=backend/app --cov-fail-under=85
Expected: exit 0; the offline fixture produces a high-risk finding with checked evidence, report, trajectory, and no target mutation.

- [ ] Step 5: Commit

    git add backend/tests/integration backend/tests/security backend/tests/conftest.py
    git commit -m "test: prove offline vertical slice and trust boundary"

### Task 13: React API Client, M1 Screens, and Browser Verification

Files:
- Create: frontend/playwright.config.ts
- Create: frontend/src/api/types.ts
- Create: frontend/src/api/client.ts
- Create: frontend/src/hooks/useRoute.ts
- Create: frontend/src/hooks/useAnalysis.ts
- Create: frontend/src/components/AppShell.tsx
- Create: frontend/src/components/ErrorNotice.tsx
- Create: frontend/src/components/StageTimeline.tsx
- Create: frontend/src/components/VerdictBanner.tsx
- Create: frontend/src/components/TopologyPanel.tsx
- Create: frontend/src/components/EvidenceBlock.tsx
- Create: frontend/src/pages/NewAnalysisPage.tsx
- Create: frontend/src/pages/AnalysisProgressPage.tsx
- Create: frontend/src/pages/FindingsDashboardPage.tsx
- Create: frontend/src/pages/FindingDetailPage.tsx
- Modify: frontend/src/App.tsx
- Modify: frontend/src/main.tsx
- Modify: frontend/src/styles.css
- Create: frontend/src/test/render.tsx
- Create: frontend/src/api/client.test.ts
- Create: frontend/src/pages/NewAnalysisPage.test.tsx
- Create: frontend/src/pages/AnalysisProgressPage.test.tsx
- Create: frontend/src/pages/FindingsDashboardPage.test.tsx
- Create: frontend/src/pages/FindingDetailPage.test.tsx
- Create: frontend/e2e/global-setup.ts
- Create: frontend/e2e/topologyproof.spec.ts

Interfaces:
- Produces typed client methods for preview/create/status/findings/detail/trajectory/report and routes for /, /analyses/:runId/progress, /analyses/:runId, and /analyses/:runId/findings/:findingId.
- Consumes API wire contracts from Task 3 and live API behavior from Tasks 11 and 12.
- Uses native fetch, React state, History API, real polling, and approved dark workbench tokens. No evaluation link, fake data, fake progress, or RUN VERIFICATION button.

- [ ] Step 1: Invoke frontend-skill and write failing UI tests

    it("renders real risk and evidence without execution controls", async () => {
      mockApiWithCompletedWebhookRun();
      render(<App />);
      await userEvent.type(screen.getByLabelText("Repository path"), fixturePath);
      await userEvent.type(screen.getByLabelText("Ticket / requirement"), ticket);
      await userEvent.type(screen.getByLabelText("Base ref"), baseRef);
      await userEvent.type(screen.getByLabelText("Candidate ref"), candidateRef);
      await userEvent.click(screen.getByRole("button", { name: "ANALYZE PATCH" }));
      expect(await screen.findByText(
        "REVIEW REQUIRED"
      )).toBeVisible();
      expect(screen.getByText("Replica Count")).toBeVisible();
      expect(screen.queryByRole("button", {
        name: "RUN VERIFICATION"
      })).not.toBeInTheDocument();
    });

- [ ] Step 2: Run to confirm failure

Run:
    Set-Location frontend
    npm test -- --run src/pages
    Set-Location ..
Expected: tests fail because the typed client, routes, pages, and browser setup are not implemented.

- [ ] Step 3: Implement API-driven screens and browser harness

Implement typed ApiError and fetch methods, abortable polling with cleanup, accessible labels, real stage states, exact evidence, five-dimension panel, report link, and loading/error/empty/not-ready states. Use the frontend-skill theme direction. Configure Playwright desktop and mobile projects with real backend/frontend servers, trusted fixture materialization, console/pageerror/failed-response collection, semantic waits, and no sleeps.

- [ ] Step 4: Verify frontend and browser evidence

Run:
    Set-Location frontend
    npm run lint
    npm run typecheck
    npm test -- --run
    npm run build
    npx playwright test --project=desktop
    npx playwright test --project=mobile
    Set-Location ..
Expected: all commands exit 0; both viewport flows render findings/detail, console and failed-network collections are empty, and the production build exists.

- [ ] Step 5: Commit

    git add frontend
    git commit -m "feat: add API-driven topology findings UI"

### Task 14: Documentation, CI, Verification Script, and Goal Ledger

Files:
- Create: .github/workflows/ci.yml
- Create: scripts/verify.ps1
- Create: backend/tests/test_documentation.py
- Modify: README.md
- Modify: ARCHITECTURE.md
- Modify: docs/status/m0-m1-goal-contract.md

Interfaces:
- Produces Windows-first setup/start/test instructions, deterministic CI, and scripts/verify.ps1 that runs named local verification commands without secrets.
- Consumes executable commands from Tasks 1 through 13.
- Documentation names only existing commands/files and does not claim live-provider execution.

- [ ] Step 1: Write failing documentation checks

    def test_documentation_names_real_verification_entrypoint() -> None:
        readme = Path("README.md").read_text(encoding="utf-8")
        assert "scripts/verify.ps1" in readme
        assert "Playwright" in readme
        assert "100% SAFE" not in readme

- [ ] Step 2: Run to confirm failure

Run: & .\.venv\Scripts\python.exe -m pytest backend/tests/test_documentation.py -v
Expected: the check fails because the script and complete documentation do not exist.

- [ ] Step 3: Implement honest docs and verification orchestration

Document offline provider defaults, optional server-side OpenAI configuration, fixture materialization, backend/frontend startup, API smoke, browser projects, artifacts, security limits, and limitations. Make verify.ps1 stop on failure and run backend tests/lint/typecheck, frontend lint/typecheck/tests/build, integration/security tests, live smoke, both Playwright projects, diff review, secret scan, and the forbidden-token scan. CI runs deterministic checks only.

- [ ] Step 4: Verify docs and CI

Run:
    & .\scripts/verify.ps1 -CheckOnly
    git diff --check
    $forbiddenPattern = [string]::Join('|', @('T'+'B'+'D', 'T'+'O'+'D'+'O', 'F'+'I'+'X'+'M'+'E', 'X'+'X'+'X', '1'+'0'+'0% SAFE', 'f'+'ake benchmark', 'place'+'holder'))
    rg -n $forbiddenPattern README.md ARCHITECTURE.md docs/status scripts .github
Expected: exit 0; no forbidden-token or unsafe-copy match.

- [ ] Step 5: Commit

    git add .github scripts README.md ARCHITECTURE.md docs/status/m0-m1-goal-contract.md
    git commit -m "docs: document M0 and M1 reproducibility"

### Task 15: Full M0/M1 Verification, Diff Review, and Milestone Gate

Files:
- Modify: docs/status/m0-m1-goal-contract.md

Interfaces:
- Produces executed evidence for GC-01 through GC-14 and a ledger with command names, timestamps, exit codes, artifact references, and explicit live-provider status.
- Consumes the repository from Tasks 1 through 14.
- Completion means M0/M1 status only; never the overall project.

- [ ] Step 1: Create a command-to-criterion checklist in working notes

Map every GC ID to exact commands and observed evidence paths, including target before/after hashes, API errors, browser console/network observations, security scans, and clean diff results. Do not create fake evidence or generated benchmark data.

- [ ] Step 2: Run the complete verification sequence

Run:
    & .\.venv\Scripts\python.exe -m pytest backend/tests -v --cov=backend/app --cov-fail-under=85
    & .\.venv\Scripts\python.exe -m ruff check backend
    & .\.venv\Scripts\python.exe -m mypy backend
    Set-Location frontend
    npm run lint
    npm run typecheck
    npm test -- --run
    npm run build
    npx playwright test --project=desktop
    npx playwright test --project=mobile
    Set-Location ..
    & .\scripts\verify.ps1 -CheckOnly
    git diff --check
    $forbiddenPattern = [string]::Join('|', @('T'+'B'+'D', 'T'+'O'+'D'+'O', 'F'+'I'+'X'+'M'+'E', 'X'+'X'+'X', '1'+'0'+'0% SAFE', 'f'+'ake benchmark', 'place'+'holder'))
    rg -n $forbiddenPattern --glob '!*.lock' --glob '!docs/superpowers/specs/**' --glob '!docs/superpowers/plans/**' .
    git status --short --untracked-files=all
Expected: every applicable command exits 0, browser console/network collections are empty, no secrets/fake metrics/unavailable controls/unrelated files exist.

- [ ] Step 3: Reconcile GC-01 through GC-14

Mark each criterion PASS, BLOCKED, or NOT-VERIFIED only with observed evidence. Any failure invokes superpowers:systematic-debugging, adds a regression test before the smallest fix, and reruns the relevant suite. Missing live credentials affect only the optional live-provider check.

- [ ] Step 4: Request code review

Run:
    git diff --stat HEAD~14..HEAD
    git diff --name-only HEAD~14..HEAD
    git log --oneline --decorate -20
Then invoke superpowers:requesting-code-review. Confirm no M2+ implementation or artifacts, all Python functions have one-line docstrings, and all API/UI names match the approved spec.

- [ ] Step 5: Record the milestone outcome and commit

If all locally verifiable criteria pass, update the ledger to M0/M1 STATUS: COMPLETE and run:
    git add docs/status/m0-m1-goal-contract.md
    git commit -m "verify: close M0 and M1 goal contract"
Otherwise continue the Goal Contract loop or record a genuine external blocker. Never report the overall TopologyProof project as complete.

