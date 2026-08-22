# Runtime hardening — non-root / caps / read-only

## Contents
1. Non-root USER (+ prove it)
2. Read-only root filesystem
3. Capabilities / privileges / seccomp
4. HEALTHCHECK

## 1. Non-root USER (+ prove it)
CIS Docker 4.1: dedicated uid/gid, `USER` dropped before the entrypoint. Every BreachSAFE image does this (uid 1000; ui 1001). **Prove it at runtime** — qureddy's `container.yml` asserts `test "$(docker run … id -u)" = "1000"`. Never infer non-root from the Dockerfile alone (a later `USER root` or an entrypoint that `su`s back undoes it).

## 2. Read-only root filesystem
Run `--read-only` (`readOnlyRootFilesystem: true` in k8s) with scoped writable `tmpfs`/volumes. Pre-own the writable dirs to the runtime user at build time (the collector's `chown -R breachsafe …`) so the app writes only its known paths.

## 3. Capabilities / privileges / seccomp
`--cap-drop=ALL`, then add back only what's needed (e.g. `--cap-add=NET_BIND_SERVICE` for a <1024 port). `--security-opt=no-new-privileges` blocks setuid escalation. Keep the default seccomp profile (don't `seccomp=unconfined`). No shared host `--pid`/`--ipc`/`--uts`. **Never `--privileged`.**

## 4. HEALTHCHECK
Define liveness. BreachSAFE defines it in `docker-compose.yml`; for an image consumed outside compose a Dockerfile `HEALTHCHECK` travels with the image. Flag *absence in both places*, not the choice between them.

Sources: CIS Docker Benchmark v1.7.0; NSA/CISA Kubernetes Hardening Guide.
