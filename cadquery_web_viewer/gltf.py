from __future__ import annotations

import copy
import importlib.metadata
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from build123d import Location, Plane, Vector
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    FLOAT,
    GLTF2,
    LINES,
    NEAREST,
    POINTS,
    SCALAR,
    TRIANGLES,
    UNSIGNED_INT,
    VEC2,
    VEC3,
    VEC4,
    Accessor,
    Asset,
    Attributes,
    Buffer,
    BufferView,
    Image,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Sampler,
    Scene,
    Texture,
    TextureInfo,
)

EXTRAS_PART_KEY = "__cadquery_web_viewer_part"
"""glTF ``extras`` key stamped on every part node, mesh and primitive with the part name."""

EXTRAS_ASSEMBLY_KEY = "__cadquery_web_viewer_assembly"
"""glTF ``extras`` key on the root node holding the assembly manifest (see ``assembly.py``)."""

DEFAULT_PART_NAME = "part"


def get_version() -> str:
    try:
        return importlib.metadata.version("cadquery-web-viewer")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@dataclass
class _PartBuffers:
    """Intermediate geometry for one part, merged into the GLTF object by :meth:`GLTFMgr.build`."""

    name: str
    node_index: int
    mesh_index: int
    material_index: int
    # - Face data
    face_indices: list[int] = field(default_factory=list)  # 3 indices per triangle
    face_positions: list[float] = field(default_factory=list)  # x, y, z
    face_normals: list[float] = field(default_factory=list)  # x, y, z
    face_tex_coords: list[float] = field(default_factory=list)  # u, v
    face_colors: list[float] = field(default_factory=list)  # r, g, b, a
    # - Edge data
    edge_indices: list[int] = field(default_factory=list)  # 2 indices per edge
    edge_positions: list[float] = field(default_factory=list)  # x, y, z
    edge_colors: list[float] = field(default_factory=list)  # r, g, b, a
    # - Vertex data
    vertex_indices: list[int] = field(default_factory=list)  # 1 index per vertex
    vertex_positions: list[float] = field(default_factory=list)  # x, y, z
    vertex_colors: list[float] = field(default_factory=list)  # r, g, b, a


class GLTFMgr:
    """A utility class to build our GLTF2 objects easily and incrementally.

    The document is always an *assembly*: a root node (``nodes[0]``) whose children are one node per
    part. Each part owns one mesh with up to three primitives (TRIANGLES / LINES / POINTS) and one
    material. Call :meth:`begin_part` before adding geometry; if geometry is added before any part
    was begun, a single implicit part named :data:`DEFAULT_PART_NAME` is created.
    """

    gltf: GLTF2
    image: tuple[bytes, str] | None  # image/png

    _parts: list[_PartBuffers]
    _current: _PartBuffers | None

    def __init__(self, image: tuple[bytes, str] | None = None):
        self.gltf = GLTF2(
            asset=Asset(generator=f"cadquery_web_viewer@{get_version()}"),
            scene=0,
            scenes=[Scene(nodes=[0])],
            nodes=[Node(children=[])],
            meshes=[],
            materials=[],
        )
        self.image = image
        self._parts = []
        self._current = None

    # ------------------------------------------------------------------ parts

    @property
    def part_names(self) -> list[str]:
        return [p.name for p in self._parts]

    def set_assembly(self, name: str, manifest: dict[str, Any] | None = None) -> None:
        """Name the root node and attach the assembly manifest to its ``extras``."""
        root = self.gltf.nodes[0]
        root.name = name
        if manifest is not None:
            extras = dict(root.extras or {})
            extras[EXTRAS_ASSEMBLY_KEY] = manifest
            root.extras = extras

    def begin_part(self, name: str) -> None:
        """Start a new part; subsequent ``add_*`` calls append geometry to it."""
        if any(p.name == name for p in self._parts):
            raise ValueError(f"duplicate part name {name!r}")
        material_index = len(self.gltf.materials)
        self.gltf.materials.append(Material(
            name=name,
            pbrMetallicRoughness=PbrMetallicRoughness(metallicFactor=0.1, roughnessFactor=1.0),
            alphaCutoff=None,
            doubleSided=True,
        ))
        mesh_index = len(self.gltf.meshes)
        part_extras = {EXTRAS_PART_KEY: name}
        self.gltf.meshes.append(Mesh(name=name, extras=dict(part_extras), primitives=[
            Primitive(indices=-1, attributes=Attributes(), mode=TRIANGLES, material=material_index,
                      extras={"face_triangles_end": [], **part_extras}),
            Primitive(indices=-1, attributes=Attributes(), mode=LINES, material=material_index,
                      extras={"edge_points_end": [], **part_extras}),
            Primitive(indices=-1, attributes=Attributes(), mode=POINTS, material=material_index,
                      extras=dict(part_extras)),
        ]))
        node_index = len(self.gltf.nodes)
        self.gltf.nodes.append(Node(name=name, mesh=mesh_index, extras=dict(part_extras)))
        root = self.gltf.nodes[0]
        root.children = list(root.children or []) + [node_index]
        part = _PartBuffers(name=name, node_index=node_index, mesh_index=mesh_index,
                            material_index=material_index)
        self._parts.append(part)
        self._current = part

    def _part(self) -> _PartBuffers:
        if self._current is None:
            self.begin_part(DEFAULT_PART_NAME)
        assert self._current is not None
        return self._current

    def _primitive(self, part: _PartBuffers, mode: int) -> Primitive:
        return [p for p in self.gltf.meshes[part.mesh_index].primitives if p.mode == mode][0]

    # --------------------------------------------------------------- geometry

    def add_face(self, vertices_raw: list[Vector], normals: list[Vector], indices_raw: list[tuple[int, int, int]],
                 tex_coord_raw: list[tuple[float, float]], color: tuple[float, float, float, float]):
        """Add a face to the current part"""
        part = self._part()
        base_index = len(part.face_positions) // 3  # All the new indices reference the new vertices
        part.face_indices.extend([base_index + i for t in indices_raw for i in t])
        part.face_positions.extend([v for t in vertices_raw for v in t])
        part.face_normals.extend([n for t in normals for n in t])
        part.face_tex_coords.extend([c for t in tex_coord_raw for c in t])
        part.face_colors.extend([col for _ in range(len(vertices_raw)) for col in color])
        self._primitive(part, TRIANGLES).extras["face_triangles_end"].append(len(part.face_indices))

    def add_edge(self, vertices_raw: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
                 color: tuple[float, float, float, float]):
        """Add an edge to the current part"""
        part = self._part()
        vertices_flat = [v for t in vertices_raw for v in t]  # Line from 0 to 1, 2 to 3, 4 to 5, etc.
        base_index = len(part.edge_positions) // 3
        part.edge_indices.extend([base_index + i for i in range(len(vertices_flat))])
        part.edge_positions.extend([v for t in vertices_flat for v in t])
        part.edge_colors.extend([col for _ in range(len(vertices_flat)) for col in color])
        self._primitive(part, LINES).extras["edge_points_end"].append(len(part.edge_indices))

    def add_vertex(self, vertex: tuple[float, float, float], color: tuple[float, float, float, float]):
        """Add a vertex to the current part"""
        part = self._part()
        base_index = len(part.vertex_positions) // 3
        part.vertex_indices.append(base_index)
        part.vertex_positions.extend(vertex)
        part.vertex_colors.extend(color)

    def add_location(self, loc: Location):
        """Add a location to the current part as axis edges + an origin vertex"""
        pl = Plane(loc)

        def vert(v: Vector) -> tuple[float, float, float]:
            return v.X, v.Y, v.Z

        # Add 1 origin vertex and 3 edges with custom colors to identify the X, Y and Z axis
        # The colors are hardcoded. You can add vertices and edges manually to change them.
        self.add_vertex(vert(pl.origin), color=(0.1, 0.1, 0.1, 1.0))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.x_dir))], color=(0.97, 0.24, 0.24, 1.0))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.y_dir))], color=(0.42, 0.8, 0.15, 1.0))
        self.add_edge([(vert(pl.origin), vert(pl.origin + pl.z_dir))], color=(0.09, 0.55, 0.94, 1.0))

    # ------------------------------------------------------------------ build

    def build(self) -> GLTF2:
        """Merge the intermediate data into the GLTF object and return it"""
        if not self._parts:
            self.begin_part(DEFAULT_PART_NAME)

        buffers_list: list[tuple[Accessor, BufferView, bytes]] = []
        any_faces = any(len(p.face_indices) > 0 for p in self._parts)
        if not any_faces:
            self.image = None  # Unused image

        # With a texture, faces use the textured part materials while edges/vertices share one
        # untextured material.
        edges_and_vertices_mat: int | None = None
        if self.image is not None:
            edges_and_vertices_mat = len(self.gltf.materials)
            new_mat = copy.deepcopy(self.gltf.materials[self._parts[0].material_index])
            new_mat.name = "edges_and_vertices"
            new_mat.pbrMetallicRoughness.baseColorTexture = None
            new_mat.doubleSided = True
            self.gltf.materials.append(new_mat)

        for part in self._parts:
            mesh = self.gltf.meshes[part.mesh_index]
            faces_primitive = self._primitive(part, TRIANGLES)
            if len(part.face_indices) > 0:
                faces_primitive.indices = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(part.face_indices, 1))
                faces_primitive.attributes.POSITION = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(part.face_positions, 3))
                faces_primitive.attributes.NORMAL = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(part.face_normals, 3))
                faces_primitive.attributes.TEXCOORD_0 = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(part.face_tex_coords, 2))
                faces_primitive.attributes.COLOR_0 = len(buffers_list)
                buffers_list.append(_gen_buffer_metadata(part.face_colors, 4))
            else:
                mesh.primitives = list(  # Remove unused faces primitive
                    filter(lambda p: p.mode != TRIANGLES, mesh.primitives))

            # Treat edges and vertices the same way
            for (indices, positions, colors, kind) in [
                (part.edge_indices, part.edge_positions, part.edge_colors, LINES),
                (part.vertex_indices, part.vertex_positions, part.vertex_colors, POINTS),
            ]:
                primitive = self._primitive(part, kind)
                if len(indices) > 0:
                    if edges_and_vertices_mat is not None:
                        primitive.material = edges_and_vertices_mat
                    primitive.indices = len(buffers_list)
                    buffers_list.append(_gen_buffer_metadata(indices, 1))
                    primitive.attributes.POSITION = len(buffers_list)
                    buffers_list.append(_gen_buffer_metadata(positions, 3))
                    primitive.attributes.COLOR_0 = len(buffers_list)
                    buffers_list.append(_gen_buffer_metadata(colors, 4))
                else:
                    mesh.primitives = list(  # Remove unused edges/vertices primitive
                        filter(lambda p: p.mode != kind, mesh.primitives))

        if self.image is not None:  # Add texture last as it creates a fake accessor that is not added!
            self.gltf.images = [Image(bufferView=len(buffers_list), mimeType=self.image[1])]
            self.gltf.textures = [Texture(source=0, sampler=0)]
            self.gltf.samplers = [Sampler(magFilter=NEAREST)]
            for part in self._parts:
                # noinspection PyPep8Naming
                self.gltf.materials[part.material_index].pbrMetallicRoughness.baseColorTexture = TextureInfo(index=0)
            buffers_list.append((Accessor(), BufferView(), self.image[0]))

        # Once all the data is ready, we can concatenate the buffers updating the accessors and views
        prev_binary_blob = self.gltf.binary_blob() or b''
        byte_offset_base = len(prev_binary_blob)
        for accessor, bufferView, blob in buffers_list:

            if accessor.componentType is not None:  # Remove accessor of texture
                buffer_view_base = len(self.gltf.bufferViews)
                accessor.bufferView = buffer_view_base
                self.gltf.accessors.append(accessor)

            bufferView.buffer = 0
            bufferView.byteOffset = byte_offset_base
            bufferView.byteLength = len(blob)
            self.gltf.bufferViews.append(bufferView)

            byte_offset_base += len(blob)
            prev_binary_blob += blob

        self.gltf.buffers.append(Buffer(byteLength=byte_offset_base))
        self.gltf.set_binary_blob(prev_binary_blob)

        return self.gltf


def _gen_buffer_metadata(data: list[Any], chunk: int) -> tuple[Accessor, BufferView, bytes]:
    return Accessor(
        componentType={1: UNSIGNED_INT, 2: FLOAT, 3: FLOAT, 4: FLOAT}[chunk],
        count=len(data) // chunk,
        type={1: SCALAR, 2: VEC2, 3: VEC3, 4: VEC4}[chunk],
        max=[max(data[i::chunk]) for i in range(chunk)],
        min=[min(data[i::chunk]) for i in range(chunk)],
    ), BufferView(
        target={1: ELEMENT_ARRAY_BUFFER, 2: ARRAY_BUFFER, 3: ARRAY_BUFFER, 4: ARRAY_BUFFER}[chunk],
    ), np.array(data, dtype={1: np.uint32, 2: np.float32, 3: np.float32, 4: np.float32}[chunk]).tobytes()
