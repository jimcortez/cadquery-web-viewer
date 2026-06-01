"""HTTP client for a running ``cadquery-web-viewer`` Flask instance."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from cadquery_web_viewer.engine import prepare_glb_upload_batch
from cadquery_web_viewer.events_api import OBJECT_CREATED, OBJECT_VERSIONED, SCENE_CLEARED
from cadquery_web_viewer.options_types import RemoteOptions

logger = logging.getLogger(__name__)

DEFAULT_REMOTE_HOST = "localhost"
DEFAULT_REMOTE_PORT = 32323
DEFAULT_UPLOAD_TIMEOUT = 300.0
DEFAULT_POST_TIMEOUT = 60.0


def _base(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _object_url(host: str, port: int, name: str) -> str:
    return f"{_base(host, port)}/api/object/{quote(name, safe='')}"


def _put_object(
    host: str,
    port: int,
    name: str,
    metadata: dict[str, Any],
    glb: bytes,
    timeout: float,
) -> dict[str, Any]:
    url = _object_url(host, port, name)
    meta_json = json.dumps(metadata, separators=(",", ":"))
    files = {"glb": ("model.glb", glb, "model/gltf-binary")}
    data = {"metadata": meta_json}
    with httpx.Client(timeout=timeout) as client:
        response = client.put(url, files=files, data=data)
        response.raise_for_status()
        return response.json()


def _publish_events(host: str, port: int, events: list[dict[str, Any]], timeout: float) -> None:
    body = events[0] if len(events) == 1 else {"events": events}
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    url = f"{_base(host, port)}/api/events"
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()


def _json_safe_show_kwargs(kw: dict[str, Any] | None) -> dict[str, Any]:
    if not kw:
        return {}
    out: dict[str, Any] = {}
    for key, val in kw.items():
        if key == "texture" and isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], bytes):
            data, mime = val[0], str(val[1])
            out[key] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        elif isinstance(val, bytes):
            continue
        else:
            out[key] = val
    return out


def _scene_names(host: str, port: int, timeout: float) -> set[str]:
    url = f"{_base(host, port)}/api/scene"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        names = response.json().get("names", [])
        if not isinstance(names, list):
            return set()
        return {n for n in names if isinstance(n, str)}


def _resolved_remote(remote_options: RemoteOptions | None) -> dict[str, Any]:
    r = dict(remote_options or {})
    return {
        "host": str(r.get("host", DEFAULT_REMOTE_HOST)),
        "port": int(r.get("port", DEFAULT_REMOTE_PORT)),
        "upload_timeout": float(r.get("upload_timeout", DEFAULT_UPLOAD_TIMEOUT)),
        "post_timeout": float(r.get("post_timeout", DEFAULT_POST_TIMEOUT)),
    }


def remote_show(
    *objs: Any,
    names: str | list[str] | None = None,
    remote_options: RemoteOptions | None = None,
    **kwargs: Any,
) -> None:
    o = _resolved_remote(remote_options)
    payloads, batch_names = prepare_glb_upload_batch(*objs, names=names, **kwargs)
    auto_clear_all = kwargs.get("auto_clear", True)
    scene_before_clear: set[str] = set()
    scene_query_ok = False
    if payloads:
        try:
            scene_before_clear = _scene_names(o["host"], o["port"], o["post_timeout"])
            scene_query_ok = True
        except httpx.HTTPError as e:
            logger.warning(
                "remote scene query failed (%s); will clear scene and use object.created", e
            )
    events: list[dict[str, Any]] = []
    if auto_clear_all and payloads:
        except_names = list(batch_names) if scene_query_ok else []
        events.append({"type": SCENE_CLEARED, "except_names": except_names})
    for name, glb, h, kw in payloads:
        meta = {"hash": h, "kwargs": _json_safe_show_kwargs(kw)}
        try:
            result = _put_object(o["host"], o["port"], name, meta, glb, timeout=o["upload_timeout"])
        except httpx.HTTPError as e:
            logger.error("remote PUT object failed for %s: %s", name, e)
            raise
        version = int(result["version"])
        in_scene = scene_query_ok and name in scene_before_clear
        if in_scene:
            events.append(
                {
                    "type": OBJECT_VERSIONED,
                    "name": name,
                    "version": version,
                    "hash": h,
                }
            )
        else:
            events.append(
                {
                    "type": OBJECT_CREATED,
                    "name": name,
                    "version": version,
                    "hash": h,
                }
            )
    if events:
        try:
            _publish_events(o["host"], o["port"], events, timeout=o["post_timeout"])
        except httpx.HTTPError as e:
            logger.error("remote publish events failed: %s", e)
            raise


def remote_remove(name: str, remote_options: RemoteOptions | None = None) -> None:
    o = _resolved_remote(remote_options)
    url = _object_url(o["host"], o["port"], name)
    try:
        with httpx.Client(timeout=o["post_timeout"]) as client:
            response = client.delete(url)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("remote remove failed: %s", e)
        raise


def remote_clear(remote_options: RemoteOptions | None = None) -> None:
    o = _resolved_remote(remote_options)
    try:
        _publish_events(o["host"], o["port"], [{"type": SCENE_CLEARED, "except_names": []}], o["post_timeout"])
        with httpx.Client(timeout=o["post_timeout"]) as client:
            response = client.delete(f"{_base(o['host'], o['port'])}/api/object")
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("remote clear failed: %s", e)
        raise


def remote_put_object_from_url(
    name: str,
    url: str,
    remote_options: RemoteOptions | None = None,
    *,
    content_hash: str | None = None,
    kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    o = _resolved_remote(remote_options)
    body: dict[str, Any] = {"url": url}
    if content_hash is not None:
        body["hash"] = content_hash
    if kwargs is not None:
        body["kwargs"] = kwargs
    put_url = _object_url(o["host"], o["port"], name)
    with httpx.Client(timeout=o["upload_timeout"]) as client:
        response = client.put(
            put_url,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def remote_list_objects(remote_options: RemoteOptions | None = None) -> list[dict[str, Any]]:
    o = _resolved_remote(remote_options)
    url = f"{_base(o['host'], o['port'])}/api/object"
    with httpx.Client(timeout=o["post_timeout"]) as client:
        response = client.get(url)
        response.raise_for_status()
        return list(response.json().get("objects", []))


def remote_patch_object(
    name: str,
    remote_options: RemoteOptions | None = None,
    *,
    new_name: str | None = None,
    notes: str | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    o = _resolved_remote(remote_options)
    body: dict[str, Any] = {}
    if new_name is not None:
        body["name"] = new_name
    if notes is not None:
        body["notes"] = notes
    if settings is not None:
        body["settings"] = settings
    url = _object_url(o["host"], o["port"], name)
    with httpx.Client(timeout=o["post_timeout"]) as client:
        response = client.patch(url, json=body)
        response.raise_for_status()
        return response.json()
