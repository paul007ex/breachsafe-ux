---
name: breachsafe-release
description: Audit supply-chain and release posture for Rust, Python, or Go packages — enforced vulnerability/license/provenance gates, registry publish readiness, OpenSSF Scorecard, artifact signing, and SLSA provenance. Use before a crates.io/PyPI publish, when tagging or cutting a release, or when checking whether security tools actually fail CI rather than just run. Audit only — never files issues, publishes, or tags a release without explicit authorization.
---

# breachsafe-release

**Applies to:** QuCrypt, QuCert (Rust / crates.io), QuReddy, Qurum (Python / PyPI), and
bao-pqc (Go / OpenBao plugin, cgo-linked to OpenSSL) once approaching release; QuCustody
once it has code to release.

## Contents
- Authorization gate — highest blast-radius skill in this library
- Stay in its lane
- Two concerns — they compose, don't duplicate
- The recurring trap
- Release preflight — operational gotchas (hard-won)
- How to run
- References

## Authorization gate — highest blast-radius skill in this library

A crates.io/PyPI publish is effectively irreversible (yanking still leaves the version
permanently listed). May run freely: read-only inspection; checks that fail closed but
don't act (`cargo audit`, `cargo deny check`, `cargo vet`, `pip-audit`, `deptry`, `reuse
lint`, `gitleaks detect`, `govulncheck`, `go mod verify`); **dry-run** publish checks (`cargo publish --dry-run`, `cargo
package --list`, `twine check`) — these build and inspect, never upload. Never runs a
real publish, creates/pushes a release tag, cuts a GitHub Release, files/comments an
issue, or edits repo config to "fix" a finding on its own initiative. Draft the checklist
or report; nothing executes until explicit, in-conversation authorization for that
specific action — "just publish it" for one version counts as authorization for that
action only, not a standing green light.

## Stay in its lane

Not general code quality (`breachsafe-quality-review`), not crypto correctness
(`breachsafe-security-audit` / `breachsafe-conformance`), not implementation
(`breachsafe-implement`), not sequencing (`breachsafe-pqc-pm`).

## Two concerns — they compose, don't duplicate

1. **Supply-chain enforcement** — is the dependency tree scanned for known
   vulnerabilities/license/provenance gaps, and is that scan wired into CI so a finding
   actually **fails the build**, not just present as a tool someone ran once.
   `references/supply-chain-checklist.md` (Rust, Python, and Go sections).
2. **Release and publication readiness** — is the package ready for its target registry,
   artifact-signing and provenance commitments. Use OpenSSF Scorecard as a security-practice
   signal. Evaluate OSPS Baseline/Best Practices conformance only when the project is
   actually eligible; PolyForm projects are not FLOSS. The checklist in
   `references/oss-release-readiness-checklist.md` defers to (1) for vulnerability scans.

## The recurring trap

A tool that **runs** but can't **fail the build** is theater: `cargo audit` without
`--deny warnings` exits 0 on findings; a misnamed `deny.toml` silently falls back to
defaults, enforcing nothing while looking configured; a gate that only lives in a local
hook is skippable. Always check the FAIL path — exit code and CI wiring — not just "the
tool is installed and I ran it once."

## Release preflight — operational gotchas (hard-won)

Concrete failures hit repeatedly across QuReddy releases (0.2.14–0.2.17), each invisible to a
green *local* gate — verify against CI and the published artifact, not just locally. Issue
refs are `breachsafe/qureddy#<n>`; **remediation + verify command for each is in
`references/release-preflight.md`** (numbering matches).

1. **Lockfile freshness after a version bump.** Bump scripts rarely relock; a stale
   `uv.lock`/`Cargo.lock`/`go.sum` still pins the old version and fails every `--locked` step.
   Relock after bumping, before tagging (#213).
2. **"Ran" ≠ "signed" — confirm the run AND the bundles.** Signing/SLSA/attestation live in a
   `release: published` workflow; a draft release or `disabled_manually` workflow never fires
   it. Confirm BOTH: `release.yml` shows `[release] <tag>: completed/success`, AND the assets
   gained `<artifact>.sigstore` bundles/attestations (#232/#219).
3. **Bit-rot while disabled — re-verify EVERY workflow individually.** "Green last time +
   re-enabled ≠ green now." Each `disabled_manually` job rots independently; force a fresh run
   of each on the release commit. This cycle: pip-audit hit pip's own advisory (#235), the
   smoke gate never built the wheel + stale `ARG` (#237/#215), ClusterFuzzLite's
   `.dockerignore` excluded `build.sh` (#86/#239).
4. **Manual/disabled-CI releases silently regress Scorecard.** Merging PRs or cutting releases
   while CI/release workflows are off drops Signed-Releases and CI-Tests; only the next
   Scorecard re-run reveals it. A local green gate ≠ Scorecard/CI reality (#219/#220/#232).
5. **`.dockerignore` is load-bearing for EVERY docker build, not just the app image.** A
   repo-root `* !Dockerfile` written for the main image silently starves a second build
   (ClusterFuzzLite needs `build.sh` + sources in context). Scope ignore rules per
   Dockerfile-dir when multiple images exist (#239).
6. **Docker wheel install.** Build the wheel into `dist/` in the SAME job; COPY the
   version-scoped wheel (`…-${VERSION}-*.whl`), never a glob over all wheels (multiple versions
   → pip ResolutionImpossible); pass `--build-arg <VERSION>` so a stale `ARG` default can't
   pick a missing wheel (#215/#237).
7. **Branch-protection sequencing — CI green FIRST.** Requiring status checks while CI is
   disabled blocks ALL merges, including release merges. Turn branch protection on only after
   CI is live and green on `main` (#84/#220).
8. **pip-audit scope divergence.** Declared-deps audit vs full-venv audit disagree: the venv's
   pip/setuptools carry their own advisories (e.g. pip PYSEC-2026-3721) that fail CI while the
   local gate passes. Align them (#235).
9. **Scorecard Pinned-Dependencies parses shell tokens literally.** A `pip install` arg made of
   multiple AST parts (literal + `${ARG}` + glob) reads as *unpinned*. Use a single-part
   literal glob (#221).
10. **Version single-sourcing.** A bump must reach EVERY sink — pyproject, README/badge,
    CHANGELOG heading + TOC, Dockerfile ARG default, lockfile, goldens. Audit for drift after
    bumping (#206).

## How to run

1. Detect ecosystem(s) — presence of `Cargo.toml`, `pyproject.toml`, and/or `go.mod`, don't assume.
2. Run the matching supply-chain checklist, verifying enforcement, not presence.
3. Run release-readiness for anything actually heading toward a publish; if nothing is
   imminently publishable, report current gaps as forward work, don't invent urgency.
4. Report met / gap / needs-repo-settings-check (some OpenSSF Scorecard checks need
   GitHub API access and aren't verifiable from a local checkout).
5. If the user wants findings filed or a real publish run, draft the exact
   command/content first and wait for explicit authorization.

## References

- `references/supply-chain-checklist.md`
- `references/oss-release-readiness-checklist.md`
- `references/release-preflight.md` — remediation + verify command for each preflight gotcha
