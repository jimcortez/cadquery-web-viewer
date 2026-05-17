# Develop the UI and Python backend

Target stack: **Python 3.10–3.12** (see [`pyproject.toml`](../pyproject.toml)) and **Node** for the Vite frontend.

## 1. Install dependencies

```bash
uv sync
yarn install
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
