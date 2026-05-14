import os
import sys

from cadquery_web_viewer.cad import grab_all_cad, image_to_gltf
from cadquery_web_viewer.engine import CadQueryWebViewer, CadQueryWebViewerProtocol

viewer = CadQueryWebViewer()
"""In-process engine used for local show/export when ``CADQUERY_WEB_VIEWER_DISABLE_SERVER`` is set."""

if (
    viewer.protocol == CadQueryWebViewerProtocol.HTTP
    and sys.platform != "emscripten"
    and os.environ.get("CADQUERY_WEB_VIEWER_DISABLE_SERVER") is None
):
    from cadquery_web_viewer import http_client

    show = http_client.remote_show
    remove = http_client.remote_remove
    clear = http_client.remote_clear

    def show_all(**kwargs):
        all_cad = list(grab_all_cad())
        return http_client.remote_show(
            *[cad for _, cad in all_cad],
            names=[name for name, _ in all_cad],
            **kwargs,
        )

else:
    show = viewer.show
    show_all = viewer.show_cad_all
    remove = viewer.remove
    clear = viewer.clear

export_all = viewer.export_all
