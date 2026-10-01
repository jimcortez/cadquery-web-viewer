"""Tests for cadquery_web_viewer.http_client publish helpers (HTTP calls patched out)."""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from build123d import Box
from cadquery_web_viewer import http_client
from cadquery_web_viewer.assembly import KWARGS_ASSEMBLY_KEY
from cadquery_web_viewer.events_api import OBJECT_CREATED, OBJECT_VERSIONED, SCENE_CLEARED


class _Recorder:
    def __init__(self, scene: set[str] | None = None) -> None:
        self.puts: list[tuple[str, dict[str, Any], bytes]] = []
        self.events: list[list[dict[str, Any]]] = []
        self.scene = scene or set()

    def put(self, host, port, name, metadata, glb, timeout):
        self.puts.append((name, metadata, glb))
        return {"name": name, "version": len([p for p in self.puts if p[0] == name]), "hash": metadata["hash"]}

    def publish(self, host, port, events, timeout):
        self.events.append(events)

    def scene_names(self, host, port, timeout):
        return set(self.scene)


class _PatchedBase(unittest.TestCase):
    def setUp(self) -> None:
        self.rec = _Recorder()
        for target, fn in (
            ("_put_object", self.rec.put),
            ("_publish_events", self.rec.publish),
            ("_scene_names", self.rec.scene_names),
        ):
            patcher = mock.patch.object(http_client, target, side_effect=fn)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestRemoteShowAssembly(_PatchedBase):
    def test_one_put_with_manifest_and_created_event(self) -> None:
        http_client.remote_show_assembly([("a", Box(1, 1, 1)), ("b", Box(2, 2, 2))], "pair")
        self.assertEqual(len(self.rec.puts), 1)
        name, meta, glb = self.rec.puts[0]
        self.assertEqual(name, "pair")
        self.assertTrue(glb.startswith(b"glTF"))
        self.assertEqual([p["name"] for p in meta["kwargs"][KWARGS_ASSEMBLY_KEY]["parts"]], ["a", "b"])
        (events,) = self.rec.events
        self.assertEqual([e["type"] for e in events], [SCENE_CLEARED, OBJECT_CREATED])
        self.assertEqual(events[0]["except_names"], ["pair"])
        self.assertEqual(events[1]["name"], "pair")
        self.assertEqual(events[1]["hash"], meta["hash"])

    def test_versioned_when_already_in_scene(self) -> None:
        self.rec.scene.add("pair")
        http_client.remote_show_assembly([("a", Box(1, 1, 1))], "pair", auto_clear=False)
        (events,) = self.rec.events
        self.assertEqual([e["type"] for e in events], [OBJECT_VERSIONED])


class TestRemoteShowGlb(_PatchedBase):
    def test_uses_provided_hash_and_kwargs(self) -> None:
        manifest = {"schema": 1, "name": "x", "tags": [], "parts": []}
        http_client.remote_show_glb(
            "x", b"glTF-bytes", content_hash="abc", kwargs={KWARGS_ASSEMBLY_KEY: manifest}
        )
        name, meta, glb = self.rec.puts[0]
        self.assertEqual((name, glb, meta["hash"]), ("x", b"glTF-bytes", "abc"))
        self.assertEqual(meta["kwargs"][KWARGS_ASSEMBLY_KEY], manifest)

    def test_hash_defaults_to_content_hash(self) -> None:
        http_client.remote_show_glb("x", b"glTF-bytes")
        http_client.remote_show_glb("x", b"glTF-bytes")
        self.assertEqual(self.rec.puts[0][1]["hash"], self.rec.puts[1][1]["hash"])
        self.assertTrue(self.rec.puts[0][1]["hash"])


if __name__ == "__main__":
    unittest.main()
