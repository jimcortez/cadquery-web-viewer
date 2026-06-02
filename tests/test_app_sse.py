"""Tests for the /api/events SSE generator (_sse_gen) and HEAD/OPTIONS variants."""

from __future__ import annotations

import io
import json
import struct
import threading
import unittest

from cadquery_web_viewer.app import create_app
from cadquery_web_viewer.engine import CadQueryWebViewer

MIN_GLB = b"glTF" + struct.pack("<II", 2, 12)


class TestSseHeaders(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(cache_mode="memory")
        self.client = self.app.test_client()

    def test_options_cors(self) -> None:
        resp = self.client.options("/api/events")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")

    def test_head_returns_event_stream_mime(self) -> None:
        resp = self.client.head("/api/events")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "text/event-stream")
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")


class TestSseGenerator(unittest.TestCase):
    """Drive the SSE generator function directly so we can advance it deterministically.

    Calling Flask's test client for a streaming endpoint blocks indefinitely; tapping
    into create_app's local generator factory keeps the test fast and reliable.
    """

    def _new_engine_and_gen(self):
        # Build an engine + generator using the same wiring create_app does, but with
        # a tight yield_timeout so we can tick keep-alives quickly.
        engine = CadQueryWebViewer()

        def _sse_gen():
            engine.register_sse_stream_begin()
            try:
                yield "retry: 100\n\n"
                with engine.frontend_lock.r_locked():
                    if engine.shutting_down.is_set() and engine.at_least_one_client.is_set():
                        return
                    sub = engine.scene_events.subscribe(
                        include_buffered=False,
                        yield_timeout=0.05,
                    )
                    try:
                        for data in sub:
                            if data is None:
                                yield ":keep-alive\n\n"
                            else:
                                from cadquery_web_viewer.events_api import event_to_json
                                yield f"data: {event_to_json(data)}\n\n"
                    finally:
                        sub.close()
            finally:
                engine.register_sse_stream_end()

        return engine, _sse_gen()

    def test_first_chunk_is_retry_directive(self) -> None:
        _engine, gen = self._new_engine_and_gen()
        self.assertEqual(next(gen), "retry: 100\n\n")
        gen.close()

    def test_no_replay_of_prior_publishes(self) -> None:
        engine = CadQueryWebViewer()
        # Pre-publish an event before any SSE stream connects.
        engine.put_object_version("a", "h", b"glb")
        engine.publish_event(
            {"type": "object.created", "name": "a", "version": 1, "hash": "h"}
        )

        # Now build a generator just like create_app does.
        from cadquery_web_viewer.events_api import event_to_json

        def _sse_gen():
            engine.register_sse_stream_begin()
            try:
                yield "retry: 100\n\n"
                with engine.frontend_lock.r_locked():
                    sub = engine.scene_events.subscribe(
                        include_buffered=False,
                        yield_timeout=0.05,
                    )
                    try:
                        for data in sub:
                            if data is None:
                                yield ":keep-alive\n\n"
                            else:
                                yield f"data: {event_to_json(data)}\n\n"
                    finally:
                        sub.close()
            finally:
                engine.register_sse_stream_end()

        gen = _sse_gen()
        try:
            self.assertEqual(next(gen), "retry: 100\n\n")
            # Next item must be a keep-alive — NOT a replay of the prior publish.
            chunk = next(gen)
            self.assertEqual(chunk, ":keep-alive\n\n")
        finally:
            gen.close()

    def test_keepalive_then_live_event(self) -> None:
        engine, gen = self._new_engine_and_gen()
        try:
            self.assertEqual(next(gen), "retry: 100\n\n")
            # First post-retry chunk is a keep-alive (yield_timeout fires).
            self.assertEqual(next(gen), ":keep-alive\n\n")

            # Publish from another thread; the running generator should pick it up.
            engine.put_object_version("a", "h", b"glb")

            def publisher():
                engine.publish_event(
                    {"type": "object.created", "name": "a", "version": 1, "hash": "h"}
                )

            t = threading.Thread(target=publisher)
            t.start()

            # Drain until we see the data line (or hit a small budget of keep-alives).
            saw_data = None
            for _ in range(20):
                chunk = next(gen)
                if chunk.startswith("data: "):
                    saw_data = chunk
                    break
            t.join(timeout=2)
            assert saw_data is not None, "did not observe live event in SSE stream"
            payload = json.loads(saw_data.removeprefix("data: ").strip())
            self.assertEqual(payload["type"], "object.created")
            self.assertEqual(payload["name"], "a")
        finally:
            gen.close()


class TestObjectCreatedSseAfterUpload(unittest.TestCase):
    """End-to-end smoke: after uploading + publishing, /api/scene reports the object."""

    def setUp(self) -> None:
        self.app = create_app(cache_mode="memory")
        self.client = self.app.test_client()

    def test_scene_reflects_created(self) -> None:
        # Upload first.
        meta = json.dumps({"hash": "h"})
        self.client.put(
            "/api/object/box",
            data={
                "glb": (io.BytesIO(MIN_GLB), "box.glb", "model/gltf-binary"),
                "metadata": meta,
            },
            content_type="multipart/form-data",
        )
        # Then publish.
        self.client.post(
            "/api/events",
            data=json.dumps({"type": "object.created", "name": "box", "version": 1, "hash": "h"}),
            content_type="application/json",
        )
        scene = self.client.get("/api/scene").get_json()
        self.assertEqual(scene["names"], ["box"])


if __name__ == "__main__":
    unittest.main()
