"""Embedded Werkzeug server for ``show(..., server_type=\"in-process\")``."""

from __future__ import annotations

import threading
import webbrowser
from typing import TYPE_CHECKING, Any, Optional

from werkzeug.serving import make_server

from cadquery_web_viewer.app import create_app
from cadquery_web_viewer.mylogger import logger

if TYPE_CHECKING:
    from cadquery_web_viewer.engine import CadQueryWebViewer

_state_lock = threading.Lock()
_wsgi_server: Any = None
_server_thread: Optional[threading.Thread] = None
_bound_engine: Optional[CadQueryWebViewer] = None
_listen_host: str = "127.0.0.1"
_listen_port: int = 32323

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 32323


def _merge_server_options(server_options: Optional[dict]) -> dict[str, Any]:
    o: dict[str, Any] = dict(server_options or {})
    o.setdefault("host", DEFAULT_HOST)
    o.setdefault("port", int(o.get("port", DEFAULT_PORT)))
    o.setdefault("open_browser", True)
    o.setdefault("wait_for_client_timeout", 120.0)
    o.setdefault("wait_for_first_client", True)
    return o


def _public_url(host: str, port: int) -> str:
    display = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{display}:{port}/"


def is_embedded_running() -> bool:
    with _state_lock:
        return _server_thread is not None and _server_thread.is_alive()


def shutdown_embedded() -> None:
    """Stop the embedded server thread if it is running."""
    global _wsgi_server, _server_thread, _bound_engine
    with _state_lock:
        srv = _wsgi_server
        th = _server_thread
        _wsgi_server = None
        _server_thread = None
        _bound_engine = None
    if srv is not None:
        try:
            srv.shutdown()
        except Exception as e:  # noqa: BLE001
            logger.debug("Embedded server shutdown: %s", e)
    if th is not None:
        th.join(timeout=15.0)


def ensure_embedded_running(
    engine: CadQueryWebViewer,
    server_options: Optional[dict] = None,
    *,
    daemon_thread: bool = False,
) -> str:
    """
    Start the Flask app on a background thread bound to ``engine`` if needed.

    :return: Base URL (e.g. ``http://127.0.0.1:32323/``) for opening the viewer.
    """
    global _wsgi_server, _server_thread, _bound_engine, _listen_host, _listen_port

    opts = _merge_server_options(server_options)
    host = str(opts["host"])
    port = int(opts["port"])

    with _state_lock:
        if _server_thread is not None and _server_thread.is_alive():
            if _bound_engine is not engine:
                raise RuntimeError("An embedded server is already running for a different engine instance")
            return _public_url(_listen_host, _listen_port)

    ready = threading.Event()
    errors: list[BaseException] = []

    def _run() -> None:
        global _wsgi_server
        try:
            app = create_app(engine=engine, cache_mode="memory", cache_dir=None)
            srv = make_server(host, port, app, threaded=True)
            with _state_lock:
                _wsgi_server = srv
            ready.set()
            srv.serve_forever()
        except BaseException as e:  # noqa: BLE001
            errors.append(e)
            ready.set()

    engine.at_least_one_client.clear()

    th = threading.Thread(target=_run, name="cadquery-web-viewer-embedded", daemon=daemon_thread)

    with _state_lock:
        _bound_engine = engine
        _listen_host = host
        _listen_port = port
        _server_thread = th

    th.start()

    ready.wait(timeout=30.0)
    if errors:
        shutdown_embedded()
        raise errors[0]
    if not is_embedded_running():
        raise RuntimeError("Embedded server thread exited before becoming ready")

    url = _public_url(host, port)

    cold_start = opts.get("wait_for_first_client", True)
    if cold_start:
        if opts.get("open_browser", True):
            try:
                webbrowser.open(url)
            except Exception as e:  # noqa: BLE001
                logger.warning("Could not open browser: %s", e)
        timeout = float(opts["wait_for_client_timeout"])
        if not engine.at_least_one_client.wait(timeout=timeout):
            shutdown_embedded()
            raise TimeoutError(
                f"No viewer connected within {timeout}s; open {url} manually or increase "
                "server_options['wait_for_client_timeout']."
            )
    elif opts.get("open_browser", True):
        try:
            webbrowser.open(url)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not open browser: %s", e)

    return url
