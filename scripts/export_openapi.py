"""Export FastAPI OpenAPI schema to a JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.qlib_research.app.api.main import app


def export_openapi(output_path: Path) -> Path:
    """Generate and persist OpenAPI schema from the running app object."""
    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema for release contract freeze.")
    parser.add_argument(
        "--output",
        default="docs/api/openapi.json",
        help="Output path for OpenAPI JSON (default: docs/api/openapi.json).",
    )
    args = parser.parse_args()
    output = export_openapi(Path(args.output))
    print(f"[OPENAPI] Exported schema to {output}")


if __name__ == "__main__":
    main()
