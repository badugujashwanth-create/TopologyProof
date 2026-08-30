# M0/M1 goal contract

Every criterion begins `NOT-VERIFIED`. Status changes require the named executed evidence; implementation alone is insufficient.

| ID | Acceptance criterion | Status | Required evidence |
|---|---|---|---|
| GC-01 | Clean checkout installs and runs documented development tooling. | PARTIAL | Frontend M0 tooling was exercised on 2026-08-30: `npm --prefix frontend install` (blocked by Windows `EPERM` opening `package-lock.json`), `npm --prefix frontend run lint` (exit 0), `npm --prefix frontend run typecheck` (blocked writing `node_modules/.tmp/*.tsbuildinfo`), `npm --prefix frontend run test -- --run` (blocked writing `node_modules/.vite-temp/*`), and `npm --prefix frontend run build` (blocked by the same TypeScript temporary-file writes). See `docs/status/task-2-report.md`; clean-checkout and startup evidence remain for Task 15. |
| GC-02 | Local repository validation and ref resolution avoid target mutation. | NOT-VERIFIED | Git integration and hostile-input tests. |
| GC-03 | Diff, changed paths, and changed Python symbols are extracted. | NOT-VERIFIED | Materialized-fixture integration tests. |
| GC-04 | Unsafe module-level deduplication state is identified without overclaiming. | NOT-VERIFIED | Positive and cache-only negative tests. |
| GC-05 | Context expansion links relevant state, route, and side effects within budgets. | NOT-VERIFIED | Context and limit tests. |
| GC-06 | Semantic provider behavior handles inference, uncertainty, and failures. | NOT-VERIFIED | Provider contract and offline analysis tests. |
| GC-07 | Findings map risk to validated candidate source evidence. | NOT-VERIFIED | Schema and evidence validation tests. |
| GC-08 | API flows return documented statuses and errors. | NOT-VERIFIED | API tests and live HTTP smoke. |
| GC-09 | UI submits analysis and renders real states across viewport sizes. | NOT-VERIFIED | Desktop and mobile browser tests. |
| GC-10 | A trajectory and reproducible report are generated. | NOT-VERIFIED | Artifact ordering and file inspection. |
| GC-11 | Missing live credentials preserve offline operation. | NOT-VERIFIED | Credential-free suite and provider failure test. |
| GC-12 | Target repositories remain untrusted, read-only input within limits. | NOT-VERIFIED | Security-focused tests. |
| GC-13 | Relevant tests, lint, typechecks, builds, smoke, and browser flows pass. | NOT-VERIFIED | Milestone command evidence. |
| GC-14 | The milestone diff has no unrelated files, secrets, fake metrics, fake trajectories, or unavailable controls. | NOT-VERIFIED | Diff and content scans. |
