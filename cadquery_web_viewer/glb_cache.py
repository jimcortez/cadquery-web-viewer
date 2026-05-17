"""On-disk persistence for versioned GLB payloads, version sidecars, and object manifests."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
VERSION_META_SUFFIX = ".meta.json"
GLB_SUFFIX = ".glb"
OBJECT_MANIFEST_SUFFIX = ".object.json"


def utc_now_iso() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def entry_id_for_version(name: str, version: int) -> str:
    return hashlib.sha256(f"{name}\0{version}".encode("utf-8")).hexdigest()


def object_id_for_name(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


@dataclass
class DiskVersionEntry:
    name: str
    version: int
    content_hash: str
    kwargs: dict[str, Any]
    created_at: str
    glb_path: str


@dataclass
class DiskObjectManifest:
    name: str
    notes: str | None
    settings: dict[str, Any]


class GlbDiskCache:
    """Versioned GLB files plus per-name object manifests under a cache directory."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self._lock = threading.RLock()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _version_paths(self, name: str, version: int) -> tuple[Path, Path]:
        eid = entry_id_for_version(name, version)
        base = self.cache_dir / eid
        return base.with_suffix(GLB_SUFFIX), base.with_suffix(VERSION_META_SUFFIX)

    def _manifest_path(self, name: str) -> Path:
        return self.cache_dir / (object_id_for_name(name) + OBJECT_MANIFEST_SUFFIX)

    def write_version(
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
        glb_path, meta_path = self._version_paths(name, version)
        meta = {
            "schema": SCHEMA_VERSION,
            "name": name,
            "version": version,
            "hash": content_hash,
            "kwargs": _json_safe_kwargs(kwargs),
            "created_at": created_at,
        }
        meta_bytes = json.dumps(meta, separators=(",", ":"), sort_keys=True).encode("utf-8")
        cache_dir_str = str(self.cache_dir)
        with self._lock:
            self._atomic_write(glb_path, glb, suffix=".glb.tmp", dir=cache_dir_str)
            self._atomic_write(meta_path, meta_bytes, suffix=".meta.json.tmp", dir=cache_dir_str)
        return created_at

    def _atomic_write(self, dest: Path, data: bytes, *, suffix: str, dir: str) -> None:
        fd, tmp = tempfile.mkstemp(suffix=suffix, dir=dir)
        os.close(fd)
        tmp_path = Path(tmp)
        try:
            tmp_path.write_bytes(data)
            os.replace(tmp, dest)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def read_object_manifest(self, name: str) -> DiskObjectManifest | None:
        path = self._manifest_path(name)
        if not path.is_file():
            return None
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            if meta.get("schema") != SCHEMA_VERSION:
                return None
            return DiskObjectManifest(
                name=meta["name"],
                notes=meta.get("notes"),
                settings=meta.get("settings") or {},
            )
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning("Invalid object manifest %s: %s", path, e)
            return None

    def write_object_manifest(
        self,
        name: str,
        *,
        notes: str | None,
        settings: dict[str, Any],
    ) -> None:
        path = self._manifest_path(name)
        meta = {
            "schema": SCHEMA_VERSION,
            "name": name,
            "notes": notes,
            "settings": settings,
        }
        meta_bytes = json.dumps(meta, separators=(",", ":"), sort_keys=True).encode("utf-8")
        with self._lock:
            self._atomic_write(path, meta_bytes, suffix=".object.json.tmp", dir=str(self.cache_dir))

    def delete_version(self, name: str, version: int) -> None:
        glb_path, meta_path = self._version_paths(name, version)
        with self._lock:
            for p in (glb_path, meta_path):
                try:
                    if p.is_file():
                        p.unlink()
                except OSError as e:
                    logger.warning("Could not delete cache file %s: %s", p, e)

    def delete_object(self, name: str) -> None:
        with self._lock:
            manifest = self._manifest_path(name)
            if manifest.is_file():
                try:
                    manifest.unlink()
                except OSError as e:
                    logger.warning("Could not delete manifest %s: %s", manifest, e)
            for entry in self.list_version_entries():
                if entry.name == name:
                    self.delete_version(name, entry.version)

    def clear(self) -> None:
        with self._lock:
            if not self.cache_dir.is_dir():
                return
            for p in self.cache_dir.iterdir():
                if p.suffix == GLB_SUFFIX or p.name.endswith(
                    (VERSION_META_SUFFIX, OBJECT_MANIFEST_SUFFIX)
                ):
                    try:
                        p.unlink()
                    except OSError as e:
                        logger.warning("Could not delete %s: %s", p, e)

    def list_version_entries(self) -> list[DiskVersionEntry]:
        entries: list[DiskVersionEntry] = []
        if not self.cache_dir.is_dir():
            return entries
        for meta_path in self.cache_dir.iterdir():
            if not meta_path.name.endswith(VERSION_META_SUFFIX):
                continue
            base = meta_path.name[: -len(VERSION_META_SUFFIX)]
            glb_path = self.cache_dir / (base + GLB_SUFFIX)
            if not glb_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("schema") != SCHEMA_VERSION:
                    logger.warning("Skipping unknown cache schema in %s", meta_path)
                    continue
                if "version" not in meta:
                    logger.warning("Skipping non-versioned cache entry %s", meta_path)
                    continue
                entries.append(
                    DiskVersionEntry(
                        name=meta["name"],
                        version=int(meta["version"]),
                        content_hash=meta["hash"],
                        kwargs=meta.get("kwargs") or {},
                        created_at=meta["created_at"],
                        glb_path=str(glb_path),
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError) as e:
                logger.warning("Invalid cache entry %s: %s", meta_path, e)
        return entries

    def read_glb(self, name: str, version: int) -> bytes | None:
        glb_path, _ = self._version_paths(name, version)
        try:
            return glb_path.read_bytes()
        except OSError:
            return None

    def rename_object(self, old_name: str, new_name: str) -> None:
        with self._lock:
            versions = [e for e in self.list_version_entries() if e.name == old_name]
            manifest = self.read_object_manifest(old_name)
            for e in versions:
                glb = Path(e.glb_path).read_bytes()
                self.delete_version(old_name, e.version)
                self.write_version(
                    new_name,
                    e.version,
                    e.content_hash,
                    glb,
                    e.kwargs,
                    created_at=e.created_at,
                )
            old_manifest = self._manifest_path(old_name)
            if old_manifest.is_file():
                old_manifest.unlink(missing_ok=True)
            if manifest is not None:
                self.write_object_manifest(new_name, notes=manifest.notes, settings=manifest.settings)
            elif versions:
                self.write_object_manifest(new_name, notes=None, settings={})


def _json_safe_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for k, v in kwargs.items():
        if k == "texture" and v is not None:
            continue
        try:
            json.dumps(v)
            safe[k] = v
        except TypeError:
            continue
    return safe
