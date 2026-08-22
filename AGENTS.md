<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# AGENTS.md — breachsafe-ux

Guidance for **any** AI assistant working in this repo (Codex, Claude Code, and others).

## Canonical source

The full, maintained agent guidance lives in [`CLAUDE.md`](CLAUDE.md). **Read it first** — it
is the single source of truth; this file only restates the load-bearing invariants so a
non-Claude agent does not miss them. If the two ever disagree, `CLAUDE.md` wins and this file
should be corrected.

## Standing invariants (do not relitigate)

- **License — Apache-2.0.** breachsafe-ux is a deliberate, reviewed OSS exception to the
  platform's PolyForm-Noncommercial default (so it can be the public shared dependency of the
  OSS QuReddy `[ux]`). Every new first-party file carries an `Apache-2.0` SPDX header. Never
  emit PolyForm or MIT headers here. Third-party or vendored material keeps its original license
  (e.g. bundled Lucide icons stay ISC).
- **Python 3.12** today (3.14 migration is tracked in #100). Use the project venv via
  `uv run --locked`; do not fall back to system Python.
- **Issue-driven, branch + PR only.** Open an issue for non-trivial work, branch from `main`,
  one thing per PR; never commit directly to `main`.
- **Quality gates are not theater.** A red gate is a bug to fix, not a threshold to lower. Never
  skip a test, add a blanket `noqa`, or weaken a gate to make it pass.
- **Fail closed.** The three-state verdict (VALID / INVALID / VALIDATOR-UNAVAILABLE) is
  load-bearing; never render a green result the validator did not give.

## Where things are

- Architecture + repo map: [`CLAUDE.md`](CLAUDE.md) and [`docs/adr/`](docs/adr/).
- How to run every gate locally (one command): [`CONTRIBUTING.md`](CONTRIBUTING.md) §4.
- First scan + reading the verdict: [`docs/first-scan.md`](docs/first-scan.md).

## Agent skills

Task-scoped skills are installed under both `.claude/skills/` (Claude) and `.agents/skills/`
(Codex), sourced from the canonical `breachsafe-common/skills` library — edit them there and
re-sync, never edit installed copies.
