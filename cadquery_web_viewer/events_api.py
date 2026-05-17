"""Scene event envelopes for ``/api/events``."""

from __future__ import annotations

import json
from typing import Any

OBJECT_CREATED = "object.created"
OBJECT_VERSIONED = "object.versioned"
OBJECT_REMOVED = "object.removed"
SCENE_CLEARED = "scene.cleared"
SERVER_SHUTDOWN = "server.shutdown"

KNOWN_TYPES = frozenset(
    {
        OBJECT_CREATED,
        OBJECT_VERSIONED,
        OBJECT_REMOVED,
        SCENE_CLEARED,
        SERVER_SHUTDOWN,
    }
)


def event_to_json(envelope: dict[str, Any]) -> str:
    return json.dumps(envelope, separators=(",", ":"))


def validate_event(envelope: dict[str, Any]) -> None:
    if not isinstance(envelope, dict):
        raise ValueError("event must be a JSON object")
    t = envelope.get("type")
    if t not in KNOWN_TYPES:
        raise ValueError(f"unknown event type: {t!r}")
    if t in (OBJECT_CREATED, OBJECT_VERSIONED, OBJECT_REMOVED):
        if not isinstance(envelope.get("name"), str) or not envelope["name"]:
            raise ValueError("object events require non-empty name")
        if not isinstance(envelope.get("hash"), str):
            raise ValueError("object events require hash")
    if t in (OBJECT_CREATED, OBJECT_VERSIONED):
        v = envelope.get("version")
        if not isinstance(v, int) or v < 1:
            raise ValueError("object.created/object.versioned require version >= 1")
    if t == SCENE_CLEARED:
        ex = envelope.get("except_names")
        if ex is not None and not (
            isinstance(ex, list) and all(isinstance(x, str) for x in ex)
        ):
            raise ValueError("except_names must be a list of strings")
