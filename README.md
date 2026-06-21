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
