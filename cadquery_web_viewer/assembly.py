"""Assemblies: one viewer object made of named, individually coloured and tagged parts.

Every object the viewer stores is an assembly. A single shape is an assembly with one part. The
manifest below is stored in the root glTF node ``extras`` (key :data:`EXTRAS_ASSEMBLY_KEY`) so the
GLB is self-describing, and mirrored in the version ``kwargs`` (key :data:`KWARGS_ASSEMBLY_KEY`) so
``GET /api/object`` can expose it without parsing the GLB.

Manifest shape (``schema`` 1)::

    {"schema": 1, "name": "<object>", "tags": ["..."],
     "parts": [{"name": "<part>", "index": 0, "color": "#rrggbb" | null, "tags": ["..."]}, ...]}
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Shape
from pygltflib import GLTF2

from cadquery_web_viewer.cad import CADCoreLike, ColorTuple, get_color, get_shape
from cadquery_web_viewer.gltf import EXTRAS_ASSEMBLY_KEY, EXTRAS_PART_KEY

__all__ = [
    "EXTRAS_ASSEMBLY_KEY",
    "EXTRAS_PART_KEY",
    "KWARGS_ASSEMBLY_KEY",
    "MANIFEST_SCHEMA",
    "AssemblyPart",
    "AssemblySpec",
    "assembly_from_object",
    "color_to_hex",
    "is_assembly_like",
    "manifest_dict",
    "normalize_manifest",
    "part_names_from_glb",
    "read_manifest_from_glb",
]

KWARGS_ASSEMBLY_KEY = "assembly"
"""Reserved key in a stored version's ``kwargs`` holding the assembly manifest."""

MANIFEST_SCHEMA = 1


@dataclass(frozen=True)
class AssemblyPart:
    """One named part of an assembly.

    :param obj: any CAD-like object accepted by :func:`cadquery_web_viewer.show` (shape, Workplane,
        build123d part, ...), or an already preprocessed :data:`CADCoreLike`.
    :param color: face colour override for this part (RGBA 0..1); ``None`` keeps the default colour.
    """

    name: str
    obj: Any
    color: ColorTuple | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssemblySpec:
    name: str
    parts: tuple[AssemblyPart, ...]
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError(f"assembly {self.name!r} has no parts")
        names = [p.name for p in self.parts]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise ValueError(f"assembly {self.name!r} has duplicate part names: {dupes}")


def color_to_hex(color: ColorTuple | None) -> str | None:
    """RGBA tuple (0..1) to ``#rrggbb``; alpha is dropped. ``None`` passes through."""
    if color is None:
        return None
    r, g, b = (max(0, min(255, round(float(c) * 255))) for c in color[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def manifest_dict(spec: AssemblySpec) -> dict[str, Any]:
    """Build the JSON manifest for ``spec`` (no geometry, only names/colours/tags)."""
    return {
        "schema": MANIFEST_SCHEMA,
        "name": spec.name,
        "tags": list(spec.tags),
        "parts": [
            {
                "name": part.name,
                "index": index,
                "color": color_to_hex(part.color),
                "tags": list(part.tags),
            }
            for index, part in enumerate(spec.parts)
        ],
    }


def _is_cq_assembly(obj: Any) -> bool:
    # cadquery.Assembly duck type: cadquery is not a dependency of this package.
    return callable(getattr(obj, "traverse", None)) and hasattr(obj, "children") and hasattr(obj, "loc")


def is_assembly_like(obj: Any) -> bool:
    """True for :class:`AssemblySpec` and CadQuery ``Assembly`` objects."""
    return isinstance(obj, AssemblySpec) or _is_cq_assembly(obj)


def _node_color(node: Any) -> ColorTuple | None:
    color = getattr(node, "color", None)
    if color is None:
        return None
    if callable(getattr(color, "toTuple", None)):  # cadquery.Color
        return get_color(tuple(color.toTuple()))
    return get_color(color)


def _world_location(node: Any) -> Any:
    """Compose ``loc`` up the parent chain, matching ``cq.Assembly.toCompound()``."""
    loc = node.loc
    parent = getattr(node, "parent", None)
    while parent is not None:
        loc = parent.loc * loc
        parent = getattr(parent, "parent", None)
    return loc


def _parts_from_cq_assembly(assy: Any) -> list[AssemblyPart]:
    parts: list[AssemblyPart] = []
    for node_name, node in assy.traverse():
        raw = getattr(node, "obj", None)
        if raw is None:
            continue
        shape = get_shape(raw, error=False)
        if shape is None or isinstance(shape, TopLoc_Location):
            continue
        loc = _world_location(node)
        wrapped = getattr(loc, "wrapped", None)
        if isinstance(wrapped, TopLoc_Location) and not wrapped.IsIdentity():
            shape = TopoDS_Shape.Moved(shape, wrapped)
        parts.append(AssemblyPart(name=str(node_name), obj=shape, color=_node_color(node)))
    if not parts:
        raise ValueError("assembly has no tessellatable parts")
    return parts


def assembly_from_object(obj: Any, name: str) -> AssemblySpec:
    """Turn ``obj`` into an :class:`AssemblySpec` named ``name``.

    Accepts an :class:`AssemblySpec` (returned as-is, renamed if needed), a CadQuery ``Assembly``
    (one part per shape-bearing node, world locations applied, node colours kept), a sequence of
    ``(part_name, shape)`` pairs, or any single CAD-like object (one part named ``name``).
    """
    if isinstance(obj, AssemblySpec):
        return obj if obj.name == name else AssemblySpec(name=name, parts=obj.parts, tags=obj.tags)
    if _is_cq_assembly(obj):
        return AssemblySpec(name=name, parts=tuple(_parts_from_cq_assembly(obj)))
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)) and obj and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in obj
    ):
        return AssemblySpec(name=name, parts=tuple(AssemblyPart(name=n, obj=s) for n, s in obj))
    return AssemblySpec(name=name, parts=(AssemblyPart(name=name, obj=obj, color=get_color(obj)),))


def normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Fill in optional manifest keys (``tags``, ``color``, ``index``).

    glTF writers drop ``null`` values and empty lists from ``extras``, so a manifest read back from
    a GLB may be missing them.
    """
    parts = []
    for index, raw in enumerate(manifest.get("parts") or []):
        part = dict(raw)
        part.setdefault("index", index)
        part.setdefault("color", None)
        part.setdefault("tags", [])
        parts.append(part)
    out = dict(manifest)
    out.setdefault("schema", MANIFEST_SCHEMA)
    out.setdefault("tags", [])
    out["parts"] = parts
    return out


def read_manifest_from_glb(glb: bytes) -> dict[str, Any] | None:
    """Return the (normalised) manifest stored in the root node of a viewer-produced GLB, or ``None``."""
    gltf = GLTF2.load_from_bytes(glb)
    if not gltf.nodes:
        return None
    scene_index = gltf.scene or 0
    roots = gltf.scenes[scene_index].nodes if gltf.scenes else [0]
    for index in roots or []:
        extras = gltf.nodes[index].extras or {}
        manifest = extras.get(EXTRAS_ASSEMBLY_KEY)
        if isinstance(manifest, dict):
            return normalize_manifest(manifest)
    return None


def part_names_from_glb(glb: bytes) -> list[str]:
    """Names of the part nodes (``extras[EXTRAS_PART_KEY]``) in document order."""
    gltf = GLTF2.load_from_bytes(glb)
    names: list[str] = []
    for node in gltf.nodes or []:
        part = (node.extras or {}).get(EXTRAS_PART_KEY)
        if isinstance(part, str):
            names.append(part)
    return names


def preprocessed(part: AssemblyPart, shape: CADCoreLike) -> AssemblyPart:
    """Copy of ``part`` with ``obj`` replaced by its preprocessed core shape."""
    return AssemblyPart(name=part.name, obj=shape, color=part.color, tags=part.tags)
