"""Flask application: static UI, SSE updates, GLB upload API, and optional disk cache."""

from __future__ import annotations

import json
import os
from typing import Optional
from urllib.parse import unquote

from flask import Blueprint, Flask, Response, abort, request, send_from_directory, stream_with_context

from cadquery_web_viewer.glb_cache import GlbDiskCache
from cadquery_web_viewer.myhttp import FRONTEND_BASE_PATH
from cadquery_web_viewer.mylogger import logger
from cadquery_web_viewer.engine import CadQueryWebViewer


def _cors(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, HEAD, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def create_app(
    cache_mode: str = "memory",
    cache_dir: Optional[str] = None,
) -> Flask:
    """
    :param cache_mode: ``memory`` or ``disk``.
    :param cache_dir: Required when ``cache_mode`` is ``disk`` (or set via ``CADQUERY_WEB_VIEWER_CACHE_DIR``).
    """
    cache_mode = (cache_mode or os.environ.get("CADQUERY_WEB_VIEWER_CACHE_MODE", "memory")).lower()
    if cache_mode not in ("memory", "disk"):
        raise ValueError("cache_mode must be 'memory' or 'disk'")
    if cache_mode == "disk":
        cache_dir = cache_dir or os.environ.get("CADQUERY_WEB_VIEWER_CACHE_DIR")
        if not cache_dir:
            cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "cadquery-web-viewer", "glb")
        os.makedirs(cache_dir, exist_ok=True)
        disk_cache = GlbDiskCache(cache_dir)
        logger.info("GLB disk cache enabled at %s", cache_dir)
    else:
        disk_cache = None

    engine = CadQueryWebViewer()

    if disk_cache is not None:
        for entry in disk_cache.list_entries():
            try:
                with open(entry.glb_path, "rb") as f:
                    glb = f.read()
                with engine.build_events_lock:
                    engine.ingest_prebuilt_glb(
                        entry.name,
                        entry.content_hash,
                        glb,
                        entry.kwargs,
                        auto_clear=False,
                    )
            except OSError as e:
                logger.warning("Skipping cache entry %s: %s", entry.glb_path, e)

    app = Flask(__name__)

    bp = Blueprint("api", __name__, url_prefix="/api")

    def _sse_gen():
        yield "retry: 100\n\n"
        with engine.frontend_lock.r_locked():
            if engine.shutting_down.is_set() and engine.at_least_one_client.is_set():
                return
            engine.at_least_one_client.set()
            logger.debug("Updates client connected")
            subscription = engine.show_events.subscribe(yield_timeout=1.0)
            try:
                for data in subscription:
                    if data is None:
                        yield ":keep-alive\n\n"
                    else:
                        logger.debug("Sending info about %s", data.name)
                        yield f"data: {data.to_json()}\n\n"
            except (BrokenPipeError, ConnectionResetError, GeneratorExit):
                pass
            finally:
                subscription.close()
            logger.debug("Updates client disconnected")

    @bp.route("/updates", methods=["GET", "HEAD", "OPTIONS"])
    def api_updates():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        if request.method == "HEAD":
            return _cors(Response("", mimetype="text/event-stream"))
        return _cors(
            Response(
                stream_with_context(_sse_gen()),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
        )

    @bp.route("/object/<path:name>", methods=["GET", "HEAD", "OPTIONS"])
    def api_object(name: str):
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        name = unquote(name)
        exported = engine.export(name)
        if exported is None:
            abort(404)
        glb, etag = exported
        if request.method == "HEAD":
            r = Response("", mimetype="model/gltf-binary")
            r.headers["Content-Length"] = str(len(glb))
            r.headers["E-Tag"] = f'"{etag}"'
            r.headers["Content-Disposition"] = f'attachment; filename="{name}.glb"'
            return _cors(r)
        r = Response(glb, mimetype="model/gltf-binary")
        r.headers["Content-Disposition"] = f'attachment; filename="{name}.glb"'
        r.headers["E-Tag"] = f'"{etag}"'
        return _cors(r)

    @bp.route("/show", methods=["POST", "OPTIONS"])
    def api_show():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        glb_f = request.files.get("glb")
        meta_raw = request.form.get("metadata")
        if not glb_f or not meta_raw:
            abort(400, "Expected multipart fields 'glb' and 'metadata'")
        try:
            meta = json.loads(meta_raw)
        except json.JSONDecodeError:
            abort(400, "Invalid metadata JSON")
        name = meta.get("name")
        content_hash = meta.get("hash")
        if not name or content_hash is None:
            abort(400, "metadata must include 'name' and 'hash'")
        auto_clear = bool(meta.get("auto_clear", False))
        except_names = meta.get("except_names")
        if except_names is not None and not isinstance(except_names, list):
            abort(400, "except_names must be a list of strings")
        kwargs = meta.get("kwargs") if isinstance(meta.get("kwargs"), dict) else {}
        data = glb_f.read()
        with engine.build_events_lock:
            engine.ingest_prebuilt_glb(
                name,
                str(content_hash),
                data,
                kwargs,
                auto_clear=auto_clear,
                except_names=except_names,
            )
            if disk_cache is not None:
                disk_cache.write(name, str(content_hash), data, kwargs)
        return _cors(Response(json.dumps({"ok": True}), mimetype="application/json"))

    @bp.route("/remove", methods=["POST", "OPTIONS"])
    def api_remove():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        body = request.get_json(silent=True) or {}
        name = body.get("name")
        if not name or not isinstance(name, str):
            abort(400, "JSON body must include string 'name'")
        with engine.build_events_lock:
            engine.remove(name)
            if disk_cache is not None:
                disk_cache.delete(name)
        return _cors(Response(json.dumps({"ok": True}), mimetype="application/json"))

    @bp.route("/clear", methods=["POST", "OPTIONS"])
    def api_clear():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        with engine.build_events_lock:
            engine.clear()
            if disk_cache is not None:
                disk_cache.clear()
        return _cors(Response(json.dumps({"ok": True}), mimetype="application/json"))

    app.register_blueprint(bp)

    fe = FRONTEND_BASE_PATH

    def _safe_join(root: str, rel: str) -> Optional[str]:
        full = os.path.realpath(os.path.join(root, rel))
        root_r = os.path.realpath(root)
        if not full.startswith(root_r + os.sep) and full != root_r:
            return None
        return full

    @app.get("/")
    def index():
        if not fe:
            abort(503, "Frontend bundle not found")
        return send_from_directory(fe, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename: str):
        if not fe:
            abort(503)
        if filename.startswith("api/"):
            abort(404)
        full = _safe_join(fe, filename)
        if full and os.path.isfile(full):
            return send_from_directory(fe, filename)
        idx = os.path.join(fe, "index.html")
        if os.path.isfile(idx):
            return send_from_directory(fe, "index.html")
        abort(404)

    @app.after_request
    def add_cors(resp):  # noqa: ANN001
        if "Access-Control-Allow-Origin" not in resp.headers:
            resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    return app
