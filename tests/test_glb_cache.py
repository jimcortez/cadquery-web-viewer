"""Tests for cadquery_web_viewer.glb_cache.GlbDiskCache."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cadquery_web_viewer.glb_cache import (
    OBJECT_MANIFEST_SUFFIX,
    SCHEMA_VERSION,
    GlbDiskCache,
    object_id_for_name,
    utc_now_iso,
)


class TestUtcNowIso(unittest.TestCase):
    def test_format(self) -> None:
        s = utc_now_iso()
        self.assertTrue(s.endswith("Z"))
        # Three-digit milliseconds.
        self.assertRegex(s, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class TestGlbDiskCache(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = GlbDiskCache(self._tmp.name)

    def test_write_and_read_version(self) -> None:
        self.cache.write_version("a", 1, "h1", b"glb-1", {"k": "v"})
        glb = self.cache.read_glb("a", 1)
        self.assertEqual(glb, b"glb-1")

    def test_list_version_entries_after_writes(self) -> None:
        self.cache.write_version("a", 1, "h1", b"1")
        self.cache.write_version("a", 2, "h2", b"2")
        self.cache.write_version("b", 1, "hb", b"b")
        entries = sorted(self.cache.list_version_entries(), key=lambda e: (e.name, e.version))
        self.assertEqual([(e.name, e.version, e.content_hash) for e in entries],
                         [("a", 1, "h1"), ("a", 2, "h2"), ("b", 1, "hb")])

    def test_read_missing_glb(self) -> None:
        self.assertIsNone(self.cache.read_glb("missing", 1))

    def test_kwargs_strip_texture(self) -> None:
        # The texture field is image bytes — must not be persisted.
        self.cache.write_version(
            "a", 1, "h", b"glb",
            kwargs={"k": "v", "texture": (b"jpgbytes", "image/jpeg")},
        )
        entry = next(e for e in self.cache.list_version_entries() if e.name == "a")
        self.assertNotIn("texture", entry.kwargs)
        self.assertEqual(entry.kwargs.get("k"), "v")

    def test_kwargs_strip_unjsonable(self) -> None:
        class NotJsonable:
            pass

        self.cache.write_version(
            "a", 1, "h", b"glb", kwargs={"ok": 1, "bad": NotJsonable()}
        )
        entry = next(e for e in self.cache.list_version_entries() if e.name == "a")
        self.assertEqual(entry.kwargs, {"ok": 1})

    def test_object_manifest_round_trip(self) -> None:
        self.cache.write_object_manifest("a", notes="hi", settings={"k": "v"})
        m = self.cache.read_object_manifest("a")
        assert m is not None
        self.assertEqual(m.name, "a")
        self.assertEqual(m.notes, "hi")
        self.assertEqual(m.settings, {"k": "v"})

    def test_manifest_path_uses_object_id(self) -> None:
        self.cache.write_object_manifest("a", notes=None, settings={})
        expected = Path(self._tmp.name) / (object_id_for_name("a") + OBJECT_MANIFEST_SUFFIX)
        self.assertTrue(expected.is_file())
        meta = json.loads(expected.read_text())
        self.assertEqual(meta["schema"], SCHEMA_VERSION)

    def test_delete_version(self) -> None:
        self.cache.write_version("a", 1, "h", b"1")
        self.cache.write_version("a", 2, "h", b"2")
        self.cache.delete_version("a", 1)
        self.assertIsNone(self.cache.read_glb("a", 1))
        self.assertEqual(self.cache.read_glb("a", 2), b"2")

    def test_delete_object_removes_versions_and_manifest(self) -> None:
        self.cache.write_version("a", 1, "h1", b"1")
        self.cache.write_version("a", 2, "h2", b"2")
        self.cache.write_object_manifest("a", notes="x", settings={})
        self.cache.delete_object("a")
        self.assertEqual(self.cache.list_version_entries(), [])
        self.assertIsNone(self.cache.read_object_manifest("a"))

    def test_clear(self) -> None:
        self.cache.write_version("a", 1, "h", b"1")
        self.cache.write_object_manifest("a", notes=None, settings={})
        self.cache.clear()
        self.assertEqual(self.cache.list_version_entries(), [])
        self.assertIsNone(self.cache.read_object_manifest("a"))

    def test_rename_object(self) -> None:
        self.cache.write_version("old", 1, "h1", b"v1", {"k": 1})
        self.cache.write_version("old", 2, "h2", b"v2", {"k": 2})
        self.cache.write_object_manifest("old", notes="kept", settings={"s": "x"})
        self.cache.rename_object("old", "new")

        # Old name is gone.
        self.assertEqual([e for e in self.cache.list_version_entries() if e.name == "old"], [])
        self.assertIsNone(self.cache.read_object_manifest("old"))

        # New name has the same content + manifest.
        new_entries = sorted(
            (e for e in self.cache.list_version_entries() if e.name == "new"),
            key=lambda e: e.version,
        )
        self.assertEqual([(e.version, e.content_hash) for e in new_entries], [(1, "h1"), (2, "h2")])
        self.assertEqual(self.cache.read_glb("new", 1), b"v1")
        self.assertEqual(self.cache.read_glb("new", 2), b"v2")
        m = self.cache.read_object_manifest("new")
        assert m is not None
        self.assertEqual(m.notes, "kept")
        self.assertEqual(m.settings, {"s": "x"})

    def test_atomic_write_does_not_leave_tempfiles_on_success(self) -> None:
        self.cache.write_version("a", 1, "h", b"1")
        leftovers = [p for p in Path(self._tmp.name).iterdir() if p.suffix.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_invalid_manifest_returns_none(self) -> None:
        # Corrupt manifest path with junk.
        path = Path(self._tmp.name) / (object_id_for_name("bad") + OBJECT_MANIFEST_SUFFIX)
        path.write_text("not json")
        self.assertIsNone(self.cache.read_object_manifest("bad"))


if __name__ == "__main__":
    unittest.main()
