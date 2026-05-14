"""cadquery-web-viewer: CAD preview with ``show()`` and static export."""

from __future__ import annotations

import sys
from typing import Any, Callable, Literal, Optional, Union

from cadquery_web_viewer.cad import grab_all_cad, image_to_gltf
from cadquery_web_viewer.engine import CadQueryWebViewer, CadQueryWebViewerProtocol

ServerType = Literal["in-process", "remote", "local"]

viewer = CadQueryWebViewer()
"""Default engine used by :func:`show`, :func:`export_all`, and related helpers."""

export_all = viewer.export_all


def _stderr_like() -> bool:
    return viewer.protocol == CadQueryWebViewerProtocol.STDERR or sys.platform == "emscripten"


def _in_process_session(
    *,
    server_options: Optional[dict],
    block_until_disconnect: bool,
    body: Callable[[], None],
) -> None:
    from cadquery_web_viewer import embedded_server

    embedded_server.ensure_embedded_running(
        viewer,
        server_options,
        daemon_thread=not block_until_disconnect,
    )
    try:
        body()
    finally:
        if block_until_disconnect:
            viewer.wait_until_no_sse_streams(timeout=None)
            embedded_server.shutdown_embedded()


def show(
    *objs: Any,
    names: Optional[Union[str, list[str]]] = None,
    server_type: ServerType = "in-process",
    remote_options: Optional[dict] = None,
    server_options: Optional[dict] = None,
    block_until_disconnect: bool = True,
    **kwargs: Any,
) -> None:
    if _stderr_like():
        viewer.show(*objs, names=names, **kwargs)
        return
    if server_type == "local":
        viewer.show(*objs, names=names, **kwargs)
        return
    if server_type == "remote":
        from cadquery_web_viewer import http_client

        http_client.remote_show(*objs, names=names, remote_options=remote_options, **kwargs)
        return
    _in_process_session(
        server_options=server_options,
        block_until_disconnect=block_until_disconnect,
        body=lambda: viewer.show(*objs, names=names, **kwargs),
    )


def show_all(
    server_type: ServerType = "in-process",
    remote_options: Optional[dict] = None,
    server_options: Optional[dict] = None,
    block_until_disconnect: bool = True,
    **kwargs: Any,
) -> None:
    all_cad = list(grab_all_cad())
    show(
        *[cad for _, cad in all_cad],
        names=[name for name, _ in all_cad],
        server_type=server_type,
        remote_options=remote_options,
        server_options=server_options,
        block_until_disconnect=block_until_disconnect,
        **kwargs,
    )


def remove(
    name: str,
    server_type: ServerType = "in-process",
    remote_options: Optional[dict] = None,
    server_options: Optional[dict] = None,
    block_until_disconnect: bool = True,
) -> None:
    if _stderr_like():
        viewer.remove(name)
        return
    if server_type == "local":
        viewer.remove(name)
        return
    if server_type == "remote":
        from cadquery_web_viewer import http_client

        http_client.remote_remove(name, remote_options=remote_options)
        return
    _in_process_session(
        server_options=server_options,
        block_until_disconnect=block_until_disconnect,
        body=lambda: viewer.remove(name),
    )


def clear(
    server_type: ServerType = "in-process",
    remote_options: Optional[dict] = None,
    server_options: Optional[dict] = None,
    block_until_disconnect: bool = True,
) -> None:
    if _stderr_like():
        viewer.clear()
        return
    if server_type == "local":
        viewer.clear()
        return
    if server_type == "remote":
        from cadquery_web_viewer import http_client

        http_client.remote_clear(remote_options=remote_options)
        return
    _in_process_session(
        server_options=server_options,
        block_until_disconnect=block_until_disconnect,
        body=lambda: viewer.clear(),
    )


__all__ = [
    "CadQueryWebViewer",
    "CadQueryWebViewerProtocol",
    "ServerType",
    "clear",
    "export_all",
    "grab_all_cad",
    "image_to_gltf",
    "remove",
    "show",
    "show_all",
    "viewer",
]
