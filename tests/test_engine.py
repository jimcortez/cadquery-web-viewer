"""Tests for cadquery_web_viewer.engine.CadQueryWebViewer scene/object methods.

Covers the non-CAD code paths: versioned object storage, event publish/validate,
scene state mutations, and describe shape — which is what app.py and
http_client.py compose against.
"""

from __future__ import annotations

import unittest

from cadquery_web_viewer.engine import CadQueryWebViewer, ScenePublishError
from cadquery_web_viewer.events_api import (
    OBJECT_CREATED,
    OBJECT_REMOVED,
    OBJECT_VERSIONED,
    SCENE_CLEARED,
)


class TestPutObjectVersion(unittest.TestCase):
    def test_auto_increments(self) -> None:
        engine = CadQueryWebViewer()
        v1, _ = engine.put_object_version("a", "h1", b"glb1")
        v2, _ = engine.put_object_version("a", "h2", b"glb2")
        self.assertEqual(v1, 1)
        self.assertEqual(v2, 2)

    def test_force_version(self) -> None:
        engine = CadQueryWebViewer()
        v, _ = engine.put_object_version("a", "h", b"glb", force_version=7)
        self.assertEqual(v, 7)
        # Subsequent auto-increment respects the forced version.
        v_next, _ = engine.put_object_version("a", "h2", b"glb2")
        self.assertEqual(v_next, 8)


class TestPublishEventChecked(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CadQueryWebViewer()
        self.engine.put_object_version("a", "h-a", b"glb-a")  # version 1

    def test_created_succeeds_when_not_in_scene(self) -> None:
        self.engine.publish_event_checked(
            {"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h-a"}
        )
        self.assertIn("a", self.engine.scene_active_names())

    def test_created_409_when_already_in_scene(self) -> None:
        self.engine.publish_event_checked(
            {"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h-a"}
        )
        with self.assertRaises(ScenePublishError) as ctx:
            self.engine.publish_event_checked(
                {"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h-a"}
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_versioned_409_when_not_in_scene(self) -> None:
        with self.assertRaises(ScenePublishError) as ctx:
            self.engine.publish_event_checked(
                {"type": OBJECT_VERSIONED, "name": "a", "version": 1, "hash": "h-a"}
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_hash_mismatch_409(self) -> None:
        with self.assertRaises(ScenePublishError) as ctx:
            self.engine.publish_event_checked(
                {"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "WRONG"}
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_unknown_version_404(self) -> None:
        with self.assertRaises(ScenePublishError) as ctx:
            self.engine.publish_event_checked(
                {"type": OBJECT_CREATED, "name": "a", "version": 99, "hash": "h-a"}
            )
        self.assertEqual(ctx.exception.status_code, 404)


class TestSceneStateMutations(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CadQueryWebViewer()
        self.engine.put_object_version("a", "h-a", b"glb-a")
        self.engine.put_object_version("b", "h-b", b"glb-b")
        self.engine.publish_event(
            {"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h-a"}
        )
        self.engine.publish_event(
            {"type": OBJECT_CREATED, "name": "b", "version": 1, "hash": "h-b"}
        )

    def test_scene_active_names_is_frozen(self) -> None:
        names = self.engine.scene_active_names()
        self.assertIsInstance(names, frozenset)
        self.assertEqual(names, frozenset({"a", "b"}))

    def test_object_removed_event_drops_from_scene(self) -> None:
        self.engine.publish_event({"type": OBJECT_REMOVED, "name": "a", "hash": "h-a"})
        self.assertEqual(self.engine.scene_active_names(), frozenset({"b"}))

    def test_scene_cleared_with_except(self) -> None:
        self.engine.publish_event({"type": SCENE_CLEARED, "except_names": ["b"]})
        self.assertEqual(self.engine.scene_active_names(), frozenset({"b"}))

    def test_scene_cleared_no_except_clears_all(self) -> None:
        self.engine.publish_event({"type": SCENE_CLEARED})
        self.assertEqual(self.engine.scene_active_names(), frozenset())

    def test_scene_has_name(self) -> None:
        self.assertTrue(self.engine.scene_has_name("a"))
        self.assertFalse(self.engine.scene_has_name("missing"))


class TestDeleteAndClear(unittest.TestCase):
    def test_delete_object_drops_scene_membership(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.publish_event({"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h"})
        self.assertTrue(engine.delete_object("a"))
        self.assertFalse(engine.scene_has_name("a"))
        self.assertFalse(engine.object_store.has_name("a"))

    def test_delete_version_keeps_other_versions(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h1", b"1")
        engine.put_object_version("a", "h2", b"2")
        self.assertTrue(engine.delete_object("a", force_version=1))
        self.assertTrue(engine.object_store.has_name("a"))
        self.assertIsNone(engine.object_store.get_version("a", 1))

    def test_delete_all_objects(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.publish_event({"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h"})
        engine.delete_all_objects()
        self.assertEqual(engine.object_store.list_names(), [])
        self.assertEqual(engine.scene_active_names(), frozenset())


class TestDescribeObjectShape(unittest.TestCase):
    def test_shape_matches_api_doc(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h1", b"1")
        engine.put_object_version("a", "h2", b"2")
        engine.object_store.set_metadata("a", notes="hi", settings_merge={"k": "v"})
        desc = engine.describe_object("a", in_memory=True, on_disk=True)
        assert desc is not None
        # Required keys, per docs/api.md "GET /api/object" descriptor.
        for key in ("name", "notes", "settings", "version", "hash", "kwargs",
                    "created_at", "in_memory", "on_disk", "versions"):
            self.assertIn(key, desc, f"missing {key!r}")
        self.assertEqual(desc["version"], 2)
        self.assertEqual(desc["hash"], "h2")
        # Older versions are listed newest-first (only one here).
        self.assertEqual([v["version"] for v in desc["versions"]], [1])
        self.assertEqual(desc["versions"][0]["hash"], "h1")

    def test_describe_missing_returns_none(self) -> None:
        engine = CadQueryWebViewer()
        self.assertIsNone(engine.describe_object("nothing"))


class TestPatchObject(unittest.TestCase):
    def test_rename_moves_object(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.object_store.set_metadata("a", notes="orig")
        desc = engine.patch_object("a", new_name="b")
        self.assertEqual(desc["name"], "b")
        self.assertTrue(engine.object_store.has_name("b"))
        self.assertFalse(engine.object_store.has_name("a"))

    def test_rename_conflict_raises(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.put_object_version("b", "h", b"glb")
        with self.assertRaises(ValueError):
            engine.patch_object("a", new_name="b")

    def test_patch_missing_raises_keyerror(self) -> None:
        engine = CadQueryWebViewer()
        with self.assertRaises(KeyError):
            engine.patch_object("nope", new_name="other")

    def test_patch_notes_default_unset_no_change(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.object_store.set_metadata("a", notes="initial")
        desc = engine.patch_object("a", settings_merge={"x": "1"})
        self.assertEqual(desc["notes"], "initial")
        self.assertEqual(desc["settings"], {"x": "1"})

    def test_patch_notes_clear(self) -> None:
        engine = CadQueryWebViewer()
        engine.put_object_version("a", "h", b"glb")
        engine.object_store.set_metadata("a", notes="initial")
        desc = engine.patch_object("a", notes=None)
        self.assertIsNone(desc["notes"])


if __name__ == "__main__":
    unittest.main()
