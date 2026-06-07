"""cadquery-web-viewer: CAD preview with ``show()`` and static export."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from cadquery_web_viewer.cad import grab_all_cad, image_to_gltf
from cadquery_web_viewer.engine import (
    CadQueryWebViewer,
    CadQueryWebViewerProtocol,
    get_default_engine,
    glb_bytes_list_from_show_inputs,
)
from cadquery_web_viewer.options_types import RemoteOptions, ServerOptions

ServerType = Literal["in-process", "remote", "local"]

viewer = get_default_engine()
"""Default engine used by :func:`show`, :func:`export_all`, and related helpers."""

export_all = viewer.export_all


def render(
    *objs: Any,
    names: str | list[str] | None = None,
    **kwargs: Any,
) -> list[bytes]:
    """
    Tessellate CAD-like objects to GLB bytes (``bytes`` inputs are returned unchanged).

    Use the same ``names`` and ``**kwargs`` when calling :func:`show` so hashes and viewer metadata match.
    """
    glbs, _ = glb_bytes_list_from_show_inputs(*objs, names=names, **kwargs)
    return glbs


def _in_process_session(
    *,
    server_options: ServerOptions | None,
    block_until_disconnect: bool,
    body: Callable[[], None],
) -> None:
    from cadquery_web_viewer import embedded_server

    embedded_server.ensure_embedded_running(
        viewer,
        server_options,
        daemon_thread=not block_until_disconnect,
    )
    # Ctrl+C during ``wait_until_no_sse_streams`` used to abort ``finally`` before
    # ``shutdown_embedded()``. Ctrl+C during ``body()`` also led to the same wait and
    # a second interrupt. Skip the wait after any KeyboardInterrupt; always shut down.
    skip_wait_due_to_interrupt = False
    try:
        body()
    except KeyboardInterrupt:
        skip_wait_due_to_interrupt = True
    finally:
        if block_until_disconnect:
            if not skip_wait_due_to_interrupt:
                try:
                    viewer.wait_until_no_sse_streams(timeout=None)
                except KeyboardInterrupt:
                    skip_wait_due_to_interrupt = True
            embedded_server.shutdown_embedded()
    if skip_wait_due_to_interrupt:
        raise KeyboardInterrupt from None


def show(
    *objs: Any,
    names: str | list[str] | None = None,
    server_type: ServerType = "in-process",
    remote_options: RemoteOptions | None = None,
    server_options: ServerOptions | None = None,
    block_until_disconnect: bool = True,
    **kwargs: Any,
) -> None:
    disp_objs: tuple[Any, ...] = objs
    disp_names: str | list[str] | None = names
    if objs and any(not isinstance(o, bytes) for o in objs):
        glbs, resolved = glb_bytes_list_from_show_inputs(*objs, names=names, **kwargs)
        disp_objs = tuple(glbs)
        disp_names = resolved

    if server_type == "local":
        viewer.show(*disp_objs, names=disp_names, **kwargs)
        return
    if server_type == "remote":
        from cadquery_web_viewer import http_client

        http_client.remote_show(*disp_objs, names=disp_names, remote_options=remote_options, **kwargs)
        return
    _in_process_session(
        server_options=server_options,
        block_until_disconnect=block_until_disconnect,
        body=lambda: viewer.show(*disp_objs, names=disp_names, **kwargs),
    )


def show_all(
    server_type: ServerType = "in-process",
    remote_options: RemoteOptions | None = None,
    server_options: ServerOptions | None = None,
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
    remote_options: RemoteOptions | None = None,
    server_options: ServerOptions | None = None,
    block_until_disconnect: bool = True,
) -> None:
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
    remote_options: RemoteOptions | None = None,
    server_options: ServerOptions | None = None,
    block_until_disconnect: bool = True,
) -> None:
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
    "get_default_engine",
    "RemoteOptions",
    "ServerOptions",
    "ServerType",
    "clear",
    "export_all",
    "grab_all_cad",
    "image_to_gltf",
    "remove",
    "render",
    "show",
    "show_all",
    "viewer",
]
