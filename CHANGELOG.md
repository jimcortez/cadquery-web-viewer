# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project documentation: `SECURITY.md`, expanded `CONTRIBUTING.md`, GitHub issue
  and pull-request templates, `CODEOWNERS`.
- README badges (PyPI, Python versions, license, CI, downloads), live-demo link,
  and a "Trust model" section.
- Trust-model section in `docs/api.md` (CORS, URL import, deployment posture).
- CI: real `test-python` and `test-frontend` jobs running `ruff`, `pyright`,
  `unittest`, `yarn type-check`, with coverage upload.
- CI: weekly CodeQL scans for `python` and `javascript-typescript`.
- Backend tests covering `object_store`, `pubsub`, `events_api`, `engine`,
  `glb_cache`, the object/scene Flask routes, and the SSE event stream.
- `engine.scene_active_names()` public accessor; `object_store.UNSET` public
  sentinel.
- GHCR publish job in the release workflow (image: `ghcr.io/jimcortez/
  cadquery-web-viewer`). Image is `linux/amd64` only — `cadquery-ocp` 7.8.x
  (transitively pinned via `build123d>=0.10,<0.11`) has no
  `manylinux_aarch64` wheel; arm64 hosts need `--platform linux/amd64`.

### Changed
- All GitHub Actions are now pinned to commit SHAs (with the human tag in a
  trailing comment for Dependabot).
- Single source of version truth: `package.json` is authoritative; the Hatchling
  build hook reads it and injects the version into wheel metadata.
- Yarn 1 → Yarn 4 (Berry) via Corepack with the `node-modules` linker. `yarn
  install --frozen-lockfile` is replaced by `yarn install --immutable`.
- Python support remains `>=3.10,<3.13`. Adding 3.13 was attempted in this
  release but blocked by `vtk==9.3.1` (transitively pinned through `build123d`
  → `cadquery-ocp` 7.8.x), which has no `cp313` wheels. Re-add when `build123d`
  adopts `cadquery-ocp` 7.9.3.1+ which depends on `vtk==9.6.x`.
- `package.json` `author` corrected to **Jim Cortez** (Yeicor remains credited
  in *Special thanks* and the LICENSE).
- Pyright reporting tightened: argument/return/assignment/optional-access checks
  promoted from "off" to "warning" (errors will follow in a later release).
- `MAX_GLB_BYTES` (URL-import size cap) is documented in `docs/api.md` so
  integrators don't have to read source to find it.
- CLI prints a deployment-posture log line on startup pointing at
  [SECURITY.md](SECURITY.md).

### Removed
- `docs/release-notes-v2.0.0.md` (folded into this changelog under
  [v2.0.0](#200) below).
- Hardcoded `--platform linux/amd64` requirement from `docs/install.md` for
  hosts where ARM64 wheels of `cadquery-ocp` are available.

## [2.0.0]

Major release: the HTTP API is redesigned around **versioned object storage**
and a **typed event stream**. The browser viewer and Python remote client were
updated to match.

### Breaking changes — HTTP API

| v1.1.0 | v2.0.0 |
|--------|--------|
| `GET /api/updates` (SSE) | `GET /api/events` (SSE) |
| `POST /api/show` (multipart upload + scene update) | `PUT /api/object/<name>` then `POST /api/events` |
| `POST /api/remove` | `DELETE /api/object/<name>` |
| `POST /api/clear` | `POST /api/events` (`scene.cleared`) + `DELETE /api/object` |
| `GET /api/object/<name>` (latest GLB only) | Same path; optional `?version=<n>`; JSON descriptor via `Accept: application/json` |

SSE payloads are now typed envelopes (`{"type":"object.created", …}`). Storing
a GLB with `PUT /api/object/<name>` does **not** update the live viewer;
publish `object.created` or `object.versioned` via `POST /api/events` so
subscribers load the model.

### Breaking changes — Python `http_client`

`remote_show`, `remote_remove`, and `remote_clear` use the new API internally.
Custom code that called `/api/show` or parsed the old SSE format must be
updated.

New helpers: `remote_list_objects()`, `remote_patch_object()` (rename, notes,
settings).

### Versioning semantics

- Each object **name** can hold multiple GLB **versions** (`1`, `2`, …).
- `PUT` without `force-version` allocates the next version; `force-version=<n>`
  creates or overwrites a specific version.
- `DELETE` without query removes all versions; `force-version=<n>` removes one
  version only.
- Object-level `notes` and `settings` apply across all versions of a name.

### Added

- Versioned `VersionedObjectStore` and `object_store` module backing disk and
  memory GLB storage, version history, rename, and per-object metadata.
- `GET /api/object` lists all objects with latest version metadata and older
  versions (newest first).
- `PUT /api/object/<name>` accepts JSON `{"url": "https://..."}` so the server
  fetches and stores a remote GLB (optional `hash`, `kwargs`).
- `PATCH /api/object/<name>` updates `name`, `notes`, and/or `settings` without
  uploading a new GLB.
- Binary responses use `E-Tag: "<hash>-v<n>"` and response header
  `X-Object-Version` on upload.
- `POST /api/events` accepts a single event or `{"events":[...]}` batch.
- Validation: `object.created` / `object.versioned` require a matching stored
  `name`, `version`, and `hash`; conflicts return **409**.

### Fixed

- **Blank viewport fix:** align **three.js** with **@google/model-viewer**
  (pinned via `resolutions`); dismiss the loading poster on model reveal and
  progress completion.
- **Orientation gizmo:** no longer corrupts the main scene graph (isolated
  render path).
- **Double-sided materials** on GLB export (Python tessellation and frontend
  glTF transform) so thin faces remain visible.
- CI: `deploy-pypi` sets `GH_REPO` so `gh release upload` works without a
  checkout in that job.
- CI: Frontend `vue-tsc` strict checks pass on GitHub Actions (safe casts for
  `globalThis.THREE` and model-viewer progress events).

## [1.1.1]

- Automated version bump release.

## [1.1.0]

- Last release on the v1 HTTP API. See [v2.0.0](#200) for the migration table.

[Unreleased]: https://github.com/jimcortez/cadquery-web-viewer/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v2.0.0
[1.1.1]: https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v1.1.1
[1.1.0]: https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v1.1.0
