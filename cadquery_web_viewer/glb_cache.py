"""Optional on-disk persistence for uploaded GLB payloads and metadata."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    kwargs: Dict[str, Any]
    glb_path: str
    mtime: float


class GlbDiskCache:
    """Stores one GLB + JSON sidecar per object name under a fixed directory."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self._lock = threading.Lock()
        os.makedirs(self.cache_dir, exist_ok=True)

    def _paths(self, name: str) -> Tuple[str, str]:
        eid = entry_id_for_name(name)
        base = os.path.join(self.cache_dir, eid)
        return base + GLB_SUFFIX, base + META_SUFFIX

    def write(self, name: str, content_hash: str, glb: bytes, kwargs: Optional[Dict[str, Any]] = None) -> None:
        kwargs = kwargs or {}
        glb_path, meta_path = self._paths(name)
        meta = {
            "schema": SCHEMA_VERSION,
            "name": name,
            "hash": content_hash,
            "kwargs": _json_safe_kwargs(kwargs),
        }
        meta_bytes = json.dumps(meta, separators=(",", ":"), sort_keys=True).encode("utf-8")
        with self._lock:
            fd, tmp_glb = tempfile.mkstemp(suffix=".glb.tmp", dir=self.cache_dir)
            os.close(fd)
            try:
                with open(tmp_glb, "wb") as f:
                    f.write(glb)
                os.replace(tmp_glb, glb_path)
            except BaseException:
                if os.path.exists(tmp_glb):
                    os.unlink(tmp_glb)
                raise
            fd, tmp_meta = tempfile.mkstemp(suffix=".meta.json.tmp", dir=self.cache_dir)
            os.close(fd)
            try:
                with open(tmp_meta, "wb") as f:
                    f.write(meta_bytes)
                os.replace(tmp_meta, meta_path)
            except BaseException:
                if os.path.exists(tmp_meta):
                    os.unlink(tmp_meta)
                raise

    def delete(self, name: str) -> None:
        glb_path, meta_path = self._paths(name)
        with self._lock:
            for p in (glb_path, meta_path):
                try:
                    if os.path.isfile(p):
                        os.unlink(p)
                except OSError as e:
                    logger.warning("Could not delete cache file %s: %s", p, e)

    def clear(self) -> None:
        with self._lock:
            if not os.path.isdir(self.cache_dir):
                return
            for fn in os.listdir(self.cache_dir):
                if fn.endswith(GLB_SUFFIX) or fn.endswith(META_SUFFIX):
                    try:
                        os.unlink(os.path.join(self.cache_dir, fn))
                    except OSError as e:
                        logger.warning("Could not delete %s: %s", fn, e)

    def list_entries(self) -> List[DiskCacheEntry]:
        """Return all valid cache entries sorted by GLB mtime (oldest first)."""
        entries: List[DiskCacheEntry] = []
        if not os.path.isdir(self.cache_dir):
            return entries
        for fn in os.listdir(self.cache_dir):
            if not fn.endswith(META_SUFFIX):
                continue
            base = fn[: -len(META_SUFFIX)]
            glb_fn = base + GLB_SUFFIX
            glb_path = os.path.join(self.cache_dir, glb_fn)
            meta_path = os.path.join(self.cache_dir, fn)
            if not os.path.isfile(glb_path) or not os.path.isfile(meta_path):
                continue
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("schema") != SCHEMA_VERSION:
                    logger.warning("Skipping unknown cache schema in %s", meta_path)
                    continue
                name = meta["name"]
                content_hash = meta["hash"]
                kwargs = meta.get("kwargs") or {}
                mtime = os.path.getmtime(glb_path)
                entries.append(
                    DiskCacheEntry(
                        name=name,
                        content_hash=content_hash,
                        kwargs=kwargs,
                        glb_path=glb_path,
                        mtime=mtime,
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError) as e:
                logger.warning("Invalid cache entry %s: %s", meta_path, e)
        entries.sort(key=lambda e: e.mtime)
        return entries

    def read_glb(self, name: str) -> Optional[bytes]:
        glb_path, _ = self._paths(name)
        try:
            with open(glb_path, "rb") as f:
                return f.read()
        except OSError:
            return None


def _json_safe_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Strip non-JSON-serializable values from tessellation kwargs for disk cache."""
    safe: Dict[str, Any] = {}
    for k, v in kwargs.items():
        if k == "texture" and v is not None:
            continue
        try:
            json.dumps(v)
            safe[k] = v
        except TypeError:
            continue
    return safe
