"""CLI entry point for the Flask-backed viewer server."""

import argparse
import os

from glb_preview_server.app import create_app
from glb_preview_server.mylogger import logger


def main() -> None:
    parser = argparse.ArgumentParser(description="glb-preview-server — Flask GLB/CAD viewer")
    parser.add_argument(
        "--host",
        default=os.environ.get("GLB_PREVIEW_HOST", "localhost"),
        help="Bind address (default: localhost or GLB_PREVIEW_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("GLB_PREVIEW_PORT", "32323")),
        help="TCP port (default: 32323 or GLB_PREVIEW_PORT)",
    )
    parser.add_argument(
        "--cache-mode",
        choices=("memory", "disk"),
        default=os.environ.get("GLB_PREVIEW_CACHE_MODE", "memory"),
        help="Store uploaded GLBs in RAM only, or on disk for persistence across restarts",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.environ.get("GLB_PREVIEW_CACHE_DIR"),
        help="Directory for disk cache (default when disk: ~/.cache/glb-preview-server/glb or GLB_PREVIEW_CACHE_DIR)",
    )
    args = parser.parse_args()
    app = create_app(cache_mode=args.cache_mode, cache_dir=args.cache_dir)
    logger.info("Starting Flask on http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
