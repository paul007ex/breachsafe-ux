---
name: breachsafe-cicd-hygiene
description: Spot and fix concrete GitHub Actions/CI-CD hygiene mistakes — missing concurrency guards causing stacked redundant runs, duplicate CI running the same content across two repos, treating a scheduled/cron job as disposable CI cost when it's actually production monitoring, and skip-masking (a green test run that quietly didn't run everything). Use when auditing or writing GitHub Actions workflows, or when CI cost/redundancy looks off. Distinct from breachsafe-release (crate/package release-readiness, narrow "applies to" list) and breachsafe-implement's code-review quality-theater check (a diff-review item, not a pipeline-design one) — this is general CI/CD workflow hygiene, any repo.
---

# breachsafe-cicd-hygiene

Every finding here is a real thing found in a live cross-repo audit, not a hypothetical
"best practice" — cited with the actual repo/PR/issue.

## Contents
- Missing concurrency guards
- Duplicate CI across repos
- A cron job might be production, not CI cost
- Skip-masking: green doesn't mean it ran
- Tools
- Boundary with other skills

## Missing concurrency guards

**What it looks like**: a workflow runs on `push`/`pull_request` with no `concurrency:`
block. Every rapid push (agent-driven iteration especially) stacks a full redundant run
instead of canceling the superseded one.

**Real example**: `breachsafe/qureddy` had 5 of 7 workflows with a `concurrency:
{group: ..., cancel-in-progress: true}` guard already — but `container.yml` and
`scorecard.yml` were missing it, found during a resource audit that also turned up 733
CI runs in 30 days on that repo. Fix (PR
[breachsafe/qureddy#96](https://github.com/breachsafe/qureddy/pull/96)):

```yaml
concurrency:
  group: <workflow-name>-${{ github.ref }}
  cancel-in-progress: true
```

**Check before assuming this is safe everywhere**: a `workflow_dispatch`-triggered
*publish* job (not a test job) canceling itself on a second dispatch is usually the
right default (you don't want two concurrent registry pushes racing), but it's the one
case worth a second thought, not a blind copy-paste — flag it in the PR description if
the workflow has a publish/deploy job, don't just add the block silently.

## Duplicate CI across repos

**What it looks like**: two repos with the same or forked content both run full,
independent CI/CD suites — CI, CodeQL, Scorecard, Container builds — indefinitely, on
identical or near-identical code.

**Real example**: `paul007ex/qureddy` was running a near-duplicate weekly-scheduled
CI/CodeQL/Scorecard suite (199 runs/30d) alongside the actual canonical
`breachsafe/qureddy` (733 runs/30d on the same content). Neither repo's maintainer had
flagged this as duplication — it surfaced only from a cross-repo audit, not from either
repo's own dashboard. See [paul007ex/qureddy#287](https://github.com/paul007ex/qureddy/issues/287).

**Check**: before wiring CI on a fork/mirror/staging copy, confirm which repo is
actually canonical and whether the copy needs its own full gate suite or just enough to
validate before pushing upstream.

## A cron job might be production, not CI cost

**What it looks like**: an `on: schedule:` cron entry in `.github/workflows/` looks like
routine CI (weekly Scorecard scans, nightly builds) — until it isn't. A workflow named
like a canary/health-check running **hourly** is a different category of thing entirely:
disabling it during a "reduce CI cost" pass could silently kill real monitoring.

**Real example**: during a blanket CI-disable pass across several repos,
`sts-delegate`'s `idp-canary.yml` (`real-idp-canary`) turned up with an hourly cron
(`0 * * * *`) — a plausible production IdP health check, not a cost item. It got
disabled along with everything else in the blanket pass, then specifically flagged in
[paul007ex/sts-delegate#732](https://github.com/paul007ex/sts-delegate/issues/732) for
the repo owner to verify before leaving it off. **The mistake to avoid: don't
blanket-disable-by-schedule-frequency without reading what each cron job's *name*
implies it does.**

## Skip-masking: green doesn't mean it ran

**What it looks like**: a test run reports "N passed," everyone reads that as "N ran and
all N passed" — but a skip marker (`@pytest.mark.skip`, `xfail`) lets a test count
toward "passed" without exercising anything.

**Real, documented cost** (qureddy's own `docs/contributors/review-process.md`): a PR
displayed "192 passed" while 5 tests were hard-failing under a rerun-masking bug
(issue #15). The fix wasn't "trust green harder" — it was a dedicated gate that reads
the actual JUnit XML `skipped` count and fails if it's nonzero, plus a reviewer rule
requiring new tests to be rerun 3x specifically to defeat rerun-masking.

This is the same failure class `breachsafe-implement`'s self-audit checklist already
flags in a code-review context ("quality theater: skipped tests, lowered thresholds,
retry-count increases used to hide a deterministic failure") — that's the right place
for *reviewing a diff*; this skill is about *the CI wiring* that catches it
mechanically, so it doesn't depend on a reviewer noticing.

## Tools

Two of the above are now real, portable, tested scripts in `breachsafe-common`
(cross-repo shared tooling, not this skill library — see `breachsafe-common/README.md`):

- `quality-gates/check_no_skipped_tests.py` — the skip-masking gate above, generalized.
- `quality-gates/check_size_policy.py` — a related hygiene check (file/function/class
  LOC ceilings) from the same qureddy CI audit.
- `ci/quality-gates-python.yml` — reusable workflow calling both.

Vendor or adapt these rather than re-implementing from scratch — `docs/adr/ADR-bqp-004-
quality-gates-from-qureddy.md` in that repo documents what was and wasn't portable and
why.

## Boundary with other skills

- **`breachsafe-release`**: crate/package release-readiness and supply-chain
  enforcement for a narrow, named list of repos approaching a real publish
  (`cargo audit`/`pip-audit` wired to fail CI, OpenSSF Scorecard/OSPS Baseline). Composes
  with this skill's "gate must actually enforce" theme but doesn't duplicate it — that
  skill's "recurring trap" section is the release-readiness version of the same idea
  this skill applies to CI/CD hygiene generally.
- **`breachsafe-implement`**'s self-audit checklist: reviewing one diff for quality
  theater (a single PR's tests/thresholds). This skill: auditing the pipeline itself
  across possibly many repos (concurrency, duplication, schedule awareness).
- Neither of the above already covered concurrency guards, cross-repo CI duplication,
  or cron/canary-awareness before this skill existed — verified by grep across the
  library before writing this, not assumed.
