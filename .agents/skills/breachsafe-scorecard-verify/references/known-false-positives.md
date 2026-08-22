# Scorecard false-positives, lagging scores, and the shift-left signing gate

Generic catalog — none of this is specific to any one repo. When a Scorecard check
scores below 10, decide which bucket it is BEFORE opening an issue, so a
heuristic limitation or an already-fixed lag doesn't get chased as a live defect.

## Contents
- 1. FALSE-POSITIVE: self-installed local wheel (Pinned-Dependencies)
- 2. FIXED-BUT-LAGGING: PR-only CodeQL scored "not run on all commits" (SAST)
- 3. FLOOR NOT TRUTH: local `scorecard` PAT run under-scores hosted checks
- 4. FROZEN SCORE: disabled scorecard.yml workflow
- 5. The real one: signing step present but the workflow never ran (Signed-Releases)
- 6. Shift-left: a release.yml CI job that blocks an unsigned release

## 1. FALSE-POSITIVE: self-installed local wheel (Pinned-Dependencies)

A `RUN pip install ./dist/<project>-<ver>-*.whl` (or `/tmp/...whl`) in a Dockerfile is
your own build artifact from an earlier stage. Scorecard's Pinned-Dependencies flags it
as "pipCommand not pinned by hash" because it wants `pkg==x.y --hash=sha256:...`. You
CANNOT hash-pin an artifact you just built in the same build — the hash isn't known until
after it's built, and pinning it would be circular. This is a heuristic limitation, not a
supply-chain gap. Document it; do not "fix" it. Distinguish from a REAL gap: an unpinned
*remote* dependency (`pip install requests`, an `uses: actions/checkout@v4` tag instead
of a commit SHA) genuinely should be pinned.

## 2. FIXED-BUT-LAGGING: PR-only CodeQL scored "not run on all commits" (SAST)

Scorecard's SAST reason "SAST tool detected but not run on all commits" (e.g. "10 of 15
commits checked") counts historical commits. If `codeql.yml` triggers only on
`pull_request:`, direct-to-main / admin pushes go unscanned and the ratio stays low —
a REAL gap. But once a `push: branches: [main]` trigger is added, every new commit is
scanned; the score then only lags because the *older, pre-fix* commits in the window
were never scanned and can't be retroactively. So `push:` present + a sub-10 SAST score
is FIXED-BUT-LAGGING: it climbs on its own as pre-fix commits age out of the window. No
`push:` trigger = still a REAL gap.

## 3. FLOOR NOT TRUTH: local `scorecard` PAT run under-scores hosted checks

Running `scorecard --repo=github.com/<owner>/<repo>` locally with a personal access token
gives LOWER scores on Signed-Releases, CI-Tests, and SAST than the GitHub-hosted scan,
because a PAT can't fully see release provenance, check runs, or code-scanning results the
hosted app can. Treat a local run as a floor for triage only; reconcile against the
official API (`api.securityscorecards.dev`) for the authoritative per-check number, and
always state which one produced the numbers you're quoting.

## 4. FROZEN SCORE: disabled scorecard.yml workflow

If the repo owns a `scorecard.yml` workflow and it's disabled, the published score is
frozen at the last run and won't refresh. Triggering it fails with
`HTTP 422: Cannot trigger on a disabled workflow`. Re-enable
(`gh workflow enable scorecard.yml -R <owner/repo>`) then
`gh workflow run scorecard.yml -R <owner/repo>`, or run scorecard locally. A repo with no
`scorecard.yml` may still be scored by the deps.dev weekly crawl — there's nothing to
trigger; you wait for the crawl or run locally.

## 5. The real one: signing step present but the workflow never ran (Signed-Releases)

The trap that looks exactly like a config bug but isn't: `release.yml` can carry full
signing (`actions/attest-build-provenance` for SLSA provenance, `sigstore/cosign` keyless
OIDC, with `id-token: write` + `attestations: write` permissions) and STILL ship unsigned
releases — because the workflow never executed for those tags. Causes: the release was cut
manually, the run was cancelled, or the tag predates the signing job. Worked example
(`breachsafe/qureddy`, verified 2026-08): `release.yml` had cosign + attest-build-provenance,
but `gh run list --workflow=release.yml` showed its last run was for `v0.2.13` — it never
ran for `v0.2.14/15/16`, which is precisely why those three are unsigned. Note also that
`attest-build-provenance` leaves NO release asset — the attestation lives only in GitHub's
attestation store — so an assets-only check is blind to it; verify with
`gh attestation verify <artifact> --repo <owner/repo>`. Generalizable rule: **the signing
step existing in the workflow ≠ it ran for THIS release.** `scripts/release-integrity-gate.sh`
checks both the signature/attestation AND that the workflow ran successfully for the tag.

## 6. Shift-left: a release.yml CI job that blocks an unsigned release

Catch #5 at publish time, not weeks later via Scorecard. Add a gate job that runs after
your build/sign/publish jobs and verifies the artifacts it just produced carry a
provenance attestation. Drop this into the target project's own `.github/workflows/release.yml`
(adjust `needs:` to your publish job and the artifact path):

```yaml
  verify-signed:
    needs: [publish]          # your build+sign+publish job(s)
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write         # allow gh attestation verify against the store
    steps:
      - name: Download released artifacts
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          mkdir -p dist
          gh release download "${GITHUB_REF_NAME}" \
            --repo "${GITHUB_REPOSITORY}" --dir dist \
            --pattern '*.whl' --pattern '*.tar.gz'
      - name: Fail the release if any artifact is not attested
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          shopt -s nullglob
          fail=0
          for f in dist/*; do
            if gh attestation verify "$f" --repo "${GITHUB_REPOSITORY}" >/dev/null 2>&1; then
              echo "OK  attested: $f"
            else
              echo "ERR NOT attested: $f"; fail=1
            fi
          done
          [ "$fail" -eq 0 ] || { echo "::error::release artifacts are not signed/attested"; exit 1; }
```

Because it runs inside the release workflow, a run that skips or fails signing turns the
release red instead of silently shipping an unsigned build that Scorecard flags later.
