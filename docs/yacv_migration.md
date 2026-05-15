# Migrating from `yacv-server` / `yacv-viewer`

This fork keeps the same overall idea as [Yet Another CAD Viewer (YACV)](https://github.com/yeicor-3d/yet-another-cad-viewer) but renames packages and makes server modes explicit.

| Before (upstream names) | After (this fork) |
|-------------------------|-------------------|
| PyPI / import `yacv_server` | `cadquery-web-viewer` / `cadquery_web_viewer` |
| CLI `yacv-server` | `cadquery-web-viewer` or `python -m cadquery_web_viewer` |
| Implicit “use whatever server env says” | Explicit `server_type`: `"in-process"` (default), `"remote"`, or `"local"` |
| Separate process required for browser preview | Default `show()` embeds the server and blocks until preview connections close |
| Host / port via environment | `server_options` / `remote_options` on `show`, `remove`, `clear`, `show_all` |

Optional styling-related environment variables may still apply (for example default colors); **connection behavior** is controlled by the keyword arguments above.
