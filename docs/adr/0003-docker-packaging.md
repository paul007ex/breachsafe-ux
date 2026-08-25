<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# ADR-0003 — Docker packaging: a base host image, tool images build FROM it

- **Status:** Accepted, **Updated 2026-08-22** (see "Update" below — the base+socket two-layer
  model was superseded by a self-contained multi-arch image before first release).
- **Date:** 2026-08-22
- **Deciders:** BreachSAFE (paul)
- **Related:** ADR-0001 (facade), ADR-0002 (host↔descriptor boundary + trust posture), #35, #67, #120.

## Update — 2026-08-22: self-contained, multi-arch `qureddy-ux` image

The original Decision below (a host-only BASE image, with each tool's product image building
`FROM` it, and the tool reached via a mounted docker socket or a pip install) never shipped. The
released packaging (v0.3.1) is a **single self-contained, multi-arch `qureddy-ux` image**:

```
  official tool image (multi-arch)              breachsafe-ux repo (this repo)
 ┌───────────────────────────────┐   FROM      ┌────────────────────────────────────┐
 │ ghcr.io/breachsafe/qureddy    │◀────────────│ ghcr.io/paul007ex/qureddy-ux       │
 │  qureddy + python + openssl   │             │  + EnXemble host wheel (gradio+eng) │
 │  (amd64 + arm64)              │             │  + tools/qureddy, tools/qureddy-ssh │
 └───────────────────────────────┘             │  + openssh-client (SSH tab)        │
                                                │  = the product a user runs         │
                                                └────────────────────────────────────┘
                                                 docker run -p 7860:7860 …  (no socket)
```

- **Built FROM the official multi-arch `ghcr.io/breachsafe/qureddy:latest`** (qureddy, python,
  and openssl already inside), then adds the EnXemble host wheel and the TLS/SSH descriptors.
  See `Dockerfile.qureddy-ux` and `.github/workflows/qureddy-ux-image.yml`.
- **Scans run in-process.** qureddy is on `PATH` in the image, so the local-binary backend is
  taken; there is **no docker socket mount** and no in-container docker daemon. The workflow's
  smoke test asserts exactly this ("one command, no socket, serves + resolves tools").
- **Multi-arch** (`linux/amd64,linux/arm64`) via buildx + QEMU, so one image runs on Intel and
  Apple Silicon. Published as `:edge` on `main` and `:latest` + version tag on release.
- **One command, any arch, no socket, tool stays in its maintained image.** Building `FROM` the
  official qureddy image means qureddy is upgraded by rebuilding on a new base, not vendored or
  re-packaged here.

**Why the pivot.** The two-layer base+consumer model plus a docker-socket (or pip-install) path
added operator setup and a privileged socket mount for no gain now that the product ships as one
image per tool-UX. Building `FROM` the tool's own official image keeps the tool in the place its
maintainers already ship and test it, gives in-process scans with no socket, and makes
`docker run …` a single copy-paste on any architecture.

**What is preserved.** The engine's `run.image` docker backend (originally W-3) still exists as
the **general fallback**: a descriptor may declare `run.image`, and the engine runs the local
binary when it resolves on `PATH` and falls back to `docker run --pull=always <image>` otherwise
(`src/breachsafe_ux/facade.py`, `resolve.py`; README §6). In the shipped `qureddy-ux` image the
local binary always resolves, so the image path is not exercised there.

**Base image retired (2026-08-22, #131).** Because the product image builds `FROM` the tool's
official image (not the host-only base), the `ghcr.io/paul007ex/breachsafe-ux` **base image had no
consumer**. It has been removed (`Dockerfile` + `.github/workflows/container.yml` + the base
`.dockerignore`) and its container package deprecated. What remains is **one image per tool-UX
product** (`qureddy-ux`) plus the **`breachsafe-ux` Python package/wheel** (the host engine —
`pip install` and the wheel the product image bakes in). A future generic "bring-your-own-tools"
host, if ever needed, would be reintroduced deliberately rather than maintained speculatively.

The original context and decision are kept below unchanged as the historical record.

## Context

breachsafe-ux is Docker-first (no PyPI publish). We need to ship it so a user can `docker run`
a tool's web UX, while keeping the host generic and reusable across tools (the ADR-0001/0002
thesis). Non-functional requirements:

1. **Reproducible** — build from the committed `uv.lock`; pin the base images (dependabot's
   docker ecosystem digest-pins them).
2. **Generic base reusable** across tool-UXes (already two consumers: qureddy, mint-oscal).
3. **Editions by env, not image forks** — `BREACHSAFE_UX_MINT_OSCAL` etc. (#67) select
   capability at runtime; one artifact, many editions.
4. **Container hygiene** — non-root, minimal slim runtime, `HEALTHCHECK`, no secrets in the
   build context.
5. **Private during dev → public at release** (#35), avoiding a surprise-public image.

## Decision

**Two layers.** breachsafe-ux publishes a **host-only BASE image**; each tool's product image
builds `FROM` it.

```
  breachsafe-ux repo (this repo, #35)             qureddy repo (issue, not code here)
 ┌───────────────────────────────┐   FROM        ┌────────────────────────────────┐
 │ ghcr.io/paul007ex/             │◀──────────────│ ghcr.io/paul007ex/qureddy-ux   │
 │   breachsafe-ux  (BASE)        │               │  + pip install breachsafe-qureddy│
 │  gradio + engine, NO tools     │               │  + tools/qureddy/qureddy.yaml   │
 │  non-root, HEALTHCHECK,        │               │  + BREACHSAFE_UX_TOOLS_DIR=…    │
 │  ENV HOST=0.0.0.0,             │               │  = the product a user runs      │
 │  ENTRYPOINT breachsafe-ux      │               └────────────────────────────────┘
 └───────────────────────────────┘                    docker run -p 7860:7860 …
```

- **Base = this repo.** Multi-stage: `uv build` the wheel, install into a slim non-root runtime.
  It carries the host + bundled assets + `descriptor.schema.json`, but **no tools** — a consumer
  sets `BREACHSAFE_UX_TOOLS_DIR`. Smoke-tested in CI by "starts and serves HTTP 200"; full
  render/run coverage is the pytest suite (in CI) + the consumer image.
- **Product images build FROM the base**, in the *tool's* repo (keeps breachsafe-ux
  tool-agnostic). The `qureddy-ux` image is specified as a detailed issue in the qureddy repo,
  not code here.
- **Trust boundary (ADR-0002 §3):** inside the container the host binds `0.0.0.0` so the port
  can be mapped; the boundary is the operator's `-p` / reverse proxy, not code in the image.
  No in-image auth.

## Alternatives considered

- **Single monolithic product image** (host + tool in one Dockerfile): ships fastest but gives
  no reuse once a second tool-UX exists — rejected given two consumers already.
- **pip extra `qureddy[ux]`:** needs a PyPI publish of breachsafe-ux — rejected (Docker-first).

## Consequences

- Adding a tool-UX = a small Dockerfile `FROM` the base + a descriptor, in that tool's repo.
- The base image alone isn't a runnable product (no tools) — acceptable; its job is to be a base.
  The "is it wired right" gap is covered by the pytest suite and the smoke test.
- Bundling assets into the package (moved under `src/breachsafe_ux/assets/`) was a prerequisite,
  since the repo-root layout doesn't exist in an installed wheel.

## Open questions

- Digest-pin the base images now vs. let dependabot's docker ecosystem do it on the first run.
- Whether to also publish a multi-arch (arm64 + amd64) base.
