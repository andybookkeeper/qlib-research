"""Run optional config-driven model training workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.qlib_research.app.services.training_runtime_service import TrainingRuntimeService


def _load_config(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "YAML support requires PyYAML. Install with `python -m pip install pyyaml` "
                "or use a JSON config file."
            )
        data = yaml.safe_load(content)
    else:
        data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Workflow config must be a JSON/YAML object.")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run config-driven workflow training.")
    parser.add_argument("config_path", help="Path to workflow config YAML/JSON file.")
    args = parser.parse_args()

    config_path = Path(args.config_path)
    workflow_config = _load_config(config_path)
    runtime = TrainingRuntimeService()
    result = runtime.run_config_workflow(workflow_config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
