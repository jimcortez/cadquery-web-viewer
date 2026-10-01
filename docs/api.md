# HTTP API

The `cadquery-web-viewer` Flask app serves the browser UI plus a REST API under **`/api`**. Unless noted, responses include broad CORS headers (`Access-Control-Allow-Origin: *`, and on **`OPTIONS`** the methods/headers listed below).

Assumed base URL: `http://<host>:<port>` (default port **32323**). Interactive use from Python is described in [usage.md](usage.md).

---

## Trust model

`cadquery-web-viewer` is a developer tool; the HTTP server is intended to run on **localhost or a trusted network**. The defaults that make local development convenient also expand the attack surface if the server is exposed to untrusted clients:

- **CORS is wide open.** Every response carries `Access-Control-Allow-Origin: *`, so any origin (including pages you didn't author) can call the API from a browser tab.
- **URL import.** `PUT /api/object/<name>` accepts a JSON body of the form `{"url": "https://…"}`. The server fetches that URL over `http`/`https` and stores the GLB. Fetches are capped at `MAX_GLB_BYTES` (50 MB; see `cadquery_web_viewer/url_import.py`), but the URL itself is otherwise unrestricted (any host, any path). This is convenient but means any caller can cause the server to make arbitrary outbound HTTP requests.
- **No auth, rate limiting, or TLS.** The runtime is plain `flask.Flask.run`. Use a reverse proxy (e.g. nginx, Caddy, Traefik) if you need any of those.

**Recommendation:** bind to a private interface (`--host 127.0.0.1` is the default) and front the server with a reverse proxy if you need to expose it to other machines. To opt out of URL import entirely, block requests to `PUT /api/object/<name>` with a JSON body at the proxy. See [SECURITY.md](../SECURITY.md) for the full hardening guide and the private vulnerability-reporting channel.

---

## Typical remote workflow

1. **`PUT /api/object/<name>`** — store a GLB version (does not update the viewer).
2. **`POST /api/events`** — publish `object.created` or `object.versioned` so subscribers load the model.
3. The viewer **`GET /api/object/<name>?version=<n>`** — download the GLB bytes.

---

## `/api/events`

Scene notifications (Server-Sent Events + publish). No GLB bodies on this resource.

### `GET` / `HEAD` / `OPTIONS`

| Method | Behavior |
|--------|----------|
| `GET` | `Content-Type: text/event-stream`, `Cache-Control: no-cache`. SSE stream. |
| `HEAD` | Same content type; empty body. |
| `OPTIONS` | `204` with CORS. |

Stream: `retry: 100`, periodic `:keep-alive` comments, each event one `data: ` line (compact JSON).

New connections receive **live** events only (no replay of past publishes). Cached objects are listed with `GET /api/object`; the viewer loads them when the user selects them in the UI (or when Python publishes a new event while the tab is connected).

### Event types

| `type` | Meaning | Viewer |
|--------|---------|--------|
| `object.created` | New object in scene | Add draw-list entry; fetch GLB |
| `object.versioned` | New version of existing name | Replace model; fetch GLB |
| `object.removed` | Remove from scene | Remove draw-list entry |
| `scene.cleared` | Clear scene | Clear except `except_names` |
| `server.shutdown` | Server stopping | Disconnect |

**`object.created` / `object.versioned`** (required fields: `name`, `version`, `hash`):

```json
{"type":"object.created","name":"part_a","version":1,"hash":"abc123"}
```

**`object.removed`:**

```json
{"type":"object.removed","name":"part_a","hash":"abc123"}
```

**`scene.cleared`:**

```json
{"type":"scene.cleared","except_names":["fixture"]}
```

**`server.shutdown`:**

```json
{"type":"server.shutdown"}
```

### `POST /api/events`

Publish one event or a batch.

**Content-Type:** `application/json`

Single event: one envelope object. Batch: `{"events":[...]}`.

Validation: `object.created` / `object.versioned` require a matching stored `name`, `version`, and `hash`. `object.created` fails with **`409`** if the name is already in the scene. `object.versioned` fails with **`409`** if the name is not in the scene.

**Success:** `204 No Content`.

---

## `/api/object`

Versioned GLB storage. Object-level **`notes`** and **`settings`** apply to all versions of a name.

Every stored object is an **assembly**: one GLB whose root node has one child node per named part
(a single shape is an assembly with one part). The optional per-version **`assembly`** manifest
describes the parts; see [Assemblies](#assemblies) below.

### `GET /api/object`

List all objects. One row per name; top-level `version` / `hash` / `created_at` / `kwargs` are the **latest** version; `versions` lists older versions **newest first** (excluding latest).

```json
{
  "objects": [
    {
      "name": "part_a",
      "notes": null,
      "settings": {},
      "version": 2,
      "hash": "...",
      "kwargs": {"assembly": {"schema": 1, "name": "part_a", "tags": [], "parts": [{"name": "part_a", "index": 0, "color": null, "tags": []}]}},
      "assembly": {"schema": 1, "name": "part_a", "tags": [], "parts": [{"name": "part_a", "index": 0, "color": null, "tags": []}]},
      "created_at": "2026-05-16T18:30:00.123Z",
      "in_memory": true,
      "on_disk": true,
      "versions": [
        {"version": 1, "hash": "...", "created_at": "2026-05-16T16:00:00.000Z", "assembly": null}
      ]
    }
  ]
}
```

`created_at` values are ISO 8601 UTC (e.g. `2026-05-16T18:30:00.123Z`). `assembly` is the
manifest stored in that version's `kwargs["assembly"]`, or `null` when the version has none
(plain GLB imports, versions stored before assemblies existed).

### `PUT /api/object/<name>`

Store a GLB version. **Does not** publish SSE. Name comes from the URL path only.

Use **either** multipart upload **or** JSON import (not both).

**Multipart:** `glb` (file), `metadata` (JSON string with required `hash`, optional `kwargs`).
Put the assembly manifest in `kwargs.assembly` so it is listed without parsing the GLB.

**JSON** (`Content-Type: application/json`):

```json
{
  "url": "https://example.com/model.glb",
  "hash": "optional-sha256-hex",
  "kwargs": { "source_url": "https://example.com/model.glb" }
}
```

| Field | Behavior |
|-------|----------|
| `url` | Required for JSON mode. Server fetches the GLB over `http`/`https` (max 50 MB). |
| `hash` | Optional. If omitted, `sha256(glb_bytes)` hex digest. |
| `kwargs` | Optional. `source_url` is set to `url` when not provided. |

| Query | Behavior |
|-------|----------|
| *(none)* | Next version (`1`, `2`, …) |
| `force-version=<n>` | Create or overwrite version `n` |

**Errors (JSON import):** `400` invalid body; `413` file too large; `502` fetch failed or not a GLB.

**Success:** `201` + `{"name","version","hash"}` and header `X-Object-Version`.

### `GET` / `HEAD` `/api/object/<name>`

| `Accept` | Behavior |
|----------|----------|
| `model/gltf-binary` (default) | GLB for latest or `?version=<n>` |
| `application/json` | Object descriptor (no GLB body) |

`E-Tag` on binary responses: `"<hash>-v<n>"`.

### `PATCH /api/object/<name>`

Update `name` (rename), `notes`, and/or `settings`. Does not upload GLB or publish events.

**JSON body** (at least one field):

| Field | Behavior |
|-------|----------|
| `name` | Rename; moves all versions; **`409`** if taken |
| `notes` | Set or `null` to clear |
| `settings` | Merge keys; `null` value removes a key. Values: string, number, or `null` only |

**Success:** `200` + full object descriptor (same shape as JSON `GET`).

### `DELETE /api/object/<name>`

| Query | Behavior |
|-------|----------|
| *(none)* | Delete all versions; auto-publish `object.removed` if in scene |
| `force-version=<n>` | Delete one version only |

**Success:** `204`.

### `DELETE /api/object`

Delete all stored objects. Does not publish `scene.cleared` (call `POST /api/events` separately if needed).

---

## Assemblies

An assembly is one object name, one GLB per version, and a list of named **parts**. Parts are
shown/hidden and recoloured individually in the viewer; removal and versioning happen per
assembly.

**GLB layout** (as produced by the Python tessellator, `cadquery_web_viewer.tessellate.tessellate_parts`):

| Element | Content |
|---------|---------|
| `nodes[0]` | root: `name` = object name, no mesh, `children` = part nodes, `extras["__cadquery_web_viewer_assembly"]` = manifest |
| `nodes[i]` | one per part: `name` = part name, `mesh` = its mesh, `extras["__cadquery_web_viewer_part"]` = part name |
| `meshes[i-1]` | TRIANGLES / LINES / POINTS primitives with `COLOR_0`; each primitive also carries the part extras key |
| `materials` | one per part (face colour is baked as vertex colour, not as `baseColorFactor`) |

The browser derives the part list from the part extras key, so an uploaded GLB is self-describing.
A GLB without part tags (e.g. a URL import) is treated as a single part named after the object.

**Manifest** (`kwargs.assembly`, schema `1`):

```json
{
  "schema": 1,
  "name": "k6_1",
  "tags": ["bevel", "part:k6_1"],
  "parts": [
    {"name": "segment_00", "index": 0, "color": "#e04a4a", "tags": ["body:segment_00", "index:0"]},
    {"name": "segment_01", "index": 1, "color": null, "tags": ["body:segment_01", "index:1"]}
  ]
}
```

`color` is `#rrggbb` or `null` (default face colour). Because glTF writers drop `null` and empty
lists from `extras`, readers should treat missing `color`/`tags` as those defaults
(`cadquery_web_viewer.assembly.normalize_manifest`).

---

## Static UI

| Route | Behavior |
|-------|----------|
| `GET /` | `index.html` from bundled frontend. **`503`** if missing. |
| `GET /<path>` | Static assets or SPA fallback. Paths starting with `api/` → **`404`**. |

---

## Python client

Helpers in `cadquery_web_viewer.http_client`:

- `remote_show` — `PUT` each object, then `POST /api/events` (`scene.cleared` + `object.created` / `object.versioned`). CadQuery `Assembly` / `AssemblySpec` inputs become one multi-part object.
- `remote_show_assembly` — publish one object built from `(part_name, shape)` pairs, a CadQuery `Assembly` or an `AssemblySpec`.
- `remote_show_glb` — publish an already-built GLB (with optional `kwargs["assembly"]` manifest and hash).
- `remote_show_payloads` — publish `(name, glb, hash, kwargs)` tuples from `engine.prepare_glb_upload_batch` / `engine.prepare_assembly_upload`.
- `remote_remove` — `DELETE /api/object/<name>`.
- `remote_clear` — `POST scene.cleared` + `DELETE /api/object`.
- `remote_list_objects` — `GET /api/object`.
- `remote_patch_object` — `PATCH /api/object/<name>`.

Texture tuples in upload `kwargs` are encoded as `data:<mime>;base64,...` in JSON metadata.
