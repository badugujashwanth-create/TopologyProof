# Task 2 M0 frontend evidence

Date: 2026-08-30

Scope: React/Vite/TypeScript foundation only. No M1 screens, API client, analysis workflow, or backend work was added.

## Tooling verification

Executed from `frontend/`:

| Command | Result | Observed evidence |
| --- | --- | --- |
| `npm install` | BLOCKED | Windows `EPERM` (`-4048`) opening `frontend/package-lock.json`. |
| `npm run lint` | PASS | ESLint exited 0 with no diagnostics. |
| `npm run typecheck` | BLOCKED | TypeScript could not write `node_modules/.tmp/tsconfig.app.tsbuildinfo` or `tsconfig.node.tsbuildinfo` because of `EPERM`. |
| `npm run test -- --run` | BLOCKED | Vitest could not write its generated config under `node_modules/.vite-temp` because of `EPERM`. |
| `npm run build` | BLOCKED | It stopped at the same TypeScript temporary-file `EPERM` errors as typecheck. |

## Environment diagnosis

`package-lock.json` was present and not read-only. Several Node processes were active while the commands ran. The denied paths are shared generated files in `frontend/node_modules`, so this report records the checks as blocked rather than claiming full M0 tooling verification. The `npm install` failure also prevented fresh install evidence.

## Dependency correction

The plan now records TypeScript 5.9.3, matching `frontend/package.json` and the lockfile. This stable release is peer-compatible with the selected Vite, Vitest, and `typescript-eslint` dependency set; the prior planned 7.0.2 value was not.

## Goal-contract impact

GC-01 remains `PARTIAL`: lint has executed successfully, while install, typecheck, test, build, clean-checkout, and startup evidence require an unlocked workspace or Task 15's full verification pass.
