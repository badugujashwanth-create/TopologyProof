# TopologyProof Design Specification

**Status:** Proposed for written-spec approval  
**Date:** 2026-08-29  
**Milestones covered in implementation detail:** M0 and M1  
**Product horizon covered architecturally:** M0 through M9

## 1. Purpose

TopologyProof is a static-first verification system for Python/FastAPI backend patches. It accepts a local Git repository, a ticket or requirement, a base ref, and a candidate ref, then identifies correctness properties that silently depend on deployment topology.

The core product claim is deliberately narrow:

> A backend patch is not fully verified until the assumptions of its deployment topology have been challenged.

The M1 showcase is webhook deduplication implemented with process-local mutable state. TopologyProof must connect a concrete code signal to duplicate suppression, a durable business side effect, and the hidden assumption that equivalent deliveries observe shared state.

TopologyProof is a falsification aid, not a formal proof system. It reports evidence, confidence, uncertainty, limitations, and—only when justified—a focused runtime verification recommendation.

## 2. Goals and non-goals

### 2.1 Product goals

- Analyze a target repository without mutating it.
- Resolve exact Git commits for a requested base and candidate ref and analyze their diff.
- Build bounded, provenance-rich context instead of sending an entire repository to a model.
- Separate deterministic static signals from semantic findings.
- Explain the correctness property, deployment assumption, affected topology dimensions, predicted failure, evidence, and confidence for every finding.
- Support deterministic tests and an offline M1 showcase without API credentials.
- Expose real analysis state, findings, trajectory events, and reports through a FastAPI API and React UI.
- Preserve observable engineering actions without storing or exposing private model reasoning.
- Establish reproducible foundations for later runtime verification and evaluation milestones.

### 2.2 Explicit non-goals for M0 and M1

- GitHub or pull-request ingestion.
- Automatic modification or repair of target repositories.
- Arbitrary target-repository command execution.
- Languages or frameworks other than Python and FastAPI.
- Runtime topology experiments, Docker Compose, PostgreSQL, Redis, Kubernetes, or a Cartesian-product test lab.
- Bug families other than webhook deduplication.
- The 24-patch benchmark, baselines, evaluation engine, evaluation metrics, or Evaluation Dashboard.
- Claims of universal safety, formal verification, or generic concurrency/distributed-systems coverage.
- LangGraph, microservices, or other orchestration frameworks not required by the M1 flow.

## 3. Fixed topology taxonomy

The MVP has exactly five top-level dimensions. Internal enums use the following lowercase wire values; the UI renders human-readable labels.

| Enum member | Wire value | Meaning |
|---|---|---|
| `REPLICA_COUNT` | `replica_count` | Correctness changes between one and multiple workers or replicas. |
| `REQUEST_ROUTING` | `request_routing` | Correctness depends on equivalent requests reaching the same process. |
| `RESTART_RECOVERY` | `restart_recovery` | Correctness state is lost or changed across process restart. |
| `CONCURRENCY` | `concurrency` | Correctness changes between sequential and simultaneous operations. |
| `STATE_LOCALITY` | `state_locality` | Correctness depends on process-local versus shared durable state. |

No other top-level dimension may be added without repository evidence and an explicitly reviewed scope change.

## 4. System context and trust boundary

TopologyProof is a local developer tool in M1. The API binds to loopback by default, accepts filesystem paths visible to the backend process, and permits CORS only from the configured frontend development origin. It is not designed as a remotely exposed multi-tenant service.

The TopologyProof repository and configured artifact directory are trusted. An analyzed repository, its source, Git metadata, refs, configuration, symlinks, and text are untrusted input. Repository instructions cannot authorize commands or override TopologyProof behavior.

The target repository remains read-only. All source used for commit analysis is read from resolved Git objects so analysis corresponds to the candidate commit and does not depend on or alter the working tree. Filesystem access to the target is limited to repository discovery and using its canonical root as the Git process working directory. Git is invoked with argument arrays, never through a shell. User refs are first resolved to commit object IDs; subsequent diff and blob operations use only those object IDs. Target-repository hooks, test commands, build commands, and executable files are never run in M1.

## 5. Architecture

The M1 system is a monorepo with one FastAPI backend, one React/Vite frontend, local file-backed run artifacts, deterministic analysis components, and a provider boundary for semantic assumption mining.

```text
Local Git repository + ticket + base ref + candidate ref
                         |
                         v
                  Repository Intake
                         |
                         v
                    Context Builder
                         |
                         v
                Static Signal Engine
                         |
                         v
                  Assumption Miner
                         |
                         v
                Finding Synthesizer
                         |
                         v
          Verification Recommendation Policy
                         |
                         v
                 Verdict + Report
                         |
            +------------+------------+
            |                         |
         FastAPI                  JSONL/JSON/MD
            |
        React/Vite
```

Each stage receives typed input and returns typed output. The orchestrator owns stage ordering and state transitions; components do not call the UI, mutate the target repository, or silently trigger runtime verification.

### 5.1 Repository organization policy

The implementation plan will assign exact files, but M0 and M1 may create only directories with an immediate responsibility:

- `backend/` for the FastAPI service and analysis pipeline.
- `frontend/` for the React/Vite client.
- `tests/` for cross-component and end-to-end tests that do not belong beside a package.
- `demo/` for source-controlled webhook fixture inputs and the materializer that creates a real temporary Git repository.
- `trajectories/` only for documented schemas or intentionally retained example outputs generated by real runs; transient run data belongs in the ignored artifact directory.
- `docs/` for architecture, milestone status, and the Superpowers specifications/plans.

Directories for benchmarks, evaluation results, experiments, infrastructure, or submission artifacts are deferred until their milestones create real content. Empty speculative folders are not part of M0.

## 6. Core components and interfaces

### 6.0 Shared stage contracts

All contracts are Pydantic models. Filesystem paths are serialized as strings only at API/artifact boundaries; internal path values use the platform path type. Repository-relative evidence paths use normalized POSIX separators.

| Contract | Required contents | Produced by | Consumed by |
|---|---|---|---|
| `AnalysisRequest` | Repository path, ticket, base ref, candidate ref, optional provider name. | API/UI | Intake and orchestrator. |
| `RepositorySnapshot` | Canonical root, resolved base/candidate commit IDs, repository identity metadata safe to retain. | Intake resolution | Diff loader, context builder, evidence validator. |
| `DiffArtifact` | Bounded patch text, changed-path records, diff summary, parse diagnostics. | Intake diff loader | Symbol detector, context builder, static engine, miner. |
| `ChangedSymbol` | Path, symbol kind/name, old/new line spans when available, resolved commit. | Symbol detector | Context builder and trajectory recorder. |
| `ContextItem` | Source excerpt, path, commit, line range, symbol, selection reason, provenance, redaction status. | Context builder | Static engine and miner. |
| `StaticSignal` | Signal kind, normalized facts, exact evidence, related context IDs, diagnostics. | Static Signal Engine | Assumption Miner. |
| `AssumptionMiningInput` | Ticket, diff summary/excerpts, bounded context, signals, tests/deployment context, limitations. | Orchestrator | Configured assumption provider. |
| `AssumptionHypothesis` | Engineering summary, correctness property, deployment assumption, predicted failure, dimensions, evidence refs, confidence, recommendation candidate, limitations. | Assumption provider/miner | Finding Synthesizer. |
| `Finding` | Validated common finding contract defined in section 6.5. | Finding Synthesizer | Verdict, report, API, UI. |
| `AnalysisRun` | Run state, current/completed stages, provider, timestamps, artifact refs, limitations, safe error. | Orchestrator/run store | API and UI. |
| `TrajectoryEvent` | Observable action schema defined in section 6.9. | Every stage through recorder | Artifact store and API. |

Stage interfaces are explicit and dependency-injected:

```text
resolve_request(AnalysisRequest) -> RepositorySnapshot
load_diff(RepositorySnapshot) -> DiffArtifact
detect_changed_symbols(RepositorySnapshot, DiffArtifact) -> list[ChangedSymbol]
build_context(AnalysisRequest, RepositorySnapshot, DiffArtifact, list[ChangedSymbol]) -> list[ContextItem]
scan_static_signals(RepositorySnapshot, DiffArtifact, list[ContextItem]) -> list[StaticSignal]
mine_assumptions(AssumptionMiningInput) -> list[AssumptionHypothesis]
synthesize_findings(RepositorySnapshot, list[AssumptionHypothesis]) -> list[Finding]
render_report(AnalysisRun, list[Finding], list[TrajectoryEvent]) -> ReportArtifact
```

Concrete implementations may be synchronous or asynchronous internally, but these logical boundaries and ownership rules remain stable. Errors cross boundaries as typed domain errors rather than provider/subprocess exceptions.

### 6.1 Repository Intake

Repository Intake validates and normalizes an `AnalysisRequest`, then produces a `RepositorySnapshot` and `DiffArtifact`.

Required behavior:

1. Validate that `repo_path` is absolute, exists, is a directory, and identifies a Git work tree.
2. Resolve the repository root and preserve it as an absolute canonical path.
3. Resolve `base_ref` and `candidate_ref` as commit objects without treating them as command options.
4. Obtain a no-external-diff, no-text-conversion diff between the resolved commits.
5. List changed paths and change types.
6. Read candidate/base blobs from Git objects, not from a mutable checkout.
7. Parse changed Python symbols where the relevant blob is valid Python; record a non-fatal parse diagnostic otherwise.
8. Collect only relevant test, FastAPI lifecycle, and deployment/configuration metadata selected by deterministic rules.
9. Return structured, user-actionable failures for invalid paths, repositories, refs, oversized inputs, timeouts, and unsupported binary content.

Git subprocesses use a fixed executable, explicit argument lists, a clean controlled environment, captured output limits, and timeouts. M1 configuration exposes validated named limits with these defaults:

| Setting | Default |
|---|---:|
| `GIT_COMMAND_TIMEOUT_SECONDS` | 30 |
| `MAX_DIFF_BYTES` | 5,000,000 |
| `MAX_SOURCE_FILE_BYTES` | 1,000,000 |
| `MAX_CHANGED_FILES` | 500 |
| `MAX_CONTEXT_FILES` | 50 |
| `MAX_TICKET_CHARACTERS` | 20,000 |

Limits fail closed with a structured error; they are not silently truncated in a way that could support a strong verdict.

### 6.2 Context Builder

The Context Builder starts with the ticket, changed files, changed symbols, and diff. It produces a bounded list of `ContextItem` records containing candidate-commit source excerpts and provenance.

For the webhook slice, expansion follows deterministic references relevant to the changed code:

- definitions and uses of the mutable state;
- membership checks and mutations of that state;
- containing FastAPI route and helper functions;
- direct call sites and one-hop callees needed to understand side effects;
- nearby tests referring to the route, event identifier, or changed symbols;
- FastAPI startup/lifespan code and deployment configuration when it can affect process count or state;
- Redis/database usage only when related to the state or side effect under review.

Each item records its repository-relative path, resolved commit, line range, symbol when available, selection reason, and source stage. The builder enforces the file and byte budgets. If the budget prevents adequate context, the run records a limitation and cannot emit a high-confidence finding based on omitted evidence.

Files likely to contain secrets—such as `.env`, credentials, private keys, token stores, and Git internals—are excluded. Text sent to a remote provider is limited to selected excerpts and passed through secret-pattern redaction. Binary files are never sent.

### 6.3 Static Signal Engine

The Static Signal Engine is deterministic and operates on Python AST plus bounded source context. A signal is evidence of a pattern, not a defect.

M1 must detect module-level mutable `set`, `dict`, and `list` state created by literals, comprehensions, or direct built-in constructors. The webhook path must additionally record observable uses relevant to deduplication, including membership checks and mutation such as `add`, `update`, or assignment.

The engine emits `StaticSignal` records with:

- a stable signal identifier within the run;
- a signal kind;
- exact source evidence;
- the enclosing module/symbol;
- normalized facts, such as collection type, mutation operations, and membership-check locations;
- related context references;
- diagnostics and limitations.

The engine does not assign product severity or state that a correctness bug exists.

### 6.4 Assumption Miner

The Assumption Miner performs the semantic step: it evaluates the ticket, diff, selected context, signals, tests, and deployment metadata to propose concise `AssumptionHypothesis` records.

Its provider-independent input and output are Pydantic models. The provider protocol has one responsibility: accept an `AssumptionMiningInput` and return validated hypotheses. Business orchestration does not import a provider SDK.

M1 implements three provider roles. The deterministic offline provider is the credential-free default; selecting a remote provider is explicit configuration or an allowed API selection.

- A deterministic fake/stub injected by tests to cover success, uncertainty, invalid-output, and provider-failure paths.
- A deterministic offline webhook provider used for the credential-free fixture showcase. It is explicitly limited to the M1 webhook pattern and derives its output from signals and context rather than a fixture name or ground-truth label.
- An OpenAI provider adapter selected by configuration. Its implementation must be based on current official OpenAI documentation at implementation time, request structured output, apply timeouts, validate every response, and expose no key to the client or logs. Live invocation is credential-gated and is not required for deterministic M1 completion.

Remote-provider prompts identify repository text as untrusted quoted evidence, not instructions. Provider output cannot directly select files, invoke tools, change run state, or bypass evidence validation.

The miner must distinguish performance-only local state from correctness-bearing local state. For an M1 high-risk hypothesis, available evidence must connect all four links:

```text
process-local mutable state
    -> duplicate-detection decision
    -> externally visible or durable business side effect
    -> shared-state / routing / restart deployment assumption
```

A missing link lowers confidence or produces no hypothesis. The miner stores a concise engineering summary and evidence references, never private chain-of-thought or raw hidden reasoning.

### 6.5 Finding Synthesizer

The Finding Synthesizer converts validated hypotheses into the common `Finding` contract and rejects unsupported claims. It requires evidence to resolve to real candidate-commit source locations.

The contract includes:

| Field | Type/constraint |
|---|---|
| `finding_id` | Unique non-empty string within a run; numeric ordering has no semantic meaning. |
| `title` | Concise engineer-facing title. |
| `category` | One of the five topology dimension wire values; M1 primary category is `state_locality`. |
| `severity` | `critical`, `high`, `medium`, or `low`. |
| `confidence` | Number from 0 through 1. |
| `deployment_assumption` | Specific falsifiable statement. |
| `topology_dimensions` | Non-empty unique list drawn only from the fixed taxonomy. |
| `evidence` | Non-empty list of candidate-commit `EvidenceLocation` records. |
| `correctness_property` | The invariant the ticket/code is expected to preserve. |
| `predicted_failure` | Concrete failure mode under a changed topology. |
| `verification_recommendation` | `worth_running`, summary, relevant dimensions, and proposed property assertion. |
| `verdict` | `high-risk`, `review-required`, or `no-tested-failure`. |
| `limitations` | Explicit evidence or capability gaps. |

`EvidenceLocation` contains repository-relative POSIX path, one-based line number, optional end line, optional symbol, resolved candidate commit, and a short excerpt. Evidence paths must exist in the candidate tree and line numbers must be checked against the corresponding blob.

For the unsafe webhook showcase, the expected mapping is:

- primary category: `state_locality`;
- topology dimensions: `replica_count`, `request_routing`, `restart_recovery`, and `state_locality`;
- correctness property: one event identifier produces at most one durable side effect;
- predicted failure: duplicate effects when equivalent deliveries reach different processes or local state is erased by restart.

`concurrency` is assigned only if source evidence supports a read-check-write race; it is not added merely because web requests can be concurrent.

### 6.6 Verification Recommendation Policy

M1 may recommend a minimal experiment but cannot run it. `RUN VERIFICATION` is absent from the M1 UI because no real verifier exists until M2.

For the webhook finding, a useful recommendation specifies the later M2 comparison:

- baseline: one replica, two duplicate deliveries, durable side-effect count at most one;
- challenge: two replicas, identical event ID routed once to each replica, durable side-effect count at most one.

Only dimensions relevant to the hypothesis are included. No Cartesian product is generated.

### 6.7 Verdict Policy

Finding verdicts and the overall product verdict are separate.

- A finding is `high-risk` only when it links a correctness property to exact evidence and has severity `critical` or `high` with confidence at or above the named `HIGH_CONFIDENCE_THRESHOLD` of `0.80`.
- A finding is `review-required` when evidence suggests a potentially important dependency but the high-risk gate is not met.
- `no-tested-failure` means no high-confidence topology-sensitive correctness failure was confirmed in the analyzed scope. It never means safe in all deployments.

Overall rendering rules:

| Color | Label | Rule |
|---|---|---|
| Red | `TOPOLOGY-SENSITIVE CORRECTNESS RISK` | At least one static/semantic finding is `high-risk`. |
| Red | `REPRODUCIBLE TOPOLOGY-SENSITIVE FAILURE` | A later real runtime verifier observes the stated property violation. This label is impossible in M1. |
| Yellow | `REVIEW REQUIRED` | At least one finding requires review and none is high-risk. |
| Green | `NO TESTED TOPOLOGY FAILURE` | No high-risk or review-required finding exists in scope. |

The UI and report must never display `100% SAFE`.

### 6.8 Orchestrator and run storage

The orchestrator is an explicit Python pipeline with these externally visible stages:

1. `repository_loaded`
2. `diff_parsed`
3. `context_expanded`
4. `static_analysis_completed`
5. `assumption_mining_completed`
6. `finding_synthesis_completed`
7. `verification_recommendation_completed`
8. `report_generated`

An `AnalysisRun` has state `queued`, `running`, `completed`, or `failed`, a current stage, stage timestamps, limitations, and an optional structured error. Stage changes occur only after the corresponding work succeeds. The frontend polls real run state; no fake timers or synthetic progress percentages are used.

M1 uses a single-process in-process executor suitable for a local tool. Analysis creation synchronously validates the schema, repository, provider selection, and refs through `resolve_request`. It then creates a run, records the completed repository-loaded stage, returns `202`, and uses a FastAPI background task for diff loading and all later stages. The preview endpoint reuses `resolve_request` and `load_diff` without persisting or starting semantic analysis. Run metadata and output are written atomically beneath a configured TopologyProof-owned artifact root, defaulting to `.topologyproof/runs/<run_id>/`:

```text
run.json
request.json
trajectory.jsonl
findings.json
report.md
```

The target repository is never used as the output location. Per-run in-process locks serialize metadata and trajectory writes, and publish operations use temporary sibling files followed by atomic replacement. On startup, a run left in `queued` or `running` is marked `failed` with a restart-interruption error; M1 does not claim durable job resumption. Completed artifacts remain readable. File-store operations validate run IDs and prevent path traversal.

### 6.9 Trajectory recorder

The trajectory is append-only JSONL. Each event contains `run_id`, monotonic `step`, UTC timestamp, component, action, input references, optional output reference, concise summary, measured duration in milliseconds when applicable, and structured tool-result metadata safe for display.

Supported M1 actions include:

- `repository_loaded`
- `diff_parsed`
- `changed_symbol_detected`
- `context_expanded`
- `static_signal_created`
- `hypothesis_created`
- `topology_dimension_assigned`
- `verification_proposed`
- `tool_result_observed`
- `hypothesis_updated`
- `finding_created`
- `report_generated`

Events are emitted only when the action occurs. Summaries expose engineering outcomes, not hidden model reasoning, secrets, or unbounded source content.

### 6.10 Report generator

The report generator consumes stored request metadata, resolved commits, findings, trajectory references, diagnostics, and limitations. It writes deterministic finding ordering and stable Markdown sections:

1. scope and analyzed refs;
2. overall verdict;
3. finding summary;
4. per-finding correctness property, assumption, evidence, dimensions, predicted failure, severity/confidence, and recommendation;
5. analysis limitations and provider/runtime verification status;
6. reproduction metadata.

The report is reproducible from the stored run artifacts. Timestamps and run identifiers are recorded metadata, not fabricated or normalized benchmark evidence.

## 7. API contract

All endpoints are versioned below `/api/v1`. Responses use Pydantic schemas. Expected domain failures use a structured error body with `code`, `message`, and optional field/detail data; unexpected failures are logged with a correlation/run ID and return no stack trace or source secret.

| Method and path | Purpose | Success |
|---|---|---|
| `GET /api/v1/health` | Process health for local development checks. | `200` with service/version status. |
| `POST /api/v1/analysis-previews` | Validate repository and refs and return resolved commits, changed-file count, changed Python-file count, and diff summary without starting semantic analysis. | `200`. |
| `POST /api/v1/analyses` | Resolve the request, create a run, and enqueue diff loading plus later analysis stages. | `202` with run ID and status URL. |
| `GET /api/v1/analyses/{run_id}` | Return real run state, stages, summary verdict when available, limitations, and safe error data. | `200` or `404`. |
| `GET /api/v1/analyses/{run_id}/findings` | Return ordered findings after synthesis; return an empty list only for a completed run with no findings. | `200`, `409` if not ready, or `404`. |
| `GET /api/v1/analyses/{run_id}/findings/{finding_id}` | Return one finding. | `200`, `404`, or `409` if not ready. |
| `GET /api/v1/analyses/{run_id}/trajectory` | Return display-safe structured trajectory events. | `200` or `404`. |
| `GET /api/v1/analyses/{run_id}/report` | Return the generated report as `text/markdown` with a safe download filename. | `200`, `409` if not ready, or `404`. |

Request schema:

```text
AnalysisRequest
  repo_path: absolute local directory path
  ticket: non-blank text, at most MAX_TICKET_CHARACTERS
  base_ref: non-blank Git ref
  candidate_ref: non-blank Git ref
  provider: optional allowed provider name, default offline; clients cannot supply API keys
```

Malformed schema input returns `422`. Validly shaped but invalid repository/ref input returns `400` with a stable domain code. Oversized input returns `413`; a Git timeout returns `408`; unavailable configured providers return `503`. If a background stage fails after `202`, the run becomes `failed` and the status endpoint exposes a safe structured error.

## 8. Frontend design

The frontend is engineering verification software, not a chatbot. It is mobile-first and responsive, with a dark technical-workbench theme: deep ink/slate surfaces, cool blue structural accents, amber for uncertainty, red for verified/high-risk danger, and restrained green for scoped no-failure results. Typography prioritizes dense legibility and code evidence. Motion is limited to real stage transitions, focus, and navigation feedback; there are no decorative fake progress animations.

M1 implements four of the eventual five product screens:

1. **New Analysis** — repository path, ticket, base ref, candidate ref, optional real preview summary, validation errors, and `ANALYZE PATCH`.
2. **Analysis Progress** — the eight real stages, current status, safe failure details, and transition to findings when complete.
3. **Findings Dashboard** — overall verdict, finding counts, severity, confidence, and finding summaries; includes a deliberate empty/no-finding state with scope limitations.
4. **Finding Detail / Verification** — correctness property, hidden assumption, five-dimension sensitivity panel, exact source evidence, predicted failure, confidence/severity, recommendation, and limitations. M1 labels verification as recommended/not recommended but provides no execution button.

The **Evaluation Dashboard** is deferred to M7 and is not represented by fake navigation, placeholder metrics, or hard-coded values in M1.

Critical states include initial, preview-loading, preview-error, analysis-submitting, queued/running, completed-with-findings, completed-empty, failed, API-unavailable, finding-not-found, and report-not-ready. UI state derives from API responses.

## 9. M1 webhook vertical slice

The source-controlled demo fixture contains base and candidate source snapshots plus metadata and a materializer. The materializer creates a genuine local temporary Git repository with two commits and returns its path and refs. A nested `.git` directory is not committed to TopologyProof.

The candidate FastAPI patch uses process-local mutable state to suppress duplicate webhook handling and invokes a business-side-effect function. The analyzer never receives an unsafe/safe label. The ticket states the idempotency requirement.

The end-to-end acceptance flow is:

1. Materialize the fixture Git repository.
2. Submit its path, ticket, base ref, and candidate ref through the UI.
3. Resolve both refs and extract the real diff.
4. Identify changed Python symbols and a module-level mutable collection signal.
5. Expand context to the membership check, mutation, route, and side-effect call.
6. Produce a semantic hypothesis that shared deduplication state is assumed.
7. Synthesize a finding with checked source evidence and the relevant topology dimensions.
8. Persist trajectory events and a Markdown report.
9. Expose real run progress and findings through the API.
10. Render the dashboard and finding detail in the browser.

The unsafe fixture must produce a high-risk result under the deterministic offline provider. Unit tests must separately prove that a mutable global used only as a cache/performance optimization does not automatically become a high-risk correctness finding.

## 10. Error handling and uncertainty

- Input validation failures identify the invalid field without leaking local source.
- Git failures preserve a safe error code and bounded diagnostic; commands and credentials are not echoed wholesale.
- Syntax errors in an individual Python file create diagnostics and reduce coverage; they do not crash unrelated analysis.
- Context budget exhaustion creates an explicit limitation and prevents unsupported high-confidence claims.
- Provider timeout, authentication failure, invalid structured output, or transport failure is recorded. The configured offline provider may be used only when explicitly selected; a live-provider failure is not silently disguised as live model output.
- A run-level unrecoverable stage failure transitions once to `failed`; partially written final findings/report files are not published.
- A finding with insufficient semantic or evidence support is YELLOW or omitted, not forced to RED.
- No-finding results state analyzed refs, supported bug-family scope, provider used, and limitations.

## 11. Security requirements

- Treat repository content as data, never instructions.
- Never run target tests, lifecycle hooks, package managers, Docker files, scripts, binaries, or commands during M1 analysis.
- Never check out or write into the target repository.
- Use shell-free subprocess argument arrays and resolved commit IDs.
- Reject path traversal for API artifact identifiers and evidence lookups.
- Do not follow working-tree symlinks to read source; use Git blobs and validate any unavoidable filesystem read remains inside the canonical root.
- Exclude secret-prone files and redact likely credentials before remote-provider requests and logs.
- Read API credentials only from environment configuration; provide `.env.example`; never return keys through the API.
- Bound repository inputs, subprocess duration/output, source excerpts, provider input/output, and artifact paths.
- Log safe identifiers and outcomes, not full ticket/source/provider payloads by default.
- Keep the M1 server loopback-only by default and document that remote/multi-tenant deployment is unsupported.

## 12. Testing and evidence strategy

Implementation follows test-driven development. Each production behavior starts with a failing test that demonstrates the intended contract.

### 12.1 Backend

- Unit tests for path/ref validation, Git argument construction, diff parsing, symbol extraction, AST signals, bounded context selection, evidence validation, verdict rules, report ordering, trajectory sequencing, and artifact path safety.
- Negative tests for non-repositories, missing/hostile refs, binary/oversized input, syntax errors, symlink escape attempts, timeouts, provider failures, invalid provider output, and cache-only mutable state.
- Provider-contract tests with a deterministic fake; OpenAI transport tests are mocked and never require credentials.
- Integration tests materialize a real Git fixture and run the complete offline analysis pipeline.
- API tests cover success status codes, malformed input, domain errors, run polling, not-ready responses, missing IDs, findings, trajectory, and report retrieval.
- Runtime smoke evidence starts the FastAPI process and performs the primary HTTP flow against it; route registration or unit tests alone are insufficient.

### 12.2 Frontend

- Component tests cover the important loading, error, empty, verdict, evidence, and topology-panel states.
- API client tests validate typed response handling and failures.
- Lint, typecheck, test, and production build run in M1 verification.
- Playwright starts the real frontend and backend, materializes the fixture, submits the form, observes real progress, opens findings and detail, checks the five topology labels, retrieves the report through the API-backed link, and checks browser console/network errors.
- Browser checks include a narrow mobile viewport and a desktop viewport.

### 12.3 Evidence rules

No test, build, endpoint, browser flow, provider call, or benchmark result is reported as passing without executed evidence. Missing OpenAI credentials make only live-provider verification `BLOCKED` or `NOT-VERIFIED`; deterministic tests and the offline vertical slice must still pass.

## 13. Reproducibility and developer experience

M0 establishes reproducible dependency declarations and lockfiles for supported Python and Node versions, one-command documented install/test/lint/typecheck/build flows per application, a root command summary, `.env.example`, and ignore rules for environments, dependencies, build output, local artifacts, and credentials.

Windows PowerShell instructions are first-class. Commands avoid undocumented global state. The README skeleton distinguishes offline deterministic demo use from optional live-provider configuration. CI, if added in M0, runs only deterministic checks that need no secrets and directly support M1.

## 14. Milestone boundaries

### 14.1 M0 — foundation only

M0 creates only what M1 needs:

- Git hygiene and repository instructions/documentation foundation.
- Backend package, FastAPI startup skeleton, Pydantic settings, dependency lock, lint/typecheck/test configuration.
- Frontend React/Vite/TypeScript skeleton, dependency lock, lint/typecheck/test/build configuration.
- Shared API contract strategy without speculative code generation.
- Root README startup/test skeleton and `.env.example` with names only.
- Artifact-directory convention and fixture-materialization strategy.
- Minimal deterministic CI only if it is executable and useful immediately.

M0 does not implement the analysis pipeline, fake product data, runtime lab, benchmark, or submission package.

### 14.2 M1 — flawless static-first webhook slice

M1 includes:

- read-only local Git intake and preview;
- diff, changed-file, and changed-symbol extraction;
- bounded provenance-rich context;
- deterministic module-level mutable-state signals;
- provider abstraction, fake provider tests, deterministic offline webhook provider, and a documented OpenAI adapter with mocked contract tests;
- semantic webhook assumption mining and finding synthesis;
- fixed topology taxonomy, verdict policy, exact evidence validation, uncertainty, and limitations;
- in-process orchestration, real progress state, file-backed artifacts, observable trajectory, and Markdown report;
- versioned FastAPI endpoints and error contracts;
- React screens 1 through 4 with real API state;
- a materialized local Git showcase fixture;
- backend, frontend, integration, runtime API, and Playwright evidence.

M1 explicitly excludes runtime verification. A recommendation is data; an execution control is not shown.

### 14.3 Later milestones

- **M2:** selective one-versus-two-worker webhook runtime verification.
- **M3:** harden classification across the fixed five-dimension taxonomy.
- **M4:** add the remaining bug families with safe counterparts.
- **M5:** build the 24-patch benchmark without label leakage.
- **M6:** implement fair existing-tests, static-scanner, and generic-agent baselines plus evaluation engine.
- **M7:** render only actual evaluation files in the Evaluation Dashboard.
- **M8:** security, browser QA, Docker/reproduction, and documentation hardening.
- **M9:** real submission artifacts, screenshots, demo script, final benchmark, and regression evidence.

Each later milestone requires its own reviewed plan. M0+M1 are the only milestones planned after this specification is approved.

## 15. M0+M1 Goal Contract

Every criterion begins `NOT-VERIFIED` because the repository is empty at specification time. Code existence cannot change a status to PASS; the named evidence must be executed.

| ID | Acceptance criterion | Initial status | Required evidence |
|---|---|---|---|
| GC-01 | A clean checkout can install and run backend/frontend development tooling from documented Windows-friendly commands. | NOT-VERIFIED | Clean-environment install plus startup commands. |
| GC-02 | Local repository validation and exact base/candidate ref resolution work without target mutation. | NOT-VERIFIED | Git integration tests, before/after target status check, hostile-input tests. |
| GC-03 | The requested diff, changed paths, and practical changed Python symbols are extracted from resolved commits. | NOT-VERIFIED | Real materialized-fixture integration tests. |
| GC-04 | The signal engine deterministically identifies the unsafe module-level deduplication state without declaring every mutable global a bug. | NOT-VERIFIED | Positive signal and cache-only negative tests. |
| GC-05 | Context expansion connects the changed state to membership, mutation, route, and side-effect code with provenance and budgets. | NOT-VERIFIED | Context unit/integration assertions and limit tests. |
| GC-06 | The semantic provider path links the M1 chain and handles uncertainty/failure deterministically in tests. | NOT-VERIFIED | Fake-provider contract tests, mocked OpenAI-adapter tests, and offline fixture analysis. |
| GC-07 | A valid structured finding maps the webhook risk to exact candidate source evidence and relevant fixed dimensions. | NOT-VERIFIED | Pydantic validation and evidence line/blob checks. |
| GC-08 | The API starts and the preview/create/status/findings/detail/trajectory/report flows return their specified statuses and errors. | NOT-VERIFIED | Live-process HTTP smoke plus API test suite. |
| GC-09 | The UI submits a real analysis, shows real progress, renders dashboard/detail/evidence/dimensions, and handles loading/error/empty states. | NOT-VERIFIED | Playwright desktop/mobile run with console/network inspection. |
| GC-10 | A real trajectory JSONL and reproducible Markdown report are generated from the run. | NOT-VERIFIED | Artifact schema/ordering tests and end-to-end file inspection. |
| GC-11 | Missing live-provider credentials do not break tests or the offline showcase and are reported honestly. | NOT-VERIFIED | Credential-free full suite and configured-provider failure test. |
| GC-12 | Target repositories are treated as untrusted read-only input within documented M1 limits. | NOT-VERIFIED | Security-focused tests for command injection, traversal, symlinks, secrets, limits, and no target execution. |
| GC-13 | Relevant backend/frontend tests, lint, typecheck, builds, runtime API smoke, and browser flow all pass. | NOT-VERIFIED | Exact commands and captured exit/runtime evidence at milestone close. |
| GC-14 | The milestone diff contains no unrelated files, secrets, fake metrics, fake trajectories, or controls for unavailable functionality. | NOT-VERIFIED | Diff review, secret scan, placeholder/TODO scan, UI review. |

M1 is complete only when every locally verifiable criterion is PASS. A credential-dependent live-provider check may remain `BLOCKED` or `NOT-VERIFIED` without blocking the deterministic M1 product only because live-provider execution is optional; its status must remain visible.

## 16. Planning and execution constraints

After written-spec approval:

1. Invoke `superpowers:writing-plans`.
2. Write milestone-specific plans under `docs/superpowers/plans/`; start with M0 and M1 only.
3. Use subagent-driven development as the selected execution mode.
4. Do not permit overlapping write ownership of the same files.
5. Apply test-driven development to features and systematic debugging to unexpected failures.
6. Re-evaluate the Goal Contract after each meaningful task, not only at milestone end.
7. Use verification-before-completion and request code review after meaningful completed milestones.
8. Stop M1 only when all locally actionable M0/M1 criteria pass or a genuine external blocker remains explicitly identified.

## 17. Design decisions and resolved trade-offs

- **Static-first over runtime-first:** matches the thesis and avoids premature infrastructure; runtime evidence begins in M2.
- **Explicit orchestration over LangGraph:** M1 has a linear, inspectable workflow and does not justify another framework.
- **Git-object reads over checkout reads:** keeps refs exact and the target working tree untouched.
- **Local file artifacts over a database:** sufficient for a single-user local M1 while preserving inspectable trajectories and reports.
- **Background task over distributed queue:** real progress without introducing a broker; interrupted-run recovery is explicitly unsupported in M1.
- **Deterministic offline provider plus optional LLM adapter:** preserves credential-free reproducibility while keeping semantic reasoning behind a replaceable provider boundary.
- **Fixture materialization over a nested Git repository:** produces real Git evidence without committing nested repository metadata.
- **Four real M1 screens over five partially fake screens:** Evaluation Dashboard waits for real evaluation files in M7.
- **Recommendation without execution control:** avoids pretending M2 runtime capability exists in M1.

## 18. Open decisions

There are no unresolved product or architectural decisions requiring user choice before M0+M1 planning. Exact package versions, concrete file boundaries, task ordering, and conservative implementation details belong in the M0/M1 implementation plans and must follow this specification without broadening scope.
