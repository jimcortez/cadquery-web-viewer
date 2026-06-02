"""Tests for cadquery_web_viewer.pubsub.BufferedPubSub."""

from __future__ import annotations

import threading
import time
import unittest

from cadquery_web_viewer.pubsub import BufferedPubSub


class TestPubSub(unittest.TestCase):
    def test_publish_and_buffer(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        ps.publish(1)
        ps.publish(2)
        self.assertEqual(ps.buffer(), [1, 2])

    def test_max_buffer_size_drops_oldest(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub(max_buffer_size=2)
        ps.publish(1)
        ps.publish(2)
        ps.publish(3)
        self.assertEqual(ps.buffer(), [2, 3])

    def test_subscribe_includes_buffered_history(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        ps.publish(10)
        ps.publish(20)
        gen = ps.subscribe(include_buffered=True, include_future=False)
        out = list(gen)
        self.assertEqual(out, [10, 20])

    def test_subscribe_live_only_skips_history(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        ps.publish(10)  # buffered before subscription

        # Open a generator; it must not yield the pre-existing buffered events.
        # yield_timeout makes get_next return None when there's nothing pending.
        gen = ps.subscribe(include_buffered=False, yield_timeout=0.05)
        try:
            # First yield is None (timeout) because no live event has arrived yet.
            self.assertIsNone(next(gen))
            # Now publish and the next non-None should be the live value.
            ps.publish(99)
            seen = []
            for _ in range(5):
                v = next(gen)
                if v is not None:
                    seen.append(v)
                    break
            self.assertEqual(seen, [99])
        finally:
            gen.close()

    def test_yield_timeout_emits_none_for_keepalive(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        gen = ps.subscribe(include_buffered=False, yield_timeout=0.01)
        try:
            v = next(gen)
            self.assertIsNone(v)
        finally:
            gen.close()

    def test_close_unsubscribes(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        gen = ps.subscribe(include_buffered=False, yield_timeout=0.01)
        # Trigger __next__ once so the generator is running and gets registered.
        next(gen)
        # Closing the generator should drop the subscriber on the publisher's side.
        gen.close()
        self.assertEqual(len(ps._subscribers), 0)

    def test_publish_to_multiple_subscribers(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        gen_a = ps.subscribe(include_buffered=False, yield_timeout=0.05)
        gen_b = ps.subscribe(include_buffered=False, yield_timeout=0.05)
        try:
            # Drain initial timeouts on both.
            next(gen_a)
            next(gen_b)

            received_a: list[int] = []
            received_b: list[int] = []

            def drain(gen, into: list[int]) -> None:
                for _ in range(10):
                    v = next(gen)
                    if v is not None:
                        into.append(v)
                    if len(into) >= 1:
                        return

            t_a = threading.Thread(target=drain, args=(gen_a, received_a))
            t_b = threading.Thread(target=drain, args=(gen_b, received_b))
            t_a.start()
            t_b.start()
            time.sleep(0.01)
            ps.publish(42)
            t_a.join(timeout=2)
            t_b.join(timeout=2)

            self.assertEqual(received_a, [42])
            self.assertEqual(received_b, [42])
        finally:
            gen_a.close()
            gen_b.close()

    def test_prune_buffer(self) -> None:
        ps: BufferedPubSub[dict] = BufferedPubSub()
        ps.publish({"type": "a", "n": 1})
        ps.publish({"type": "b", "n": 2})
        ps.publish({"type": "a", "n": 3})
        ps.prune_buffer(lambda e: e["type"] == "a")
        self.assertEqual(ps.buffer(), [{"type": "b", "n": 2}])

    def test_clear(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        ps.publish(1)
        ps.publish(2)
        ps.clear()
        self.assertEqual(ps.buffer(), [])

    def test_delete(self) -> None:
        ps: BufferedPubSub[int] = BufferedPubSub()
        ps.publish(1)
        ps.publish(2)
        ps.delete(1)
        self.assertEqual(ps.buffer(), [2])


if __name__ == "__main__":
    unittest.main()
