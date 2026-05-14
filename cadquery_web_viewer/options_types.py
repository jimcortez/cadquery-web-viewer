"""Typed options dicts for embedded server and remote HTTP client."""

from __future__ import annotations

from typing import TypedDict


class ServerOptions(TypedDict, total=False):
    """Options for :func:`~cadquery_web_viewer.embedded_server.ensure_embedded_running`."""

    host: str
    port: int
    open_browser: bool
    wait_for_client_timeout: float
    wait_for_first_client: bool


class RemoteOptions(TypedDict, total=False):
    """Options for :mod:`cadquery_web_viewer.http_client` remote helpers."""

    host: str
    port: int
    upload_timeout: float
    post_timeout: float
