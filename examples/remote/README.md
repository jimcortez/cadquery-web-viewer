# Remote client

Same geometry as the in-process example, but models are uploaded to a **separately started** `cadquery-web-viewer` server (`server_type="remote"`).

## Run

1. From the repository root, install dependencies (`uv sync` or `pip install -r examples/requirements.txt`).

2. Run this script; it will print a command to copy into **another** terminal:

   ```bash
   uv run python examples/remote/object.py
   ```

3. In that second terminal, start the server, then return to the first terminal and press **Enter** when prompted.

The script defaults to `localhost:32323`; edit `REMOTE_HOST` / `REMOTE_PORT` in `object.py` if your server uses different values.

This example is interactive only. It exits immediately when `CI` is set so automated jobs do not block on `input()`.
