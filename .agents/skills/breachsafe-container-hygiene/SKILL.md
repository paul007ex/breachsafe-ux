---
name: breachsafe-container-hygiene
description: Audit and harden the container image artifact and its Dockerfile — Dockerfile linting (Hadolint DL-rules, multi-stage, layer/apt cleanup), base-image digest pinning vs floating tags, runtime hardening (non-root USER, read-only rootfs, cap-drop ALL, no-new-privileges, HEALTHCHECK), image vulnerability scanning wired to actually FAIL the build (Trivy/Grype) with disciplined .trivyignore suppressions, SBOM emission (Syft, CycloneDX/SPDX), cosign signing + SLSA/buildx provenance attestation on a pinned digest, OCI image labels/annotations, and secret-leak / .dockerignore / build-context hygiene. Use when writing or reviewing a Dockerfile, docker-compose, or container CI. Distinct from breachsafe-cicd-hygiene (GitHub Actions workflow design — concurrency, duplication, cron awareness — the workflow YAML, not the image), breachsafe-release (dependency-tree supply-chain scanning + OSS registry release-readiness + the canonical Sigstore/SLSA framing this skill defers to for signing), and breachsafe-security-audit (crypto correctness + secret handling; this skill only checks that a secret isn't baked into an image layer, not whether the crypto is sound). Audit-only by default — never edits a Dockerfile, files an issue, or pushes an image without explicit per-action authorization.
---

# breachsafe-container-hygiene

Answers one question: **"is this container image safe, minimal, reproducible, and honestly
attested — or does it ship as root, from a floating tag, with a scanner that can't fail the
build?"** — distinct from "is the *workflow* well-designed" (`breachsafe-cicd-hygiene`), "is
the *package* ready to publish" (`breachsafe-release`), or "is the *crypto/secret handling*
sound" (`breachsafe-security-audit`).

Every check below is grounded in an authoritative source or a live BreachSAFE precedent, not
a hypothetical — cite the URL or the file:line when you flag it.

## Contents
1. Applies to
2. Stay in its lane
3. Authorization gate
4. Mode 1 — Dockerfile hygiene
5. Mode 2 — Base-image pinning, provenance + OCI labels
6. Mode 3 — Runtime hardening (non-root / caps / read-only)
7. Mode 4 — Image scanning (Trivy/Grype) + SBOM
8. Mode 5 — Signing + attestation (cosign / SLSA)
9. Mode 6 — Secret-leak / .dockerignore / build-context
10. The recurring trap
11. References

## 1. Applies to

Any repo that ships a `Dockerfile`, `docker-compose*.yml`, or a container CI workflow —
EnXemble (root/api/ui/mcp_server + the endpoint-collector image), qureddy, and any future
image. Language-agnostic; the Dockerfile is the object, not the app inside it. Modes 4 and 5
apply only once an image is actually built and/or published in CI — report "not built yet"
as a valid state, never a synthesized PASS.

## 2. Stay in its lane

- **`breachsafe-cicd-hygiene`** owns the *workflow* (concurrency, cross-repo duplication,
  cron/canary awareness, skip-masking). This skill owns the *image*. A missing
  `concurrency:` on `container.yml` is that skill's; a floating `FROM` inside the Dockerfile
  is this one's.
- **`breachsafe-release`** owns dependency-tree supply-chain scanning (`cargo audit` /
  `pip-audit`), OSS release-readiness, and is the **canonical authority on Sigstore/SLSA
  provenance**. Mode 5 here applies that framing to the *image artifact on a registry*
  (cosign on a digest, buildx attestations) and defers to release for the "is the package
  release-ready" verdict — it does not re-derive it.
- **`breachsafe-security-audit`** owns secret-handling and crypto correctness. Mode 6 here
  checks only the *mechanical* "is a credential baked into an image layer / build arg" — the
  moment a real secret is found, that's a security-audit finding.

Rule of thumb: "would fixing this differently change the image's build/runtime posture, or
only the workflow around it / the app's crypto?" — the former is this skill's.

## 3. Authorization gate

Audit-only by default. May run freely — read-only inspection and diagnostic tooling that
inspects but does not mutate or publish: `hadolint <Dockerfile>`, `docker build` to a local
tag, `trivy image` / `grype`, `syft` SBOM generation, `docker run … id -u` identity probes,
`cosign verify` / `cosign verify-attestation` (read), `docker sbom` / `docker scout`. **Never
without explicit per-action authorization**: editing a Dockerfile to "fix" a finding, pushing
an image, running `cosign sign` (writes to a transparency log — effectively irreversible),
`docker push`, or filing/commenting an issue/PR. Draft the finding or the patch and show it;
act only on explicit authorization for that specific action. "Harden this image" is not
standing authorization to push a signed image.

## 4. Mode 1 — Dockerfile hygiene

Lint the Dockerfile before reasoning about it. Run `hadolint` and treat these as the load-
bearing rules (`references/dockerfile-hygiene.md` has the full DL-rule map):
- **DL3007** — never `FROM …:latest` (or a bare floating tag); pin explicitly. (Mode 2 takes
  this further to a digest.)
- **DL3008 / DL3013 / DL3018** — pin `apt-get` / `pip` / `apk` package versions where
  practical; a deliberate exception must carry an inline `# hadolint ignore=DL3008` with a
  reason (EnXemble does exactly this on the apt block in `api/Dockerfile`).
- Multi-stage build separating build tooling from the runtime image; runtime stage `FROM`s a
  minimal base and copies only artifacts. Every EnXemble image already does this
  (`api/Dockerfile` build→dev/prod; `ui/Dockerfile` base→deps→builder→prod).
- Purge build-only packages in the same or a later layer (`api/Dockerfile` runs
  `apt-get purge -y --auto-remove …` after the build); `--no-install-recommends` +
  `rm -rf /var/lib/apt/lists/*` in the same `RUN`.
- Downloads that enter the image must be checksum- or digest-verified, fail-closed. Precedent:
  the collector Dockerfile pins `OPENSSL_SHA256` and runs `sha256sum -c`
  (`api/src/backend/api/collectors/endpoint/Dockerfile`); the api image re-verifies a
  `<wheel>.sha256` sidecar at bake time so the build FAILS CLOSED on tamper.

Sources: Hadolint (https://github.com/hadolint/hadolint), Docker best-practices
(https://docs.docker.com/build/building/best-practices/).

## 5. Mode 2 — Base-image pinning, provenance + OCI labels

- **Pin the base image by digest**, not just a tag: `FROM python:3.12.13-slim-bookworm@sha256:…`.
  A tag is mutable; the daemon refuses any manifest whose digest differs. Precedent (good):
  qureddy's `Dockerfile` and EnXemble root/`api`/`ui`/`mcp_server` pin `@sha256:…`; the api
  image pins the upstream qureddy image it copies OpenSSL from by digest ("PINNED BY DIGEST
  (#178)"). **Gap to flag**: the collector Dockerfile uses bare `FROM debian:bookworm-slim` /
  `FROM python:3.12-slim-bookworm` with no digest.
- **Minimal base**: base image drives most of an image's CVE count. Prefer slim/distroless/
  Chainguard over a full distro (note the musl caveat for Python C-extensions on Alpine).
- **A pinned digest needs a rebuild cadence** or it silently rots past CVE fixes — pair the
  pin with a CI job that bumps it.
- **OCI labels/annotations** — carry the standard `org.opencontainers.image.*` set:
  `title`, `description`, `source`, `revision`, `version`, `licenses`, and the base-image
  link `base.name` + `base.digest`. Precedent (good): qureddy's `Dockerfile`. **Gap**: the
  collector Dockerfile has no OCI labels; EnXemble root/api set only `maintainer` +
  `image.source`.

Sources: OCI image-spec annotations
(https://github.com/opencontainers/image-spec/blob/main/annotations.md);
`references/base-image-provenance.md`.

## 6. Mode 3 — Runtime hardening (non-root / caps / read-only)

Per the CIS Docker Benchmark v1.7.0 and Docker security guidance:
- **Non-root `USER`** (CIS 4.1): dedicated uid/gid, `USER` down before entrypoint. Every
  BreachSAFE image does this (uid 1000; ui 1001). **Prove it at runtime** — qureddy's
  `container.yml` asserts `test "$(docker run … id -u)" = "1000"`. Copy that check; don't
  infer non-root from the Dockerfile alone.
- **Read-only root filesystem** (`--read-only` / `readOnlyRootFilesystem: true`) with scoped
  writable `tmpfs`/volumes; pre-own writable dirs to the runtime user at build time (the
  collector `chown -R breachsafe …`).
- **Drop all capabilities**, add back only what's needed (`--cap-drop=ALL` then e.g.
  `--cap-add=NET_BIND_SERVICE`); `--security-opt=no-new-privileges`; keep default seccomp;
  no shared host PID/IPC/UTS; never `--privileged`.
- **HEALTHCHECK**: define liveness. BreachSAFE defines it in `docker-compose.yml`; for an
  image consumed outside compose a Dockerfile `HEALTHCHECK` travels with the image. Flag
  *absence in both places*, not the choice between them.

Sources: CIS Docker Benchmark v1.7.0; NSA/CISA Kubernetes Hardening Guide;
`references/runtime-hardening.md`.

## 7. Mode 4 — Image scanning (Trivy/Grype) + SBOM

- Scan the built image for OS + language CVEs (Trivy or Grype). BreachSAFE ships a reusable
  Trivy composite action (`.github/actions/trivy-scan/action.yml`) with SARIF upload.
- **The scanner must be able to FAIL the build** — same theater trap `breachsafe-release`
  names for `cargo audit`. **Flag it**: the BreachSAFE `trivy-scan` action defaults
  `fail-on-critical: 'false'` — a scan that reports but never gates is not a gate. Check the
  CI exit path, not just that the tool ran.
- **`.trivyignore` discipline**: suppressions scoped per-package with (a) why-it-ships,
  (b) why-not-exploitable, (c) upstream-fix-status, (d) an `exp:` expiry. EnXemble's
  `.trivyignore` is the model — every entry has all four. A bare `CVE-XXXX` with no
  rationale/expiry is a finding.
- **SBOM**: emit CycloneDX (security) or SPDX (license) with Syft, or buildx `--sbom=true`
  (qureddy `container.yml`). Watch the generator→consumer pitfall: a Syft SBOM that
  Trivy/Grype fails to parse yields a silent "0 vulns" — test the specific pairing.

Sources: Trivy (https://trivy.dev/), Syft/Grype (https://github.com/anchore/syft,
https://github.com/anchore/grype); `references/image-scanning-and-sbom.md`.

## 8. Mode 5 — Signing + attestation (cosign / SLSA)

Defers to `breachsafe-release` for the "release-ready" verdict; this is the image-artifact
mechanics.
- **Sign by digest, never a tag**: `cosign sign <img>@sha256:…`. Prefer **keyless** via
  GitHub Actions OIDC (Fulcio cert + Rekor log) over long-lived keys.
- **Verify with a pinned identity**: `cosign verify <img>@digest
  --certificate-identity-regexp 'https://github.com/<org>/<repo>/.*'
  --certificate-oidc-issuer https://token.actions.githubusercontent.com`.
- **Provenance + attestations**: buildx `--provenance=true --sbom=true`; verify with
  `cosign verify-attestation --type slsaprovenance` / `--type cyclonedx`. **Gap to flag**:
  qureddy's publish sets `--provenance=true --sbom=true` but **no repo runs `cosign` at all**
  — nothing is signed or signature-verified in EnXemble or qureddy CI. That's the concrete
  forward work.

Sources: Sigstore cosign (https://docs.sigstore.dev/cosign/verifying/verify/), SLSA
(https://slsa.dev/); `references/signing-and-attestation.md`.

## 9. Mode 6 — Secret-leak / .dockerignore / build-context

- **No secret in an image layer** — no credential in `ENV`, `ARG` (visible in
  `docker history`), or a `COPY`'d `.env`. Use BuildKit `RUN --mount=type=secret` for
  build-time secrets. A real secret found here escalates to `breachsafe-security-audit`.
- **`.dockerignore` must exclude secrets, VCS, cruft, and test code** — `.git`, `.env*`,
  `node_modules`, `__pycache__`, `**/tests`. EnXemble's root `.dockerignore` is the model:
  deny-all (`*`) then re-include exactly the COPY sources, with belt-and-suspenders
  `**/tests`/`**/.env*`/`**/.git` globs (#133/#137, "never ship TEST code").
- **Scope the build context tightly** — a huge repo root as context is slow and leak-prone;
  the deny-all `.dockerignore` narrows it.

Sources: Docker `.dockerignore` best-practices; `references/secrets-and-build-context.md`.

## 10. The recurring trap

A scanner that **runs** but can't **fail the build** is theater (Mode 4:
`fail-on-critical: 'false'`). A digest pin with **no rebuild cadence** silently rots past CVE
fixes (Mode 2). A `USER` line is not proof the container runs non-root — **probe `id -u` at
runtime** (Mode 3). `--provenance=true` is not a **verified** signature — provenance with no
`cosign verify` in CI is unenforced (Mode 5). Always check the enforcement/exit path, not
just that the good-looking config is present.

## 11. References
1. `references/dockerfile-hygiene.md` — Hadolint DL-rule map, multi-stage, layer/apt cleanup, checksum-verified downloads.
2. `references/base-image-provenance.md` — digest-pin vs floating tag, minimal-base selection, rebuild cadence, OCI `image.*` labels.
3. `references/runtime-hardening.md` — non-root USER, read-only rootfs, cap-drop ALL, no-new-privileges/seccomp, HEALTHCHECK, runtime identity probe.
4. `references/image-scanning-and-sbom.md` — Trivy/Grype wired to FAIL, disciplined `.trivyignore`, Syft SBOM, generator→consumer pitfall.
5. `references/signing-and-attestation.md` — cosign keyless sign-by-digest + verify, buildx provenance/SBOM, SLSA; defers to `breachsafe-release`.
6. `references/secrets-and-build-context.md` — no-secret-in-layer, BuildKit secret mounts, deny-all `.dockerignore`, tight context.
