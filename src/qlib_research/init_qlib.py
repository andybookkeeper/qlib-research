from __future__ import annotations

import os
from pathlib import Path

import qlib
from qlib.constant import REG_CN, REG_US

_REGION_MAP = {
    "cn": REG_CN,
    "us": REG_US,
}


def get_default_provider_uri() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "qlib" / "cn_data"


def resolve_provider_uri(provider_uri: str | os.PathLike[str] | None = None) -> str:
    env_provider_uri = os.getenv("QLIB_PROVIDER_URI")
    selected_provider_uri = provider_uri or env_provider_uri or get_default_provider_uri()
    return str(Path(selected_provider_uri).expanduser().resolve())


def init_qlib(
    provider_uri: str | os.PathLike[str] | None = None,
    region: str = "cn",
    **kwargs,
) -> None:
    region_key = region.lower()
    if region_key not in _REGION_MAP:
        supported_regions = ", ".join(sorted(_REGION_MAP))
        raise ValueError(f"Unsupported region '{region}'. Expected one of: {supported_regions}.")

    qlib.init(provider_uri=resolve_provider_uri(provider_uri), region=_REGION_MAP[region_key], **kwargs)
