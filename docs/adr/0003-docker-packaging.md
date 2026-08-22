<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# ADR-0003 — Docker packaging: a base host image, tool images build FROM it

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** BreachSAFE (paul)
- **Related:** ADR-0001 (facade), ADR-0002 (host↔descriptor boundary + trust posture), #35, #67.

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
 │ ghcr.io/paul007ex/             │◀──────────────│ ghcr.io/breachsafe/qureddy-ux  │
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
