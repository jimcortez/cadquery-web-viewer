# cadquery-web-viewer v2.0.0

Release notes since **[v1.1.0](https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v1.1.0)**.

v2.0.0 is a **major** release: the HTTP API is redesigned around **versioned object storage** and a **typed event stream**. The browser viewer and Python remote client were updated to match. If you integrate over HTTP or maintain custom clients, plan a migration using the table below and [docs/api.md](api.md).

---

## Breaking changes

### HTTP API

| v1.1.0 | v2.0.0 |
|--------|--------|
| `GET /api/updates` (SSE) | `GET /api/events` (SSE) |
| `POST /api/show` (multipart upload + scene update) | `PUT /api/object/<name>` then `POST /api/events` |
| `POST /api/remove` | `DELETE /api/object/<name>` |
| `POST /api/clear` | `POST /api/events` (`scene.cleared`) + `DELETE /api/object` |
| `GET /api/object/<name>` (latest GLB only) | Same path; optional `?version=<n>`; JSON descriptor via `Accept: application/json` |

**SSE payloads** no longer use `{name, hash, is_remove}`. Events are typed envelopes, for example:

```json
{"type":"object.created","name":"part_a","version":1,"hash":"abc123"}
{"type":"object.versioned","name":"part_a","version":2,"hash":"def456"}
{"type":"object.removed","name":"part_a","hash":"abc123"}
{"type":"scene.cleared","except_names":["fixture"]}
{"type":"server.shutdown"}
```

**Upload flow:** storing a GLB with `PUT /api/object/<name>` does **not** update the live viewer. Publish `object.created` or `object.versioned` via `POST /api/events` so subscribers load the model. The viewer fetches bytes with `GET /api/object/<name>?version=<n>`.

**Removed endpoints:** `/api/show`, `/api/remove`, `/api/clear`, `/api/updates`.

### Python `http_client`

`remote_show`, `remote_remove`, and `remote_clear` use the new API internally. Custom code that called `/api/show` or parsed the old SSE format must be updated.

**New helpers:** `remote_list_objects()`, `remote_patch_object()` (rename, notes, settings).

### Versioning semantics

- Each object **name** can hold multiple GLB **versions** (`1`, `2`, …).
- `PUT` without `force-version` allocates the next version; `force-version=<n>` creates or overwrites a specific version.
- `DELETE` without query removes all versions; `force-version=<n>` removes one version only.
- Object-level `notes` and `settings` apply across all versions of a name.

---

## Features

### Versioned object store

- New `VersionedObjectStore` and `object_store` module back disk/memory GLB storage, version history, rename, and per-object metadata.
- `GET /api/object` lists all objects with latest version metadata and older versions (newest first).
- `PUT /api/object/<name>` accepts JSON `{"url": "https://..."}` so the server fetches and stores a remote GLB (optional `hash`, `kwargs`).
- `PATCH /api/object/<name>` updates `name`, `notes`, and/or `settings` without uploading a new GLB.
- Binary responses use `E-Tag: "<hash>-v<n>"` and response header `X-Object-Version` on upload.

### Event publishing

- `POST /api/events` accepts a single event or `{"events":[...]}` batch.
- Validation: `object.created` / `object.versioned` require a matching stored `name`, `version`, and `hash`; conflicts return **409**.

### Viewer and rendering

- **Blank viewport fix:** align **three.js** with **@google/model-viewer** (pinned via `resolutions`); dismiss the loading poster on model reveal and progress completion.
- **Orientation gizmo:** no longer corrupts the main scene graph (isolated render path).
- **Double-sided materials** on GLB export (Python tessellation and frontend glTF transform) so thin faces remain visible.
- Frontend loads models by **versioned URL** and handles the new event types in `frontend/misc/network.ts`.

### Documentation

- [docs/api.md](api.md) rewritten for the REST + events model, remote workflow, and Python client parity.

---

## Fixes and maintenance

- **CI:** `deploy-pypi` sets `GH_REPO` so `gh release upload` works without a checkout in that job.
- **CI:** Frontend `vue-tsc` strict checks pass on GitHub Actions (safe casts for `globalThis.THREE` and model-viewer progress events).

---

## Upgrade guide

1. **Remote / HTTP integrations**
   - Replace SSE subscription to `/api/updates` with `/api/events`.
   - Replace `POST /api/show` with `PUT /api/object/<name>` + `POST /api/events`.
   - Replace remove/clear POSTs with `DELETE` and/or `scene.cleared` events as documented in [api.md](api.md).

2. **Python users**
   - Upgrade with `pip install -U cadquery-web-viewer` (or your usual install path).
   - Existing `show(..., server_type="remote")` and `remote_*` helpers are updated; no API change required unless you called HTTP endpoints directly.

3. **Custom clients**
   - Parse typed `type` fields on SSE events.
   - Request specific GLB revisions with `?version=<n>` when replaying or diffing models.

4. **Documentation**
   - Full endpoint reference: [docs/api.md](api.md)
   - Usage and `show()` options: [docs/usage.md](usage.md)

---

## Full changelog (commits since v1.1.0)

| Commit | Summary |
|--------|---------|
| `af181de` | Versioned object API; `/api/events`; viewer blank-screen, gizmo, and double-sided GLB fixes |
| `efcd6a3` | CI: `GH_REPO` for PyPI release asset upload |
| `bb322c9` | Version bump automation (1.1.1) |
| `ff5ab86` | CI: vue-tsc strict type assertions in frontend |

---

## Assets

GitHub Releases for this tag include:

- `cadquery-web-viewer-v2.0.0-frontend.zip` — static UI bundle
- Python **wheel** and **sdist** on PyPI (`cadquery-web-viewer`)
