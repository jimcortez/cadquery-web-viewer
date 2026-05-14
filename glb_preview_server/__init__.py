import os
import sys

from glb_preview_server.cad import grab_all_cad, image_to_gltf
from glb_preview_server.engine import GlbPreview, GlbPreviewProtocol

glb_preview = GlbPreview()
"""In-process engine used for local show/export when ``GLB_PREVIEW_DISABLE_SERVER`` is set."""

if (
    glb_preview.protocol == GlbPreviewProtocol.HTTP
    and sys.platform != "emscripten"
    and os.environ.get("GLB_PREVIEW_DISABLE_SERVER") is None
):
    from glb_preview_server import http_client

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
    show = glb_preview.show
    show_all = glb_preview.show_cad_all
    remove = glb_preview.remove
    clear = glb_preview.clear

export_all = glb_preview.export_all
