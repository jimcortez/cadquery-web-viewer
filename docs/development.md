# Develop the UI and Python backend

Target stack: **Python 3.10–3.13** (see [`pyproject.toml`](../pyproject.toml)) and **Node.js LTS** for the Vite frontend. Yarn is supplied via [Corepack](https://nodejs.org/api/corepack.html); the version is pinned in `package.json#packageManager` (currently Yarn 4 / Berry).

## 1. Install dependencies

```bash
uv sync                    # Python deps (preferred via uv)
corepack enable            # one-time: lets Node ship Yarn 4 transparently
yarn install               # JavaScript deps (full install — needed for yarn build)
```

If you do not use [uv](https://docs.astral.sh/uv/), create a virtual environment and run `pip install -e .` from the repo root instead of `uv sync`.

## 2. Start the Python API

Default URL: `http://localhost:32323`

```bash
uv run cadquery-web-viewer
```

Same effect after install: `python -m cadquery_web_viewer`.

## 3. Start the frontend (second terminal)

```bash
yarn dev
```

Open the URL Vite prints (often `http://localhost:5173`). The viewer tries the same origin for `/api/events`; when the page is not served by Flask, it falls back to `http://localhost:32323` so the UI and API stay aligned.

## Backend-only with a built UI

Run `yarn install` once, then `yarn build` (writes `dist/` at the repo root). Then run only `cadquery-web-viewer`. Flask serves that bundle when the packaged `frontend` tree is absent (see `FRONTEND_BASE_PATH` in the package). A full `yarn build` needs devDependencies (including `generate-license-file`). Installing with `NODE_ENV=production` skips those and the build will fail.

## Notes on Yarn 4

- Use `yarn install --immutable` in CI / scripts (Yarn 4 renamed `--frozen-lockfile`).
- The `nodeLinker` is `node-modules` (set in `.yarnrc.yml`) so Vite's `resolve.dedupe` of `three` and `@google/model-viewer` continues to work as it did under Yarn 1.
- Don't commit the `.yarn/` runtime cache; the `.gitignore` allowlists only the parts Yarn 4 expects to track (`patches/`, `plugins/`, `releases/`, `sdks/`, `versions/`).
