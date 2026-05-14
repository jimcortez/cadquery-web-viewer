"""Frontend static path resolution (used by the Flask app)."""

import os
from pathlib import Path

from cadquery_web_viewer.mylogger import logger

_PKG_DIR = Path(__file__).resolve().parent
_DEFAULT_FRONTEND = _PKG_DIR / "frontend"
_env_override = os.getenv("FRONTEND_BASE_PATH")
if _env_override:
    _candidate = Path(_env_override)
else:
    _candidate = _DEFAULT_FRONTEND

if _candidate.exists():
    FRONTEND_BASE_PATH: str | None = str(_candidate.resolve())
elif (_PKG_DIR.parent / "dist").exists():
    FRONTEND_BASE_PATH = str((_PKG_DIR.parent / "dist").resolve())
else:
    logger.warning("Frontend not found at %s", _candidate)
    FRONTEND_BASE_PATH = None

UPDATES_API_PATH = "/api/updates"
OBJECTS_API_PATH = "/api/object"
