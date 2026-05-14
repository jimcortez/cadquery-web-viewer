# CadQuery Web Viewer

**Preview CadQuery or build123d models in your browser** and refresh the view while you edit Python—without manually exporting meshes each time.

The API and packaging are meant to be a **mostly drop-in replacement** for [Yet Another CAD Viewer (YACV)](https://github.com/yeicor-3d/yet-another-cad-viewer). Renames and explicit `server_type` are covered in **Migrating from `yacv-server` / `yacv-viewer`** below; project history and upstream links are in **Special thanks** at the end of this file.

## Table of contents

- [Quick start](#quick-start)
  - [Install the package](#install-the-package)
  - [Run from Python](#run-from-python)
- [What you get](#what-you-get)
- [Run the app as a server](#run-the-app-as-a-server)
- [Run with Docker](#run-with-docker)
- [Call `show()` from Python](#call-show-from-python)
  - [Embedded viewer (default)](#embedded-viewer-default)
  - [Host, port, and timeouts](#host-port-and-timeouts)
  - [Several `show()` calls in one script](#several-show-calls-in-one-script)
  - [Remote server (Flask already running)](#remote-server-flask-already-running)
  - [Buffer only, then export GLBs (no browser)](#buffer-only-then-export-glbs-no-browser)
- [Examples in this repo](#examples-in-this-repo)
- [Migrating from `yacv-server` / `yacv-viewer`](#migrating-from-yacv-server--yacv-viewer)
- [Develop the UI and Python backend](#develop-the-ui-and-python-backend)
- [Related projects](#related-projects)
- [Special thanks](#special-thanks)

## Quick start

Requires **Python 3.10 through 3.12** (see `requires-python` in `pyproject.toml`).

### Install the package

Pick one approach. The `cadquery-web-viewer` command is registered by the package; you only get it on your shell **PATH** when you install into an active environment, use **pipx**, or use **`uv tool install`** (see below).

**pip inside a virtual environment** (good when you import the library from the same project):

```bash
python -m venv .venv
source .venv/bin/activate
pip install cadquery-web-viewer
```

On Windows, activate with `.venv\Scripts\activate`. While the venv is active, run `cadquery-web-viewer` or `python -m cadquery_web_viewer`.

**pipx** installs the app in an isolated environment and links the CLI into pipx’s binary directory so you can run it from any directory. If `cadquery-web-viewer` is not found, run `pipx ensurepath`, restart the shell, and confirm that directory is on your `PATH`.

```bash
pipx install cadquery-web-viewer
```

**uv** can do the same with **tools**: an isolated install plus executables on your user path (commonly `~/.local/bin`). Add that directory to `PATH` if your shell does not already.

```bash
uv tool install cadquery-web-viewer
```

To upgrade later: `pipx upgrade cadquery-web-viewer` or `uv tool upgrade cadquery-web-viewer`.

**pip for the current user only** (global to your account, not system-wide): `pip install --user cadquery-web-viewer` then ensure your user script directory (for example `~/.local/bin` on many Unix setups) is on `PATH`.

### Run from Python

Pass any solid you already built (CadQuery or build123d). The library starts a small local web server, opens a tab, and shows your model:

```python
from cadquery_web_viewer import show

show(my_solid)
```

By default the process **waits until you close the viewer tab** (same idea as closing the last connection to a live preview). That keeps one-shot scripts from exiting before you look at the model.

## What you get

- **Browser viewer** for 3D models: orbit, zoom, measurements, clipping, transparency, and related viewing tools.
- **glTF 2.0 / GLB** — a standard mesh format many 3D tools understand. The UI is built around the web [model-viewer](https://modelviewer.dev/) component, so you get common material and lighting behavior in the browser.
- **Live updates** while you change geometry in Python (the app keeps a channel open so the page can refresh when you publish again).
- **Optional disk cache** for uploaded GLBs when you run the long-lived server (see flags below).

## Run the app as a server

Use this when you want the viewer listening continuously—for example another machine, or a workflow where Python scripts only *push* models to an already-running process.

Start the Flask app (static UI plus HTTP API):

```bash
cadquery-web-viewer --host localhost --port 32323
```

**Cache** (separate idea): add `--cache-mode memory` or `--cache-mode disk`. With `disk`, set `--cache-dir` to the folder you want. Defaults live in the CLI; there are no environment-variable overrides for host, port, or cache mode.

## Run with Docker

The [Dockerfile](Dockerfile) in this repository builds an image with the **compiled frontend** and the **Python package** installed. Use it when you want the long-lived viewer server in a container instead of installing CadQuery tooling on the host.

**Build** from the repository root (use `linux/amd64` so the image matches the architecture of published `cadquery-ocp` wheels, including on Apple Silicon hosts):

```bash
docker build --platform linux/amd64 -t cadquery-web-viewer:local .
```

**Run** maps the default app port `32323` on the container to the same port on your machine. The process listens on all interfaces inside the container so you can reach it from the host.

```bash
docker run --rm --platform linux/amd64 -p 32323:32323 cadquery-web-viewer:local
```

Open `http://localhost:32323` in a browser. From Python on the host, use `server_type="remote"` and `remote_options` with the same host and port you published (see **Remote server** in [Call `show()` from Python](#call-show-from-python)).

**Configure the container** with environment variables read by [docker-entrypoint.sh](docker-entrypoint.sh) (these apply to the image entrypoint, not to a plain `cadquery-web-viewer` install on your PATH):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CADQUERY_WEB_VIEWER_HOST` | `0.0.0.0` | Bind address inside the container. |
| `CADQUERY_WEB_VIEWER_PORT` | `32323` | App port (match your `-p host:container` mapping). |
| `CADQUERY_WEB_VIEWER_CACHE_MODE` | `memory` | `memory` or `disk`. |
| `CADQUERY_WEB_VIEWER_CACHE_DIR` | *(empty)* | Required when cache mode is `disk`; mount a volume if you want the cache to persist. |
| `PUID` / `PGID` | *(unset)* | When both are set, the server runs as that uid/gid via `su-exec` (useful to match a bind-mounted cache directory). |

**Disk cache example:** mount a writable directory and point the cache there:

```bash
docker run --rm --platform linux/amd64 \
  -p 32323:32323 \
  -v cadquery-web-viewer-cache:/cache \
  -e CADQUERY_WEB_VIEWER_CACHE_MODE=disk \
  -e CADQUERY_WEB_VIEWER_CACHE_DIR=/cache \
  cadquery-web-viewer:local
```

An interactive walkthrough that prints a matching `docker run` line is in [`examples/remote/`](examples/remote/).

## Call `show()` from Python

### Embedded viewer (default)

`server_type="in-process"` is the default: one short-lived server thread, one browser session, shared tessellation with the full app.

```python
from cadquery_web_viewer import show

show(my_solid)
```

### Host, port, and timeouts

`server_options` is an ordinary dict. Keys include `host`, `port`, and `wait_for_client_timeout` (seconds to wait for the browser to connect).

```python
show(my_solid, server_options={"host": "127.0.0.1", "port": 32323, "wait_for_client_timeout": 180.0})
```

### Several `show()` calls in one script

Pass `block_until_disconnect=False` on every call **except** the last one so the embedded server stays up between publishes.

### Remote server (Flask already running)

First start `cadquery-web-viewer` in another terminal (or container). Then point `show()` at that process with `server_type="remote"` and a `remote_options` dict (`host`, `port`; optional `upload_timeout`, `post_timeout`).

```python
from cadquery_web_viewer import show

show(
    my_solid,
    server_type="remote",
    remote_options={"host": "localhost", "port": 32323},
)
```

The [`examples/remote/`](examples/remote/) script prints a command to start the server, then waits for you before calling `show()`.

### Buffer only, then export GLBs (no browser)

**Tessellation** here means turning CAD solids into triangle meshes (GLB) the viewer can draw.

Use `server_type="local"` when you only want models in memory—typical for CI or headless pipelines:

```python
from cadquery_web_viewer import show

show(my_solid, server_type="local")
```

Write everything currently in the buffer to a folder of `.glb` files:

```python
from cadquery_web_viewer import export_all

export_all("./glbs")
```

## Examples in this repo

| Folder | Purpose |
|--------|---------|
| [`examples/in-process/`](examples/in-process/) | Full build123d sample, `show()` with optional textures; with `CI` set, runs `export_all("export")` after the viewer closes (not run in GitHub Actions). |
| [`examples/remote/`](examples/remote/) | Same style of model sent with `server_type="remote"`. |

## Migrating from `yacv-server` / `yacv-viewer`

| Before (upstream names) | After (this fork) |
|-------------------------|-------------------|
| PyPI / import `yacv_server` | `cadquery-web-viewer` / `cadquery_web_viewer` |
| CLI `yacv-server` | `cadquery-web-viewer` or `python -m cadquery_web_viewer` |
| Implicit “use whatever server env says” | Explicit `server_type`: `"in-process"` (default), `"remote"`, or `"local"` |
| Separate process required for browser preview | Default `show()` embeds the server and blocks until preview connections close |
| Host / port via environment | `server_options` / `remote_options` on `show`, `remove`, `clear`, `show_all` |

Optional styling-related environment variables may still apply (for example default colors); **connection behavior** is controlled by the keyword arguments above.

## Develop the UI and Python backend

Target stack: **Python 3.10–3.12** (see `pyproject.toml`) and **Node** for the Vite frontend.

**1. Install dependencies**

```bash
uv sync
yarn install
```

If you do not use [uv](https://docs.astral.sh/uv/), create a virtual environment and run `pip install -e .` from the repo root instead of `uv sync`.

**2. Start the Python API** (default `http://localhost:32323`)

```bash
uv run cadquery-web-viewer
```

Same effect after install: `python -m cadquery_web_viewer`.

**3. Start the frontend** (second terminal)

```bash
yarn dev
```

Open the URL Vite prints (often `http://localhost:5173`). The viewer tries the same origin for `/api/updates`; when the page is not served by Flask, it falls back to `http://localhost:32323` so the UI and API stay aligned.

**Backend-only with a built UI:** run `yarn install` once, then `yarn build` (writes `dist/` at the repo root). Then run only `cadquery-web-viewer`. Flask serves that bundle when the packaged `frontend` tree is absent (see `FRONTEND_BASE_PATH` in the package). A full `yarn build` needs devDependencies (including `generate-license-file`). Installing with `NODE_ENV=production` skips those and the build will fail.

## Related projects

- [cq-studio](https://github.com/ccazabon/cq-studio) — alternative file-watch workflow; related viewer history.
- [build123d-docker](https://github.com/derhuerst/build123d-docker/pkgs/container/build123d) — containers for CAD tooling.
- [OCP.wasm](https://github.com/yeicor/OCP.wasm/) — OpenCASCADE compiled for WebAssembly (another browser CAD direction).

## Special thanks

[Yet Another CAD Viewer (YACV)](https://github.com/yeicor-3d/yet-another-cad-viewer) by Yeicor and contributors is the upstream project: a web-based CAD and GLB viewer with a Python backend for live tessellation, hot reload, and static export. This repository continues that MIT-licensed codebase as **cadquery-web-viewer** (import `cadquery_web_viewer`), with credit to the original authors. Use that repository for the legacy product name, the PyPI package `yacv-server`, and upstream issues and releases.

[MIT License](LICENSE). Third-party notices: [assets/licenses.txt](assets/licenses.txt).
