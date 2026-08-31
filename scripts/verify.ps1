$ErrorActionPreference = "Stop"
& .\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp .final-backend -p no:cacheprovider
& .\.venv\Scripts\python.exe -m ruff check backend
& .\.venv\Scripts\python.exe -m mypy backend/app
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run test -- --run
npm --prefix frontend run build
Set-Location frontend
.\node_modules\.bin\playwright.cmd test --project=desktop
Set-Location ..
git diff --check
