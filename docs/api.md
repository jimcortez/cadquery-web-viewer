# HTTP API

The `cadquery-web-viewer` Flask app serves the browser UI plus a small JSON/multipart API under **`/api`**. Unless noted, responses include broad CORS headers (`Access-Control-Allow-Origin: *`, and on **`OPTIONS`** requests the methods/headers Flask wires for preflight).

Assumed base URL: `http://<host>:<port>` (default port **32323**). Interactive use from Python is described in [usage.md](usage.md).

---

## `GET` / `HEAD` `OPTIONS` — `/api/updates`

Server-Sent Events (**SSE**) stream of scene updates for the viewer.

| Method | Behavior |
|--------|----------|
| `GET` | `Content-Type: text/event-stream`, `Cache-Control: no-cache`. Body is an SSE stream. |
| `HEAD` | Same content type; empty body (no stream). |
| `OPTIONS` | `204 No Content` with CORS headers. |

Stream behavior:

- First lines include `retry: 100` (reconnect hint in milliseconds).
- Periodic comment frames `:keep-alive` may appear when nothing else is published.
- Each event **`data`** line is a single JSON object (compact encoding, no extra whitespace), matching the shape below.

### SSE payload (`data:` JSON)

Derived from `UpdatesApiData` in the server (`name`, `hash`, optional `is_remove`):

| Field | Type | Meaning |
|-------|------|---------|
| `name` | string | Object identifier (must match `/api/object/...` paths). |
| `hash` | string | Content fingerprint so clients can skip redundant reloads when unchanged. |
| `is_remove` | boolean \| omitted | When `true`, remove this object from the scene. When omitted or `false`, show/update it. |

Example (show or update):

```json
{"name":"part_a","hash":"abc123","is_remove":false}
```

Example (remove):

```json
{"name":"part_a","hash":"abc123","is_remove":true}
```

---

## `GET` / `HEAD` `OPTIONS` — `/api/object/<name>`

Download the GLB for a shown object. `<name>` is a URL path segment; reserved characters should be percent-encoded (the server applies `urllib.parse.unquote`).

| Method | Behavior |
|--------|----------|
| `GET` | `200`: body is raw GLB (`Content-Type: model/gltf-binary`). Headers include `Content-Disposition: attachment; filename="<name>.glb"` and `E-Tag: "<etag>"`. |
| `HEAD` | Same headers as `GET`; `Content-Length` set to GLB size; empty body. |
| `OPTIONS` | `204` with CORS headers. |

| Status | Meaning |
|--------|---------|
| `404` | No such object (or nothing to export). |

---

## `POST` `OPTIONS` — `/api/show`

Upload a pre-built GLB and register it like an in-process `show()` of raw bytes.

**Content type:** `multipart/form-data` with exactly:

| Part | Required | Description |
|------|----------|-------------|
| `glb` | yes | File field: binary GLB (`model/gltf-binary`). |
| `metadata` | yes | Form field: JSON **object** (string). |

### `metadata` JSON fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | yes | string | Unique object name (overwrites prior uploads with the same name). |
| `hash` | yes | string | Hash string stored with the object (clients use it in SSE payloads). |
| `auto_clear` | no | boolean | Default `false`. If `true`, clears existing objects before applying this upload (see `except_names`). |
| `except_names` | no | string[] | When `auto_clear` is true: names **not** removed during that clear. Must be a JSON array of strings if present. |
| `kwargs` | no | object | Optional viewer/metadata dict (same role as keyword args on Python `show()`). Must be a JSON object if present; arbitrary keys supported server-side. |

On success: `200`, `Content-Type: application/json`, body `{"ok":true}`.

| Error | Typical cause |
|-------|----------------|
| `400` | Missing `glb` or `metadata`, invalid JSON in `metadata`, missing `name`/`hash`, or `except_names` not a list. |

Disk cache (when the server runs with `--cache-mode disk`): a successful upload is also written through to the configured cache directory.

---

## `POST` `OPTIONS` — `/api/remove`

Remove one object by name.

**Content type:** `application/json`

Body:

```json
{"name":"part_a"}
```

`name` must be a non-empty string.

Success: `200`, body `{"ok":true}`.

| Error | Typical cause |
|-------|----------------|
| `400` | Missing or non-string `name`. |

With disk cache enabled, the cached entry for that name is deleted.

---

## `POST` `OPTIONS` — `/api/clear`

Remove **all** shown objects.

**Content type:** `application/json`

Body may be an empty object `{}` (what the bundled Python client sends).

Success: `200`, body `{"ok":true}`.

With disk cache enabled, the cache is cleared as well.

---

## Static UI (not under `/api`)

| Route | Behavior |
|-------|----------|
| `GET /` | Serves `index.html` from the bundled frontend (or repo `dist/` in dev layouts). **`503`** if no frontend bundle is found. |
| `GET /<path>` | Serves a file under the frontend root if it exists and resolves safely below that root. Requests whose path starts with `api/` are rejected with **`404`** so they do not shadow the blueprint. Otherwise, if no file matches, **`index.html`** is returned when present (**SPA fallback**). **`503`** if no frontend. |

---

## Python client parity

The package helpers in `cadquery_web_viewer.http_client` call:

- `POST /api/show` — multipart as above (`remote_show`).
- `POST /api/remove` with `{"name": ...}` (`remote_remove`).
- `POST /api/clear` with `{}` (`remote_clear`).

Texture tuples in `kwargs` are encoded for JSON as `data:<mime>;base64,...` strings before upload.
