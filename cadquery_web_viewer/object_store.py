"""In-memory versioned object store with notes and settings."""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from typing import Any

from cadquery_web_viewer.glb_cache import utc_now_iso

SettingsValue = str | int | float | None

# Public sentinel for "do not change". Use ``UNSET`` from outside this module;
# ``_UNSET`` is kept as a backwards-compatible alias for code in the wild.
UNSET: object = object()
_UNSET = UNSET


@dataclass
class StoredVersion:
    glb: bytes
    hash: str
    kwargs: dict[str, Any]
    created_at: str


@dataclass
class ObjectRecord:
    notes: str | None = None
    settings: dict[str, SettingsValue] = field(default_factory=dict)
    versions: dict[int, StoredVersion] = field(default_factory=dict)


class VersionedObjectStore:
    def __init__(self) -> None:
        self._objects: dict[str, ObjectRecord] = {}
        self._lock = threading.Lock()

    def has_name(self, name: str) -> bool:
        with self._lock:
            return name in self._objects and len(self._objects[name].versions) > 0

    def put_version(
        self,
        name: str,
        version: int,
        content_hash: str,
        glb: bytes,
        kwargs: dict[str, Any] | None = None,
        *,
        created_at: str | None = None,
    ) -> str:
        kwargs = kwargs or {}
        created_at = created_at or utc_now_iso()
        with self._lock:
            rec = self._objects.setdefault(name, ObjectRecord())
            rec.versions[version] = StoredVersion(
                glb=glb,
                hash=content_hash,
                kwargs=dict(kwargs),
                created_at=created_at,
            )
        return created_at

    def next_version(self, name: str) -> int:
        with self._lock:
            rec = self._objects.get(name)
            if not rec or not rec.versions:
                return 1
            return max(rec.versions) + 1

    def get_version(self, name: str, version: int | None = None) -> StoredVersion | None:
        with self._lock:
            rec = self._objects.get(name)
            if not rec or not rec.versions:
                return None
            if version is None:
                version = max(rec.versions)
            return rec.versions.get(version)

    def delete_version(self, name: str, version: int) -> bool:
        with self._lock:
            rec = self._objects.get(name)
            if not rec or version not in rec.versions:
                return False
            del rec.versions[version]
            if not rec.versions and rec.notes is None and not rec.settings:
                del self._objects[name]
            return True

    def delete_object(self, name: str) -> bool:
        with self._lock:
            if name not in self._objects:
                return False
            del self._objects[name]
            return True

    def clear(self) -> None:
        with self._lock:
            self._objects.clear()

    def list_names(self) -> list[str]:
        with self._lock:
            return sorted(self._objects.keys())

    def get_record(self, name: str) -> ObjectRecord | None:
        with self._lock:
            rec = self._objects.get(name)
            return copy.deepcopy(rec) if rec else None

    def set_metadata(
        self,
        name: str,
        *,
        notes: str | None | object = _UNSET,
        settings_merge: dict[str, SettingsValue] | None = None,
    ) -> None:
        with self._lock:
            rec = self._objects.setdefault(name, ObjectRecord())
            if notes is not _UNSET:
                rec.notes = notes  # type: ignore[assignment]
            if settings_merge is not None:
                for k, v in settings_merge.items():
                    if v is None:
                        rec.settings.pop(k, None)
                    else:
                        rec.settings[k] = v

    def rename(self, old_name: str, new_name: str) -> None:
        with self._lock:
            if old_name not in self._objects:
                raise KeyError(old_name)
            if new_name in self._objects:
                raise ValueError(f"Object {new_name!r} already exists")
            self._objects[new_name] = self._objects.pop(old_name)

    def ensure_object(self, name: str) -> None:
        with self._lock:
            self._objects.setdefault(name, ObjectRecord())


def validate_settings_value(v: Any) -> SettingsValue:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        raise ValueError("boolean settings values are not allowed")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    raise ValueError(f"invalid settings value type: {type(v).__name__}")


def validate_settings_map(settings: dict[str, Any]) -> dict[str, SettingsValue]:
    return {k: validate_settings_value(v) for k, v in settings.items()}


def latest_version_info(rec: ObjectRecord) -> tuple[int, StoredVersion] | None:
    if not rec.versions:
        return None
    v = max(rec.versions)
    return v, rec.versions[v]


def describe_object_record(name: str, rec: ObjectRecord, *, in_memory: bool, on_disk: bool) -> dict[str, Any]:
    latest = latest_version_info(rec)
    if latest is None:
        raise ValueError(f"object {name!r} has no versions")
    ver, sv = latest
    other_versions = sorted(
        (
            {"version": v, "hash": rec.versions[v].hash, "created_at": rec.versions[v].created_at}
            for v in rec.versions
            if v != ver
        ),
        key=lambda x: x["version"],
        reverse=True,
    )
    return {
        "name": name,
        "notes": rec.notes,
        "settings": dict(rec.settings),
        "version": ver,
        "hash": sv.hash,
        "kwargs": dict(sv.kwargs),
        "created_at": sv.created_at,
        "in_memory": in_memory,
        "on_disk": on_disk,
        "versions": other_versions,
    }
