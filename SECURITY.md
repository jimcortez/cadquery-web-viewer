# Security policy

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security problems.

Use one of the following private channels instead:

- **GitHub Security Advisory** (preferred): open a draft advisory on the repo's
  [Security tab](https://github.com/jimcortez/cadquery-web-viewer/security/advisories/new).
- **Email:** `jim@jimcortez.com`

Please include:

- A description of the issue and the impact you observed.
- Steps to reproduce, or a minimal proof-of-concept.
- Any affected versions you've confirmed.

You should expect an acknowledgement within a few days. Critical fixes will be
released as a patch version; lower-severity issues may be folded into the next
scheduled release.

## Supported versions

Only the latest release is actively supported. Older versions may receive
critical security fixes at maintainer discretion.

## Trust model

`cadquery-web-viewer` is a **developer tool**. The HTTP server is intended to
run on **localhost or a trusted network** during a CAD authoring session. It is
**not** a public-facing application and should not be deployed as one without
additional safeguards.

In particular, the default configuration:

- Returns CORS `Access-Control-Allow-Origin: *` so any origin may call the API
  from a browser. This makes development against `vite dev` easy but means a
  malicious page on another tab can talk to a viewer running on `localhost`.
- Accepts `PUT /api/object/<name>` with a JSON body of the form `{"url": "…"}`
  and **fetches that URL** server-side over `http`/`https`, up to a 50 MB cap.
  This is convenient for sharing GLB links but lets any caller cause the server
  to fetch arbitrary URLs (subject only to the URL scheme check).
- Runs on plain `flask.Flask.run` — there is no authentication, rate limiting,
  or TLS.

If you need to expose the viewer beyond a trusted network, place it behind
a reverse proxy that enforces auth/TLS and disable URL import (the simplest
approach is to remove the JSON branch in `cadquery_web_viewer.app.api_object_put`
or block the route at the proxy).

These defaults are documented in
[docs/api.md](docs/api.md#trust-model) so integrators know what to expect.

## Hardening recommendations

If you must expose the server to a wider audience:

1. Bind to a private interface (`--host 127.0.0.1`) and front it with a reverse
   proxy that adds authentication and TLS.
2. Restrict CORS at the proxy layer (override `Access-Control-Allow-Origin` to
   the known origins you serve the UI from).
3. Block `PUT /api/object/<name>` with a JSON body, or restrict the proxy to
   accept only the multipart upload path.
4. Run the container/process as a non-root user and limit its outbound network
   access (URL import will then fail closed).
