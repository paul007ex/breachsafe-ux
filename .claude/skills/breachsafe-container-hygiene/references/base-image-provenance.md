# Base-image pinning, provenance + OCI labels

## Contents
1. Digest pin vs floating tag
2. Minimal-base selection
3. Rebuild cadence (pins rot)
4. OCI image labels

## 1. Digest pin vs floating tag
`FROM python:3.12.13-slim-bookworm@sha256:…` — a tag is mutable, a digest is not; the daemon refuses any manifest whose digest differs, so the build is reproducible and tamper-evident. Good: qureddy + EnXemble root/`api`/`ui`/`mcp_server` pin `@sha256:…`; the api image pins the qureddy image it copies OpenSSL from ("PINNED BY DIGEST (#178)"). Gap: the collector Dockerfile uses bare `FROM debian:bookworm-slim` / `python:3.12-slim-bookworm`.

## 2. Minimal-base selection
The base drives most of an image's CVE count. Prefer slim → distroless → Chainguard over a full distro. Caveats: distroless has no shell (debug via an ephemeral/`:debug` variant); Alpine's musl breaks Python C-extension wheels (manylinux is glibc) — don't switch a Python image to Alpine to "reduce CVEs" and silently force source builds.

## 3. Rebuild cadence (pins rot)
A pinned digest is frozen — it does **not** receive upstream CVE fixes. Pair every pin with a scheduled CI job (Dependabot/Renovate for Docker, or a cron) that bumps the digest and re-scans. A pin with no cadence is a slow-rotting liability, not just "safe."

## 4. OCI image labels
Carry the `org.opencontainers.image.*` set: `title`, `description`, `source`, `revision`, `version`, `licenses`, plus the base link `base.name` + `base.digest`. Good: qureddy's Dockerfile. Gap: the collector image has none; EnXemble root/api set only `maintainer` + `image.source`. Labels trace an image back to its commit + base.

Sources: OCI image-spec annotations (https://github.com/opencontainers/image-spec/blob/main/annotations.md).
