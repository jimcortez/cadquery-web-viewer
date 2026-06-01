"""Tests for cadquery_web_viewer.object_store."""

from __future__ import annotations

import unittest

from cadquery_web_viewer.object_store import (
    UNSET,
    VersionedObjectStore,
    _UNSET,
    describe_object_record,
    latest_version_info,
    validate_settings_map,
    validate_settings_value,
)


class TestVersionedObjectStore(unittest.TestCase):
    def setUp(self) -> None:
        self.store = VersionedObjectStore()

    def test_put_get_version(self) -> None:
        ts = self.store.put_version("a", 1, "hash1", b"glb-bytes-1", {"k": "v"})
        self.assertTrue(ts.endswith("Z"))
        sv = self.store.get_version("a", 1)
        self.assertIsNotNone(sv)
        assert sv is not None
        self.assertEqual(sv.glb, b"glb-bytes-1")
        self.assertEqual(sv.hash, "hash1")
        self.assertEqual(sv.kwargs, {"k": "v"})

    def test_get_version_latest_when_none(self) -> None:
        self.store.put_version("a", 1, "h1", b"1")
        self.store.put_version("a", 5, "h5", b"5")
        sv = self.store.get_version("a")
        assert sv is not None
        self.assertEqual(sv.hash, "h5")  # latest = max version

    def test_get_version_missing(self) -> None:
        self.assertIsNone(self.store.get_version("nonexistent"))
        self.store.put_version("a", 1, "h", b"1")
        self.assertIsNone(self.store.get_version("a", 99))

    def test_next_version(self) -> None:
        self.assertEqual(self.store.next_version("new"), 1)
        self.store.put_version("a", 1, "h", b"x")
        self.assertEqual(self.store.next_version("a"), 2)
        self.store.put_version("a", 7, "h7", b"y")
        self.assertEqual(self.store.next_version("a"), 8)

    def test_delete_version(self) -> None:
        self.store.put_version("a", 1, "h1", b"1")
        self.store.put_version("a", 2, "h2", b"2")
        self.assertTrue(self.store.delete_version("a", 1))
        self.assertIsNone(self.store.get_version("a", 1))
        self.assertIsNotNone(self.store.get_version("a", 2))
        # Removing the last version of a name with no metadata drops the record.
        self.assertTrue(self.store.delete_version("a", 2))
        self.assertFalse(self.store.has_name("a"))

    def test_delete_version_keeps_record_when_metadata(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.set_metadata("a", notes="keep me")
        self.store.delete_version("a", 1)
        # Metadata is retained even when the last version is removed.
        rec = self.store.get_record("a")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.notes, "keep me")

    def test_delete_object(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.assertTrue(self.store.delete_object("a"))
        self.assertFalse(self.store.has_name("a"))
        self.assertFalse(self.store.delete_object("a"))

    def test_clear(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.put_version("b", 1, "h", b"1")
        self.store.clear()
        self.assertEqual(self.store.list_names(), [])

    def test_list_names_sorted(self) -> None:
        for n in ("c", "a", "b"):
            self.store.put_version(n, 1, "h", b"x")
        self.assertEqual(self.store.list_names(), ["a", "b", "c"])

    def test_set_metadata_with_unset_no_change(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.set_metadata("a", notes="initial")
        # Default sentinel must leave notes alone (this is the contract patch_object relies on).
        self.store.set_metadata("a", settings_merge={"x": "y"})
        rec = self.store.get_record("a")
        assert rec is not None
        self.assertEqual(rec.notes, "initial")
        self.assertEqual(rec.settings, {"x": "y"})

    def test_set_metadata_clear_notes(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.set_metadata("a", notes="some")
        self.store.set_metadata("a", notes=None)
        rec = self.store.get_record("a")
        assert rec is not None
        self.assertIsNone(rec.notes)

    def test_settings_merge_null_removes(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.set_metadata("a", settings_merge={"k1": "v1", "k2": "v2"})
        self.store.set_metadata("a", settings_merge={"k1": None})
        rec = self.store.get_record("a")
        assert rec is not None
        self.assertEqual(rec.settings, {"k2": "v2"})

    def test_rename_happy_path(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.set_metadata("a", notes="moved")
        self.store.rename("a", "b")
        self.assertFalse(self.store.has_name("a"))
        self.assertTrue(self.store.has_name("b"))
        rec = self.store.get_record("b")
        assert rec is not None
        self.assertEqual(rec.notes, "moved")

    def test_rename_conflict_raises(self) -> None:
        self.store.put_version("a", 1, "h", b"1")
        self.store.put_version("b", 1, "h", b"1")
        with self.assertRaises(ValueError):
            self.store.rename("a", "b")
        with self.assertRaises(KeyError):
            self.store.rename("missing", "newname")

    def test_get_record_returns_deepcopy(self) -> None:
        self.store.put_version("a", 1, "h", b"1", {"k": [1, 2, 3]})
        rec = self.store.get_record("a")
        assert rec is not None
        # Mutating the returned record must not affect store state.
        rec.versions[1].kwargs["k"].append(4)
        rec.notes = "tampered"
        rec2 = self.store.get_record("a")
        assert rec2 is not None
        self.assertEqual(rec2.versions[1].kwargs["k"], [1, 2, 3])
        self.assertIsNone(rec2.notes)


class TestUnsetSentinel(unittest.TestCase):
    def test_public_alias(self) -> None:
        # _UNSET is preserved as a private alias of the public UNSET.
        self.assertIs(UNSET, _UNSET)

    def test_distinct_from_none(self) -> None:
        self.assertIsNot(UNSET, None)


class TestValidateSettings(unittest.TestCase):
    def test_value_string(self) -> None:
        self.assertEqual(validate_settings_value("x"), "x")

    def test_value_number(self) -> None:
        self.assertEqual(validate_settings_value(3), 3)
        self.assertEqual(validate_settings_value(1.5), 1.5)

    def test_value_none_passthrough(self) -> None:
        self.assertIsNone(validate_settings_value(None))

    def test_value_bool_rejected(self) -> None:
        # bool subclasses int but is explicitly rejected.
        with self.assertRaises(ValueError):
            validate_settings_value(True)

    def test_value_other_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_settings_value([1, 2])
        with self.assertRaises(ValueError):
            validate_settings_value({"k": "v"})

    def test_map_validates_each(self) -> None:
        out = validate_settings_map({"a": "x", "b": 1, "c": None})
        self.assertEqual(out, {"a": "x", "b": 1, "c": None})
        with self.assertRaises(ValueError):
            validate_settings_map({"a": True})


class TestDescribeRecord(unittest.TestCase):
    def setUp(self) -> None:
        self.store = VersionedObjectStore()

    def test_describe_shape(self) -> None:
        self.store.put_version("a", 1, "h1", b"1")
        self.store.put_version("a", 2, "h2", b"2")
        self.store.set_metadata("a", notes="hello", settings_merge={"k": "v"})
        rec = self.store.get_record("a")
        assert rec is not None
        desc = describe_object_record("a", rec, in_memory=True, on_disk=False)
        # Required by docs/api.md.
        self.assertEqual(desc["name"], "a")
        self.assertEqual(desc["notes"], "hello")
        self.assertEqual(desc["settings"], {"k": "v"})
        self.assertEqual(desc["version"], 2)
        self.assertEqual(desc["hash"], "h2")
        self.assertTrue(desc["in_memory"])
        self.assertFalse(desc["on_disk"])
        self.assertEqual(desc["versions"], [
            {"version": 1, "hash": "h1", "created_at": rec.versions[1].created_at}
        ])

    def test_latest_version_info_empty(self) -> None:
        from cadquery_web_viewer.object_store import ObjectRecord

        self.assertIsNone(latest_version_info(ObjectRecord()))


if __name__ == "__main__":
    unittest.main()
