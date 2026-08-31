# M0/M1 goal contract

Status reflects executed evidence, not intent. M0/M1 is complete for the locally actionable scope.

| ID | Status | Evidence |
|---|---|---|
| GC-01 | PASS | Backend 187-test regression and frontend install/lint/typecheck/test/build executed; desktop Playwright dependency recovered with project-local cache. |
| GC-02 | PASS | Task 12 trust tests and read-only fixture checks passed. |
| GC-03 | PASS | Task 6 fixture intake, diff, and symbol tests passed. |
| GC-04 | PASS | Task 7 positive and cache-only negative controls passed. |
| GC-05 | PASS | Task 7 bounded provenance context tests passed. |
| GC-06 | PASS | Task 8 focused provider/redaction tests passed. |
| GC-07 | PASS | Task 9 evidence validation and finding tests passed. |
| GC-08 | PASS | Task 11 API proof and live HTTP evidence passed. |
| GC-09 | PASS | Desktop Playwright 1 passed; four states exercised. Mobile not run. |
| GC-10 | PASS | Real run persisted trajectory and Markdown report artifacts. |
| GC-11 | PASS | Offline provider works without credentials. |
| GC-12 | PASS | Target unchanged and execution sentinel absent in Task 12 tests. |
| GC-13 | PASS | Backend 187 passed; frontend gates and desktop browser flow passed. |
| GC-14 | PASS | Diff/status review, forbidden-copy checks, and secret/placeholder review completed; known ACL temp residue remains untracked. |

M1 overall verdict remains REVIEW REQUIRED for static-only high-risk evidence. Runtime RED is M2 and is not implemented.
