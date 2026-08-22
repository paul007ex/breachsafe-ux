# Dockerfile hygiene — Hadolint DL-rule map + layer discipline

## Contents
1. Load-bearing Hadolint rules
2. Multi-stage discipline
3. Layer / apt / pip cleanup
4. Checksum-verified downloads

## 1. Load-bearing Hadolint rules
Run `hadolint <Dockerfile>`; treat these as gating (the rest are style):
- **DL3007** — no `FROM …:latest` / bare floating tag. Pin a tag (Mode 2 goes to a digest).
- **DL3008 / DL3013 / DL3018** — pin `apt-get` / `pip` / `apk` versions where practical.
- **DL3009** — `rm -rf /var/lib/apt/lists/*` in the same `RUN` as `apt-get update`.
- **DL3015** — `apt-get install --no-install-recommends`.
- **DL3042** — `pip --no-cache-dir`; **DL4006** — `SHELL ["/bin/bash","-o","pipefail","-c"]` before a piped `RUN`.
- **DL3002** — do not end on `USER root`; **DL3025** — exec-form `CMD`/`ENTRYPOINT` (JSON array) for correct signal handling.
A deliberate exception carries an inline `# hadolint ignore=DLxxxx` **with a reason** (EnXemble does this on `api/Dockerfile`'s apt block).

## 2. Multi-stage discipline
Separate build tooling from runtime: a `builder` stage compiles/installs; the final stage `FROM`s a minimal base and `COPY --from=builder` only the artifacts. Every EnXemble image does this (`api/Dockerfile` build→dev/prod; `ui/Dockerfile` base→deps→builder→prod). Never ship compilers, `-dev` headers, or the build cache in the runtime image.

## 3. Layer / apt / pip cleanup
- One `RUN` for `apt-get update && apt-get install --no-install-recommends … && rm -rf /var/lib/apt/lists/*` — a separate `rm` in a later layer does not shrink the image.
- Purge build-only packages in the same or a later layer (`apt-get purge -y --auto-remove …`, as `api/Dockerfile` does).
- Order layers cache-friendliest→volatile (deps before source) so a source edit doesn't bust the dependency layer.

## 4. Checksum-verified downloads
Anything fetched into the image must be checksum- or digest-verified and **fail closed**. Precedents: the collector Dockerfile pins `OPENSSL_SHA256` + `sha256sum -c`; the api image re-verifies a `<wheel>.sha256` sidecar at bake time so the build FAILS on tamper. A bare `curl | tar` with no verification is a finding.

Sources: Hadolint (https://github.com/hadolint/hadolint), Docker best-practices (https://docs.docker.com/build/building/best-practices/).
