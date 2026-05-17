"""Fetch GLB bytes from a remote URL for object store import."""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse

import httpx

GLB_MAGIC = b"glTF"
MAX_GLB_BYTES = 50 * 1024 * 1024
FETCH_TIMEOUT_S = 60.0


class UrlImportError(Exception):
    """Failed to import GLB from URL."""


def content_hash_from_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_glb_bytes(data: bytes) -> None:
    if len(data) < 12:
        raise UrlImportError("Response is too small to be a GLB file")
    if data[:4] != GLB_MAGIC:
        raise UrlImportError("Response is not a GLB file (missing glTF magic)")


def fetch_glb_bytes(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlImportError("url must use http or https")
    if not parsed.netloc:
        raise UrlImportError("url must include a host")

    try:
        with httpx.Client(timeout=FETCH_TIMEOUT_S, follow_redirects=True) as client:
            response = client.get(url)
    except httpx.HTTPError as e:
        raise UrlImportError(f"Failed to fetch url: {e}") from e

    if response.status_code != 200:
        raise UrlImportError(f"Fetch returned HTTP {response.status_code}")

    data = response.content
    if len(data) > MAX_GLB_BYTES:
        raise UrlImportError(f"GLB exceeds maximum size ({MAX_GLB_BYTES} bytes)")

    try:
        validate_glb_bytes(data)
    except UrlImportError:
        raise
    return data
