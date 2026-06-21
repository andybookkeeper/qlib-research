# my-qlib-research

This repository uses **Microsoft Qlib as the engine** and keeps project-specific code, configs, and notebooks in this repo.

## Layout

```text
.
├─ configs/
│  └─ workflow/
├─ data/
│  └─ qlib/
│     └─ cn_data/
├─ notebooks/
├─ src/
│  └─ qlib_research/
│     ├─ __init__.py
│     └─ init_qlib.py
└─ requirements.txt
```

## Setup

```powershell
cd "D:\00-AI Project\my-qlib-research"
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
# Optional: install native Qlib package when supported by your Python/runtime
pip install -r requirements-qlib.txt
```

## Data location

By default, the local Qlib provider path is:

```text
data\qlib\cn_data
```

If your dataset is too large for the repository, keep it outside the repo and set:

```powershell
$env:QLIB_PROVIDER_URI = "D:\market-data\qlib\cn_data"
```

## Initializing Qlib

```python
from qlib_research import init_qlib

init_qlib()
```

You can also override the path or region directly:

```python
from qlib_research import init_qlib

init_qlib(provider_uri=r"D:\market-data\qlib\cn_data", region="cn")
```

## API contract export (Phase 2 hardening)

Freeze the API contract for release with:

```powershell
python scripts\export_openapi.py --output docs\api\openapi.json
```

Optional config-driven workflow execution:

```powershell
python scripts\run_workflow_config.py configs\workflow\example_workflow.json
```

## Production runtime checks

When `FASTAPI_ENV=production`, startup now enforces:

1. `SECRET_KEY` must be set to a non-default value.
2. `DATABASE_URL` must not use SQLite.
3. `CORS_ORIGINS` must be configured.

## Phase 3 kickoff (Step 1)

Phase 3 starts with scope + feature flags using safe defaults (all high-risk paths disabled):

- `PHASE3_ENABLE_LIVE_BROKER_ADAPTER=false`
- `PHASE3_ENABLE_BROKER_RECONCILIATION=false`
- `PHASE3_ENABLE_STRATEGY_AUTOMATION=false`
- `PHASE3_ENFORCE_MANUAL_TRADE_CONFIRMATION=true`

Current Phase 3 status and flags are visible at `GET /api/status`.

Phase 3 live-broker skeleton endpoints (safe/read-only):

- `GET /api/broker/live/status`
- `GET /api/broker/live/account`
- `POST /api/broker/live/sync`
- `GET /api/broker/live/reconciliation` (requires `PHASE3_ENABLE_BROKER_RECONCILIATION=true`)
- `GET /api/broker/live/reconciliation/history` (requires `PHASE3_ENABLE_BROKER_RECONCILIATION=true`)

Strategy automation (feature-flagged, manual confirmation enforced by default):

- `POST /api/broker/automation/proposals`
- `GET /api/broker/automation/proposals`
- `POST /api/broker/automation/proposals/{proposal_id}/execute`

Pre-trade guardrails are configurable via:

- `PHASE3_MAX_TRADE_NOTIONAL`
- `PHASE3_MAX_POSITION_NOTIONAL`
- `PHASE3_MAX_DAILY_LOSS`

## Deploy with public URLs (recommended)

This repo is configured for:

1. **Backend API + PostgreSQL on Render** (`render.yaml`)
2. **Frontend UI on Vercel** (`src/app/frontend/vercel.json`)

### 1. Deploy backend on Render

- Create a new Render Blueprint from this repo.
- Render will create:
  - `qlib-api` (web service)
  - `qlib-db` (PostgreSQL database)
- After deploy, copy backend URL:
  - Example: `https://qlib-api.onrender.com`

### 2. Deploy frontend on Vercel

- Import repo in Vercel
- Set **Root Directory** to: `src/app/frontend`
- Set environment variable:
  - `VITE_API_BASE_URL=https://qlib-api.onrender.com/api`
- Deploy and copy frontend URL:
  - Example: `https://qlib-trading-ui.vercel.app`

### 3. Final backend CORS update

In Render, set:

- `CORS_ORIGINS=https://qlib-trading-ui.vercel.app`

Then redeploy backend.

### 4. Enable automatic deploy from GitHub pushes

This repo now includes GitHub Actions workflows:

- `.github/workflows/deploy-backend-render.yml`
- `.github/workflows/deploy-frontend-vercel.yml`

Set these repository secrets in GitHub:

- `RENDER_DEPLOY_HOOK_URL`
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

After secrets are set, pushes to `master`/`main` auto-deploy backend/frontend.

### Frontend environment variables

- `VITE_API_BASE_URL` (required for deployed frontend)
- `VITE_WS_BASE_URL` (optional websocket override)

Local defaults are in `src/app/frontend/.env.example`.
