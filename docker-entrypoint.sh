#!/bin/sh
set -eu

HOST="${CADQUERY_WEB_VIEWER_HOST:-0.0.0.0}"
PORT="${CADQUERY_WEB_VIEWER_PORT:-32323}"
CACHE_MODE="${CADQUERY_WEB_VIEWER_CACHE_MODE:-memory}"
CACHE_DIR="${CADQUERY_WEB_VIEWER_CACHE_DIR:-}"

set -- --host "$HOST" --port "$PORT" --cache-mode "$CACHE_MODE"

if [ "$CACHE_MODE" = "disk" ] && [ -n "$CACHE_DIR" ]; then
  set -- "$@" --cache-dir "$CACHE_DIR"
fi

if [ -n "${PUID:-}" ] && [ -n "${PGID:-}" ]; then
  export HOME="${HOME:-/tmp/cadquery-web-viewer-home}"
  mkdir -p "$HOME"
  chown -R "${PUID}:${PGID}" "$HOME" || true
  if [ "$CACHE_MODE" = "disk" ] && [ -n "$CACHE_DIR" ]; then
    mkdir -p "$CACHE_DIR"
    chown -R "${PUID}:${PGID}" "$CACHE_DIR" || true
  fi
  exec /usr/local/bin/su-exec "${PUID}:${PGID}" cadquery-web-viewer "$@"
else
  exec cadquery-web-viewer "$@"
fi
