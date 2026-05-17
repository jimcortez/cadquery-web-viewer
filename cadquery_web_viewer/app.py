"""Flask application: static UI, SSE events, and versioned object API."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import unquote

from flask import Blueprint, Flask, Response, abort, request, send_from_directory, stream_with_context

from cadquery_web_viewer.engine import CadQueryWebViewer, ScenePublishError
from cadquery_web_viewer.events_api import (
    OBJECT_REMOVED,
    OBJECT_VERSIONED,
    event_to_json,
    validate_event,
)
from cadquery_web_viewer.glb_cache import GlbDiskCache
from cadquery_web_viewer.object_store import validate_settings_map
from cadquery_web_viewer.url_import import (
    UrlImportError,
    content_hash_from_bytes,
    fetch_glb_bytes,
)

logger = logging.getLogger(__name__)


def _resolve_frontend_base_path() -> str | None:
    pkg_dir = Path(__file__).resolve().parent
    default_frontend = pkg_dir / "frontend"
    env_override = os.getenv("FRONTEND_BASE_PATH")
    candidate = Path(env_override) if env_override else default_frontend
    if candidate.exists():
        return str(candidate.resolve())
    dist = pkg_dir.parent / "dist"
    if dist.exists():
        return str(dist.resolve())
    logger.warning("Frontend not found at %s", candidate)
    return None


FRONTEND_BASE_PATH = _resolve_frontend_base_path()


def _cors(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, HEAD, PUT, PATCH, POST, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Accept"
    return resp


def _wants_json() -> bool:
    accept = request.headers.get("Accept", "")
    return "application/json" in accept and "model/gltf-binary" not in accept.split(",")[0]


def _parse_force_version() -> int | None:
    raw = request.args.get("force-version")
    if raw is None:
        return None
    try:
        v = int(raw)
    except ValueError:
        abort(400, "force-version must be an integer")
    if v < 1:
        abort(400, "force-version must be >= 1")
    return v


def _parse_version() -> int | None:
    raw = request.args.get("version")
    if raw is None:
        return None
    try:
        v = int(raw)
    except ValueError:
        abort(400, "version must be an integer")
    if v < 1:
        abort(400, "version must be >= 1")
    return v


def _disk_sync_put(
    disk_cache: GlbDiskCache | None,
    name: str,
    version: int,
    content_hash: str,
    glb: bytes,
    kwargs: dict,
    created_at: str,
    notes: str | None,
    settings: dict,
) -> None:
    if disk_cache is None:
        return
    disk_cache.write_version(name, version, content_hash, glb, kwargs, created_at=created_at)
    disk_cache.write_object_manifest(name, notes=notes, settings=settings)


def _hydrate_from_disk(engine: CadQueryWebViewer, disk_cache: GlbDiskCache) -> None:
    manifests: dict[str, tuple[str | None, dict]] = {}
    for meta_path in disk_cache.cache_dir.iterdir():
        if not meta_path.name.endswith(".object.json"):
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            manifests[meta["name"]] = (meta.get("notes"), meta.get("settings") or {})
        except (OSError, json.JSONDecodeError, KeyError):
            continue

    by_name: dict[str, list] = {}
    for entry in disk_cache.list_version_entries():
        by_name.setdefault(entry.name, []).append(entry)

    with engine.build_events_lock:
        for name, entries in by_name.items():
            notes, settings = manifests.get(name, (None, {}))
            engine.object_store.ensure_object(name)
            engine.object_store.set_metadata(name, notes=notes, settings_merge=settings)
            for e in entries:
                glb = Path(e.glb_path).read_bytes()
                engine.object_store.put_version(
                    name,
                    e.version,
                    e.content_hash,
                    glb,
                    e.kwargs,
                    created_at=e.created_at,
                )
            # Restored objects are listed via GET /api/object; do not publish SSE here
            # (would flood new browser tabs with object.created and load every cached GLB).


def _publish_removed_if_needed(engine: CadQueryWebViewer, name: str) -> None:
    if not engine.scene_has_name(name):
        return
    sv = engine.object_store.get_version(name)
    h = sv.hash if sv else ""
    engine.publish_event({"type": OBJECT_REMOVED, "name": name, "hash": h})


def create_app(
    cache_mode: str = "memory",
    cache_dir: str | None = None,
    engine: CadQueryWebViewer | None = None,
) -> Flask:
    cache_mode = (cache_mode or "memory").lower()
    if cache_mode not in ("memory", "disk"):
        raise ValueError("cache_mode must be 'memory' or 'disk'")
    disk_cache: GlbDiskCache | None = None
    if cache_mode == "disk":
        if not cache_dir:
            cache_dir = str(Path("~/.cache/cadquery-web-viewer/glb").expanduser())
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        disk_cache = GlbDiskCache(cache_dir)
        logger.info("GLB disk cache enabled at %s", cache_dir)

    engine = engine or CadQueryWebViewer()

    if disk_cache is not None:
        try:
            _hydrate_from_disk(engine, disk_cache)
        except OSError as e:
            logger.warning("Disk cache hydrate failed: %s", e)

    app = Flask(__name__)
    bp = Blueprint("api", __name__, url_prefix="/api")

    def _sse_gen():
        engine.register_sse_stream_begin()
        try:
            yield "retry: 100\n\n"
            with engine.frontend_lock.r_locked():
                if engine.shutting_down.is_set() and engine.at_least_one_client.is_set():
                    return
                # Live events only — do not replay the buffered history (hydrate / past publishes).
                subscription = engine.scene_events.subscribe(
                    include_buffered=False,
                    yield_timeout=1.0,
                )
                try:
                    for data in subscription:
                        if data is None:
                            yield ":keep-alive\n\n"
                        else:
                            yield f"data: {event_to_json(data)}\n\n"
                except (BrokenPipeError, ConnectionResetError, GeneratorExit):
                    pass
                finally:
                    subscription.close()
        finally:
            engine.register_sse_stream_end()

    @bp.route("/events", methods=["GET", "HEAD", "OPTIONS"])
    def api_events():
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

    @bp.route("/events", methods=["POST"])
    def api_events_post():
        body = request.get_json(silent=True)
        if body is None:
            abort(400, "Expected JSON body")
        events = body.get("events") if isinstance(body.get("events"), list) else [body]
        try:
            with engine.build_events_lock:
                for ev in events:
                    if not isinstance(ev, dict):
                        abort(400, "each event must be an object")
                    engine.publish_event_checked(ev)
        except ScenePublishError as e:
            abort(e.status_code, str(e))
        except ValueError as e:
            abort(400, str(e))
        return _cors(Response(status=204))

    @bp.route("/object", methods=["GET", "OPTIONS"])
    def api_object_list():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        memory_names = set(engine.object_store.list_names())
        disk_names: set[str] = set()
        if disk_cache is not None:
            disk_names = {e.name for e in disk_cache.list_version_entries()}
        payload = {"objects": engine.list_object_descriptors(memory_names=memory_names, disk_names=disk_names)}
        body = json.dumps(payload, separators=(",", ":"))
        return _cors(Response(body, mimetype="application/json"))

    @bp.route("/object", methods=["DELETE", "OPTIONS"])
    def api_object_delete_all():
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        with engine.build_events_lock:
            for name in list(engine._scene_active):
                _publish_removed_if_needed(engine, name)
            engine.delete_all_objects()
            if disk_cache is not None:
                disk_cache.clear()
        return _cors(Response(status=204))

    @bp.route("/object/<path:name>", methods=["GET", "HEAD", "OPTIONS"])
    def api_object_get(name: str):
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        name = unquote(name)
        version = _parse_version()
        if _wants_json():
            on_disk = False
            if disk_cache is not None:
                on_disk = name in {e.name for e in disk_cache.list_version_entries()}
            desc = engine.describe_object(
                name,
                in_memory=engine.object_store.has_name(name),
                on_disk=on_disk,
            )
            if desc is None:
                abort(404)
            body = json.dumps(desc, separators=(",", ":"))
            if request.method == "HEAD":
                r = Response("", mimetype="application/json")
                r.headers["Content-Length"] = str(len(body.encode("utf-8")))
                return _cors(r)
            return _cors(Response(body, mimetype="application/json"))
        exported = engine.export(name, version)
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

    def _store_glb_version(
        name: str,
        content_hash: str,
        data: bytes,
        kwargs: dict,
    ) -> tuple[int, str]:
        force_version = _parse_force_version()
        with engine.build_events_lock:
            version, created_at = engine.put_object_version(
                name,
                str(content_hash),
                data,
                kwargs,
                force_version=force_version,
            )
            rec = engine.object_store.get_record(name)
            notes = rec.notes if rec else None
            settings = dict(rec.settings) if rec else {}
            _disk_sync_put(
                disk_cache, name, version, str(content_hash), data, kwargs, created_at, notes, settings
            )
        return version, str(content_hash)

    @bp.route("/object/<path:name>", methods=["PUT", "OPTIONS"])
    def api_object_put(name: str):
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        name = unquote(name)
        glb_f = request.files.get("glb")
        meta_raw = request.form.get("metadata")
        json_body = request.get_json(silent=True) if request.is_json else None

        if json_body is not None:
            if glb_f or meta_raw:
                abort(400, "Use either JSON body or multipart upload, not both")
            if not isinstance(json_body, dict):
                abort(400, "Expected JSON object body")
            source_url = json_body.get("url")
            if not isinstance(source_url, str) or not source_url.strip():
                abort(400, "JSON body must include non-empty 'url'")
            source_url = source_url.strip()
            try:
                data = fetch_glb_bytes(source_url)
            except UrlImportError as e:
                msg = str(e)
                if "maximum size" in msg.lower():
                    abort(413, msg)
                abort(502, msg)
            content_hash = json_body.get("hash")
            if content_hash is None:
                content_hash = content_hash_from_bytes(data)
            else:
                content_hash = str(content_hash)
            kwargs = json_body.get("kwargs") if isinstance(json_body.get("kwargs"), dict) else {}
            kwargs = dict(kwargs)
            kwargs.setdefault("source_url", source_url)
        elif glb_f and meta_raw:
            try:
                meta = json.loads(meta_raw)
            except json.JSONDecodeError:
                abort(400, "Invalid metadata JSON")
            content_hash = meta.get("hash")
            if content_hash is None:
                abort(400, "metadata must include 'hash'")
            kwargs = meta.get("kwargs") if isinstance(meta.get("kwargs"), dict) else {}
            data = glb_f.read()
            content_hash = str(content_hash)
        else:
            abort(
                400,
                "Expected multipart fields 'glb' and 'metadata', or JSON body with 'url'",
            )

        version, content_hash = _store_glb_version(name, content_hash, data, kwargs)
        resp_body = json.dumps(
            {"name": name, "version": version, "hash": content_hash},
            separators=(",", ":"),
        )
        r = Response(resp_body, status=201, mimetype="application/json")
        r.headers["X-Object-Version"] = str(version)
        return _cors(r)

    @bp.route("/object/<path:name>", methods=["PATCH", "OPTIONS"])
    def api_object_patch(name: str):
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        name = unquote(name)
        body = request.get_json(silent=True)
        if not body or not isinstance(body, dict):
            abort(400, "Expected JSON object body")
        new_name = body.get("name")
        if new_name is not None and (not isinstance(new_name, str) or not new_name):
            abort(400, "name must be a non-empty string")
        has_notes = "notes" in body
        has_settings = "settings" in body
        if new_name is None and not has_notes and not has_settings:
            abort(400, "at least one of name, notes, settings required")
        settings_merge = None
        if has_settings:
            if not isinstance(body["settings"], dict):
                abort(400, "settings must be an object")
            try:
                settings_merge = validate_settings_map(body["settings"])
            except ValueError as e:
                abort(400, str(e))
        from cadquery_web_viewer.object_store import _UNSET

        notes_arg: str | None | object = body["notes"] if has_notes else _UNSET
        try:
            with engine.build_events_lock:
                desc = engine.patch_object(
                    name,
                    new_name=new_name,
                    notes=notes_arg,
                    settings_merge=settings_merge,
                )
                final_name = desc["name"]
                if disk_cache is not None and new_name and new_name != name:
                    disk_cache.rename_object(name, new_name)
                elif disk_cache is not None:
                    rec = engine.object_store.get_record(final_name)
                    if rec:
                        disk_cache.write_object_manifest(
                            final_name, notes=rec.notes, settings=dict(rec.settings)
                        )
        except KeyError:
            abort(404)
        except ValueError as e:
            abort(409, str(e))
        body_out = json.dumps(desc, separators=(",", ":"))
        return _cors(Response(body_out, mimetype="application/json"))

    @bp.route("/object/<path:name>", methods=["DELETE", "OPTIONS"])
    def api_object_delete(name: str):
        if request.method == "OPTIONS":
            return _cors(Response(status=204))
        name = unquote(name)
        force_version = _parse_force_version()
        with engine.build_events_lock:
            if not engine.object_store.has_name(name):
                abort(404)
            if force_version is None:
                _publish_removed_if_needed(engine, name)
                engine.delete_object(name)
                if disk_cache is not None:
                    disk_cache.delete_object(name)
            else:
                if engine.object_store.get_version(name, force_version) is None:
                    abort(404)
                engine.delete_object(name, force_version=force_version)
                if disk_cache is not None:
                    disk_cache.delete_version(name, force_version)
                if not engine.object_store.has_name(name):
                    _publish_removed_if_needed(engine, name)
        return _cors(Response(status=204))

    app.register_blueprint(bp)

    fe = FRONTEND_BASE_PATH

    def _safe_join(root: str, rel: str) -> Path | None:
        root_p = Path(root).resolve()
        try:
            full = (root_p / rel).resolve()
        except OSError:
            return None
        try:
            if not full.is_relative_to(root_p):
                return None
        except ValueError:
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
        if full is not None and full.is_file():
            return send_from_directory(fe, filename)
        idx = Path(fe) / "index.html"
        if idx.is_file():
            return send_from_directory(fe, "index.html")
        abort(404)

    @app.after_request
    def add_cors(resp):  # noqa: ANN001
        if "Access-Control-Allow-Origin" not in resp.headers:
            resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    return app
