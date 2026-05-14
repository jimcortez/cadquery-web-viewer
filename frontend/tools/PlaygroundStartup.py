import micropip

# Fetch and run the upstream OCP.wasm bootstrap for build123d and its dependencies.
# This ensures we automatically stay up-to-date with the upstream bootstrap logic.
from pyodide.http import pyfetch
response = await pyfetch("https://raw.githubusercontent.com/yeicor/OCP.wasm/master/build123d/bootstrap_in_pyodide.py")
bootstrap_code = await response.string()
exec(bootstrap_code)
await bootstrap()

# Install glb-preview-server (Python package glb_preview_server) for the playground.
await micropip.install("glb-preview-server", pre=True)

# Preimport so symbols are in global scope; mock ocp_vscode for editor integration.
from glb_preview_server import *

micropip.add_mock_package("ocp-vscode", "2.8.9", modules={"ocp_vscode": 'from glb_preview_server import *'})
show_object = show

# Preinstall the font-fetcher package and install its hook to automatically download any requested font.
await micropip.install("font-fetcher", pre=True)

from font_fetcher.ocp import install_ocp_font_hook

install_ocp_font_hook()
