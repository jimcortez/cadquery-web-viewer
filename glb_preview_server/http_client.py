"""HTTP client for posting models to a running ``glb-preview-server`` Flask instance."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from glb_preview_server.mylogger import logger
from glb_preview_server.engine import prepare_glb_upload_batch


def _base(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _multipart_upload(url: str, metadata: dict, glb: bytes, timeout: float = 300.0) -> None:
    boundary = uuid.uuid4().hex
    meta_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    crlf = b"\r\n"
    chunks = [
        f"--{boundary}".encode() + crlf,
        b'Content-Disposition: form-data; name="metadata"; filename="metadata.json"' + crlf,
        b"Content-Type: application/json" + crlf + crlf,
        meta_bytes + crlf,
        f"--{boundary}".encode() + crlf,
        b'Content-Disposition: form-data; name="glb"; filename="model.glb"' + crlf,
        b"Content-Type: model/gltf-binary" + crlf + crlf,
        glb + crlf,
        f"--{boundary}--".encode() + crlf,
    ]
    body = b"".join(chunks)
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urlopen(req, timeout=timeout) as r:
        code = r.getcode()
        if code != 200:
            raise RuntimeError(f"upload failed with HTTP {code}")


def _post_json(host: str, port: int, path: str, body: dict, timeout: float = 60.0) -> None:
    data = json.dumps(body).encode("utf-8")
    req = Request(f"{_base(host, port)}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=timeout) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"{path} failed with HTTP {r.getcode()}")


def _resolve_host_port(host: Optional[str], port: Optional[int]) -> tuple[str, int]:
    h = host or os.environ.get("GLB_PREVIEW_HOST", "localhost")
    p = int(port if port is not None else os.environ.get("GLB_PREVIEW_PORT", 32323))
    return h, p


def remote_show(
    *objs,
    names: Optional[Union[str, List[str]]] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    **kwargs: Any,
) -> None:
    host_r, port_r = _resolve_host_port(host, port)
    url = f"{_base(host_r, port_r)}/api/show"
    show_kw = {k: v for k, v in kwargs.items() if k not in ("host", "port")}
    payloads, batch_names = prepare_glb_upload_batch(*objs, names=names, **show_kw)
    auto_clear_all = show_kw.get("auto_clear", True)
    for i, (name, glb, h, kw) in enumerate(payloads):
        meta: Dict[str, Any] = {
            "name": name,
            "hash": h,
            "kwargs": kw,
            "auto_clear": bool(auto_clear_all and i == 0),
            "except_names": list(batch_names) if (auto_clear_all and i == 0) else None,
        }
        try:
            _multipart_upload(url, meta, glb)
        except (HTTPError, URLError, OSError, RuntimeError) as e:
            logger.error("remote show failed for %s: %s", name, e)
            raise


def remote_remove(name: str, host: Optional[str] = None, port: Optional[int] = None) -> None:
    host_r, port_r = _resolve_host_port(host, port)
    try:
        _post_json(host_r, port_r, "/api/remove", {"name": name})
    except (HTTPError, URLError, OSError, RuntimeError) as e:
        logger.error("remote remove failed: %s", e)
        raise


def remote_clear(host: Optional[str] = None, port: Optional[int] = None) -> None:
    host_r, port_r = _resolve_host_port(host, port)
    try:
        _post_json(host_r, port_r, "/api/clear", {})
    except (HTTPError, URLError, OSError, RuntimeError) as e:
        logger.error("remote clear failed: %s", e)
        raise
