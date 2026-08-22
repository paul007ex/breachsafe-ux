# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
# syntax=docker/dockerfile:1
#
# breachsafe-ux BASE image: the generic, tool-agnostic UX host (gradio + engine), NO tools
# bundled. A consumer image (e.g. qureddy-ux, in the qureddy repo) builds FROM this, installs
# its tool, drops a descriptor, and points BREACHSAFE_UX_TOOLS_DIR at it. See ADR-0003.

# --- build: produce the wheel with uv (locked, reproducible) ---
# Base images are digest-pinned (#119) — tag comment kept for humans; the digest is authoritative.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS build
WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv build --wheel --out-dir /dist

# --- runtime: slim, non-root ---
FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52 AS runtime
LABEL org.opencontainers.image.title="breachsafe-ux" \
      org.opencontainers.image.vendor="BreachSAFE" \
      org.opencontainers.image.source="https://github.com/paul007ex/breachsafe-ux" \
      org.opencontainers.image.description="breachsafe-ux — generic config-driven tool UX host (base image)" \
      org.opencontainers.image.base.name="docker.io/library/python:3.12-slim-bookworm" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN useradd --create-home --uid 10001 app
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

USER app
WORKDIR /home/app

# In a container the host binds 0.0.0.0 so the port can be mapped out; the trust boundary is the
# operator's `-p` mapping / reverse proxy, not code in the image (ADR-0002 §3).
ENV BREACHSAFE_UX_HOST=0.0.0.0 \
    BREACHSAFE_UX_PORT=7860 \
    GRADIO_ANALYTICS_ENABLED=False

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["breachsafe-ux"]
