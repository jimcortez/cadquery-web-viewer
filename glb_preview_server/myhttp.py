"""Frontend static path resolution (used by the Flask app)."""

import os

from glb_preview_server.mylogger import logger

FILE_DIR = os.path.dirname(__file__)
FRONTEND_BASE_PATH = os.getenv("FRONTEND_BASE_PATH", os.path.join(FILE_DIR, "frontend"))
if not os.path.exists(FRONTEND_BASE_PATH):
    if os.path.exists(os.path.join(FILE_DIR, "..", "dist")):
        FRONTEND_BASE_PATH = os.path.join(FILE_DIR, "..", "dist")
    else:
        logger.warning("Frontend not found at %s", FRONTEND_BASE_PATH)
        FRONTEND_BASE_PATH = None

UPDATES_API_PATH = "/api/updates"
OBJECTS_API_PATH = "/api/object"
