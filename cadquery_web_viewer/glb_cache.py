"""Optional on-disk persistence for uploaded GLB payloads and metadata."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cadquery_web_viewer.mylogger import logger

SCHEMA_VERSION = 1
META_SUFFIX = ".meta.json"
GLB_SUFFIX = ".glb"


def entry_id_for_name(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


@dataclass
class DiskCacheEntry:
    name: str
    content_hash: str
    kwargs: dict[str, Any]
    glb_path: str
    mtime: float


class GlbDiskCache:
    """Stores one GLB + JSON sidecar per object name under a fixed directory."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self._lock = threading.Lock()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, name: str) -> tuple[Path, Path]:
        eid = entry_id_for_name(name)
        base = self.cache_dir / eid
        return base.with_suffix(GLB_SUFFIX), base.with_suffix(META_SUFFIX)

    def write(self, name: str, content_hash: str, glb: bytes, kwargs: dict[str, Any] | None = None) -> None:
        kwargs = kwargs or {}
        glb_path, meta_path = self._paths(name)
        meta = {
            "schema": SCHEMA_VERSION,
            "name": name,
            "hash": content_hash,
            "kwargs": _json_safe_kwargs(kwargs),
        }
        meta_bytes = json.dumps(meta, separators=(",", ":"), sort_keys=True).encode("utf-8")
        cache_dir_str = str(self.cache_dir)
        with self._lock:
            fd, tmp_glb = tempfile.mkstemp(suffix=".glb.tmp", dir=cache_dir_str)
            os.close(fd)
            tmp_glb_path = Path(tmp_glb)
            try:
                tmp_glb_path.write_bytes(glb)
                os.replace(tmp_glb, glb_path)
            except Exception:
                if tmp_glb_path.exists():
                    tmp_glb_path.unlink(missing_ok=True)
                raise
            fd, tmp_meta = tempfile.mkstemp(suffix=".meta.json.tmp", dir=cache_dir_str)
            os.close(fd)
            tmp_meta_path = Path(tmp_meta)
            try:
                tmp_meta_path.write_bytes(meta_bytes)
                os.replace(tmp_meta, meta_path)
            except Exception:
                if tmp_meta_path.exists():
                    tmp_meta_path.unlink(missing_ok=True)
                raise

    def delete(self, name: str) -> None:
        glb_path, meta_path = self._paths(name)
        with self._lock:
            for p in (glb_path, meta_path):
                try:
                    if p.is_file():
                        p.unlink()
                except OSError as e:
                    logger.warning("Could not delete cache file %s: %s", p, e)

    def clear(self) -> None:
        with self._lock:
            if not self.cache_dir.is_dir():
                return
            for p in self.cache_dir.iterdir():
                if p.suffix == ".glb" or p.name.endswith(META_SUFFIX):
                    try:
                        p.unlink()
                    except OSError as e:
                        logger.warning("Could not delete %s: %s", p, e)

    def list_entries(self) -> list[DiskCacheEntry]:
        """Return all valid cache entries sorted by GLB mtime (oldest first)."""
        entries: list[DiskCacheEntry] = []
        if not self.cache_dir.is_dir():
            return entries
        for meta_path in self.cache_dir.iterdir():
            if not meta_path.name.endswith(META_SUFFIX):
                continue
            base = meta_path.name[: -len(META_SUFFIX)]
            glb_path = self.cache_dir / (base + GLB_SUFFIX)
            if not glb_path.is_file() or not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("schema") != SCHEMA_VERSION:
                    logger.warning("Skipping unknown cache schema in %s", meta_path)
                    continue
                name = meta["name"]
                content_hash = meta["hash"]
                kwargs = meta.get("kwargs") or {}
                mtime = glb_path.stat().st_mtime
                entries.append(
                    DiskCacheEntry(
                        name=name,
                        content_hash=content_hash,
                        kwargs=kwargs,
                        glb_path=str(glb_path),
                        mtime=mtime,
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError) as e:
                logger.warning("Invalid cache entry %s: %s", meta_path, e)
        entries.sort(key=lambda e: e.mtime)
        return entries

    def read_glb(self, name: str) -> bytes | None:
        glb_path, _ = self._paths(name)
        try:
            return glb_path.read_bytes()
        except OSError:
            return None


def _json_safe_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Strip non-JSON-serializable values from tessellation kwargs for disk cache."""
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
