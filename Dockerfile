# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend

WORKDIR /src

RUN corepack enable \
    && corepack prepare yarn@1.22.22 --activate

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .

ENV CADQUERY_WEB_VIEWER_SMALL_BUILD=true
RUN yarn build-only --outDir cadquery_web_viewer/frontend

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    CADQUERY_WEB_VIEWER_SKIP_FRONTEND_BUILD=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        gcc \
        libc6-dev \
        wget \
    && wget -qO /tmp/su-exec.tar.gz https://github.com/ncopa/su-exec/archive/refs/tags/v0.2.tar.gz \
    && tar -xzf /tmp/su-exec.tar.gz -C /tmp \
    && gcc -Wall -Werror -O2 -o /usr/local/bin/su-exec /tmp/su-exec-0.2/su-exec.c \
    && chmod +x /usr/local/bin/su-exec \
    && rm -rf /tmp/su-exec* \
    && apt-get purge -y gcc libc6-dev wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml hatch_build.py README.md LICENSE ./
COPY cadquery_web_viewer ./cadquery_web_viewer
COPY --from=frontend /src/cadquery_web_viewer/frontend ./cadquery_web_viewer/frontend

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN pip install --no-cache-dir .

# cadquery-ocp / VTK wheels expect common GLX / X11 client libs at import time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsm6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 32323

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
