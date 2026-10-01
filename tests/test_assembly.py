"""Tests for multi-part (assembly) tessellation, manifests and upload payloads."""

from __future__ import annotations

import unittest

from build123d import Box, Location
from cadquery_web_viewer.assembly import (
    EXTRAS_ASSEMBLY_KEY,
    EXTRAS_PART_KEY,
    KWARGS_ASSEMBLY_KEY,
    MANIFEST_SCHEMA,
    AssemblyPart,
    AssemblySpec,
    assembly_from_object,
    color_to_hex,
    manifest_dict,
    normalize_manifest,
    part_names_from_glb,
    read_manifest_from_glb,
)
from cadquery_web_viewer.cad import get_shape
from cadquery_web_viewer.engine import prepare_assembly_upload, prepare_glb_upload_batch
from cadquery_web_viewer.tessellate import tessellate, tessellate_parts
from OCP.TopLoc import TopLoc_Location
from pygltflib import GLTF2, LINES, POINTS, TRIANGLES

RED = (1.0, 0.0, 0.0, 1.0)
BLUE = (0.0, 0.0, 1.0, 1.0)
DARK = (0.1, 0.1, 0.1, 1.0)


def _box_shape(size: float = 1.0):
    shape = get_shape(Box(size, size, size))
    assert shape is not None
    return shape


def _bbox_center_x(shape) -> float:
    from build123d import Shape

    bb = Shape(shape).bounding_box()
    return (bb.min.X + bb.max.X) / 2


class TestTessellateParts(unittest.TestCase):
    def setUp(self) -> None:
        spec = AssemblySpec(
            name="pair",
            parts=(AssemblyPart("a", _box_shape(), color=RED), AssemblyPart("b", _box_shape(2.0))),
            tags=("t1",),
        )
        self.manifest = manifest_dict(spec)
        gltf = tessellate_parts(
            [(p.name, p.obj, p.color) for p in spec.parts],
            assembly_name="pair",
            manifest=self.manifest,
            color_faces=BLUE,
            color_edges=DARK,
            color_vertices=DARK,
        )
        self.glb = b"".join(gltf.save_to_bytes())
        self.doc = GLTF2.load_from_bytes(self.glb)

    def test_node_tree(self) -> None:
        self.assertEqual(len(self.doc.nodes), 3)
        root = self.doc.nodes[0]
        self.assertEqual(root.name, "pair")
        self.assertIsNone(root.mesh)
        self.assertEqual(root.children, [1, 2])
        # glTF writers drop null / empty-list extras; normalising restores the defaults.
        self.assertEqual(normalize_manifest(root.extras[EXTRAS_ASSEMBLY_KEY]), self.manifest)
        self.assertEqual(self.doc.scenes[0].nodes, [0])
        for index, name in ((1, "a"), (2, "b")):
            node = self.doc.nodes[index]
            self.assertEqual(node.name, name)
            self.assertEqual(node.mesh, index - 1)
            self.assertEqual(node.extras[EXTRAS_PART_KEY], name)

    def test_meshes_primitives_and_materials(self) -> None:
        self.assertEqual(len(self.doc.meshes), 2)
        self.assertEqual(len(self.doc.materials), 2)
        for mesh, name in zip(self.doc.meshes, ("a", "b")):
            self.assertEqual(mesh.name, name)
            self.assertEqual(mesh.extras[EXTRAS_PART_KEY], name)
            modes = sorted(p.mode for p in mesh.primitives)
            self.assertEqual(modes, sorted([TRIANGLES, LINES, POINTS]))
            for prim in mesh.primitives:
                self.assertEqual(prim.extras[EXTRAS_PART_KEY], name)
                self.assertIsNotNone(prim.attributes.COLOR_0)
                self.assertIsNotNone(prim.indices)
            faces = [p for p in mesh.primitives if p.mode == TRIANGLES][0]
            self.assertTrue(faces.extras["face_triangles_end"])
        self.assertEqual({m.material for mesh in self.doc.meshes for m in mesh.primitives}, {0, 1})
        # Face colour is baked as COLOR_0, not as a material factor (three.js would multiply both).
        for material in self.doc.materials:
            self.assertIn(material.pbrMetallicRoughness.baseColorFactor, (None, [1.0, 1.0, 1.0, 1.0]))
        self.assertEqual(len(self.doc.buffers), 1)

    def test_manifest_round_trips_through_glb(self) -> None:
        self.assertEqual(read_manifest_from_glb(self.glb), self.manifest)
        self.assertEqual(part_names_from_glb(self.glb), ["a", "b"])

    def test_single_shape_tessellate_is_one_part(self) -> None:
        gltf = tessellate(_box_shape(), color_faces=BLUE, color_edges=DARK, color_vertices=DARK, name="solo")
        doc = GLTF2.load_from_bytes(b"".join(gltf.save_to_bytes()))
        self.assertEqual([n.name for n in doc.nodes], ["solo", "solo"])
        self.assertEqual(doc.nodes[1].extras[EXTRAS_PART_KEY], "solo")
        self.assertEqual(len(doc.meshes), 1)

    def test_duplicate_part_name_rejected(self) -> None:
        with self.assertRaises(ValueError):
            tessellate_parts(
                [("a", _box_shape(), None), ("a", _box_shape(), None)],
                assembly_name="x", color_faces=BLUE, color_edges=DARK, color_vertices=DARK,
            )


class TestManifest(unittest.TestCase):
    def test_manifest_dict_shape(self) -> None:
        spec = AssemblySpec(
            name="asm",
            parts=(AssemblyPart("a", None, color=RED, tags=("x",)), AssemblyPart("b", None)),
            tags=("bevel",),
        )
        self.assertEqual(
            manifest_dict(spec),
            {
                "schema": MANIFEST_SCHEMA,
                "name": "asm",
                "tags": ["bevel"],
                "parts": [
                    {"name": "a", "index": 0, "color": "#ff0000", "tags": ["x"]},
                    {"name": "b", "index": 1, "color": None, "tags": []},
                ],
            },
        )

    def test_color_to_hex(self) -> None:
        self.assertEqual(color_to_hex((1.0, 0.5, 0.0, 1.0)), "#ff8000")
        self.assertIsNone(color_to_hex(None))

    def test_spec_validation(self) -> None:
        with self.assertRaises(ValueError):
            AssemblySpec(name="empty", parts=())
        with self.assertRaises(ValueError):
            AssemblySpec(name="dup", parts=(AssemblyPart("a", None), AssemblyPart("a", None)))


class _FakeNode:
    """Minimal stand-in for ``cadquery.Assembly`` nodes (cadquery is not a test dependency)."""

    def __init__(self, name: str, obj, loc, color=None, parent=None):
        self.name = name
        self.obj = obj
        self.loc = loc
        self.color = color
        self.parent = parent
        self.children: list[_FakeNode] = []

    def add(self, child: _FakeNode) -> None:
        child.parent = self
        self.children.append(child)

    def traverse(self):
        yield self.name, self
        for child in self.children:
            yield from child.traverse()


class _FakeLoc:
    def __init__(self, wrapped: TopLoc_Location):
        self.wrapped = wrapped

    def __mul__(self, other: _FakeLoc) -> _FakeLoc:
        return _FakeLoc(self.wrapped * other.wrapped)


class _FakeColor:
    def __init__(self, rgba):
        self._rgba = rgba

    def toTuple(self):
        return self._rgba


def _loc(x: float) -> _FakeLoc:
    return _FakeLoc(Location((x, 0, 0)).wrapped)


class TestAssemblyFromObject(unittest.TestCase):
    def test_pairs(self) -> None:
        spec = assembly_from_object([("a", Box(1, 1, 1)), ("b", Box(2, 2, 2))], "pair")
        self.assertEqual([p.name for p in spec.parts], ["a", "b"])

    def test_single_object(self) -> None:
        spec = assembly_from_object(Box(1, 1, 1), "solo")
        self.assertEqual([p.name for p in spec.parts], ["solo"])

    def test_spec_is_renamed(self) -> None:
        spec = AssemblySpec(name="x", parts=(AssemblyPart("a", None),))
        self.assertEqual(assembly_from_object(spec, "y").name, "y")
        self.assertIs(assembly_from_object(spec, "x"), spec)

    def test_cq_assembly_applies_world_location_and_color(self) -> None:
        root = _FakeNode("root", None, _loc(10.0))
        root.add(_FakeNode("a", Box(1, 1, 1), _loc(5.0), color=_FakeColor((0.0, 1.0, 0.0, 1.0))))
        root.add(_FakeNode("b", Box(1, 1, 1), _loc(0.0)))
        spec = assembly_from_object(root, "asm")
        self.assertEqual([p.name for p in spec.parts], ["a", "b"])
        self.assertAlmostEqual(_bbox_center_x(spec.parts[0].obj), 15.0, places=5)
        self.assertAlmostEqual(_bbox_center_x(spec.parts[1].obj), 10.0, places=5)
        self.assertEqual(spec.parts[0].color, (0.0, 1.0, 0.0, 1.0))
        self.assertIsNone(spec.parts[1].color)


class TestUploadPayloads(unittest.TestCase):
    def test_prepare_assembly_upload(self) -> None:
        spec = AssemblySpec(
            name="pair",
            parts=(AssemblyPart("a", Box(1, 1, 1), color=RED, tags=("p",)), AssemblyPart("b", Box(2, 2, 2))),
            tags=("bevel",),
        )
        name, glb, h1, kw = prepare_assembly_upload(spec, "pair")
        self.assertEqual(name, "pair")
        self.assertTrue(glb.startswith(b"glTF"))
        manifest = kw[KWARGS_ASSEMBLY_KEY]
        self.assertEqual(manifest["name"], "pair")
        self.assertEqual(manifest["tags"], ["bevel"])
        self.assertEqual([p["name"] for p in manifest["parts"]], ["a", "b"])
        self.assertEqual(manifest["parts"][0]["color"], "#ff0000")
        self.assertEqual(read_manifest_from_glb(glb), manifest)
        self.assertEqual(part_names_from_glb(glb), ["a", "b"])
        _, _, h2, _ = prepare_assembly_upload(spec, "pair")
        self.assertEqual(h1, h2)

    def test_single_shape_gets_one_part_manifest(self) -> None:
        payloads, names = prepare_glb_upload_batch(Box(1, 1, 1), names="box", color_faces="#ff0000")
        self.assertEqual(names, ["box"])
        name, glb, _, kw = payloads[0]
        self.assertEqual(name, "box")
        manifest = kw[KWARGS_ASSEMBLY_KEY]
        self.assertEqual(manifest["parts"], [{"name": "box", "index": 0, "color": "#ff0000", "tags": []}])
        self.assertEqual(read_manifest_from_glb(glb), manifest)

    def test_caller_manifest_is_kept(self) -> None:
        custom = {"schema": 1, "name": "box", "tags": ["mine"], "parts": [{"name": "box", "index": 0, "color": None, "tags": []}]}
        payloads, _ = prepare_glb_upload_batch(Box(1, 1, 1), names="box", assembly=custom)
        _, glb, _, kw = payloads[0]
        self.assertEqual(kw[KWARGS_ASSEMBLY_KEY], custom)
        self.assertEqual(read_manifest_from_glb(glb), custom)

    def test_bytes_input_has_no_manifest(self) -> None:
        payloads, _ = prepare_glb_upload_batch(b"glTF", names="raw")
        self.assertNotIn(KWARGS_ASSEMBLY_KEY, payloads[0][3])


if __name__ == "__main__":
    unittest.main()
