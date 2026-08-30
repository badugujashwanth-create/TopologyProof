# Task 3 report: typed domain and API contracts

Date: 2026-08-30

Scope: Task 3 schema contracts only. No Task 4 fixture, Task 6 preview contract, runtime verification, M2+ capability, or frontend file was added or changed.

## Outcome

- Added strict frozen Pydantic contracts for repository intake, evidence, analysis context and hypotheses, findings, run state, trajectories, and reports.
- Added the documented provider, topology, severity, verdict, run, stage, and trajectory wire enums, including the five fixed topology dimensions and eight pipeline stages.
- Enforced non-blank text, absolute repository paths, canonical repository-relative POSIX evidence paths, lowercase 40-to-64-character Git IDs, positive forward line ranges, closed-unit confidence, unique evidence and dimensions, and safe artifact names.
- Added immutable, unique, storage-safe run artifact references and lifecycle rules that prevent a failed run from claiming a completed pipeline or an M1 run from claiming an M2-only reproducible verdict.
- Reused Task 1 `ProviderName` and named settings limits; `backend/app/config.py` remains unchanged.
- Removed the prematurely added `AnalysisPreview` model and test because the approved plan assigns that contract to Task 6.

## Regression record

The inherited schema implementation predates this handoff, so this report makes no retroactive RED claim for its initial creation. Fresh correction evidence:

- The first fresh schema run found public-export omissions and stale Task 6 preview references.
- The next full schema run exposed four lifecycle-contract failures: missing artifact references, M2-only verdict acceptance, and inconsistent failed-run states. The smallest model changes made all four pass.
- RED: `test_error_response_rejects_blank_optional_field` failed because `ErrorResponse.field` accepted whitespace.
- GREEN: the same focused test passed after the field used the shared non-blank validator.

## Verification

All commands below ran on 2026-08-30 with Python 3.13.7:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/schemas/test_contracts.py -v --basetemp=.pytest-task3-verify -o cache_dir=.pytest-task3-verify-cache
& .\.venv\Scripts\python.exe -m ruff check backend/app/schemas backend/tests/schemas backend/app/config.py
& .\.venv\Scripts\python.exe -m mypy backend/app/schemas backend/app/config.py
& .\.venv\Scripts\python.exe -m pytest backend/tests -v --basetemp=.pytest-task3-backend -o cache_dir=.pytest-task3-backend-cache
& .\.venv\Scripts\python.exe -m ruff check backend
& .\.venv\Scripts\python.exe -m mypy backend
```

Results: 95 schema-contract tests passed; the schema lint and type checks passed; 112 backend tests passed; and the full backend lint and type checks passed.

## Review

Independent specification and quality review found and the implementation corrected: missing `AnalysisRun.artifact_refs`, incomplete failed-run/M2 lifecycle guards, a blank optional error field, stale task-3 verification claims, and premature Task 6 preview scope. All workspace-local Task 3 pytest basetemp and cache directories are removed before the Task 3 commit.
