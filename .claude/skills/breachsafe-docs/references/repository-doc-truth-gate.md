# Repository documentation truth gate

Use this checklist after editing BreachSAFE repository documentation. Record PASS, FAIL, or
NOT RUN for every applicable row.

## Contents
- Evidence baseline
- Product identity and release truth
- Public contracts
- Diátaxis and architecture
- Links, ledgers, and provenance
- Mechanical verification
- Report

## Evidence baseline

- Current branch and Git status recorded; unrelated work preserved.
- Canonical repository and issue tracker identified.
- Accepted ADRs, public CLI/API/schema, tests, package metadata, and current issues read.
- Scratch and handoff claims independently verified before promotion.
- Every maturity claim classified as shipped, verified, designed, planned, blocked, or
  historical.

## Product identity and release truth

- Project name, CLI, distribution name, canonical repository, license, and version agree.
- README badges match package metadata and actual release state.
- Changelog version matches the intended tag; compare links share valid history or use
  explicit commits.
- PyPI/TestPyPI/Docker/signature/provenance claims have external proof.
- Supported Python, OpenSSL, OS, and tool versions match tested configurations.

## Public contracts

- CLI reference includes every shipped command, option, output format, and exit code.
- JSON/CBOM schema docs describe current emitted bytes, not an earlier milestone.
- Failure, partial, unsupported, and `UNKNOWN` states remain explicit.
- Examples use the built distribution in an isolated temporary environment.
- Machine-readable examples keep stdout parseable, including real `2>&1` checks when that
  behavior is promised.
- Network examples name their capture date/tool version or are clearly illustrative.

## Diátaxis and architecture

- Tutorials teach one successful path without becoming exhaustive reference.
- How-to pages solve a named task without re-explaining architecture.
- Reference pages are exact and complete.
- Explanation pages justify behavior without inventing implementation status.
- Architecture diagrams match actual dependency direction and have explanatory prose.
- Contributor policy and agent instructions do not leak into user-facing distribution
  artifacts.

## Links, ledgers, and provenance

- Every internal Markdown path and anchor resolves.
- Every GitHub issue/PR link targets the correct owner/repository and describes that item.
- ADR identifiers are unique within the declared ledger; collisions are reconciled without
  deleting history.
- ADR statuses match implementation and linked issue/PR state.
- Superseded ADRs remain present and name their successor.
- Changelog entries link issue + PR + governing ADR when those exist.

## Mechanical verification

- Markdown formatter/linter passes if configured.
- Repository doc-link checker passes if configured.
- Package long description passes `twine check`.
- Safe shell examples execute successfully from a clean install.
- Counts (modules, tests, fixtures, skills) are mechanically derived or removed.
- Repo-wide search finds no stale version, owner, planned/shipped, or pre-MVP language for
  the changed surface.

## Report

```text
Docs truth gate:
Files changed:
Truth sources:
Executable examples:
Link/anchor check:
Release claims verified:
Blocked/unverified claims:
Result: PASS | FAIL
```
