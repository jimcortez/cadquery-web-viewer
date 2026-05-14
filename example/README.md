# cadquery-web-viewer example

## Installation

1. Copy or clone this folder in the context of the full **cadquery-web-viewer** repository (it depends on the repo root `pyproject.toml` / `uv.lock` when using `uv`).
2. With Python 3.12 and [uv](https://docs.astral.sh/uv/) (or `pip`), install dependencies:

```bash
cd /path/to/cadquery-web-viewer
uv sync
# or: pip install -r example/requirements.txt
```

## Usage

### Development with hot-reloading

1. Start the bundled viewer and API in one terminal:

   ```bash
   cadquery-web-viewer
   ```

   Defaults to `http://localhost:32323`. Use `--host` / `--port` or `CADQUERY_WEB_VIEWER_HOST` / `CADQUERY_WEB_VIEWER_PORT` to change the bind address.

2. In another terminal, run `uv run python example/object.py` (or `python object.py` from the `example/` directory with the venv active). Each `show(...)` call uploads tessellated models to that server over HTTP so the browser updates live.

For a **local-only** workflow (no Flask process, useful for CI or exporting GLBs without a browser), set `CADQUERY_WEB_VIEWER_DISABLE_SERVER=1` before importing `cadquery_web_viewer`. Then `show()` writes into an in-process buffer and `export_all()` works as before.

The recommended way for interactive editing is still cell mode (`#%%`) in an IDE so slow imports run once while you iterate on `show(...)`.

### Static final deployment

Once your model is complete, you may want to share it with others using the same viewer.

Export the model as `.glb` in your script (as in `object.py` when `CI` is set). Host the built viewer and the `.glb` files on any static server, then share a link of the form:

`https://<your-site>/?preload=<url-to-object.glb>`

The [Yet Another CAD Viewer](https://yeicor-3d.github.io/yet-another-cad-viewer/) upstream deployment is a useful reference for the same URL parameters on the original project’s hosted demo.

For CI-built artifacts from this repo, see [.github/workflows/build.yml](../.github/workflows/build.yml) and the deployment workflows under [.github/workflows/](../.github/workflows/).
