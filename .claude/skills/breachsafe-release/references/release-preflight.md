# Release preflight — operational gotchas (hard-won)

Concrete failures hit repeatedly across QuReddy releases **0.2.14–0.2.17**. Every one is
invisible to a green *local* gate: it only shows up in CI, on the published artifact, or on
the next OpenSSF Scorecard re-run. Verify each against CI reality and the published
artifact, never "it passed locally." The numbered items match the tight list in `SKILL.md`;
this file carries the detail, the fix, and the verification command for each.

Every issue reference is `breachsafe/qureddy#<n>`.

1. **Lockfile freshness after a version bump.** Bump scripts usually do NOT relock. A stale
   `uv.lock` (or `Cargo.lock` / `go.sum`) still pins the *previous* version and fails every
   `--locked` CI step and release gate. Regenerate the lockfile after bumping and before
   tagging. *Verify:* the lockfile's project version equals the new tag; a `--locked`
   install succeeds. (#213 — `uv.lock` stale at 0.2.14, pinned v0.2.13, RED main.)

2. **"Ran" ≠ "signed" — confirm the run AND the signature bundles.** Signing / SLSA
   provenance / attestation live in a workflow gated on `release: published`. A *draft*
   release, or a workflow left `disabled_manually`, means that workflow NEVER FIRES: the
   artifact ships unsigned while the repo still advertises signing. Publishing (not
   drafting) `0.2.17` and letting it flow through `release.yml` is what produced signatures.
   *Verify BOTH, not just one:*
   - the run happened — `gh run list --workflow=release.yml` shows `[release] <tag>:
     completed / success` for that exact tag (not the previous release); and
   - the signatures exist — the published assets gained `<artifact>.sigstore` bundles and
     `gh attestation verify` / cosign confirms provenance.
   A signing step that never ran is not a signed release. (#232 enforcement half — `release.yml`
   never executed for 0.2.14–16; #219 the Signed-Releases Scorecard gap it caused.)

3. **Bit-rot while disabled — re-verify EVERY previously-disabled workflow individually.**
   "Green last time + workflow re-enabled ≠ green now." When jobs sit `disabled_manually`
   (billing / manual pause) and are later re-enabled, each one rots independently and fails
   in its own unrelated way; a fresh run of one does not vindicate the batch. Re-enabling and
   trusting the last green badge misses this — the last badge was earned on a commit that
   predates every PR merged during the dark window. **Force a fresh run of each workflow on
   the actual release commit** and read each result. This cycle exposed THREE distinct
   bit-rotted jobs on one re-enable:
   - pip-audit / wheel-runtime-audit hitting pip's OWN advisory (#235);
   - the container smoke gate never building the wheel + a stale `ARG` default (#237, root
     cause class of #215);
   - ClusterFuzzLite's build failing because a `* !Dockerfile` `.dockerignore` excluded
     `build.sh` from the build context (#239, closing #86).

4. **Manual / disabled-CI releases silently regress OpenSSF Scorecard.** Cutting releases or
   merging PRs while CI/release workflows are off drops **Signed-Releases** and **CI-Tests**,
   and the score only reveals it on the next Scorecard re-run — a local green gate does not
   reflect Scorecard/CI reality. #220's evidence: two PRs (including a real TLS/OpenSSL code
   change) merged 2026-08-21 with `statusCheckRollup=[]`, dropping local CI-Tests to 7/10
   while the last official scan still read 10/10. *Verify:* every recent merged PR carried
   status checks (`gh pr list --state merged --json number,statusCheckRollup`); the next
   official Scorecard run, not just the local one. (#219 / #220 / #232.)

5. **Docker build context & `.dockerignore` are load-bearing for EVERY docker build**, not
   just the app image. A repo-root `.dockerignore` written for the main image
   (`* !Dockerfile` — send only the Dockerfile) silently starves any *second* docker build
   that needs other files in context: ClusterFuzzLite's build reads `build.sh` and sources
   from the repo-root context and gets an empty context, so it fails in CI while passing on a
   laptop (local ClusterFuzzLite bind-mounts the repo and bypasses `.dockerignore`
   entirely). When multiple images exist, scope the ignore rules per Dockerfile-dir (a
   `.dockerignore` beside each Dockerfile, or BuildKit `Dockerfile.dockerignore`) so the
   app-image optimization can't govern the fuzz build. *Verify:* reproduce each image with a
   plain `docker build` from its real CI context, not the bind-mounted local path. (#239.)

6. **Docker wheel install — same job, version-scoped COPY, explicit build-arg.** Build the
   wheel into `dist/` in the SAME job before `docker build` (the build context has no
   gitignored `dist/` otherwise). COPY the version-scoped wheel (`…-${VERSION}-*.whl`), never
   a glob over all wheels — multiple versions in `dist/` → pip `ResolutionImpossible` (#215).
   Pass `--build-arg QUREDDY_VERSION=<version>` (resolved from `pyproject.toml`, via
   `$GITHUB_ENV` not inline `${{ }}` for injection-hardening) so a stale `ARG …=x.y.z` default
   can't select a missing/wrong wheel. The container smoke gate hit exactly this: a bare
   `docker build .` fell back to `ARG QUREDDY_VERSION=0.2.14`, whose COPY glob matched nothing
   in a `dist/` holding only `0.2.16`. Add a `--version` banner smoke check. (#215 / #237.)

7. **Branch-protection sequencing — CI live and green FIRST.** Enabling branch protection
   that REQUIRES status checks while CI is disabled blocks ALL merges, including your own
   release merges: the required contexts never report, so nothing can land. Turn branch
   protection (required checks) on only AFTER CI is re-enabled and green on `main`. Conversely
   CI-Tests / Code-Review Scorecard checks stay at 0 until required checks + review are
   enforced — so the sequencing is: re-enable CI → confirm green → then require it. (#84
   branch-protection ask; #220 CI-Tests self-heals once required checks block merges.)

8. **pip-audit scope divergence — declared deps vs full venv.** Auditing declared runtime
   deps (`pip-audit -r runtime-requirements.txt`) and auditing the full installed venv
   DISAGREE: the venv carries pip / setuptools whose OWN advisories (e.g. pip
   PYSEC-2026-3721) fail the CI job while the local declared-deps gate passes clean. Align the
   two — upgrade the tooling and/or ignore tooling-only advisories with a documented
   rationale — so local and CI audit the same closure. (#235.)

9. **Scorecard Pinned-Dependencies parses shell tokens literally.** A Dockerfile `pip install`
   argument assembled from multiple AST parts (a literal + `${ARG}` + a glob) is dropped by
   Scorecard's parser and read as *unpinned*, costing the check even when the pin is real. Use
   a single-part literal glob so the parser sees one token. (#221.)

10. **Version single-sourcing — a bump must reach EVERY sink.** `pyproject.toml`,
    README / badge, CHANGELOG heading + TOC, Dockerfile `ARG` default, the lockfile, and any
    golden/fixture files. Bump tools routinely miss several of these; audit for drift after
    bumping and before tagging. (#206.)
