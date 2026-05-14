# Local-buffer example (this folder)

This script tessellates with `show(..., server_type="local")`: models go into the in-memory buffer **only** (no browser, no Flask).

When **`CI`** is set (for example in GitHub Actions), it also runs `export_all("export")` and writes `.glb` files under `export/` at the repository root.

For the **embedded viewer** (default `show()` / `server_type="in-process"`), see the main [README](../../README.md) client section. For publishing to a server running in another terminal, see [`../remote/`](../remote/).

## Run

From the repository root:

```bash
uv run python examples/in-process/object.py
```
