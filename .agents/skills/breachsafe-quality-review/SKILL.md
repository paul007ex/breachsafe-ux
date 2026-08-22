---
name: breachsafe-quality-review
description: General software-engineering quality review for the BreachSAFE Quantum Platform — fast local build/test/lint checks, PR diff audits against house coding rules, issue-resolution verification (does the fix actually resolve the bug, not just "tests pass"), documentation-drift sweeps, and a pre-commit anti-pattern self-check. Use when confirming a change builds and passes, auditing a PR/diff before merge, verifying a claimed fix actually resolves its issue, sweeping docs for drift, or self-checking your own diff before committing. Read-only/audit-only by default; never files issues, comments on PRs, changes labels, or pushes/merges without explicit user authorization.
---

# breachsafe-quality-review

**Applies to:** all BQP components — general software-engineering quality and process
review. Consolidates what used to be eight overlapping skills across three repos.

## Contents
- Stay in its lane
- Authorization gate
- The six modes
- Ground rules
- References

## Stay in its lane

Not crypto-correctness/FIPS/memory-safety (`breachsafe-security-audit`), not RFC/NIST
citation accuracy (`breachsafe-conformance`), not supply-chain/release readiness
(`breachsafe-release`), not implementation (`breachsafe-implement`), not sequencing
(`breachsafe-pqc-pm`). Rule of thumb: "would fixing this differently change whether the
crypto is correct, or only whether the code is well-behaved?" — the former belongs to
`breachsafe-security-audit`.

## Authorization gate

Modes 2–4 are read-only/audit-only by default — draft findings, never file/comment/
label/push/merge without explicit per-action authorization. **Mode 5 is the exception**:
fixing your own uncommitted work before commit is expected and normal; it still never
pushes or opens a PR without authorization.

## The six modes

1. **Fast local check** — build + full suite + lint, before anything else. Rust:
   `references/rust-quality-gates.md`. Python: `references/python-quality-gates.md`. Go:
   `references/go-quality-gates.md`. For EnXemble backend/DB tests (Django + Postgres), run
   them **natively**, not via Docker — use the `breachsafe-enxemble-local-tests` skill
   (~20s vs a slow, flaky compose stack).
2. **PR diff audit** — walk the diff against the repo's own coding-rules doc, category
   by category, before "is this ready to merge." `references/pr-audit-checklist.md`. On a
   repo where more than one agent/human may review concurrently, use
   `references/multi-reviewer-arbitration.md` for the reviewer/arbiter split and label
   taxonomy. Check for forward-pressure structural debt with
   `references/size-canary-patterns.md`, scan the diff against
   `references/recurring-bug-categories.md`'s trap list of shapes that recur across
   repos, and walk `references/comprehensive-anti-pattern-catalog.md`'s 173-item
   catalog (20 categories: code smells, SOLID, security bugs, CI/CD, Windows/cross-platform, language-specific,
   this library's own must/must-not rules, etc.) — decide which categories plausibly
   apply, walk only those, cite a number for any real hit. **Prove the walk happened**:
   before reporting, state which categories you actually went through (not "checked
   against the catalog" as a blanket claim), which of the fast-local-check tools (Mode
   1) you actually ran with their real exit codes, and only then report the audit
   complete to the human — a completion claim with no visible verification trail is
   itself the failure mode Mode 2 exists to catch in *other* people's diffs; it applies
   to this skill's own output too.
3. **Issue-resolution verification** — "tests pass" and "the issue is resolved" are
   different questions; requires pre-patch reproduction, not just a patched-state check.
   `references/issue-resolution-verification.md`.
4. **Documentation-drift audit** — read-only sweep for docs that were correct when
   written and are stale now; run as a recurring practice, not a one-off cleanup.
   `references/doc-drift-checklist.md`.
5. **Anti-pattern self-check** — pre-commit checklist on your own diff; the only mode
   that fixes instead of reporting. `references/anti-pattern-self-check.md` (includes the
   §6 test-integrity / false-green check — masking fixtures, weakened tests, DoD = live
   path runs). Crypto-specific anti-patterns are `breachsafe-security-audit`'s, not this.
6. **Test-suite integrity** — "green" is not "tested"; ask whether the tests would fail if
   the code were wrong. Mutation testing (the discriminator), Hypothesis property tests for
   parsers/validators, container-structure tests for any image, and the adversarial input
   corpus (SSRF/injection/encoding/ReDoS). `references/adversarial-and-mutation-testing.md`.
   Reach for it when a suite looks reassuring but bugs still ship (precedent: 33 green tests,
   4 image bugs + a latent SSRF shipped; only 6/33 touched the guard).

Modes 2 and 5 share four checks (panics, subprocess discipline, logging discipline, dead
code) — both point at `references/generic-code-hygiene.md` rather than restating them.
Run `scripts/hygiene_scan.sh <path> [shim-file]` for those four in one deterministic
pass instead of re-typing the greps by hand; each hit is still a candidate to read and
judge, not an automatic finding.

For **Python** specifically, `references/python-style-conventions.md` (PEP 257 + Google
Python Style Guide) adds the docstring / comment-style / precise-typing checks that
`ruff` does **not** catch — a lint-clean, test-green module can still fail it (the
endpoint collector did: 11 undocumented nontrivial functions, `#NN:` ticket-refs used as
comments, 20 `mypy --strict` bare-container errors). Apply it in Modes 1, 2, and 5.

## Ground rules

Verify before you assert — run the tool the project's own way and quote the real exit
code before filing any tool-based finding; a "lint is red"/"mypy fails" claim without a
canonical run is how false HIGHs ship. Read `references/review-false-positives.md` before
writing up findings — a noisy review gets the real ones ignored. Separate `[bug]` from
`[style, your call]`. Verify, don't trust old text — never carry forward a specific
pass/fail count, issue number, or file:line from a previous run or memory; derive it fresh. No hardcoded
absolute paths. A file this skill mentions may have moved — find the module that plays
that role now. Never claim a check passed without running it; "NOT RUN: <reason>" beats
a guessed PASS. Structured output over prose — each mode's reference file has an
explicit report format; use it.

**Self-check before any completion claim** — catch yourself using "should", "probably",
"seems to," or expressing satisfaction ("Great!", "Perfect!", "Done!") before the actual
verification command has been run in this response. Any of those phrasings appearing
before fresh command output is the tell that a claim is about to outrun its evidence —
stop and run the command first. (Credit: this phrasing borrowed from the `superpowers`
skill framework's `verification-before-completion` skill, which states the same
evidence-before-claims principle this section already held, more concretely.)

## References

- `references/rust-quality-gates.md`, `references/python-quality-gates.md`, `references/go-quality-gates.md`
- `references/pr-audit-checklist.md`
- `references/issue-resolution-verification.md`
- `references/doc-drift-checklist.md`
- `references/anti-pattern-self-check.md`
- `references/generic-code-hygiene.md` — shared Mode 2 / Mode 5 checks
- `references/python-style-conventions.md` — Python docstrings/comments/typing (PEP 257 + Google) + concrete traps, Modes 1/2/5
- `references/review-false-positives.md` — the "what NOT to flag" brake; read before writing up any finding (Modes 2/5)
- `references/adversarial-and-mutation-testing.md` — mutation/property/container-structure testing + adversarial input corpus; "green ≠ tested" (Mode 6)
- `references/multi-reviewer-arbitration.md` — reviewer/arbiter split, label taxonomy, for repos with concurrent multi-agent review (Mode 2)
- `references/size-canary-patterns.md` — forward-looking structural-debt flags before a ceiling breaches (Mode 2)
- `references/recurring-bug-categories.md` — trap list of bug shapes that recur across repos, each grounded in a named precedent (Modes 2, 5)
- `references/comprehensive-anti-pattern-catalog.md` — 173-item, 20-category catalog sourced from established literature (Fowler, SOLID, OWASP/CWE, per-language/platform idioms), domain-tagged so a reviewer can skip whole categories fast; distinct from `recurring-bug-categories.md`'s own-incident-only scope (Modes 2, 5)
