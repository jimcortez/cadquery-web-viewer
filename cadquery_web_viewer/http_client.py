"""HTTP client for posting models to a running ``cadquery-web-viewer`` Flask instance."""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Dict, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cadquery_web_viewer.mylogger import logger
from cadquery_web_viewer.engine import prepare_glb_upload_batch

DEFAULT_REMOTE_HOST = "localhost"
DEFAULT_REMOTE_PORT = 32323
DEFAULT_UPLOAD_TIMEOUT = 300.0
DEFAULT_POST_TIMEOUT = 60.0


def _base(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _multipart_upload(url: str, metadata: dict, glb: bytes, timeout: float) -> None:
    boundary = uuid.uuid4().hex
    meta_bytes = json.dumps(metadata, separators=(",", ":")).encode("utf-8")
    crlf = b"\r\n"
    chunks = [
        f"--{boundary}".encode() + crlf,
        b'Content-Disposition: form-data; name="metadata"' + crlf,
        b"Content-Type: application/json; charset=utf-8" + crlf + crlf,
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


def _post_json(host: str, port: int, path: str, body: dict, timeout: float) -> None:
    data = json.dumps(body).encode("utf-8")
    req = Request(f"{_base(host, port)}{path}", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=timeout) as r:
        if r.getcode() != 200:
            raise RuntimeError(f"{path} failed with HTTP {r.getcode()}")


def _json_safe_show_kwargs(kw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Make ``CadQueryWebViewer.show`` kwargs safe for JSON in multipart ``metadata`` (e.g. texture as ``(bytes, mime)``)."""
    if not kw:
        return {}
    out: Dict[str, Any] = {}
    for key, val in kw.items():
        if key == "texture" and isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], bytes):
            data, mime = val[0], str(val[1])
            out[key] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        elif isinstance(val, bytes):
            continue
        else:
            out[key] = val
    return out


def _resolved_remote(remote_options: Optional[dict]) -> dict[str, Any]:
    r = dict(remote_options or {})
    return {
        "host": str(r.get("host", DEFAULT_REMOTE_HOST)),
        "port": int(r.get("port", DEFAULT_REMOTE_PORT)),
        "upload_timeout": float(r.get("upload_timeout", DEFAULT_UPLOAD_TIMEOUT)),
        "post_timeout": float(r.get("post_timeout", DEFAULT_POST_TIMEOUT)),
    }


def remote_show(
    *objs: Any,
    names: Optional[Union[str, List[str]]] = None,
    remote_options: Optional[dict] = None,
    **kwargs: Any,
) -> None:
    o = _resolved_remote(remote_options)
    url = f"{_base(o['host'], o['port'])}/api/show"
    payloads, batch_names = prepare_glb_upload_batch(*objs, names=names, **kwargs)
    auto_clear_all = kwargs.get("auto_clear", True)
    for i, (name, glb, h, kw) in enumerate(payloads):
        meta: Dict[str, Any] = {
            "name": name,
            "hash": h,
            "kwargs": _json_safe_show_kwargs(kw),
            "auto_clear": bool(auto_clear_all and i == 0),
            "except_names": list(batch_names) if (auto_clear_all and i == 0) else None,
        }
        try:
            _multipart_upload(url, meta, glb, timeout=o["upload_timeout"])
        except (HTTPError, URLError, OSError, RuntimeError) as e:
            logger.error("remote show failed for %s: %s", name, e)
            raise


def remote_remove(name: str, remote_options: Optional[dict] = None) -> None:
    o = _resolved_remote(remote_options)
    try:
        _post_json(o["host"], o["port"], "/api/remove", {"name": name}, timeout=o["post_timeout"])
    except (HTTPError, URLError, OSError, RuntimeError) as e:
        logger.error("remote remove failed: %s", e)
        raise


def remote_clear(remote_options: Optional[dict] = None) -> None:
    o = _resolved_remote(remote_options)
    try:
        _post_json(o["host"], o["port"], "/api/clear", {}, timeout=o["post_timeout"])
    except (HTTPError, URLError, OSError, RuntimeError) as e:
        logger.error("remote clear failed: %s", e)
        raise
