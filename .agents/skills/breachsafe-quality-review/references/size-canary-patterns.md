# Size-canary patterns (Mode 2 extension)

`pr-audit-checklist.md`'s Size check is reactive — flag what's already over the repo's
limit. This is the forward-looking complement: flag what's *approaching* the limit,
before a future PR is forced to split it mid-feature. Generalized from QuReddy's
`python-oss-crypto-reviewer` skill, which found this earns its keep empirically there
(a function 1-2 lines under ceiling reliably breaches in the next feature PR; a file 30
lines under ceiling reliably breaches within 2-3).

## Contents
- Rule
- Canary patterns worth checking, regardless of ceiling values
- What NOT to flag as a canary
- Procedure on detection

## Rule

Read the repo's own documented hard ceilings (its coding-rules doc, not a number assumed
from another repo — QuReddy's happen to be 50 lines/function and 400 lines/file, that is
a worked example, not a universal constant). Flag anything at roughly 90% of that ceiling
as a canary, distinct from anything already over it (which is a Mode-2 finding on its
own). A canary is forward pressure, not a defect — never block the PR being reviewed for
it.

## Canary patterns worth checking, regardless of ceiling values

- **A function within ~10% of the ceiling.**
- **A file within ~10% of the ceiling.**
- **Two or more functions in the same file both flagged for high cyclomatic complexity**
  (many linters expose this, e.g. Radon/Pylint `R0912`/`R0915`-class checks) — this is a
  file-shape canary distinct from any single function's size: it means the file is doing
  too many things even if no individual function has breached yet.
- **A repeated ad-hoc ID/token-generation pattern** (e.g. the same
  `f"{prefix}-{uuid.uuid4().hex[:n]}"` shape) appearing across 3+ call sites — a
  centralization candidate, not yet a defect.
- **The same multi-field block duplicated across 2+ data models/structs** (a Pydantic
  model, a Rust struct, a TypeScript interface) — most lint tools only catch duplication
  past 4 lines; flag a 3-line shared group visually even if the tool stays quiet.
- **A repeated try/except (or match/Result) error-handling ladder** appearing 3+ times in
  one file — a candidate for a small shared helper.
- **8 or more call sites of the same construction pattern.** The 8-site threshold is
  empirical: by then the duplication has propagated through enough of the codebase that
  fixing one call site in isolation becomes fragile — a canary for "extract now," not
  "extract eventually."

## What NOT to flag as a canary

- A function comfortably under the ceiling (QuReddy's worked example: 30-44 lines
  against a 50-line ceiling is fine, no note needed).
- Duplication that only looks similar — two blocks that differ in the middle by content
  that's *meaningfully* different (different enum values, different policy branches) is
  parallel code serving different purposes, not duplication; don't force an extraction
  that would hide the meaningful difference behind a parameter.

## Procedure on detection

1. Note it in a non-blocking "Concerns" section of the review — cite file:line and the
   actual metric (LOC, complexity score, occurrence count) against the actual ceiling.
2. File a `[refactor]` follow-up issue: concrete metric, suggested split, what tests pin
   the new boundary, and why now rather than later (the size-pressure rationale itself,
   not a vague "this could be cleaner").
3. Cross-link the follow-up from the review. Do not bundle the refactor into the PR under
   review — that violates "one thing per PR," the same rule `pr-audit-checklist.md`
   already applies to feature/cleanup bundling.

Lost-and-forgotten structural debt is a common way real technical debt accumulates in
BQP repos specifically because nobody flagged it at the moment it was easiest to see —
capturing the canary the first time it's visible is cheaper than rediscovering it once
it's already a hard breach blocking a feature.
