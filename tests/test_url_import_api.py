"""Tests for PUT /api/object JSON url import."""

from __future__ import annotations

import json
import struct
import unittest
from unittest.mock import patch

from cadquery_web_viewer.app import create_app
from cadquery_web_viewer.url_import import content_hash_from_bytes

MIN_GLB = b"glTF" + struct.pack("<II", 2, 12)


class TestUrlImportApi(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(cache_mode="memory")
        self.client = self.app.test_client()

    @patch("cadquery_web_viewer.app.fetch_glb_bytes", return_value=MIN_GLB)
    def test_put_json_url_stores_object(self, _fetch: object) -> None:
        url = "https://example.com/sphere.glb"
        response = self.client.put(
            "/api/object/test_import",
            data=json.dumps({"url": url}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        assert body is not None
        self.assertEqual(body["name"], "test_import")
        self.assertEqual(body["version"], 1)
        expected_hash = content_hash_from_bytes(MIN_GLB)
        self.assertEqual(body["hash"], expected_hash)

        list_resp = self.client.get("/api/object")
        self.assertEqual(list_resp.status_code, 200)
        objects = list_resp.get_json()["objects"]
        names = [o["name"] for o in objects]
        self.assertIn("test_import", names)

    @patch("cadquery_web_viewer.app.fetch_glb_bytes", return_value=MIN_GLB)
    def test_put_json_url_increments_version(self, _fetch: object) -> None:
        payload = json.dumps({"url": "https://example.com/a.glb"})
        self.client.put("/api/object/vtest", data=payload, content_type="application/json")
        response = self.client.put("/api/object/vtest", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["version"], 2)

    def test_put_json_missing_url(self) -> None:
        response = self.client.put(
            "/api/object/bad",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
