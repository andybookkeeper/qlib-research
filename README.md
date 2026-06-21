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
