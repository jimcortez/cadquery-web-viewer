# Installation

For the shortest **pip + virtualenv** path (including a CadQuery quickstart), see [README.md](../README.md#quick-start).

The `cadquery-web-viewer` command is registered by the package. You only get it on your shell **PATH** when you install into an active environment, use **pipx**, or use **`uv tool install`** (below).

## pipx

pipx installs the app in an isolated environment and links the CLI into pipx’s binary directory so you can run it from any directory. If `cadquery-web-viewer` is not found, run `pipx ensurepath`, restart the shell, and confirm that directory is on your `PATH`.

```bash
pipx install cadquery-web-viewer
```

## uv tool

uv can do the same with **tools**: an isolated install plus executables on your user path (commonly `~/.local/bin`). Add that directory to `PATH` if your shell does not already.

```bash
uv tool install cadquery-web-viewer
```

To upgrade later: `pipx upgrade cadquery-web-viewer` or `uv tool upgrade cadquery-web-viewer`.

## pip for the current user only

Global to your account, not system-wide: `pip install --user cadquery-web-viewer`, then ensure your user script directory (for example `~/.local/bin` on many Unix setups) is on `PATH`.

## Docker

The [Dockerfile](../Dockerfile) in this repository builds an image with the **compiled frontend** and the **Python package** installed. Use it when you want the long-lived viewer server in a container instead of installing CAD tooling on the host.

### Pull a published image (recommended)

Tagged releases publish `linux/amd64` images to **GitHub Container Registry**:

```bash
docker pull ghcr.io/jimcortez/cadquery-web-viewer:latest
docker run --rm -p 32323:32323 ghcr.io/jimcortez/cadquery-web-viewer:latest
```

> **Apple Silicon / arm64 hosts:** the image is `linux/amd64` only because `cadquery-ocp` 7.8.x (pinned via `build123d>=0.10,<0.11`) ships **no** `manylinux_aarch64` wheel. Pass `--platform linux/amd64` when running on an arm64 host so Docker uses Rosetta/QEMU emulation:
> ```bash
> docker run --rm --platform linux/amd64 -p 32323:32323 ghcr.io/jimcortez/cadquery-web-viewer:latest
> ```

### Build locally

```bash
docker build -t cadquery-web-viewer:local .
docker run --rm -p 32323:32323 cadquery-web-viewer:local
```

(On arm64 hosts, add `--platform linux/amd64` to both commands.)

Open `http://localhost:32323` in a browser. From Python on the host, use `server_type="remote"` and `remote_options` with the same host and port you published (see [Usage](usage.md#remote-server-flask-already-running)).

**Configure the container** with environment variables read by [docker-entrypoint.sh](../docker-entrypoint.sh) (these apply to the image entrypoint, not to a plain `cadquery-web-viewer` install on your PATH):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CADQUERY_WEB_VIEWER_HOST` | `0.0.0.0` | Bind address inside the container. |
| `CADQUERY_WEB_VIEWER_PORT` | `32323` | App port (match your `-p host:container` mapping). |
| `CADQUERY_WEB_VIEWER_CACHE_MODE` | `memory` | `memory` or `disk`. |
| `CADQUERY_WEB_VIEWER_CACHE_DIR` | *(empty)* | Required when cache mode is `disk`; mount a volume if you want the cache to persist. |
| `PUID` / `PGID` | *(unset)* | When both are set, the server runs as that uid/gid via `su-exec` (useful to match a bind-mounted cache directory). |

**Disk cache example:** mount a writable directory and point the cache there:

```bash
docker run --rm \
  -p 32323:32323 \
  -v cadquery-web-viewer-cache:/cache \
  -e CADQUERY_WEB_VIEWER_CACHE_MODE=disk \
  -e CADQUERY_WEB_VIEWER_CACHE_DIR=/cache \
  cadquery-web-viewer:local
```

An interactive walkthrough that prints a matching `docker run` line is in [`examples/remote/`](../examples/remote/).
