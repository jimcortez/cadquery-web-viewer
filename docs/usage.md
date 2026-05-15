# Usage

## Run the app as a server

Use this when you want the viewer listening continuously—for example another machine, or a workflow where Python scripts only *push* models to an already-running process.

Start the Flask app (static UI plus HTTP API):

```bash
cadquery-web-viewer --host localhost --port 32323
```

### Cache and CLI defaults

Add `--cache-mode memory` or `--cache-mode disk`. With `disk`, set `--cache-dir` to the folder you want.

Defaults live in the CLI; for a normal install there are **no** environment-variable overrides for host, port, or cache mode. The Docker image is different: its entrypoint reads `CADQUERY_WEB_VIEWER_*` variables—see [install.md](install.md#docker).

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

The [`examples/remote/`](../examples/remote/) script prints a command to start the server, then waits for you before calling `show()`.

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
