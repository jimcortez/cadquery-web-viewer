"""CLI entry point for the Flask-backed viewer server."""

import argparse
import logging

from cadquery_web_viewer.app import create_app

logger = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 32323
DEFAULT_CACHE_DIR = None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(description="cadquery-web-viewer — Flask GLB/CAD viewer")
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--cache-mode",
        choices=("memory", "disk"),
        default="memory",
        help="Store uploaded GLBs in RAM only, or on disk for persistence across restarts",
    )
    parser.add_argument(
        "--cache-dir",
        default=DEFAULT_CACHE_DIR,
        help="Directory for disk cache (default when --cache-mode disk: ~/.cache/cadquery-web-viewer/glb)",
    )
    args = parser.parse_args()
    app = create_app(cache_mode=args.cache_mode, cache_dir=args.cache_dir)
    logger.info(
        "cadquery-web-viewer is intended for trusted/local networks; see SECURITY.md"
    )
    logger.info("Starting Flask on http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
