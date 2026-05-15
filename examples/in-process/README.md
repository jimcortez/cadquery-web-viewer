# Local-buffer example (this folder)

This script tessellates with `show(..., server_type="local")`: models go into the in-memory buffer **only** (no browser, no Flask).

When **`CI`** is set, the script also runs `export_all("export")` after `show()` returns (after you close the viewer), writing `.glb` files under `export/` at the repository root. This sample is not run in GitHub Actions: the default `show()` path expects a browser session and would time out on headless runners.

For the **embedded viewer** (default `show()` / `server_type="in-process"`), see [docs/usage.md](../../docs/usage.md). For publishing to a server running in another terminal, see [`../remote/`](../remote/).

## Run

From the repository root:

```bash
uv run python examples/in-process/object.py
```
