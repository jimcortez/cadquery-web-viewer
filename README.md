# cadquery-web-viewer

**cadquery-web-viewer** is a hard fork of [**Yet Another CAD Viewer**](https://github.com/yeicor-3d/yet-another-cad-viewer) (YACV): a web-based CAD and GLB viewer with a Python (`cadquery_web_viewer`) backend for live tessellation, hot reload, and static export. This repository continues the same MIT-licensed codebase under a new name and package layout while crediting the original project and its authors.

Upstream reference: [yeicor-3d/yet-another-cad-viewer](https://github.com/yeicor-3d/yet-another-cad-viewer) — use that project’s issue tracker and releases if you need the original branding or PyPI package `yacv-server`.

## Features

- Cross-platform: works on any modern web browser.
- Full [glTF 2.0](https://www.khronos.org/gltf/) and [model-viewer](https://modelviewer.dev/) capabilities (textures, PBR, AR, navigation).
- Load multiple models, external URLs, and images as quads; clipping, transparency, edge/vertex styling, explode, topology picking, measurements.
- Live updates while editing CAD in Python via the `cadquery-web-viewer` CLI (`cadquery-web-viewer` command) and the `cadquery_web_viewer` import package.
- Optional disk cache for uploaded GLBs and static deployment of the built UI plus `.glb` files.

## Install

```bash
pip install cadquery-web-viewer
```

Run the viewer and API (default `http://localhost:32323`):

```bash
cadquery-web-viewer
```

Environment variables use the `CADQUERY_WEB_VIEWER_*` prefix (for example `CADQUERY_WEB_VIEWER_HOST`, `CADQUERY_WEB_VIEWER_PORT`, `CADQUERY_WEB_VIEWER_DISABLE_SERVER`). See the [example](example) project and package CLI help for details.

## Development

Run the **Flask API** and the **Vite dev server** in two terminals so the UI hot-reloads while Python still serves `/api` (SSE, uploads, tessellation).

1. **Install dependencies** (Python 3.12 as in `pyproject.toml`, and Node for the frontend):

   ```bash
   uv sync
   yarn install
   ```

   If you do not use [uv](https://docs.astral.sh/uv/), use a virtual environment and `pip install -e .` from the repository root instead of `uv sync`.

2. **Start the backend** (default `http://localhost:32323`):

   ```bash
   uv run cadquery-web-viewer
   ```

   Equivalent: `python -m cadquery_web_viewer` after the package is installed.

3. **Start the frontend** in another shell:

   ```bash
   yarn dev
   ```

   Open the URL Vite prints (by default `http://localhost:5173`). The viewer’s default preload discovers `/api/updates` on the same origin; when that is not the Flask app (as with Vite alone), it falls back to `http://localhost:32323`, so the UI and API stay in sync.

To work on the backend only with a static UI, run `yarn install` if you have not yet, then `yarn build` once (writes `dist/` at the repository root), then start only `cadquery-web-viewer`. Flask serves that bundle when `cadquery_web_viewer/frontend` is missing (see `FRONTEND_BASE_PATH` in the package). A full `yarn build` needs devDependencies (including `generate-license-file`); installing with `NODE_ENV=production` omits those and the build will fail.

## Usage

The [example](example) directory is a minimal project that calls `show()` / `export_all()` against a running server.

The original project’s public demos remain on GitHub Pages under the YACV name. After you publish this fork’s frontend, you can use query parameters with your own base URL (for example `?preload=…` for static GLBs).

## Related projects

- [cq-studio](https://github.com/ccazabon/cq-studio) — alternative file-watch workflow; historically related to the same viewer stack.
- [build123d-docker](https://github.com/derhuerst/build123d-docker/pkgs/container/build123d) — containers for CAD tooling.
- [OCP.wasm](https://github.com/yeicor/OCP.wasm/) — OpenCASCADE compiled for WebAssembly (related browser CAD stacks).

## License

This project is released under the [MIT License](LICENSE), consistent with the upstream Yet Another CAD Viewer distribution. Third-party notices are collected under [assets/licenses.txt](assets/licenses.txt) as in the original project.
