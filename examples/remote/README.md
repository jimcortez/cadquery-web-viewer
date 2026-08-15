# Remote client

Same geometry as the in-process example, but models are uploaded to a **separately started** `cadquery-web-viewer` server (`server_type="remote"`).

## Run

1. From the repository root, install dependencies (`uv sync` or `pip install -r examples/requirements.txt`).

2. **If you use Docker:** build the viewer image from the repo root. **If you use the CLI server only**, skip this step once `cadquery-web-viewer` is on your `PATH`.

   ```bash
   docker build -t cadquery-web-viewer:test .
   ```

   The build is native to your host architecture, arm64 included — no `--platform` flag is needed.

3. Run this script; it will print a **`docker run`** line and a **`cadquery-web-viewer`** line—use whichever you prefer—in **another** terminal:

   ```bash
   uv run python examples/remote/object.py
   ```

4. In that second terminal, start the server with **Docker** or the **command line** (whichever you prefer), then return to the first terminal and press **Enter** when prompted.

The script defaults to `localhost:32323` for the Python client. Override the printed image with `CADQUERY_WEB_VIEWER_DOCKER_IMAGE`, or edit `REMOTE_HOST` / `REMOTE_PORT` in `object.py` if you use a different host or port.

This example is interactive only. It exits immediately when `CI` is set so automated jobs do not block on `input()`.
