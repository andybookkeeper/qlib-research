try:
    from .init_qlib import get_default_provider_uri, init_qlib, resolve_provider_uri
    __all__ = ["get_default_provider_uri", "init_qlib", "resolve_provider_uri"]
except ImportError:
    # qlib not yet installed, allow imports of other modules
    __all__ = []
