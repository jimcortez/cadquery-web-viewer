from __future__ import annotations

import base64
import inspect
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from io import BytesIO
from pathlib import Path
from typing import Any, Union

# noinspection PyProtectedMember
from build123d import Axis, Location, Vector
from build123d.topology.shape_core import Shape
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
from PIL import Image

from cadquery_web_viewer.cad import CADCoreLike, CADLike, ColorTuple, _hashcode, get_color, get_shape, grab_all_cad
from cadquery_web_viewer.events_api import (
    OBJECT_CREATED,
    OBJECT_REMOVED,
    OBJECT_VERSIONED,
    SCENE_CLEARED,
    SERVER_SHUTDOWN,
    validate_event,
)
from cadquery_web_viewer.gltf import get_version
from cadquery_web_viewer.object_store import (
    VersionedObjectStore,
    describe_object_record,
    validate_settings_map,
)
from cadquery_web_viewer.pubsub import BufferedPubSub
from cadquery_web_viewer.rwlock import RWLock
from cadquery_web_viewer.tessellate import tessellate

logger = logging.getLogger(__name__)


CadQueryWebViewerObject = Union[bytes, CADCoreLike]


class ScenePublishError(Exception):
    """Invalid or conflicting scene event."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class _CadShowPayload:
    """In-process tessellation payload (not sent over SSE)."""

    name: str
    hash: str
    obj: CadQueryWebViewerObject
    kwargs: dict[str, Any] = field(default_factory=dict)


class CadQueryWebViewerProtocol(Enum):
    """Enum of communication protocols supported by the server."""

    HTTP = auto()
    """The protocol used for the embedded / remote HTTP viewer."""


class CadQueryWebViewer:
    """Core preview engine: manages CAD/GLB objects and update streams for the viewer."""

    # Startup
    protocol: CadQueryWebViewerProtocol
    """Always :attr:`CadQueryWebViewerProtocol.HTTP` (reserved for future transport options)."""
    server_thread: Any | None
    """Reserved; embedded HTTP server is no longer started from ``CadQueryWebViewer``."""
    server: Any | None
    startup_complete: threading.Event
    """Event to signal when the server has started"""

    # Running
    object_store: VersionedObjectStore
    scene_events: BufferedPubSub[dict[str, Any]]
    """PubSub for typed scene event envelopes (``/api/events`` SSE)."""
    build_events_lock: threading.Lock
    """Lock for object store and scene state mutations."""

    # Shutdown
    at_least_one_client: threading.Event
    """Event to signal when at least one client has connected"""
    shutting_down: threading.Event
    """Event to signal when the server is shutting down"""
    frontend_lock: RWLock
    """Lock to ensure that the frontend has finished working before we shut down"""

    _sse_stream_count: int
    """Active ``GET /api/events`` SSE streams (see ``register_sse_stream_begin``)."""
    _scene_active: set[str]
    """Object names currently published to the scene."""
    _sse_idle_cv: threading.Condition
    """Notified when ``_sse_stream_count`` drops to zero."""

    texture: tuple[bytes, str] | None
    """Default texture to use for model faces, in (data, mimetype) format.
    If left as None, no texture will be used.
    
    It can be set with the CADQUERY_WEB_VIEWER_TEXTURE=<uri> and overridden by the custom `cadquery_web_viewer_texture` attribute of an object.
    The <uri> can be file:<path> or data:<mime>;base64,<data> where <mime> is the mime type and 
    <data> is the base64 encoded image."""

    color_faces: ColorTuple | None
    """Overrides the default color to use for model faces. Applies even if a texture is used. 
    
    You can use `show(..., color_faces=...)` or the standard way of setting colors for build123d/cadquery objects to 
    override this color.
    
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_FACES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    color_edges: ColorTuple | None
    """Overrides the default color to use for model edges. 
    
    You can use `show(..., color_edges=...) or the standard way of setting colors for build123d/cadquery objects to
    override this color.
        
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_EDGES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    color_vertices: ColorTuple | None
    """Overrides the default color to use for model vertices.
    
    You can use `show(..., color_vertices=...)` or the standard way of setting colors for build123d/cadquery objects to
    override this color.
    
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_VERTICES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    def __init__(self):
        """Initializes the cadquery-web-viewer engine."""
        raw_protocol = os.getenv("CADQUERY_WEB_VIEWER_PROTOCOL", "http").upper()
        self.protocol = (
            CadQueryWebViewerProtocol[raw_protocol]
            if raw_protocol in CadQueryWebViewerProtocol.__members__
            else CadQueryWebViewerProtocol.HTTP
        )
        self.server_thread = None
        self.server = None
        self.startup_complete = threading.Event()
        self.object_store = VersionedObjectStore()
        self.scene_events = BufferedPubSub()
        self.build_events_lock = threading.RLock()
        self._scene_active = set()
        self.at_least_one_client = threading.Event()
        self.shutting_down = threading.Event()
        self.frontend_lock = RWLock()
        self._sse_stream_count = 0
        self._sse_idle_cv = threading.Condition(threading.Lock())
        self.texture = _read_texture_uri(os.getenv("CADQUERY_WEB_VIEWER_TEXTURE"))
        self.color_faces = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_FACES", "#ffbf00"))  # Default yellow
        self.color_edges = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_EDGES", "#1a1aff"))  # Default blue
        self.color_vertices = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_VERTICES", "#1a1a1a"))  # Default dark gray
        logger.info('Using cadquery-web-viewer v%s', get_version())

    def start(self):
        """Legacy hook: the HTTP viewer is served by the ``cadquery-web-viewer`` Flask CLI, not this method."""
        logger.warning(
            "CadQueryWebViewer.start() is a legacy hook; use show(..., server_type='in-process') "
            "or run cadquery-web-viewer and show(..., server_type='remote')."
        )
        self.startup_complete.set()

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Legacy hook; embedded ``ThreadingHTTPServer`` is no longer used."""
        if self.server_thread is None:
            return

    def register_sse_stream_begin(self) -> None:
        """Increment active SSE stream count (``GET /api/events``)."""
        with self._sse_idle_cv:
            self._sse_stream_count += 1
            self.at_least_one_client.set()

    def register_sse_stream_end(self) -> None:
        """Decrement active SSE stream count; wake waiters when it reaches zero."""
        with self._sse_idle_cv:
            self._sse_stream_count -= 1
            if self._sse_stream_count < 0:
                logger.warning("SSE stream count underflow; resetting to 0")
                self._sse_stream_count = 0
            self._sse_idle_cv.notify_all()

    def wait_until_no_sse_streams(self, timeout: float | None = None) -> bool:
        """
        Block until there are no active SSE streams.

        :return: ``True`` if count is zero (possibly after waiting), ``False`` on timeout while streams remained.
        """
        with self._sse_idle_cv:
            deadline = None if timeout is None else (time.time() + timeout)
            while self._sse_stream_count > 0:
                remaining = None if deadline is None else (deadline - time.time())
                if remaining is not None and remaining <= 0:
                    return False
                self._sse_idle_cv.wait(timeout=remaining)
            return True

    def scene_has_name(self, name: str) -> bool:
        with self.build_events_lock:
            return name in self._scene_active

    def publish_event(self, envelope: dict[str, Any]) -> None:
        validate_event(envelope)
        with self.build_events_lock:
            self._apply_scene_event(envelope)
            self._prune_stale_buffered_events(envelope)
            self.scene_events.publish(dict(envelope))

    def _prune_stale_buffered_events(self, envelope: dict[str, Any]) -> None:
        """Remove buffered create/version events superseded by remove or clear."""
        t = envelope["type"]
        create_types = (OBJECT_CREATED, OBJECT_VERSIONED)
        if t == OBJECT_REMOVED:
            name = envelope["name"]

            def stale(ev: dict[str, Any]) -> bool:
                return ev.get("type") in create_types and ev.get("name") == name

            self.scene_events.prune_buffer(stale)
        elif t == SCENE_CLEARED:
            except_names = set(envelope.get("except_names") or [])

            def stale(ev: dict[str, Any]) -> bool:
                return ev.get("type") in create_types and ev.get("name") not in except_names

            self.scene_events.prune_buffer(stale)

    def _apply_scene_event(self, envelope: dict[str, Any]) -> None:
        t = envelope["type"]
        if t == OBJECT_CREATED:
            if envelope["name"] in self._scene_active:
                raise ScenePublishError(
                    f"{envelope['name']!r} is already in the scene; use object.versioned",
                    409,
                )
            self._scene_active.add(envelope["name"])
        elif t == OBJECT_VERSIONED:
            if envelope["name"] not in self._scene_active:
                raise ScenePublishError(
                    f"{envelope['name']!r} is not in the scene; use object.created",
                    409,
                )
        elif t == OBJECT_REMOVED:
            self._scene_active.discard(envelope["name"])
        elif t == SCENE_CLEARED:
            except_names = set(envelope.get("except_names") or [])
            self._scene_active = {n for n in self._scene_active if n in except_names}
        elif t == SERVER_SHUTDOWN:
            pass

    def _verify_object_version(self, name: str, version: int, content_hash: str) -> None:
        sv = self.object_store.get_version(name, version)
        if sv is None:
            raise ScenePublishError(f"object {name!r} version {version} not found", 404)
        if sv.hash != content_hash:
            raise ScenePublishError(
                f"hash mismatch for {name!r} version {version}",
                409,
            )

    def publish_event_checked(self, envelope: dict[str, Any]) -> None:
        validate_event(envelope)
        t = envelope["type"]
        if t in (OBJECT_CREATED, OBJECT_VERSIONED):
            self._verify_object_version(
                envelope["name"],
                envelope["version"],
                envelope["hash"],
            )
        self.publish_event(envelope)

    def put_object_version(
        self,
        name: str,
        content_hash: str,
        glb: bytes,
        kwargs: dict[str, Any] | None = None,
        *,
        force_version: int | None = None,
        created_at: str | None = None,
    ) -> tuple[int, str]:
        kwargs = kwargs or {}
        with self.build_events_lock:
            if force_version is not None:
                version = int(force_version)
            else:
                version = self.object_store.next_version(name)
            self.object_store.ensure_object(name)
            ts = self.object_store.put_version(
                name,
                version,
                content_hash,
                glb,
                kwargs,
                created_at=created_at,
            )
        return version, ts

    def describe_object(
        self,
        name: str,
        *,
        in_memory: bool = True,
        on_disk: bool = False,
    ) -> dict[str, Any] | None:
        rec = self.object_store.get_record(name)
        if rec is None or not rec.versions:
            return None
        return describe_object_record(name, rec, in_memory=in_memory, on_disk=on_disk)

    def list_object_descriptors(
        self,
        *,
        memory_names: set[str],
        disk_names: set[str],
    ) -> list[dict[str, Any]]:
        names = sorted(memory_names | disk_names)
        out: list[dict[str, Any]] = []
        for name in names:
            rec = self.object_store.get_record(name)
            if rec is None or not rec.versions:
                continue
            out.append(
                describe_object_record(
                    name,
                    rec,
                    in_memory=name in memory_names,
                    on_disk=name in disk_names,
                )
            )
        return out

    def patch_object(
        self,
        name: str,
        *,
        new_name: str | None = None,
        notes: str | None | object = None,
        settings_merge: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from cadquery_web_viewer.object_store import _UNSET

        with self.build_events_lock:
            rec = self.object_store.get_record(name)
            if rec is None or not rec.versions:
                raise KeyError(name)
            old_name = name
            if settings_merge is not None:
                self.object_store.set_metadata(
                    name, settings_merge=validate_settings_map(settings_merge)
                )
            if notes is not None and notes is not _UNSET:
                self.object_store.set_metadata(name, notes=notes)
            was_in_scene = old_name in self._scene_active
            displayed: tuple[int, str] | None = None
            if was_in_scene:
                v = max(rec.versions)
                displayed = (v, rec.versions[v].hash)
            if new_name is not None and new_name != old_name:
                self.object_store.rename(old_name, new_name)
                name = new_name
            desc = self.describe_object(name, in_memory=True, on_disk=False)
            if desc is None:
                raise KeyError(name)
        if new_name is not None and new_name != old_name and was_in_scene and displayed:
            ver, h = displayed
            self.publish_event({"type": OBJECT_REMOVED, "name": old_name, "hash": h})
            self.publish_event(
                {
                    "type": OBJECT_CREATED,
                    "name": new_name,
                    "version": ver,
                    "hash": h,
                }
            )
        return desc

    def delete_object(self, name: str, *, force_version: int | None = None) -> bool:
        with self.build_events_lock:
            if force_version is not None:
                ok = self.object_store.delete_version(name, force_version)
            else:
                ok = self.object_store.delete_object(name)
                self._scene_active.discard(name)
            return ok

    def delete_all_objects(self) -> None:
        with self.build_events_lock:
            self.object_store.clear()
            self._scene_active.clear()

    def show(
        self,
        *objs: CadQueryWebViewerObject,
        names: str | list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Shows the given CAD objects in the frontend. The objects will be tessellated and converted to GLTF. Optionally,
        the following keyword arguments can be used:

        - auto_clear: Whether to clear the previous objects before showing the new ones (default: True)
        - texture: The texture to use for the faces of the object (see `CadQueryWebViewer.texture` for more info)
        - color: The default color to use for the objects (can be overridden by the `color` attribute of each object)
        - tolerance: The tolerance for tessellating the object (default: 0.1)
        - angular_tolerance: The angular tolerance for tessellating the object (default: 0.1)
        - faces: Whether to tessellate and show the faces of the object (default: True)
        - edges: Whether to tessellate and show the edges of the object (default: True)
        - vertices: Whether to tessellate and show the vertices of the object (default: True)

        :param objs: The CAD objects to show. Can be CAD-like objects (solids, locations, etc.) or bytes (GLTF) objects.
        :param names: The names of the objects. If None, the variable names will be used (if possible). The number of
            names must match the number of objects. An object of the same name will be replaced in the frontend.
        :param kwargs: Additional options for the show_object event.
        """
        # Prepare the arguments
        start = time.time()
        names = _prepare_show_names(objs, names)
        _normalize_show_color_kwargs(kwargs)

        if kwargs.get("auto_clear", True):
            self.clear(except_names=names)

        for obj, name in zip(objs, names):
            payload = _make_show_payload_for_object(obj, name, kwargs)
            glb = _glb_bytes_from_show_payload(self, payload)
            in_scene = self.scene_has_name(name)
            version, _ = self.put_object_version(name, payload.hash, glb, payload.kwargs)
            if in_scene:
                self.publish_event(
                    {
                        "type": OBJECT_VERSIONED,
                        "name": name,
                        "version": version,
                        "hash": payload.hash,
                    }
                )
            else:
                self.publish_event(
                    {
                        "type": OBJECT_CREATED,
                        "name": name,
                        "version": version,
                        "hash": payload.hash,
                    }
                )

        logger.info("show %s took %.3f seconds", names, time.time() - start)

    def show_cad_all(self, **kwargs):
        """Publishes all CAD objects in the current scope to the server. See `show` for more details."""
        all_cad = list(grab_all_cad())  # List for reproducible iteration order
        self.show(*[cad for _, cad in all_cad], names=[name for name, _ in all_cad], **kwargs)

    def remove(self, name: str) -> None:
        """Remove object from store and scene."""
        sv = self.object_store.get_version(name)
        h = sv.hash if sv else ""
        self.delete_object(name)
        if h:
            self.publish_event({"type": OBJECT_REMOVED, "name": name, "hash": h})

    def clear(self, except_names: list[str] | None = None) -> None:
        """Clear the scene (publish ``scene.cleared``); does not delete stored objects."""
        except_names = list(except_names or [])
        self.publish_event({"type": SCENE_CLEARED, "except_names": except_names})

    def clear_store(self) -> None:
        """Delete all stored objects and clear scene tracking."""
        self.delete_all_objects()

    def shown_object_names(self) -> list[str]:
        with self.build_events_lock:
            return sorted(self._scene_active)

    def export(self, name: str, version: int | None = None) -> tuple[bytes, str] | None:
        """Return GLB bytes and ETag for a stored object version (latest if ``version`` is None)."""
        rec = self.object_store.get_record(name)
        if rec is None or not rec.versions:
            logger.warning("Object %s not found", name)
            return None
        ver = version if version is not None else max(rec.versions)
        sv = rec.versions.get(ver)
        if sv is None:
            return None
        return sv.glb, f"{sv.hash}-v{ver}"

    def export_all(
        self,
        folder: str,
        export_filter: Callable[[str, CADCoreLike | None], bool] = lambda name, obj: True,
    ) -> None:
        """Export all objects in the store to GLB files in the given folder."""
        out_dir = Path(folder)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in self.object_store.list_names():
            if export_filter(name, None):
                exp = self.export(name)
                if exp is not None:
                    (out_dir / f"{name}.glb").write_bytes(exp[0])


def _read_texture_uri(uri: str | None) -> tuple[bytes, str] | None:
    if uri is None:
        return None
    if uri.startswith("file:"):
        path = Path(uri[len("file:") :])
        data = path.read_bytes()
        buf = BytesIO(data)
        img = Image.open(buf)
        mtype = img.get_format_mimetype()
        return data, mtype
    if uri.startswith("data:"):  # https://en.wikipedia.org/wiki/Data_URI_scheme#Syntax (limited)
        mtype_and_data = uri[len("data:"):]
        mtype = mtype_and_data.split(";", 1)[0]
        data_str = mtype_and_data.split(",", 1)[1]
        data = base64.b64decode(data_str)
        return data, mtype
    return None


def _read_color(color: str) -> ColorTuple | None:
    """Reads a color from a string in the format #RRGGBB or #RRGGBBAA"""
    if color is None:
        return None
    if not color.startswith('#') or len(color) not in (7, 9):
        raise ValueError(f'Invalid color format: {color}')
    r = float(int(color[1:3], 16)) / 255.0
    g = float(int(color[3:5], 16)) / 255.0
    b = float(int(color[5:7], 16)) / 255.0
    a = float(int(color[7:9], 16)) / 255.0 if len(color) == 9 else 1.0
    return r, g, b, a


# noinspection PyUnusedLocal
def _preprocess_cad(obj: CADLike, **kwargs) -> CADCoreLike:
    # Get the shape of a CAD-like object
    obj = get_shape(obj)

    # Convert Z-up (OCCT convention) to Y-up (GLTF convention)
    if isinstance(obj, TopoDS_Shape):
        obj = Shape(obj).rotate(Axis.X, -90).wrapped
    elif isinstance(obj, TopLoc_Location):
        tmp_location = Location(obj)
        tmp_location.position = Vector(tmp_location.position.X, tmp_location.position.Z,
                                       -tmp_location.position.Y)
        tmp_location.orientation = Vector(tmp_location.orientation.X - 90, tmp_location.orientation.Y,
                                          tmp_location.orientation.Z)
        obj = tmp_location.wrapped

    return obj


_obj_name_counts = {}


def _find_var_name(obj: Any, avoid_levels: int = 2) -> str:
    """A hacky way to get a stable name for an object that may change over time"""

    # Build123d objects have a "label" property, CadQuery Assembly's have "name"
    for f in ('label', 'name'):
        if hasattr(obj, f):
            v = getattr(obj, f)
            if v != '':
                return v

    # Otherwise walk up our stack to see if there's a local variable that points to it
    obj_shape = get_shape(obj, error=False) or obj
    for frame in inspect.stack()[avoid_levels:]:
        for key, value in frame.frame.f_locals.items():
            if get_shape(value, error=False) is obj_shape:
                return key

    # Last resort, name it for its type with a disambiguating number
    global _obj_name_counts
    t = obj.__class__.__name__
    _obj_name_counts[t] = 1 if t not in _obj_name_counts else _obj_name_counts[t] + 1
    return t + str(_obj_name_counts[t])


def _prepare_show_names(objs: tuple[Any, ...], names: str | list[str] | None) -> list[str]:
    resolved = names or [_find_var_name(obj) for obj in objs]
    if isinstance(resolved, str):
        resolved = [resolved]
    if len(resolved) != len(objs):
        raise ValueError("Number of names must match the number of objects")
    return resolved


def _normalize_show_color_kwargs(kwargs: dict[str, Any]) -> None:
    for color_name in ('color_faces', 'color_edges', 'color_vertices'):
        if color_name in kwargs:
            kwargs[color_name] = get_color(kwargs[color_name]) or _read_color(kwargs[color_name])


def _make_show_payload_for_object(
    obj: CadQueryWebViewerObject, name: str, kwargs: dict[str, Any]
) -> _CadShowPayload:
    obj_color = get_color(obj)
    _kwargs = kwargs.copy()
    if obj_color is not None:
        _kwargs["color_obj"] = obj_color
    _kwargs["texture"] = _read_texture_uri(
        getattr(obj, "cadquery_web_viewer_texture", None) or kwargs.get("texture", None)
    )
    body: CadQueryWebViewerObject = obj
    if not isinstance(body, bytes):
        body = _preprocess_cad(body, **_kwargs)
    content_hash = _hashcode(body, **_kwargs)
    return _CadShowPayload(name=name, hash=content_hash, obj=body, kwargs=_kwargs or {})


def _glb_bytes_from_show_payload(viewer: CadQueryWebViewer, payload: _CadShowPayload) -> bytes:
    if isinstance(payload.obj, bytes):
        return payload.obj
    gltf = tessellate(
        payload.obj,
        color_faces=payload.kwargs.get("color_faces", viewer.color_faces),
        color_edges=payload.kwargs.get("color_edges", viewer.color_edges),
        color_vertices=payload.kwargs.get("color_vertices", viewer.color_vertices),
        color_obj=payload.kwargs.get("color_obj", None),
        tolerance=payload.kwargs.get("tolerance", 0.1),
        angular_tolerance=payload.kwargs.get("angular_tolerance", 0.1),
        faces=payload.kwargs.get("faces", True),
        edges=payload.kwargs.get("edges", True),
        vertices=payload.kwargs.get("vertices", True),
        texture=payload.kwargs.get("texture", viewer.texture),
    )
    return b"".join(gltf.save_to_bytes())


def _show_payloads_from_inputs(
    *objs: Any,
    names: str | list[str] | None,
    kwargs: dict[str, Any],
) -> tuple[list[_CadShowPayload], list[str]]:
    resolved = _prepare_show_names(objs, names)
    _normalize_show_color_kwargs(kwargs)
    payloads = [_make_show_payload_for_object(obj, name, kwargs) for obj, name in zip(objs, resolved)]
    return payloads, resolved


def glb_bytes_list_from_show_inputs(
    *objs: Any,
    names: str | list[str] | None = None,
    **kwargs: Any,
) -> tuple[list[bytes], list[str]]:
    """
    Tessellate (or pass through ``bytes``) and return one GLB blob per object, plus resolved names.

    Uses the same tessellation and metadata rules as :meth:`CadQueryWebViewer.show`. Does not touch
    the global :data:`cadquery_web_viewer.viewer` or any show-event buffer.
    """
    kw = dict(kwargs)
    payloads, resolved = _show_payloads_from_inputs(*objs, names=names, kwargs=kw)
    defaults = CadQueryWebViewer()
    glbs = [_glb_bytes_from_show_payload(defaults, p) for p in payloads]
    return glbs, resolved


def prepare_glb_upload_batch(
    *objs: Any,
    names: str | list[str] | None = None,
    **kwargs: Any,
) -> tuple[list[tuple[str, bytes, str, dict[str, Any]]], list[str]]:
    """
    Tessellate using the same path as :func:`glb_bytes_list_from_show_inputs` and return
    ``(name, glb, hash, kwargs)`` per object for multipart upload. The second return value is the
    resolved name list in the same order as the payloads.
    """
    kw = dict(kwargs)
    payloads_in, resolved = _show_payloads_from_inputs(*objs, names=names, kwargs=kw)
    defaults = CadQueryWebViewer()
    payloads = [
        (
            p.name,
            _glb_bytes_from_show_payload(defaults, p),
            p.hash,
            dict(p.kwargs or {}),
        )
        for p in payloads_in
    ]
    return payloads, resolved


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
