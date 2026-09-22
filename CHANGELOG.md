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
  cadquery-web-viewer`). `linux/arm64` now builds natively (see the `build123d`
  0.11 upgrade below); the image is still published `linux/amd64` only, so
  multi-arch publishing is a follow-up rather than an upstream limitation.

### Changed
- All GitHub Actions are now pinned to commit SHAs (with the human tag in a
  trailing comment for Dependabot).
- Single source of version truth: `package.json` is authoritative; the Hatchling
  build hook reads it and injects the version into wheel metadata.
- Yarn 1 → Yarn 4 (Berry) via Corepack with the `node-modules` linker. `yarn
  install --frozen-lockfile` is replaced by `yarn install --immutable`.
- `build123d` upgraded from `>=0.10,<0.11` to `>=0.11,<0.12`. 0.11 swaps
  `cadquery-ocp` 7.8.x for `cadquery-ocp-novtk` 7.9.x, which drops the `vtk`
  dependency entirely and ships `manylinux_2_31_aarch64` wheels. This fixes
  `pip install` / `docker build` failing on arm64 hosts (Apple Silicon), where
  `cadquery-ocp` 7.8.x had no aarch64 wheel and resolution was unsatisfiable.
  `vtk` and `matplotlib` are no longer in the dependency tree.
- `cad.get_color()` now reads `build123d` `Color` via `tuple(color)`; 0.11
  removed `Color.to_tuple()`.
- Python support remains `>=3.10,<3.13`, but no longer because of an upstream
  blocker: the `vtk==9.3.1` cp313 wheel gap is gone, so widening the range is
  now just a matter of adding 3.13 to the CI matrix and testing it.
- `package.json` `author` corrected to **Jim Cortez** (Yeicor remains credited
  in *Special thanks* and the LICENSE).
- Pyright reporting tightened: argument/return/assignment/optional-access checks
  promoted from "off" to "warning" (errors will follow in a later release).
- `MAX_GLB_BYTES` (URL-import size cap) is documented in `docs/api.md` so
  integrators don't have to read source to find it.
- CLI prints a deployment-posture log line on startup pointing at
  [SECURITY.md](SECURITY.md).

- Viewer UI redesigned around three zones: a left rail dedicated to objects
  (compact list with face/edge/vertex counts, master-detail inspector below,
  `+` opens the object picker), the viewport edge to edge with an overlay
  toolbar and the orientation gizmo, and a minimizable floating panel on the
  right holding Environment, Camera, Overlays and Selection plus export and
  licenses. Vuetify's layout wrappers are replaced by a CSS grid; its components
  stay.
- Design tokens (`frontend/styles/tokens.css`, `frontend/theme.ts`) and five
  control primitives (`SettingRow`, `SliderControl`, `ToggleControl`,
  `SelectControl`, `PanelSection`) back every setting, so all controls share one
  label column and density and every slider shows an editable numeric readout.
  Dark-first `cadDark` / `cadLight` themes.
- Per-object three.js side effects move out of `Model.vue` into
  `useModelSceneEffects`, driven by a `Map<name, EffectScope>` in
  `useModelEffectsManager`, so opacity, clipping, wireframe and fat lines keep
  applying to objects that are not the one shown in the inspector. Selection
  and camera state move to `useSelectionTools` / `useCameraTools`.
- Export-scene shortcut moves from `d` to `Ctrl/Cmd+S`; `d` was also bound to
  "toggle distances".
- Vuetify icons come from the `mdi-svg` set; the MDI font was never installed.
- Base colour is an explicit override: a non-default colour replaces the mesh's
  vertex colours, white keeps the model's own colours.
- Feature picking holds three.js objects in `shallowRef` / `markRaw` instead of
  deep refs, taking a pick from 90-115 ms to 3.5-7 ms.

### Removed
- `docs/release-notes-v2.0.0.md` (folded into this changelog under
  [v2.0.0](#200) below).
- Hardcoded `--platform linux/amd64` requirement from `docs/install.md` for
  hosts where ARM64 wheels of `cadquery-ocp` are available.

### Fixed
- Orientation gizmo never rendered: an `immediate` watch ran before the template
  ref existed, and the `THREE` global shim was scoped to construction so
  `update()` threw.
- Duplicate fat lines after overlapping edge-width changes, and wrong fat-line
  widths after a window resize (`resize` never fires on an element, and the
  listener removed a different closure than it added).
- Vuetify's internal icons were patched with `data:` URIs hardcoded to
  `fill="white"` and were invisible in the light theme.
- `onElemReady` leaked a watcher created outside any effect scope.
- Background colour setting was inert (model-viewer has no such feature). It is
  now painted on the element, which also makes Shadow and Softness visibly take
  effect.
- Camera lurched on every unrelated setting change because a deep watcher
  re-applied the target; it now fires only when the target itself changes.
- Auto-rotate and AR could not be switched off: `:auto-rotate="false"` wrote the
  string `"false"`, which lit reads as true. Boolean attributes are now
  present-or-absent.
- Base colour never applied because vertex colours always took precedence.
- Recenter & fit framed the world origin, where the axes helper is drawn, instead
  of the geometry.
- Picking stopped working after the object list emptied and refilled: mouse
  listeners stayed bound to the discarded model-viewer element.
- Back-face meshes are now parented to their source mesh's node instead of the
  scene root. GLBs with a transformed parent node (for example the Y-up root
  that OCC's glTF writer emits for assemblies) no longer render a second grey
  copy of the model rotated 90 degrees.

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
