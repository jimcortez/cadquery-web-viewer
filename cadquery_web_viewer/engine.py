import base64
import copy
import inspect
import os
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from io import BytesIO
from typing import Optional, Dict, Union, Callable, List, Tuple, Any

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
from PIL import Image
# noinspection PyProtectedMember
from build123d import Shape, Axis, Location, Vector
from dataclasses_json import dataclass_json

from cadquery_web_viewer.cad import _hashcode, get_color, ColorTuple
from cadquery_web_viewer.cad import get_shape, grab_all_cad, CADCoreLike, CADLike
from cadquery_web_viewer.gltf import get_version
from cadquery_web_viewer.mylogger import logger
from cadquery_web_viewer.pubsub import BufferedPubSub
from cadquery_web_viewer.rwlock import RWLock
from cadquery_web_viewer.tessellate import tessellate


@dataclass_json
@dataclass
class UpdatesApiData:
    """Data sent to the client through the updates API"""
    name: str
    """Name of the object. Should be unique unless you want to overwrite the previous object"""
    hash: str
    """Hash of the object, to detect changes without rebuilding the object"""
    is_remove: Optional[bool]
    """Whether to remove the object from the scene. If None, this is a shutdown request"""


CadQueryWebViewerObject = Union[bytes, CADCoreLike]


class UpdatesApiFullData(UpdatesApiData):
    obj: CadQueryWebViewerObject
    """The OCCT object (not serialized)"""
    kwargs: Optional[Dict[str, any]]
    """The show_object options, if any (not serialized)"""

    def __init__(self, obj: CadQueryWebViewerObject, name: str, _hash: str, is_remove: Optional[bool] = False,
                 kwargs: Optional[Dict[str, any]] = None):
        self.name = name
        self.hash = _hash
        self.is_remove = is_remove
        self.obj = obj
        self.kwargs = kwargs

    def to_json(self) -> str:
        # noinspection PyUnresolvedReferences
        return super().to_json()


class CadQueryWebViewerProtocol(Enum):
    """Enum of communication protocols supported by the server"""
    HTTP = auto()
    """The recommended protocol for any platform that can run a web server."""
    STDERR = auto()
    """Prints the updates one by one to stderr (first metadata, then base64 of glb file) using a special prefix. Required for Pyodide support."""


class CadQueryWebViewer:
    """Core preview engine: manages CAD/GLB objects and update streams for the viewer."""

    # Startup
    protocol: CadQueryWebViewerProtocol
    """The protocol used by the server. Defaults to HTTP, but can be set to STDERR for Pyodide support."""
    server_thread: Optional[Any]
    """Reserved; embedded HTTP server is no longer started from ``CadQueryWebViewer``."""
    server: Optional[Any]
    startup_complete: threading.Event
    """Event to signal when the server has started"""

    # Running
    show_events: BufferedPubSub[UpdatesApiFullData]
    """PubSub for show events (objects to be shown in/removed from the scene)"""
    build_events: Dict[str, BufferedPubSub[bytes]]
    """PubSub for build events (objects that were built)"""
    build_events_lock: threading.Lock
    """Lock to ensure that objects are only built once"""

    # Shutdown
    at_least_one_client: threading.Event
    """Event to signal when at least one client has connected"""
    shutting_down: threading.Event
    """Event to signal when the server is shutting down"""
    frontend_lock: RWLock
    """Lock to ensure that the frontend has finished working before we shut down"""

    texture: Optional[Tuple[bytes, str]]
    """Default texture to use for model faces, in (data, mimetype) format.
    If left as None, no texture will be used.
    
    It can be set with the CADQUERY_WEB_VIEWER_TEXTURE=<uri> and overridden by the custom `cadquery_web_viewer_texture` attribute of an object.
    The <uri> can be file:<path> or data:<mime>;base64,<data> where <mime> is the mime type and 
    <data> is the base64 encoded image."""

    color_faces: Optional[ColorTuple]
    """Overrides the default color to use for model faces. Applies even if a texture is used. 
    
    You can use `show(..., color_faces=...)` or the standard way of setting colors for build123d/cadquery objects to 
    override this color.
    
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_FACES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    color_edges: Optional[ColorTuple]
    """Overrides the default color to use for model edges. 
    
    You can use `show(..., color_edges=...) or the standard way of setting colors for build123d/cadquery objects to
    override this color.
        
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_EDGES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    color_vertices: Optional[ColorTuple]
    """Overrides the default color to use for model vertices.
    
    You can use `show(..., color_vertices=...)` or the standard way of setting colors for build123d/cadquery objects to
    override this color.
    
    It can be set with the CADQUERY_WEB_VIEWER_COLOR_VERTICES=<color> environment variable, where <color> is a color
    in the hexadecimal format #RRGGBB or #RRGGBBAA."""

    def __init__(self):
        """Initializes the cadquery-web-viewer engine."""
        raw_protocol = os.getenv('CADQUERY_WEB_VIEWER_PROTOCOL', 'http' if sys.platform != 'emscripten' else 'stderr').upper()
        self.protocol = CadQueryWebViewerProtocol[raw_protocol] if raw_protocol in CadQueryWebViewerProtocol.__members__ else CadQueryWebViewerProtocol.HTTP
        self.server_thread = None
        self.server = None
        self.startup_complete = threading.Event()
        self.show_events = BufferedPubSub()
        self.build_events = {}
        self.build_events_lock = threading.Lock()
        self.at_least_one_client = threading.Event()
        self.shutting_down = threading.Event()
        self.frontend_lock = RWLock()
        self.texture = _read_texture_uri(os.getenv("CADQUERY_WEB_VIEWER_TEXTURE"))
        self.color_faces = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_FACES", "#ffbf00"))  # Default yellow
        self.color_edges = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_EDGES", "#1a1aff"))  # Default blue
        self.color_vertices = _read_color(os.getenv("CADQUERY_WEB_VIEWER_COLOR_VERTICES", "#1a1a1a"))  # Default dark gray
        logger.info('Using cadquery-web-viewer v%s', get_version())

    def start(self):
        """Legacy hook: the HTTP viewer is served by the ``cadquery-web-viewer`` Flask CLI, not this method."""
        if self.protocol == CadQueryWebViewerProtocol.STDERR:
            return
        logger.warning(
            'CadQueryWebViewer.start() no longer starts an embedded HTTP server. Run `cadquery-web-viewer` and use remote '
            '`show()`, or set CADQUERY_WEB_VIEWER_DISABLE_SERVER=1 for local in-process show/export.'
        )
        self.startup_complete.set()

    # noinspection PyUnusedLocal
    def stop(self, *args):
        """Legacy hook; embedded ``ThreadingHTTPServer`` is no longer used."""
        if self.protocol == CadQueryWebViewerProtocol.STDERR:
            return
        if self.server_thread is None:
            return

    _stderr_model_prefix = "cadquery_web_viewer://model/"

    def _show_event(self, event: UpdatesApiFullData):
        """Handles a show event by publishing it to the show events buffer (and special handling for stderr protocol)."""
        self.show_events.publish(event)
        # If the protocol is STDERR, we need to print the event to stderr
        if self.protocol == CadQueryWebViewerProtocol.STDERR:
            msg = f'{self._stderr_model_prefix}{event.to_json()}'
            if not event.is_remove:
                # Always build the object even if the interface already has it (optimization disabled for Pyodide)
                glb_and_hash = self.export(event.name)
                if glb_and_hash is None:
                    logger.warning('Object %s not found, ignoring it...', event.name)
                    return
                glb = glb_and_hash[0]
                msg += f'{base64.b64encode(glb).decode("utf-8")}'
            print(msg, file=sys.stderr, flush=True)

    def show(self, *objs: List[CadQueryWebViewerObject], names: Optional[Union[str, List[str]]] = None, **kwargs):
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
        names = names or [_find_var_name(obj) for obj in objs]
        if isinstance(names, str):
            names = [names]
        assert len(names) == len(objs), 'Number of names must match the number of objects'
        for color_name in ('color_faces', 'color_edges', 'color_vertices'):
            if color_name in kwargs:
                kwargs[color_name] = get_color(kwargs[color_name]) or _read_color(kwargs[color_name])

        # Handle auto clearing of previous objects
        if kwargs.get('auto_clear', True):
            self.clear(except_names=names)

        # Remove a previous object event with the same name
        for old_event in self.show_events.buffer():
            if old_event.name in names:
                self.show_events.delete(old_event)
                if old_event.name in self.build_events:
                    del self.build_events[old_event.name]

        # Publish the show event
        for obj, name in zip(objs, names):
            obj_color = get_color(obj)
            # Some properties may be lost in preprocessing, so save them in kwargs
            _kwargs = kwargs.copy()
            if obj_color is not None:
                _kwargs['color_obj'] = obj_color  # Only applies to highest-dimensional objects
            _kwargs['texture'] = _read_texture_uri(getattr(obj, 'cadquery_web_viewer_texture', None) or kwargs.get('texture', None))
            if not isinstance(obj, bytes):
                obj = _preprocess_cad(obj, **_kwargs)
            _hash = _hashcode(obj, **_kwargs)
            event = UpdatesApiFullData(name=name, _hash=_hash, obj=obj, kwargs=_kwargs or {})
            self._show_event(event)

        logger.info('show %s took %.3f seconds', names, time.time() - start)

    def ingest_prebuilt_glb(
        self,
        name: str,
        content_hash: str,
        glb: bytes,
        kwargs: Optional[Dict[str, any]] = None,
        *,
        auto_clear: bool = False,
        except_names: Optional[List[str]] = None,
    ) -> None:
        """Register a ready-made GLB (e.g. from HTTP upload) like ``show`` for bytes, without tessellation."""
        kwargs = kwargs or {}
        if auto_clear:
            self.clear(except_names=list(except_names or []))
        for old_event in list(self.show_events.buffer()):
            if old_event.name == name:
                self.show_events.delete(old_event)
                if name in self.build_events:
                    del self.build_events[name]
        event = UpdatesApiFullData(name=name, _hash=content_hash, obj=glb, kwargs=kwargs)
        self._show_event(event)

    def show_cad_all(self, **kwargs):
        """Publishes all CAD objects in the current scope to the server. See `show` for more details."""
        all_cad = list(grab_all_cad())  # List for reproducible iteration order
        self.show(*[cad for _, cad in all_cad], names=[name for name, _ in all_cad], **kwargs)

    def remove(self, name: str):
        """Removes a previously-shown object from the scene"""
        show_events = self._show_events(name)
        if len(show_events) > 0:
            # Ensure only the new remove event remains for this name
            for old_show_event in show_events:
                self.show_events.delete(old_show_event)

            # Delete any cached object builds
            with self.build_events_lock:
                if name in self.build_events:
                    del self.build_events[name]

            # Publish the remove event
            show_event = copy.copy(show_events[-1])
            show_event.is_remove = True
            self._show_event(show_event)

    def clear(self, except_names: List[str] = None):
        """Clears all previously-shown objects from the scene"""
        if except_names is None:
            except_names = []
        for event in self.show_events.buffer():
            if event.name not in except_names:
                self.remove(event.name)

    def shown_object_names(self, apply_removes: bool = True) -> List[str]:
        """Returns the names of all objects that have been shown"""
        res = set()
        for obj in self.show_events.buffer():
            if not obj.is_remove or not apply_removes:
                res.add(obj.name)
            else:
                res.discard(obj.name)
        return list(res)

    def _show_events(self, name: str, apply_removes: bool = True) -> List[UpdatesApiFullData]:
        """Returns the show events with the given name"""
        res = []
        for event in self.show_events.buffer():
            if event.name == name:
                if not event.is_remove or not apply_removes:
                    res.append(event)
                else:
                    # Also remove the previous events
                    for old_event in res:
                        if old_event.name == event.name:
                            res.remove(old_event)
        return res

    def export(self, name: str) -> Optional[Tuple[bytes, str]]:
        """Export the given previously-shown object to a single GLB blob, building it if necessary."""
        start = time.time()

        # Check that the object to build exists and grab it if it does
        events = self._show_events(name)
        if len(events) == 0:
            logger.warning('Object %s not found', name)
            return None
        event = events[-1]

        # Use the lock to ensure that we don't build the object twice
        with self.build_events_lock:
            # If there are no object events for this name, we need to build the object
            if name not in self.build_events:
                logger.debug('Building object %s with hash %s', name, event.hash)

                # Prepare the pubsub for the object
                publish_to = BufferedPubSub[bytes]()
                self.build_events[name] = publish_to

                # Build and publish the object (once)
                if isinstance(event.obj, bytes):  # Already a GLTF
                    publish_to.publish(event.obj)
                else:  # CAD object to tessellate and convert to GLTF
                    gltf = tessellate(
                        event.obj,
                        color_faces=event.kwargs.get('color_faces', self.color_faces),
                        color_edges=event.kwargs.get('color_edges', self.color_edges),
                        color_vertices=event.kwargs.get('color_vertices', self.color_vertices),
                        color_obj=event.kwargs.get('color_obj', None),
                        tolerance=event.kwargs.get('tolerance', 0.1),
                        angular_tolerance=event.kwargs.get('angular_tolerance', 0.1),
                        faces=event.kwargs.get('faces', True), edges=event.kwargs.get('edges', True),
                        vertices=event.kwargs.get('vertices', True),
                        texture=event.kwargs.get('texture', self.texture))
                    glb_list_of_bytes = gltf.save_to_bytes()
                    glb_bytes = b''.join(glb_list_of_bytes)
                    publish_to.publish(glb_bytes)
                    logger.info('export(%s) took %.3f seconds, %s', name, time.time() - start,
                                sizeof_fmt(len(glb_bytes)))

            # In either case return the elements of a subscription to the async generator
            subscription = self.build_events[name].subscribe()
            try:
                return next(subscription), event.hash
            finally:
                # noinspection PyInconsistentReturns
                subscription.close()

    def export_all(self, folder: str,
                   export_filter: Callable[[str, Optional[CADCoreLike]], bool] = lambda name, obj: True):
        """Export all previously-shown objects to GLB files in the given folder"""
        os.makedirs(folder, exist_ok=True)
        for name in self.shown_object_names():
            if export_filter(name, self._show_events(name)[-1].obj):
                with open(os.path.join(folder, f'{name}.glb'), 'wb') as f:
                    f.write(self.export(name)[0])


def _read_texture_uri(uri: str) -> Optional[Tuple[bytes, str]]:
    if uri is None:
        return None
    if uri.startswith("file:"):
        path = uri[len("file:"):]
        with open(path, 'rb') as f:
            data = f.read()
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


def _read_color(color: str) -> Optional[ColorTuple]:
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


def _find_var_name(obj: any, avoid_levels: int = 2) -> str:
    """A hacky way to get a stable name for an object that may change over time"""

    # Build123d objects have a "label" property, CadQuery Assembly's have "name"
    for f in ('label', 'name'):
        if hasattr(obj, f):
            v = getattr(obj, f)
            if v != '':
                return v;

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


def prepare_glb_upload_batch(
    *objs,
    names: Optional[Union[str, List[str]]] = None,
    **kwargs,
) -> Tuple[List[Tuple[str, bytes, str, Dict[str, Any]]], List[str]]:
    """
    Tessellate like ``CadQueryWebViewer.show`` on a scratch instance and return ``(name, glb, hash, kwargs)`` per object.
    The second return value is the resolved name list in the same order as the payloads.
    """
    resolved = names or [_find_var_name(obj) for obj in objs]
    if isinstance(resolved, str):
        resolved = [resolved]
    tmp = CadQueryWebViewer()
    tmp.show(*objs, names=resolved, **kwargs)
    payloads: List[Tuple[str, bytes, str, Dict[str, Any]]] = []
    for name in resolved:
        exp = tmp.export(name)
        if exp is None:
            continue
        glb, _ = exp
        ev = tmp._show_events(name)[-1]
        payloads.append((name, glb, ev.hash, dict(ev.kwargs or {})))
    return payloads, resolved


def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
