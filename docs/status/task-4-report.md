# Task 4 report: reproducible webhook Git fixture

Date: 2026-08-30

Scope: trusted fixture snapshots, the local two-commit materializer, test helpers,
and fixture documentation only. No repository ingestion, context analysis,
providers, API handlers, orchestration, UI, runtime verification, or M2+ work was
implemented.

## TDD record

- RED: `pytest backend/tests/demo/test_materialize.py -v --basetemp .pytest-task4-temp`
  failed during collection with `ModuleNotFoundError: No module named 'demo'`, as
  expected before the materializer existed.
- The initial implementation run passed the two-repository and typed-helper tests
  but failed the CLI test because it serialized an extra `provider` field. The
  CLI was narrowed to the required four fields.
- Review correction RED: the helper test failed when it asserted the real two-file
  diff totals and state-declaration line; the helper had placeholder counts and a
  stale line number. It now records the real `6/2` and `1/1` file deltas, aggregate
  `7/3` totals, and line 8.
- GREEN: all three materializer tests passed after the corrections.

## Verification

Executed on Python 3.13.7:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/demo/test_materialize.py -v --basetemp .pytest-task4-temp
& .\.venv\Scripts\python.exe -m ruff check demo backend/tests/helpers backend/tests/demo
& .\.venv\Scripts\python.exe -m mypy demo backend/tests/helpers backend/tests/demo
& .\.venv\Scripts\python.exe -m demo.webhook_dedup.materialize --destination .topologyproof\fixtures\manual
git -C .topologyproof\fixtures\manual status --short
```

Results: pytest reported 3 passed. Ruff reported all checks passed. Mypy reported
no issues in 11 source files. The CLI emitted absolute `repo_path`, 40-character
base and candidate commit IDs, and the trusted ticket text; the status command
emitted no output. Pytest also emitted one pre-existing `.pytest_cache` ACL warning
because the workspace cache is not writable; it did not affect test collection or
execution.

## Review

The materializer copies only repository-owned trusted snapshots, sets fixture-local
Git identity, and returns resolved commit IDs. Its CLI exposes no evaluator label.
The fixture source is never executed by these tests, and the materialized target is
left clean for later read-only analysis.
