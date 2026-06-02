"""Flask integration tests for /api/object PUT/PATCH/DELETE/GET routes."""

from __future__ import annotations

import io
import json
import struct
import unittest

from cadquery_web_viewer.app import create_app

# Smallest valid GLB binary header (12-byte container with magic, version, length).
MIN_GLB = b"glTF" + struct.pack("<II", 2, 12)


def _glb_with_marker(marker: int) -> bytes:
    # 16-byte body with a varying marker so different versions have different bytes.
    body = struct.pack("<II", marker, marker + 1)
    return b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body


class _AppTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(cache_mode="memory")
        self.client = self.app.test_client()


class TestPutMultipart(_AppTestBase):
    def test_multipart_upload(self) -> None:
        meta = json.dumps({"hash": "h-1", "kwargs": {"k": "v"}})
        resp = self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        assert body is not None
        self.assertEqual(body["name"], "box")
        self.assertEqual(body["version"], 1)
        self.assertEqual(body["hash"], "h-1")
        self.assertEqual(resp.headers["X-Object-Version"], "1")

    def test_multipart_missing_metadata(self) -> None:
        resp = self.client.put(
            "/api/object/box",
            data={"glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary")},
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)

    def test_multipart_metadata_missing_hash(self) -> None:
        resp = self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": json.dumps({}),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)

    def test_multipart_invalid_metadata_json(self) -> None:
        resp = self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": "{not json",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)


class TestPutForceVersion(_AppTestBase):
    def test_force_version(self) -> None:
        meta = json.dumps({"hash": "h-7"})
        resp = self.client.put(
            "/api/object/box?force-version=7",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["version"], 7)

    def test_force_version_invalid(self) -> None:
        meta = json.dumps({"hash": "h"})
        resp = self.client.put(
            "/api/object/box?force-version=zero",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resp.status_code, 400)


class TestGetObject(_AppTestBase):
    def setUp(self) -> None:
        super().setUp()
        meta = json.dumps({"hash": "h-1"})
        self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )

    def test_get_glb_default_accept(self) -> None:
        resp = self.client.get("/api/object/box")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "model/gltf-binary")
        self.assertEqual(resp.data, MIN_GLB)
        self.assertTrue(resp.headers["E-Tag"].startswith('"h-1-v1"'))

    def test_get_descriptor_via_accept_json(self) -> None:
        resp = self.client.get("/api/object/box", headers={"Accept": "application/json"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["name"], "box")
        self.assertEqual(body["version"], 1)
        self.assertEqual(body["hash"], "h-1")

    def test_get_unknown_404(self) -> None:
        resp = self.client.get("/api/object/missing")
        self.assertEqual(resp.status_code, 404)

    def test_list_objects(self) -> None:
        resp = self.client.get("/api/object")
        self.assertEqual(resp.status_code, 200)
        names = [o["name"] for o in resp.get_json()["objects"]]
        self.assertIn("box", names)


class TestPatch(_AppTestBase):
    def setUp(self) -> None:
        super().setUp()
        meta = json.dumps({"hash": "h-1"})
        self.client.put(
            "/api/object/orig",
            data={
                "glb": (io.BytesIO(MIN_GLB), "orig.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )

    def test_rename(self) -> None:
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"name": "renamed"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["name"], "renamed")
        self.assertEqual(self.client.get("/api/object/orig").status_code, 404)
        self.assertEqual(self.client.get("/api/object/renamed").status_code, 200)

    def test_set_notes(self) -> None:
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"notes": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["notes"], "hello")

    def test_clear_notes_with_null(self) -> None:
        self.client.patch(
            "/api/object/orig",
            data=json.dumps({"notes": "hello"}),
            content_type="application/json",
        )
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"notes": None}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.get_json()["notes"])

    def test_set_settings(self) -> None:
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"settings": {"opacity": 0.5, "label": "thing"}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["settings"], {"opacity": 0.5, "label": "thing"})

    def test_settings_remove_key(self) -> None:
        self.client.patch(
            "/api/object/orig",
            data=json.dumps({"settings": {"a": "x", "b": "y"}}),
            content_type="application/json",
        )
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"settings": {"a": None}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["settings"], {"b": "y"})

    def test_settings_invalid_value_type(self) -> None:
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"settings": {"a": True}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_rename_conflict_409(self) -> None:
        meta = json.dumps({"hash": "h"})
        self.client.put(
            "/api/object/already-there",
            data={
                "glb": (io.BytesIO(MIN_GLB), "x.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({"name": "already-there"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_patch_missing_object_404(self) -> None:
        resp = self.client.patch(
            "/api/object/no-such",
            data=json.dumps({"notes": "x"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_patch_empty_body_400(self) -> None:
        resp = self.client.patch(
            "/api/object/orig",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class TestDelete(_AppTestBase):
    def setUp(self) -> None:
        super().setUp()
        for v in (1, 2):
            meta = json.dumps({"hash": f"h-{v}"})
            self.client.put(
                f"/api/object/box?force-version={v}",
                data={
                    "glb": (io.BytesIO(_glb_with_marker(v)), "box.glb", "model/gltf-binary"),
                    "metadata": meta,
                },
                content_type="multipart/form-data",
            )

    def test_delete_single_version(self) -> None:
        resp = self.client.delete("/api/object/box?force-version=1")
        self.assertEqual(resp.status_code, 204)
        # Other versions remain.
        resp_get = self.client.get("/api/object/box?version=2")
        self.assertEqual(resp_get.status_code, 200)

    def test_delete_unknown_version_404(self) -> None:
        resp = self.client.delete("/api/object/box?force-version=99")
        self.assertEqual(resp.status_code, 404)

    def test_delete_all_versions(self) -> None:
        resp = self.client.delete("/api/object/box")
        self.assertEqual(resp.status_code, 204)
        resp_get = self.client.get("/api/object/box")
        self.assertEqual(resp_get.status_code, 404)

    def test_delete_unknown_object_404(self) -> None:
        resp = self.client.delete("/api/object/no-such")
        self.assertEqual(resp.status_code, 404)

    def test_delete_all_objects(self) -> None:
        resp = self.client.delete("/api/object")
        self.assertEqual(resp.status_code, 204)
        objects = self.client.get("/api/object").get_json()["objects"]
        self.assertEqual(objects, [])


class TestEventsEndpoint(_AppTestBase):
    def setUp(self) -> None:
        super().setUp()
        meta = json.dumps({"hash": "h-1"})
        self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )

    def test_object_created_409_when_already_in_scene(self) -> None:
        # First publish — not yet in scene, succeeds.
        ok = self.client.post(
            "/api/events",
            data=json.dumps({"type": "object.created", "name": "box", "version": 1, "hash": "h-1"}),
            content_type="application/json",
        )
        self.assertEqual(ok.status_code, 204)
        # Second publish of object.created for the same name — 409.
        dup = self.client.post(
            "/api/events",
            data=json.dumps({"type": "object.created", "name": "box", "version": 1, "hash": "h-1"}),
            content_type="application/json",
        )
        self.assertEqual(dup.status_code, 409)

    def test_object_versioned_409_when_not_in_scene(self) -> None:
        resp = self.client.post(
            "/api/events",
            data=json.dumps({"type": "object.versioned", "name": "box", "version": 1, "hash": "h-1"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_invalid_event_400(self) -> None:
        resp = self.client.post(
            "/api/events",
            data=json.dumps({"type": "totally-made-up"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_batch_events(self) -> None:
        # Set up two objects so we can publish multiple created events in one batch.
        meta = json.dumps({"hash": "h-2"})
        self.client.put(
            "/api/object/sphere",
            data={
                "glb": (io.BytesIO(_glb_with_marker(2)), "s.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        resp = self.client.post(
            "/api/events",
            data=json.dumps({
                "events": [
                    {"type": "object.created", "name": "box", "version": 1, "hash": "h-1"},
                    {"type": "object.created", "name": "sphere", "version": 1, "hash": "h-2"},
                ]
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 204)
        scene = self.client.get("/api/scene").get_json()
        self.assertEqual(sorted(scene["names"]), ["box", "sphere"])

    def test_events_get_options_204(self) -> None:
        resp = self.client.options("/api/events")
        self.assertEqual(resp.status_code, 204)


class TestCors(_AppTestBase):
    def test_options_cors_204(self) -> None:
        resp = self.client.options("/api/object")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_get_includes_cors_header(self) -> None:
        resp = self.client.get("/api/object")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")


if __name__ == "__main__":
    unittest.main()
