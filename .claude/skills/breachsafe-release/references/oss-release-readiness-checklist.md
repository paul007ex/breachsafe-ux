# Release and supply-chain readiness checklist

Audit only. This evaluates a package/crate against its target registry, artifact and
supply-chain requirements. OpenSSF Scorecard remains a useful security-practice signal for
source-available repositories, but OSPS Baseline and Best Practices badge conformance are
FLOSS programs with license eligibility requirements. It does **not** re-run `cargo audit`/`deny`/`vet` or
`pip-audit`/`deptry`/`reuse lint` — that's `supply-chain-checklist.md`'s job; reference its
result under the relevant criterion below instead of re-deriving it.

**Workspace note (generalize, don't hardcode):** in a Cargo workspace or a Python monorepo,
files can split between the repo ROOT and a per-package subdirectory. The registry (crates.io
or PyPI) publishes the *package*, so package-level metadata (Cargo.toml fields, pyproject.toml
fields, package README) lives at the package level. OpenSSF/GitHub community-health files
(LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, CI config, badges) are repo-ROOT concerns. Check
BOTH levels for every criterion below and say explicitly which level a gap is at — a file
present at the package level but absent at root (or vice versa) is a common workspace-move
trap and easy to miss if you only check one level.

## Contents

- Section 1 — OpenSSF Scorecard checks
- Section 2 — OSPS Baseline + OpenSSF Best Practices Badge
- Section 3 — crates.io publish readiness (Rust)
- Section 4 — Licensing / REUSE / SPDX (both ecosystems)
- Section 5 — PyPI publish readiness (Python)
- Section 6 — Repo community-health files (root level)
- Section 7 — Report findings (do not file)
- Honesty rules

## Section 1 — OpenSSF Scorecard checks

Scorecard (https://github.com/ossf/scorecard) scores a repo on automatable security
practices. Ecosystem-agnostic — applies the same way to a Rust crate or a Python package.
Some checks need the GitHub API (branch protection, signed releases) and can't be fully
verified from a local checkout — mark those "needs repo-settings check," don't assume pass.

- [ ] **Branch-Protection** — main protected, PRs required, no direct push. If the repo's
      own docs already say "never commit to main directly," verify it's enforced by branch
      protection settings, not just documented convention.
- [ ] **Code-Review** — PRs reviewed before merge (Scorecard wants ≥1 reviewer)
- [ ] **CI-Tests** — tests run on every PR
- [ ] **SAST** — static analysis in CI (clippy for Rust; ruff/mypy/bandit for Python) — check
      it runs in CI, not only in a local pre-commit hook
- [ ] **Fuzzing** — a fuzz target wired to CI or OSS-Fuzz, if applicable to this package
- [ ] **Dependency-Update-Tool** — Dependabot/Renovate config present
- [ ] **Pinned-Dependencies** — CI actions pinned by SHA; lockfile committed
- [ ] **Signed-Releases** — release artifacts signed (Sigstore/cosign, or minisign)
- [ ] **Token-Permissions** — GitHub Actions `permissions:` block is minimal (read-only
      default, elevated only where a step needs it)
- [ ] **Security-Policy** — SECURITY.md present and lists a real disclosure contact/SLA
- [ ] **Vulnerabilities** — dependency scan clean (defer to `supply-chain-checklist.md`)
- [ ] **License** — a recognized LICENSE file present at repo root

```bash
ls .github/dependabot.yml .github/renovate.json 2>/dev/null || echo "no dep-update tool configured"
ls .github/workflows/*.yml 2>/dev/null || echo "no CI (CI-Tests/SAST/Fuzzing all fail)"
grep -rn 'permissions:' .github/workflows/ 2>/dev/null || echo "no token-permissions hardening found"
test -f LICENSE && echo "LICENSE present" || echo "no root LICENSE"
```

## Section 2 — OSPS Baseline + OpenSSF Best Practices eligibility

First classify eligibility from the repository's actual source and release licenses:

- For a public project whose licenses meet the OSI Open Source Definition or FSF Free
  Software Definition, audit the current OSPS Baseline and Best Practices criteria.
- For a BreachSAFE PolyForm Noncommercial project, record both programs as
  `NOT_APPLICABLE — source-available, not FLOSS`. Never report this as a failed release gate,
  an intended badge, or a reason to replace PolyForm. Individual security controls may be
  reused as a non-conformance hardening checklist, clearly labeled as such.
- Date the result and name the exact OSPS version. The current-version pointer is mutable.

For an eligible FLOSS project, audit the passing/baseline-1 essentials:

- [ ] Project states what it does and how to contribute (README + CONTRIBUTING)
- [ ] Public VCS + issue tracker
- [ ] License is OSI-approved and declared (check the SPDX expression matches actual
      LICENSE file(s) present — see Section 4)
- [ ] At least one documented build + test path that works from a clean checkout
- [ ] Vulnerability-reporting process (SECURITY.md with a contact + SLA)
- [ ] Code of Conduct present
- [ ] No unjustified known vulnerabilities (defer to `supply-chain-checklist.md`)
- [ ] Release notes / CHANGELOG per release
- [ ] If the badge criterion applies to this package's domain (e.g. a crypto library): does
      it use published, standard algorithms, and are conformance tests (known-answer tests
      or equivalent) present? Note as a strength if so — readiness review isn't only gaps.

If an eligible project's Best Practices entry already exists, record its current percentage.
If no entry exists, a badge application is only a recommendation. For an ineligible
PolyForm project, do not create or recommend an entry.

## Section 3 — crates.io publish readiness (Rust)

Only run for a crate that is actually heading toward a real `cargo publish`. For each such
crate:

```bash
cd <crate directory>
# 3a. Metadata completeness — crates.io requires name/version/license/description:
grep -iE '^(name|version|license|description|repository|documentation|readme|keywords|categories|rust-version|homepage)' Cargo.toml

# 3b. Dry-run publish — the real gate, not eyeballing Cargo.toml:
cargo publish --dry-run 2>&1 | tail -20

# 3c. Packaged contents — no secrets/test junk; README+SPDX included:
cargo package --list 2>&1 | head -40
```

- [ ] Crate name available/owned on crates.io (confirm not already taken by an unrelated
      project)
- [ ] `license` is a valid SPDX expression and matches the LICENSE file(s) actually present
- [ ] `description`, `repository`, `documentation`, `readme`, `keywords`, `categories` all set
- [ ] `rust-version` (MSRV) declared and verified to actually build on that toolchain
- [ ] `cargo publish --dry-run` succeeds
- [ ] Packaged tarball excludes secrets, fixtures-with-secrets, and audit-loop artifacts
- [ ] Pre-1.0/alpha work uses a pre-release version number if it isn't stable yet
- [ ] `[package.metadata.docs.rs]` present if the crate needs non-default build config (e.g.
      a native library dependency) — without it, docs.rs can fail to build and ship an empty
      docs page silently
- [ ] **Trusted Publishing (OIDC)** configured for the publish workflow, not a long-lived
      `CRATES_IO_TOKEN` secret — crates.io supports OIDC trusted publishing from GitHub
      Actions; a token in repo secrets is the legacy, weaker path and should be flagged

## Section 4 — Licensing / REUSE / SPDX (both ecosystems)

```bash
# Rust:
grep -L 'SPDX-License-Identifier' src/*.rs 2>/dev/null   # any source file missing the header?
ls LICENSE LICENSES REUSE.toml NOTICE 2>/dev/null
grep '^license' Cargo.toml 2>/dev/null

# Python:
reuse lint 2>&1 | tail -20   # full SPDX/REUSE compliance check
grep '^license' pyproject.toml 2>/dev/null
```

- [ ] Every source file carries an `SPDX-License-Identifier` header, or `reuse lint` passes
      (covers files that can't carry a header via `REUSE.toml`/`.reuse/dep5`)
- [ ] LICENSE file(s) at root match the declared SPDX expression exactly
- [ ] **BreachSAFE first-party policy:** new first-party crates and future releases default
      to `PolyForm-Noncommercial-1.0.0`. Never replace it with the Rust ecosystem's common
      `MIT OR Apache-2.0` expression merely for convention. A different license requires an
      explicit approved exception and a contributor/file-provenance review. Historic
      grants remain effective for copies already released.
- [ ] Third-party, vendored, generated, standard and upstream files retain their original
      licenses and notices. The root `LICENSE`, `LICENSES/`, `NOTICE`, package metadata,
      README wording and SPDX/REUSE annotations must describe the mixed provenance
      accurately; `reuse lint` must pass.

## Section 5 — PyPI publish readiness (Python)

Only run for a package actually heading toward a real publish. This section covers the
Rust-crate-equivalent metadata/registry checks; twine check, clean-room install, and
version/tag matching are general PyPI-publish hygiene and belong here too — this skill does
not delegate them to a separate tool the way it might for CI mechanics.

```bash
cd <package root>
grep -iE '^(name|version|description|license|readme|requires-python|classifiers)' pyproject.toml
python -m build 2>&1 | tail -20   # or `uv build` — build sdist + wheel
twine check dist/* 2>&1
```

- [ ] Package name available/owned on PyPI (confirm not already taken)
- [ ] `pyproject.toml` metadata complete: name, version, description, license, readme,
      requires-python, classifiers
- [ ] `twine check` passes on the built sdist and wheel
- [ ] Version number matches the git tag that will be pushed for the release
- [ ] **PyPI Trusted Publishing (OIDC)** configured for the publish workflow, not a
      long-lived `PYPI_API_TOKEN` secret — this is the 2024+ standard; a token in repo
      secrets should be flagged as the legacy, weaker path
- [ ] **Sigstore signing / SLSA Build Provenance** for release artifacts (e.g.
      `actions/attest-build-provenance` and/or `sigstore/gh-action-sigstore-python`) — if
      the project's own SECURITY.md or docs already commit to this, verify it's actually
      wired into a workflow, not just promised in prose. (This exact gap — a security-policy
      commitment to Sigstore + SLSA + Trusted Publishing that isn't wired into CI yet — is a
      real, currently-open example of the kind of finding this section exists to catch; treat
      it as illustrative of the check, not as a claim about the state of any specific repo
      you haven't verified.)
- [ ] Reproducible-build spot check, if claimed: building twice in clean environments
      produces byte-identical (or hash-identical) artifacts
- [ ] `py.typed` marker present and honest (only if the package actually ships complete type
      stubs — a `py.typed` file with incomplete stubs is worse than no marker)
- [ ] Entry points (console scripts, plugin hooks) actually resolve after a clean install

## Section 6 — Repo community-health files (root level)

```bash
for f in README.md LICENSE LICENSE-MIT LICENSE-APACHE CONTRIBUTING.md \
         CODE_OF_CONDUCT.md SECURITY.md CHANGELOG.md; do
  [ -e "$f" ] && echo "root: $f present" || echo "root: $f MISSING"
done
# Cross-check: present at the package level but not at root, or vice versa?
find . -maxdepth 3 \( -iname 'README*' -o -iname 'CHANGELOG*' \) -not -path './target/*' -not -path './.git/*'
```

- [ ] Root README (or the package README is canonical and root points to it)
- [ ] CONTRIBUTING.md, CODE_OF_CONDUCT.md present
- [ ] CHANGELOG maintained at the level releases are actually cut from
- [ ] Flag any root-vs-package split explicitly — a file present only inside a workspace
      member but expected at root (or vice versa) is the workspace-move trap called out above

## Section 7 — Report findings (do not file)

Per the authorization gate in `SKILL.md`, this skill never runs `gh issue create` or any
other filing/publish action on its own. Present findings as a structured report instead —
one line per gap, with the exact command + output that surfaced it, and which OpenSSF
check / OSPS item / registry requirement it maps to. If the user then wants issues filed or
a publish run, draft the exact content/command and wait for explicit authorization before
running it.

## Honesty rules

- A criterion is "met" only if verified (file exists, dry-run passes, CI step present) — not
  "the metadata file looks complete." Run the dry-run, don't eyeball the TOML.
- Distinguish root-level vs. package-level gaps explicitly (the workspace-move trap).
- Defer vulnerability/license/secret scanning to `supply-chain-checklist.md`; don't
  double-report the same finding under both checklists.
- Scorecard checks needing the GitHub API (branch protection, signed releases) may not be
  verifiable locally — mark "needs repo-settings check," don't assume pass.
- Note real strengths (standard algorithms + conformance tests, a genuinely good SECURITY.md,
  a clean scan) alongside gaps — readiness review isn't only a list of problems.
