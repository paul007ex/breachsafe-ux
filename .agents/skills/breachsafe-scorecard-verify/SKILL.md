---
name: breachsafe-scorecard-verify
description: Verify an OpenSSF Scorecard result the trust-but-verify way — never quote the aggregate score or the securityscorecards.dev viewer, which can be weeks stale or FROZEN because the repo's scorecard.yml workflow is disabled (gh workflow run then returns "HTTP 422: Cannot trigger on a disabled workflow"). Use when a Scorecard score looks wrong, dropped, or suspiciously frozen, when triaging a Scorecard regression, when reconciling a local `scorecard` run (which under-scores Signed-Releases/CI-Tests/SAST vs the hosted scan) against the official API, or before trusting any sub-10 check — this skill re-derives each check from deterministic gh probes and classifies it REAL-GAP / FALSE-POSITIVE / FIXED-BUT-LAGGING with evidence. Also gates release signing (the signing STEP existing in release.yml ≠ it RAN for this tag). Distinct from breachsafe-openssf-badge (the self-certified bestpractices.dev passing badge) and breachsafe-release (broad publish/supply-chain readiness); this one is specifically the automated Scorecard tool and per-check verification.
---

# breachsafe-scorecard-verify

Motivating failure (`breachsafe/qureddy`, 2026-08): the aggregate Scorecard number
was quoted as if current and trustworthy. It was neither. The viewer was lagging
real commits, Signed-Releases scored low for a REAL reason (0.2.14–16 shipped only
`.whl`/`.tar.gz`), Pinned-Dependencies scored low for a FALSE reason (a `pip install`
of the repo's own build wheel, which cannot be hash-pinned), and SAST scored low for
an ALREADY-FIXED reason (CodeQL gained a `push:` trigger; the score just lagged). One
number, three completely different truths. The whole point of this skill is to NOT
trust the aggregate — probe each check.

## Contents
- Applies to / authorization
- The five rules
- How to run
- Per-check verification table
- Porting to a new project
- References

## Applies to / authorization

Any GitHub repo, first- or third-party. The scripts are read-only (one temp download
of a release artifact for attestation verification, cleaned up). This skill verifies
and classifies — it does not edit repo config, workflows, or branch rules, and does
not file or close issues on its own initiative. Requires an authenticated `gh`.

## The five rules

1. **Never trust a stale or frozen score.** Fetch
   `https://api.securityscorecards.dev/projects/github.com/<owner>/<repo>` and print its
   `date` + scanned commit. If older than the threshold, it is not "the current score."
   If the repo's `scorecard.yml` workflow is disabled, the published score is FROZEN and
   `gh workflow run scorecard.yml` returns **HTTP 422: Cannot trigger on a disabled
   workflow** — re-enable it or run `scorecard` locally, and state which produced your
   numbers.
2. **A local `scorecard` run is a FLOOR, not truth.** With a PAT it under-scores
   Signed-Releases, CI-Tests, and SAST versus the GitHub-hosted scan (it cannot see
   everything the hosted scanner can). Always reconcile local against the official API;
   never present local numbers as the real score.
3. **Per-check deterministic verification — probe the repo, don't trust the number.**
   Each sub-10 check gets a specific `gh` probe (table below), not a re-reading of the
   aggregate.
4. **Classify every sub-10 check** REAL-GAP / FALSE-POSITIVE / FIXED-BUT-LAGGING /
   STRUCTURAL, each with the evidence used.
5. **Stay-open discipline.** A genuine regression gets a `verified-regression` label and
   a **machine-checkable** close-criterion in the issue (e.g. "`scorecard-verify.sh`
   classifies Signed-Releases as not REAL-GAP" or "`release-integrity-gate.sh <tag>`
   exits 0"), never manual judgment that someone eyeballed it.

## How to run

1. `scripts/scorecard-verify.sh <owner/repo>` — prints the official score + scan date +
   staleness, the `scorecard.yml` workflow state (active vs frozen), then a per-check
   table classifying every sub-10 check with evidence. Reconciles against the hosted API.
2. `scripts/release-integrity-gate.sh <owner/repo> [tag]` — the Signed-Releases deep
   check. Confirms the release actually carries a signature/attestation (assets AND
   `gh attestation verify` against the store, since `attest-build-provenance` leaves no
   asset) **and** that the signing workflow actually RAN for that tag. Exits non-zero if
   either fails. The lesson it encodes: a signing step in `release.yml` that never
   executed for the tag ships an unsigned release that looks like a config bug.
3. Turn each REAL-GAP into an issue per rule 5; document each FALSE-POSITIVE (see the
   reference) so the next agent doesn't re-chase it.

## Per-check verification table

| Check | Probe | Typical class |
|---|---|---|
| Signed-Releases | `gh release view <tag> --json assets` → look for `.sig/.sigstore/.intoto/attestation`; then `release-integrity-gate.sh` | REAL-GAP if only `.whl/.tar.gz`; FIXED if signed but score lags |
| CI-Tests | `gh pr list --state merged --json statusCheckRollup` → merged PRs with zero checks | REAL-GAP if any merged PR has no checks |
| Pinned-Dependencies | read API details; if the unpinned line is `pip install <own build wheel>` in a Dockerfile | FALSE-POSITIVE (a local artifact cannot be hash-pinned) vs REAL-GAP for a real remote dep / unpinned action SHA |
| SAST | fetch `codeql.yml`; is `push:` in the `on:` block? | FIXED-BUT-LAGGING if `push:` present ("not run on all commits" only reflects pre-fix history); REAL-GAP if PR-only |
| Code-Review / Branch-Protection | API reason; needs the branch rule | REAL-GAP (needs approving-review / protection rule) |
| Contributors | needs 2+ orgs via contributor profile Company field | STRUCTURAL — note, don't chase |
| CII-Best-Practices | self-cert bestpractices.dev badge | STRUCTURAL — use `breachsafe-openssf-badge`, not this skill |

## Porting to a new project

Both scripts are repo-agnostic: pass any `<owner/repo>`. Nothing is hard-coded to a
BQP repo — the Pinned false-positive is detected by matching "a `pip install` of a local
`.whl`/`/tmp/` path" generically, and the signing gate takes `WORKFLOW=<name>` (default
`release.yml`) and `STALE_DAYS`/`PR_SAMPLE` overrides via env. To enforce signing
**before** publish instead of catching it later via Scorecard, drop the CI job in
`references/known-false-positives.md` into the target's own `release.yml`.

## References

- `references/known-false-positives.md` — the generic Scorecard false-positive /
  lagging-score catalog (self-installed local wheel; PR-only CodeQL; local-PAT
  under-scoring) and a copy-paste `release.yml` CI job that shift-lefts the signing gate.
