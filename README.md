# cadquery-web-viewer

**cadquery-web-viewer** is a hard fork of [**Yet Another CAD Viewer**](https://github.com/yeicor-3d/yet-another-cad-viewer) (YACV): a web-based CAD and GLB viewer with a Python (`cadquery_web_viewer`) backend for live tessellation, hot reload, and static export. This repository continues the same MIT-licensed codebase under a new name and package layout while crediting the original project and its authors.

Upstream reference: [yeicor-3d/yet-another-cad-viewer](https://github.com/yeicor-3d/yet-another-cad-viewer) — use that project’s issue tracker and releases if you need the original branding or PyPI package `yacv-server`.

## Features

- Cross-platform: works on any modern web browser.
- Full [glTF 2.0](https://www.khronos.org/gltf/) and [model-viewer](https://modelviewer.dev/) capabilities (textures, PBR, AR, navigation).
- Load multiple models, external URLs, and images as quads; clipping, transparency, edge/vertex styling, explode, topology picking, measurements.
- Live updates while editing CAD in Python via the `cadquery-web-viewer` CLI and the `cadquery_web_viewer` import package.
- Optional disk cache for uploaded GLBs and static deployment of the built UI plus `.glb` files.

## Install

```bash
pip install cadquery-web-viewer
```

## Using the project as a **server**

Install the package (globally or in a virtual environment) and run the Flask app that serves the static UI and `/api` (SSE, uploads, tessellation from remote clients):

```bash
cadquery-web-viewer --host localhost --port 32323
```

Optional flags: `--cache-mode memory|disk`, `--cache-dir <path>` when using disk cache. Defaults are defined in the CLI only (no environment-variable overrides).

## Using the project as a **client** (from Python)

### Embedded viewer (default)

`show()` starts an in-process HTTP server on a background thread (sharing one tessellation engine with Flask), opens your browser, waits for the first EventSource client, publishes your model, then **blocks until every `/api/updates` connection has closed** and shuts the server down (so one-shot scripts behave like the classic `yacv-server` workflow).

```python
from cadquery_web_viewer import show

show(my_solid)  # server_type="in-process" by default
```

See [examples/in-process](examples/in-process) for a **local-buffer** script (`server_type="local"`) plus CI `export_all`; use default `show()` above for the embedded viewer.

Tune bind address, browser, and timeouts with `server_options` (plain dict), for example:

```python
show(my_solid, server_options={"host": "127.0.0.1", "port": 32323, "wait_for_client_timeout": 180.0})
```

For several `show()` calls in one script, pass `block_until_disconnect=False` on each call except the last so the embedded server stays up between calls.

### Remote API (separate `cadquery-web-viewer` process)

With a server already running, publish models over HTTP:

```python
from cadquery_web_viewer import show

show(
    my_solid,
    server_type="remote",
    remote_options={"host": "localhost", "port": 32323},  # optional keys: upload_timeout, post_timeout
)
```

See [examples/remote](examples/remote) for a script that prints the server command to run in another window, then waits for you to press Enter before calling `show()`.

### Local buffer only (no HTTP, for `export_all` / CI)

```python
from cadquery_web_viewer import show, export_all

show(my_solid, server_type="local")
export_all("./glbs")
```

## Migrating from **yacv-server** / **yacv-viewer**

| Before (upstream / old names) | After (this fork) |
|------------------------------|-------------------|
| PyPI / import `yacv_server` | Package / import `cadquery_web_viewer` |
| CLI `yacv-server` | CLI `cadquery-web-viewer` (`python -m cadquery_web_viewer`) |
| Implicit “talk to a running server” via environment | Explicit `server_type`: `"in-process"` (default), `"remote"`, or `"local"` |
| Separate process required for browser preview | Default `show()` embeds Flask + blocks until the tab is closed |
| Host / port via env | `server_options` / `remote_options` dicts on `show`, `remove`, `clear`, `show_all` |

The `CadQueryWebViewer` engine may still honor optional styling-related environment variables (for example texture and default colors); connection and server behavior for `show()` are controlled through the keyword arguments above.

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

The [examples](examples) directory has a **local-buffer** script under `in-process/`, a **remote** client under `remote/`, and CI exports GLBs from the in-process example when `CI` is set.

The original project’s public demos remain on GitHub Pages under the YACV name. After you publish this fork’s frontend, you can use query parameters with your own base URL (for example `?preload=…` for static GLBs).

## Related projects

- [cq-studio](https://github.com/ccazabon/cq-studio) — alternative file-watch workflow; historically related to the same viewer stack.
- [build123d-docker](https://github.com/derhuerst/build123d-docker/pkgs/container/build123d) — containers for CAD tooling.
- [OCP.wasm](https://github.com/yeicor/OCP.wasm/) — OpenCASCADE compiled for WebAssembly (related browser CAD stacks).

## License

This project is released under the [MIT License](LICENSE), consistent with the upstream Yet Another CAD Viewer distribution. Third-party notices are collected under [assets/licenses.txt](assets/licenses.txt) as in the original project.
