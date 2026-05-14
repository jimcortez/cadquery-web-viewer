# glb-preview-server

**glb-preview-server** is a hard fork of [**Yet Another CAD Viewer**](https://github.com/yeicor-3d/yet-another-cad-viewer) (YACV): a web-based CAD and GLB viewer with a Python (`glb_preview_server`) backend for live tessellation, hot reload, and static export. This repository continues the same MIT-licensed codebase under a new name and package layout while crediting the original project and its authors.

Upstream reference: [yeicor-3d/yet-another-cad-viewer](https://github.com/yeicor-3d/yet-another-cad-viewer) — use that project’s issue tracker and releases if you need the original branding or PyPI package `yacv-server`.

## Features

- Cross-platform: works on any modern web browser.
- Full [glTF 2.0](https://www.khronos.org/gltf/) and [model-viewer](https://modelviewer.dev/) capabilities (textures, PBR, AR, navigation).
- Load multiple models, external URLs, and images as quads; clipping, transparency, edge/vertex styling, explode, topology picking, measurements.
- Live updates while editing CAD in Python via the `glb-preview-server` CLI (`glb-preview-server` command) and the `glb_preview_server` import package.
- Optional disk cache for uploaded GLBs, static deployment of the built UI plus `.glb` files, and a Build123d playground (full build) backed by Pyodide.

## Install

```bash
pip install glb-preview-server
```

Run the viewer and API (default `http://localhost:32323`):

```bash
glb-preview-server
```

Environment variables use the `GLB_PREVIEW_*` prefix (for example `GLB_PREVIEW_HOST`, `GLB_PREVIEW_PORT`, `GLB_PREVIEW_DISABLE_SERVER`). See the [example](example) project and package CLI help for details.

## Usage

The [example](example) directory is a minimal project that calls `show()` / `export_all()` against a running server.

The original project’s public demos remain on GitHub Pages under the YACV name, for example the [interactive playground demo](https://yeicor-3d.github.io/yet-another-cad-viewer/#pg_code=https://raw.githubusercontent.com/gumyr/build123d/refs/heads/dev/examples/toy_truck.py). After you publish this fork’s frontend, use the same query parameters with your own base URL (for example `?preload=…` for static GLBs).

## Related projects

- [cq-studio](https://github.com/ccazabon/cq-studio) — alternative file-watch workflow; historically related to the same viewer stack.
- [build123d-docker](https://github.com/derhuerst/build123d-docker/pkgs/container/build123d) — containers for CAD tooling.
- [OCP.wasm](https://github.com/yeicor/OCP.wasm/) — OpenCASCADE in the browser; powers the in-browser Build123d playground.

## License

This project is released under the [MIT License](LICENSE), consistent with the upstream Yet Another CAD Viewer distribution. Third-party notices are collected under [assets/licenses.txt](assets/licenses.txt) as in the original project.
