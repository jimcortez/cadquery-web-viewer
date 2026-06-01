"""Tests for cadquery_web_viewer.events_api."""

from __future__ import annotations

import json
import unittest

from cadquery_web_viewer.events_api import (
    KNOWN_TYPES,
    OBJECT_CREATED,
    OBJECT_REMOVED,
    OBJECT_VERSIONED,
    SCENE_CLEARED,
    SERVER_SHUTDOWN,
    event_to_json,
    validate_event,
)


class TestEventToJson(unittest.TestCase):
    def test_compact_separators(self) -> None:
        s = event_to_json({"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h"})
        # No spaces between keys/values — required by SSE framing assumptions.
        self.assertNotIn(", ", s)
        self.assertNotIn(": ", s)
        # Valid JSON round-trips.
        self.assertEqual(json.loads(s), {"type": "object.created", "name": "a", "version": 1, "hash": "h"})


class TestValidateEvent(unittest.TestCase):
    def test_unknown_type(self) -> None:
        with self.assertRaises(ValueError):
            validate_event({"type": "nope"})
        with self.assertRaises(ValueError):
            validate_event({})

    def test_non_dict_envelope(self) -> None:
        with self.assertRaises(ValueError):
            validate_event("not-a-dict")  # type: ignore[arg-type]

    def test_object_created_happy(self) -> None:
        validate_event({"type": OBJECT_CREATED, "name": "a", "version": 1, "hash": "h"})

    def test_object_versioned_happy(self) -> None:
        validate_event({"type": OBJECT_VERSIONED, "name": "a", "version": 7, "hash": "h"})

    def test_object_removed_happy(self) -> None:
        validate_event({"type": OBJECT_REMOVED, "name": "a", "hash": "h"})

    def test_object_event_missing_name(self) -> None:
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_CREATED, "version": 1, "hash": "h"})
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_CREATED, "name": "", "version": 1, "hash": "h"})

    def test_object_event_missing_hash(self) -> None:
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_REMOVED, "name": "a"})

    def test_created_versioned_require_version(self) -> None:
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_CREATED, "name": "a", "hash": "h"})
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_VERSIONED, "name": "a", "hash": "h", "version": 0})
        with self.assertRaises(ValueError):
            validate_event({"type": OBJECT_VERSIONED, "name": "a", "hash": "h", "version": "1"})

    def test_scene_cleared_happy(self) -> None:
        validate_event({"type": SCENE_CLEARED})
        validate_event({"type": SCENE_CLEARED, "except_names": ["a", "b"]})

    def test_scene_cleared_bad_except_names(self) -> None:
        with self.assertRaises(ValueError):
            validate_event({"type": SCENE_CLEARED, "except_names": "a,b"})  # not a list
        with self.assertRaises(ValueError):
            validate_event({"type": SCENE_CLEARED, "except_names": [1, 2]})  # not strings

    def test_server_shutdown(self) -> None:
        validate_event({"type": SERVER_SHUTDOWN})

    def test_known_types_set(self) -> None:
        self.assertEqual(
            KNOWN_TYPES,
            frozenset(
                {
                    OBJECT_CREATED,
                    OBJECT_VERSIONED,
                    OBJECT_REMOVED,
                    SCENE_CLEARED,
                    SERVER_SHUTDOWN,
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
