# cadquery-web-viewer examples

Small scripts that assume the full **cadquery-web-viewer** repository (or an installed `cadquery-web-viewer` plus `build123d`) on Python 3.12.

## Layout

| Directory | What it demonstrates |
|-----------|----------------------|
| [`in-process/`](in-process/) | `server_type="local"`: tessellate into the buffer only; CI also runs `export_all` to `export/`. |
| [`remote/`](remote/) | Same model published with `server_type="remote"` while `cadquery-web-viewer` runs in another terminal. |

Install from the repo root:

```bash
cd /path/to/yet-another-cad-viewer
uv sync
# or: pip install -r examples/requirements.txt
```

CI runs [`in-process/object.py`](in-process/object.py) and uploads the `export/` GLB artifacts from the workflow.
