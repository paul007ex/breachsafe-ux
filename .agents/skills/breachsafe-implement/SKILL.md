---
name: breachsafe-implement
description: Write or extend code in a BreachSAFE Quantum Platform (BQP) repo — Rust crypto crates (thin-OpenSSL-wrapper discipline) or Python scanner/tooling (locked-model, quality-gated CLI discipline) — under narrow, test-first, issue-referenced scope. Use when the task is implementing a feature, extending existing code within a defined milestone/issue scope, or fixing one specific reported bug. Does not audit, review, or decide what to prioritize.
---

# breachsafe-implement

**Applies to:** QuCrypt, QuCert, QuCustody, QuReddy, Qurum — any repo where the task is
writing or extending code. Per-repo, not platform-wide.

## Contents
- Authorization gate
- Stay in its lane
- Two modes
- Workflow: isolate, pressure-test, minimize, validate
- Compare every fork edit to the OSS Prowler baseline
- Cross-cutting principle: don't reimplement the library
- Language-specific discipline
- Scope discipline
- When you finish
- References

## Authorization gate

May run any local command freely (build/test/lint/format/run) and do local git
inspection/staging (`status`/`diff`/`log`/`add`). Never commits, pushes, branches, opens
a PR, merges, tags, or comments on an issue on its own initiative — stage the change,
show the diff, and wait for explicit authorization, even if the repo's own workflow docs
describe committing + opening a PR as "the fix workflow" (that describes the end state
a human wants, not standing authorization to execute it).

## Stay in its lane

Implements only — doesn't decide what to build (`breachsafe-pqc-pm`) or grade its own
work (`breachsafe-quality-review`, `breachsafe-security-audit`, `breachsafe-conformance`).
Starts once "what to build" is decided; ends once code + passing tests exist locally.
Running the local test/lint loop while implementing is normal; a formal PR audit or
Tier-1 gate sign-off is the reviewing skill's job.

## Two modes

- **Feature/extension** — building or extending within a defined scope (milestone spec,
  locked schema, open issue). Bootstrap sequence + a real doc-drift lesson learned
  authoring this skill: `references/bootstrap-reading.md`.
- **Narrow bug fix** — one defect, one root cause, one small patch, test-first, stop and
  escalate if scope exceeds ~1 production file + 1 test file:
  `references/surgical-fix-workflow.md`.

## Workflow: isolate, pressure-test, minimize, validate

New or risky work starts in an isolated scratch workstream — a `/tmp` clone, a
throwaway branch, a separate worktree — never directly in the production tree.
Prove the approach there first: exercise the real failure path, run adversarial/
synthetic inputs, confirm it actually works before it touches code anyone ships.

Once proven, bring the **minimum** into production: the fix/feature itself, plus
whatever test coverage is standard OSS/CI-CD practice for a change this size — not
every adversarial probe used to develop it, and not a sprawling test tree that
outweighs the code it covers. A production repo bloated with tens of thousands of
lines of test scaffolding is itself a smell, not evidence of rigor. Exploratory/
adversarial test harnesses belong in a separate harness repo (or stay in the
scratch workstream) — shipping test-only tooling inside what customers deploy is
the same anti-pattern as shipping dev dependencies in a release image.

Once the minimized version lands in production, **validate it again there** — a
green pass in the isolated workstream doesn't transfer automatically. The
production tree's own gate (lint/type-check/test/build) has to run clean in place,
not be assumed inherited from the scratch environment; the two trees can drift
(different lockfile, different config, different Python/Rust version) even when
the code is identical.

Concrete precedent from this session: the `breachsafe-common` quality-gate scripts
were built and exercised against synthetic JUnit fixtures in an isolated `/tmp`
directory first (including a real bug caught there — an absolute `--glob` pattern
that crashed) before ever being committed, then re-validated by actually running
them against this repo once in place.

## Compare every fork edit to the OSS Prowler baseline

BreachSAFE-Enterprise (EnXemble) is a **fork of Apache-2.0 `prowler-cloud/prowler`**. Before
editing any file that exists upstream, diff it against the upstream baseline — it tells you
what "as if Prowler built it" actually means for *this* file, and whether the line you're
touching is upstream code or a fork-local addition.

- **Fetch the baseline** for the exact path:
  `curl -s https://raw.githubusercontent.com/prowler-cloud/prowler/master/<path>` (or
  `gh api repos/prowler-cloud/prowler/contents/<path> --jq .download_url`). Grep the symbol
  you're about to change — if it appears **0×** upstream, it's a **BreachSAFE fork-local**
  edit; if it's upstream, match upstream's structure and keep the diff minimal.
- **Classify, then act.** *Upstream code* → change the one causal line in upstream's idiom,
  never refactor upstream shape under cover of a fix. *Fork-local code* → you own it; still
  match the file's local style.
- **Mark fork-local edits** with the repo's convention (verified in-tree):
  `// BREACHSAFE-EXTENSION(#NNN) — reason.` for a single line, or
  `// BEGIN BREACHSAFE-EXTENSION(#NNN) … // END BREACHSAFE-EXTENSION(#NNN)` for a block.
  This keeps the fork-delta ledger honest (see BreachSAFE #153/#206) so the next upstream
  rebase can see exactly what diverged and why.
- **Worked example (#218):** `NavigationLink` was missing `guarded`, breaking `next build`.
  Baseline check showed `guarded` is 0× upstream → fork-local → the added field carries
  `// BREACHSAFE-EXTENSION(#218)`. The comparison is what told us it was fork-local, not a
  regression against upstream.

## Cross-cutting principle: don't reimplement the library

This codebase family wraps a well-vetted external implementation rather than
reimplementing it — every crypto transformation goes through OpenSSL (Rust) or a real
subprocess (Python), never hand-rolled or mocked logic. If no safe wrapper exists,
isolate the raw call behind the smallest possible boundary (one named file), not spread.

Do not build a large workaround solely to avoid a small dependency/application change.
When the approved plan has not compared the unchanged upstream seam, a small additive
patch, and an external workaround or replacement—and the choice materially changes total
code, security or operations—stop and return the decision to PM. Implement an approved
dependency patch only when it is generic, isolated, compatibility-tested and
license-compliant; implementation work never invents that architecture decision.

## Language-specific discipline

- **Rust** (QuCrypt/QuCert/QuCustody) — thin-wrapper discipline, unsafe scoping, zeroize
  discipline, fail-closed errors, current module layout: `references/rust-conventions.md`.
- **Python** (QuReddy/Qurum) — locked-model discipline, subprocess-boundary discipline,
  quality-gate command set: `references/python-conventions.md`.

Test-first always — write the test before or alongside the code, confirm it fails for
the expected reason. Capture real fixtures rather than inventing them:
`references/test-fixture-capture.md`.

## Scope discipline

Build only what was asked; no placeholder scaffolding (every file must be exercised by
the working path or a test); locked schemas/models/CLI contracts stay locked unless the
scope explicitly authorizes a change; don't add dependencies without a traceable
requirement.

## When you finish

Report plainly, anchored to commands actually run: what you implemented/fixed and where
(file paths); tests added and their result; commands run (build/lint/type-check/test)
and PASS/FAIL/NOT RUN, never "looks fine"; what you intentionally left out of scope;
any `ASSUMPTION:`/`ANTIPATTERN FLAGGED:` markers stated explicitly and called out as needing
your sign-off (not silently treated as already resolved); and confirmation no git-write
happened without authorization.

## References

- `references/bootstrap-reading.md` — read-before-coding sequence; doc-drift caution.
- `references/rust-conventions.md` — thin-wrapper discipline, current module layout.
- `references/python-conventions.md` — locked-model + subprocess discipline.
- `references/surgical-fix-workflow.md` — narrow bug-fix protocol.
- `references/test-fixture-capture.md` — real-fixture capture protocol.
