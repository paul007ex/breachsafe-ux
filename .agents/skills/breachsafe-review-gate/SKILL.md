---
name: breachsafe-review-gate
description: The pre-merge orchestrator — rates a code diff against a falsifiable 10/10 bar (the code-review counterpart to breachsafe-red-team's plan/ADR rating), AND confirms which of the other review gates (breachsafe-quality-review, breachsafe-cicd-hygiene, breachsafe-release/OpenSSF) actually ran for this change, not just that they exist. Use before merging a nontrivial PR, before a release, or when asked "is this actually ready" / "did we check everything." Does not re-derive any gate's own checks — it confirms invocation and reports the combined verdict. Audit only.
---

# breachsafe-review-gate

**What it is.** Two jobs in one skill, because they're the same moment in a PR's life:
rate the diff itself, and confirm the other gates that *should* have touched this
change actually did. A code review that's clean but skipped the CI-hygiene pass, or a
release that's fast but never ran OpenSSF, is not actually "reviewed" — it's reviewed
in the parts someone remembered to ask about.

**What it is not.** Not a replacement for `breachsafe-quality-review` (style/anti-pattern
audit), `breachsafe-cicd-hygiene` (workflow-file audit), or `breachsafe-release`
(supply-chain/OpenSSF). It doesn't re-run their checks — it asks "did these run, and
what's the honest number now that they have (or haven't)."

## Contents
- Authorization gate
- Stay in its lane
- Part 1: rate the diff — a falsifiable 10/10 bar for code review
- Part 2: the gate checklist — did the other skills actually run
- Output format
- References

## Authorization gate

Audit only. May read anything freely (diff, CI logs, workflow files, `gh pr view`,
`gh run list`). May draft findings, a rating, and a gate checklist. **Never merges,
never pushes, never files an issue/comment, never edits the diff being reviewed**
without explicit in-conversation authorization for that specific action.

## Stay in its lane

| Skill | Decides |
|---|---|
| `breachsafe-quality-review` | is the code clean (style, docstrings, anti-patterns) — this skill asks whether that pass *happened*, not what it found |
| `breachsafe-cicd-hygiene` | is the CI/CD config itself well-designed — same relationship |
| `breachsafe-release` | is supply-chain/OpenSSF/release-readiness actually enforced — same relationship |
| `breachsafe-red-team` | is the *design* (plan/ADR/architecture) right — this skill is its code-diff counterpart, not a duplicate |
| `breachsafe-security-audit` | is it secure — hand off a suspected vulnerability there, don't re-derive it here |
| `breachsafe-review-gate` | **is this diff a 10, and did every gate that should have run actually run** |

Hand off: a real anti-pattern found while rating → `quality-review` owns fixing it, not
this skill. A missing CI concurrency guard → `cicd-hygiene`. A supply-chain gap →
`release`. This skill's own output is the rating + the checklist, not a fix.

## Part 1: rate the diff — a falsifiable 10/10 bar for code review

Same discipline as `breachsafe-red-team`'s plan rating, applied to a diff instead of a
design: steelman first (what's genuinely good about this change, in 2-3 sentences —
skipping this makes the critique read as reflexive negativity), then rate against
concrete, checkable axes, not vibes:

- **Scope discipline** — does the diff do only what it claims, or did it smuggle in
  unrelated refactors/renames under cover of the stated change? (`breachsafe-implement`'s
  "big-bang edits" anti-pattern, checked here as a gate item.)
- **Tests actually exercise the failure path** — not just "tests pass," but do the new/
  changed tests fail if the fix is reverted? A green suite that would still be green
  without the fix is the "33 green tests, 4 shipped bugs" failure mode this whole
  library is built to catch.
- **No quality theater** — no skipped/xfail-marked tests introduced, no lowered
  coverage threshold, no retry-count bump used to paper over a real flake (cross-check
  against `breachsafe-cicd-hygiene`'s skip-masking section if CI config changed).
- **Test footprint is proportionate, not dumped** — per `breachsafe-implement`'s
  isolate/pressure-test/minimize/validate workflow, exploratory or adversarial test
  scaffolding used to develop the change should have stayed in the scratch workstream
  (or a separate harness repo), not landed wholesale in the production tree. A diff
  that adds a large, disproportionate test tree for a small change is a flag, not a
  sign of rigor — check whether what shipped is the minimal standard-practice coverage
  or a full dump of dev-time exploration.
- **Escape hatches used honestly** — any `ASSUMPTION:`/`ANTIPATTERN FLAGGED:` marker in
  the diff is stated in the PR description, not buried in a code comment, and — per the
  governance fix already in `breachsafe-implement` — is genuinely flagged for human
  sign-off, not silently self-declared as `ANTIPATTERN APPROVED` without evidence of
  that sign-off actually happening.
- **Claims match evidence** — if the PR description says "verified against X," is X
  actually cited (file:line, command run, screenshot) or just asserted? A claim without
  an anchor is a red flag, not a pass.
- **Matches local idiom** — the diff reads like it was written by someone who'd already
  read the surrounding file, not dropped in from a different codebase's style.

**Rating**: n/10 with sub-scores per axis above and a falsifiable path to 10 (name the
specific thing that would need to change, not "needs polish"). Design-vs-execution
split matters here too — a diff can be a 9 on scope/idiom and a 4 on test rigor; say so
separately, don't average it into a mushy 6.

## Part 2: the gate checklist — did the other skills actually run

For the change under review, determine which gates *apply* (not every PR touches CI or
approaches a release), then confirm each applicable one actually happened — evidence,
not assumption:

| Gate | Applies when | Evidence it actually ran (not just "should have") |
|---|---|---|
| `breachsafe-quality-review` | any nontrivial code change | a PR-audit pass exists in the conversation/PR comments, not just "tests pass" reported |
| `breachsafe-cicd-hygiene` | diff touches `.github/workflows/*` or adds/changes a scheduled job | concurrency guards checked, no duplicate-CI risk introduced, cron frequency sanity-checked |
| `breachsafe-release` | diff is part of a release push, touches `pyproject.toml`/`Cargo.toml`/dependency pins, or the PR description says "ready to publish" | supply-chain scan confirmed wired to fail CI (not just present), OpenSSF/OSPS posture checked if this is the release-readiness pass |
| `breachsafe-security-audit` | diff touches crypto/PKI/key-custody code | explicit hand-off happened, not silently skipped because "it's a small change" |

**Report each as RAN (with the evidence) / NOT RUN (flag it, don't guess it would have
passed) / NOT APPLICABLE (say why)**. A gate marked "not run" on an applicable change is
the single most important line in this skill's output — it's the thing a rushed merge
would otherwise skip past.

## Output format

```
STEELMAN — what's genuinely good about this diff (2-3 sentences)

DIFF RATING — n/10, sub-scores per axis, falsifiable path to 10

GATE CHECKLIST
  quality-review:  RAN / NOT RUN / N/A  — evidence or reason
  cicd-hygiene:    RAN / NOT RUN / N/A  — evidence or reason
  release/OpenSSF: RAN / NOT RUN / N/A  — evidence or reason
  security-audit:  RAN / NOT RUN / N/A  — evidence or reason

VERDICT — ready to merge / ready pending [specific gate], with the smallest next step
```

## References

- Companion: `breachsafe-red-team` (same rating discipline, applied to plans/ADRs
  instead of diffs — read its "steelman first" and "Output format" sections for the
  shared pattern this skill mirrors).
- `breachsafe-quality-review`, `breachsafe-cicd-hygiene`, `breachsafe-release` — the
  three gates this skill checks for invocation, never re-derives.
