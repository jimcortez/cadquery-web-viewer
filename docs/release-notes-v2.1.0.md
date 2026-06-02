# cadquery-web-viewer v2.1.0

Release notes since **[v2.0.0](https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v2.0.0)**.

v2.1.0 is a **feature + maintenance release**. The viewer gains a real Scene settings UI and a split sidebar; the developer ergonomics around CI, tests, packaging, and contributor docs are upgraded substantially. There are no breaking HTTP API changes from v2.0.0.

---

## Highlights

- **Scene settings UI** — model-viewer lighting, camera, and per-model material controls live in a dedicated *Scene* pane; loaded models live in a separate *Models* pane with independent helper-axis ownership.
- **URL object import** — `PUT /api/object/<name>` now accepts `{"url": "https://…"}` so the server fetches a remote GLB on your behalf (capped at 50 MB).
- **Real CI quality bar** — `ruff`, `pyright`, and `unittest` run in matrix on every PR (Linux × {3.10, 3.11, 3.12} + macOS/Windows × 3.12). All GitHub Actions are SHA-pinned. Weekly CodeQL runs.
- **Tests went from sketch to substance** — ~5% line coverage to ~53% (124 unit and Flask integration tests).
- **Yarn 4 (Berry) via Corepack** — the JS toolchain is finally on the maintained line; `yarn install --immutable` replaces `--frozen-lockfile`.
- **GHCR Docker image** — published on every release tag at `ghcr.io/jimcortez/cadquery-web-viewer`.
- **Substantial docs upgrade** — README badges + live demo link, real `CONTRIBUTING.md`, `SECURITY.md` with a documented trust model, GitHub issue/PR templates, `CODEOWNERS`.

---

## New features

### Frontend — split sidebar with Scene + Models panes

- **Scene pane** exposes model-viewer lighting (environment image, exposure, shadow softness/intensity), camera (auto-rotate, FOV, target/orbit reset), and per-model material controls (variants, opacity, base color, metalness, roughness).
- **Models pane** stays focused on the loaded GLBs and their object-store metadata.
- New composables: `useAppModelLoading`, `useObjectPicker`, `useViewerSceneSettings`, `useModelDisplaySettings`.
- New components: `LeftSidebar.vue`, `ColorSwatchField.vue`.
- Helper-axis ownership is tracked separately from CAD geometry so overlays stay independent of the loaded model.

### URL import on `PUT /api/object/<name>`

Send a JSON body instead of a multipart upload and the server fetches the GLB itself:

```bash
curl -X PUT http://localhost:32323/api/object/from-url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/model.glb"}'
```

| Field | Behavior |
|---|---|
| `url` | Required for JSON mode. `http`/`https` only. |
| `hash` | Optional. Defaults to `sha256(glb_bytes)`. |
| `kwargs` | Optional. `source_url` defaults to `url`. |

Errors: `400` invalid body; `413` over the 50 MB cap (`MAX_GLB_BYTES` in `cadquery_web_viewer/url_import.py`); `502` fetch failed or response is not a GLB.

### Public Python API additions

- `cadquery_web_viewer.object_store.UNSET` — public sentinel for "do not change" on metadata patches. (`_UNSET` is preserved as a backward-compatible alias.)
- `cadquery_web_viewer.engine.CadQueryWebViewer.scene_active_names() -> frozenset[str]` — frozen snapshot of names currently published to the scene. Replaces reaching into `engine._scene_active`.

### CI / packaging

- New `test-python` matrix job runs `ruff`, `pyright`, `unittest`, and uploads coverage to Codecov.
- New `test-frontend` job runs `vue-tsc --build`.
- New `codeql.yml` workflow scans `python` and `javascript-typescript` weekly + on PR.
- Every action `uses:` is pinned to a 40-char commit SHA with the human tag in a trailing comment for Dependabot.
- `Dockerfile` is published to **GitHub Container Registry** (`ghcr.io/jimcortez/cadquery-web-viewer`) on every tag in addition to the existing optional Docker Hub publish.
- Single source of version truth: `pyproject.toml` uses `dynamic = ["version"]` and Hatchling's regex source reads from `package.json`. The release workflow only updates `package.json`.

---

## Behavior changes

### `PATCH /api/object/<name>` with `{"notes": null}` now clears notes

[`docs/api.md`](api.md) documented `notes: null` as "set or null to clear", but the engine code silently ignored a `null` notes value. The encapsulation refactor exposes the bug; clearing now works as documented.

If you have client code that intentionally sent `{"notes": null}` to *not* update notes — switch to omitting the field entirely (the documented contract for "leave unchanged").

---

## Improvements

### Backend

- `engine.patch_object()` defaults `notes` to `UNSET` (was `None`); callers that don't pass `notes` get the no-change behavior they always intended.
- `cad.get_color()` now returns a `tuple[float, float, float, float]` matching `ColorTuple`, fixing a return-type mismatch flagged by pyright.
- `http_client._resolved_remote()` annotated and silenced the `RemoteOptions` `object`-to-`int`/`float` coercions.
- `engine.build_events_lock` declared as `threading.RLock` (matches the actual init).

### Frontend

- Vertex colors are preserved when adjusting materials on meshes that already have a `COLOR_0` attribute.
- `Model.vue` re-derives material settings safely when geometry reloads.

### Remote sync

- `remote_clear()` queries shown object names before publishing `scene.cleared`, so `except_names` matches what the viewer actually has loaded.
- Remote helpers consistently emit `object.versioned` vs `object.created` based on what the *server* reports as currently in scene (via `GET /api/scene`).

---

## Tooling and developer experience

### Yarn 1 → Yarn 4 (Berry) via Corepack

- `package.json` pins `packageManager: "yarn@4.5.0"`. Yarn 1 is no longer in `devDependencies`.
- New `.yarnrc.yml` selects the `node-modules` linker to preserve Vite's `resolve.dedupe` of `three` (PnP would break the Three.js sharing constraint).
- `yarn.lock` regenerated under Yarn 4 (`__metadata.version: 8`).
- `.gitignore` adopts Yarn 4's recommended ignore set.
- `Dockerfile`, `hatch_build.py`, and the workflows all use `corepack enable` + `yarn install --immutable` (renamed from `--frozen-lockfile`).

**Migration for contributors:** `corepack enable && yarn install` once. Then everything works as before — `yarn dev`, `yarn build`, `yarn type-check`.

### Pyright tightened (first pass)

`pyproject.toml` promotes seven previously-disabled report categories to `"warning"`: `reportArgumentType`, `reportReturnType`, `reportAssignmentType`, `reportOptionalMemberAccess`, `reportOptionalSubscript`, `reportCallIssue`, `reportAttributeAccessIssue`. CI surfaces them without failing. Easy fixes were applied; remaining warnings are mostly OCP stub gaps tracked for a follow-up "errors" pass.

### Docs

- README badges (PyPI, supported Pythons, license, CI status, monthly downloads), a "Try it live" link to GitHub Pages, and a hero screenshot slot.
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) is now a real document covering setup, the four quality gates contributors should run locally, branch convention, and where the frontend source vs built bundle live.
- New [`SECURITY.md`](../SECURITY.md) with a private vulnerability-reporting channel and the **trust model** (CORS `*`, URL import, no auth — intended for trusted networks).
- New [`CHANGELOG.md`](../CHANGELOG.md) (Keep a Changelog format).
- [`docs/api.md`](api.md) gains a "Trust model" section and the URL-import error matrix.
- [`docs/install.md`](install.md) leads with `docker pull ghcr.io/jimcortez/cadquery-web-viewer:latest`.
- [`docs/development.md`](development.md) updated for Corepack + Yarn 4.
- [`AGENTS.md`](../AGENTS.md) trimmed to the agent-specific rules; setup/commands/conventions live in `CONTRIBUTING.md`.
- New GitHub issue/PR templates and `CODEOWNERS`.

### Tests

121 new tests across seven files lift line coverage from ~5% to ~53%:

| File | Targets |
|---|---|
| `tests/test_object_store.py` | put/get/patch/delete versions, `UNSET`/`_UNSET` aliasing, `validate_settings_value`/`_map`, rename happy-path and conflict, deepcopy isolation |
| `tests/test_pubsub.py` | buffered vs live subscription, `max_buffer_size` rotation, `yield_timeout` keep-alive, multi-subscriber fanout, `prune_buffer` |
| `tests/test_events_api.py` | `validate_event` happy + sad paths for every envelope type |
| `tests/test_engine.py` | `put_object_version`, `publish_event_checked` 404/409 cases, scene mutations, describe-shape, `patch_object` |
| `tests/test_glb_cache.py` | write/read versions, kwargs JSON safety, `rename_object`, manifests, atomic writes |
| `tests/test_app_object_routes.py` | Flask test client integration: PUT (multipart + force-version), GET, PATCH (rename, clear-notes-via-null, settings merge), DELETE, batch events, CORS |
| `tests/test_app_sse.py` | SSE retry directive, no-replay-on-connect contract, keep-alive emission |

---

## Fixes and maintenance

- **Frontend mesh material adjustment** — preserve vertex colors when overriding base color on meshes that already have a `COLOR_0` attribute.
- **Remote scene sync** — `remote_clear` now queries `GET /api/scene` first so `scene.cleared except_names` and the create-vs-version event split match the viewer.
- **Hatchling build hook** — uses Corepack-managed Yarn (`corepack yarn install --immutable`); the previous `npx yarn install --frozen-lockfile` would silently use the wrong yarn under Yarn 4.
- **Release workflow** — single-source version (no more `sed` on `pyproject.toml`); Yarn 4-correct `yarn version <new>` syntax.
- **`package.json` author** — corrected to **Jim Cortez** (Yeicor remains credited in *Special thanks* in the README and in `LICENSE`).

---

## Things tried that didn't ship (yet)

The plan attempted these and CI revealed upstream blockers:

| Attempted | Blocked by | Re-enable when |
|---|---|---|
| Python **3.13** in the support matrix | `vtk==9.3.1` (transitively pinned through `build123d>=0.10,<0.11` → `cadquery-ocp` 7.8.x) ships no `cp313` wheels | `build123d` adopts `cadquery-ocp` 7.9.3.1+ which depends on `vtk==9.6.x` |
| **Multi-arch Docker** (`linux/amd64,linux/arm64`) | `cadquery-ocp` 7.8.x has no `manylinux_aarch64` wheel | Same as above — aarch64 wheels exist starting in `cadquery-ocp` 7.9.3.1 |

Both are documented in [`CHANGELOG.md`](../CHANGELOG.md) and [`docs/install.md`](install.md) so users on arm64 know to pass `--platform linux/amd64`.

---

## Upgrade guide

### From v2.0.0

- **No HTTP API breaking changes.** Existing remote clients keep working.
- **If you patched objects with `{"notes": null}` expecting a no-op:** that was a latent bug; `null` now clears notes per `docs/api.md`. Omit the field instead to leave notes unchanged.
- **If you build the project locally:** run `corepack enable` once before `yarn install`. Use `yarn install --immutable` (was `--frozen-lockfile`).
- **If you build a Docker image on Apple Silicon:** keep passing `--platform linux/amd64` (or pull `ghcr.io/jimcortez/cadquery-web-viewer` and use Rosetta).

### From any earlier version

See the [v2.0.0 release notes](https://github.com/jimcortez/cadquery-web-viewer/releases/tag/v2.0.0) for the API redesign.

---

## Full changelog (commits since v2.0.0)

| Commit | Summary |
|---|---|
| [`f16683b`](https://github.com/jimcortez/cadquery-web-viewer/commit/f16683b) | Scene settings UI, split sidebar, URL object import |
| [`ec8b2e2`](https://github.com/jimcortez/cadquery-web-viewer/commit/ec8b2e2) | `fix(remote)`: sync scene clear/events via `GET /api/scene` |
| [`9172a12`](https://github.com/jimcortez/cadquery-web-viewer/commit/9172a12) | `docs`: expand README, contributor guide, security policy, changelog |
| [`83f6a57`](https://github.com/jimcortez/cadquery-web-viewer/commit/83f6a57) | `ci`: pin actions to SHAs, add test/CodeQL jobs, single-source version |
| [`726b426`](https://github.com/jimcortez/cadquery-web-viewer/commit/726b426) | `build`: migrate to Yarn 4 (Berry) via Corepack, add multi-arch Docker (later restricted to amd64) |
| [`953f39f`](https://github.com/jimcortez/cadquery-web-viewer/commit/953f39f) | `refactor(engine)`: expose `UNSET` sentinel and `scene_active_names()` |
| [`d1fbfcf`](https://github.com/jimcortez/cadquery-web-viewer/commit/d1fbfcf) | `test`: add unit/integration coverage for store, pubsub, events, engine, cache, app |
| [`745242b`](https://github.com/jimcortez/cadquery-web-viewer/commit/745242b) | `types`: tighten `cad.get_color` and `http_client._resolved_remote` |
| [`c6e5b2d`](https://github.com/jimcortez/cadquery-web-viewer/commit/c6e5b2d) | `fix(ci)`: unblock CI by handling Yarn 4 setup ordering, coverage TOML, vtk pin |
| [`4608b48`](https://github.com/jimcortez/cadquery-web-viewer/commit/4608b48) | `fix(ci)`: drop `linux/arm64` from Docker (cadquery-ocp 7.8.x lacks aarch64 wheel) |

---

## Assets

GitHub Releases for this tag will include:

- `cadquery-web-viewer-v2.1.0-frontend.zip` — static UI bundle
- Python **wheel** and **sdist** on PyPI (`cadquery-web-viewer`)
- Docker image: `ghcr.io/jimcortez/cadquery-web-viewer:2.1.0` (`linux/amd64`)
