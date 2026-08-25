<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Run a tool-UX image with Docker

Docker is the primary way to run EnXemble. The shipped image bundles the host, the TLS and SSH
descriptors, QuReddy, and the evidence/PDF toolchain, so the operator can run an assessment and
retain its artifacts without installing scanner dependencies on the workstation.

This guide uses the **shipped EnXemble** image, `ghcr.io/breachsafe/breachsafe-enxemble`, as the
concrete image name. Any EnXemble tool-UX image runs the same way.

## Quickstart

```bash
docker rm -f enxemble 2>/dev/null || true
docker run -d --pull=always -p 7860:7860 --name enxemble ghcr.io/breachsafe/breachsafe-enxemble:latest
until curl -fsS http://localhost:7860/ >/dev/null; do sleep 1; done
open http://localhost:7860       # macOS  ·  Linux: xdg-open  ·  Windows: start
```

Copy-paste the three lines:

- The first clears any container already holding port 7860, so a re-run never fails with "port
  is already allocated".
- `--pull=always` fetches the newest image, so you always run the latest.
- The third opens your browser once the host is up. It is the macOS `open`; on Linux use
  `xdg-open http://localhost:7860`, on Windows `start http://localhost:7860`.

No login, no Docker socket mount, works on Intel and Apple Silicon (the image is multi-arch).
Stop it with `docker stop enxemble`.

## Tags

- `:latest`: the newest release.
- `:edge`: the tip of `main`.
- A version tag (for example `:0.3.5`): immutable, for reproducible deployments.

`--pull=always` with `:latest` keeps the host and its bundled tools current. When
reproducibility matters more than freshness, pin an immutable reference instead of `:latest`:
a version tag, or preferably a `@sha256:` digest.

```bash
docker pull ghcr.io/breachsafe/breachsafe-enxemble:latest
docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/breachsafe/breachsafe-enxemble:latest
docker run -d -p 7860:7860 --name enxemble ghcr.io/breachsafe/breachsafe-enxemble:latest
```

## Verify the tools resolve

A `curl` on `/` only proves the web server is up; the underlying tool can still be missing. The
real health signal is `--check`, which resolves every tab's tool and validator and exits nonzero
if any is missing:

```bash
docker exec enxemble breachsafe-ux --check
```

See the [CLI reference](../reference/cli.md) for the exact output and exit behaviour.

## Configure the host

The host reads its configuration from environment variables passed with `-e`. For example, to
change the port or hide an optional tab:

```bash
docker run -d --pull=always -p 8080:8080 \
  -e BREACHSAFE_UX_PORT=8080 \
  --name enxemble ghcr.io/breachsafe/breachsafe-enxemble:latest
```

The full list is the [environment variables reference](../reference/environment-variables.md);
feature-flag tabs are covered in [enable optional tabs](enable-optional-tabs.md).

## Trust boundary

Inside the container the host binds `0.0.0.0` so the port can be mapped. Reaching the UI means
reaching a process that spawns tools, so exposure beyond your machine is a deployment decision:
put authentication at the boundary you already run (reverse proxy, Docker network, VPN). The
host ships no built-in auth. See [ADR-0002 §3](../adr/0002-host-descriptor-boundary.md) for the
full rationale.
