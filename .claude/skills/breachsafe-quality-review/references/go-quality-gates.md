# Go quality gates (Mode 1 — fast local check)

Applies to the Go components (crypto/plugin code and any Go tooling in the platform). Run
this before opening a PR, or whenever you want to confirm a change compiles and the suite
is green.

## Contents
- Environment first
- Sequence
- The cgo caveat
- Recording a baseline
- Report format

## Environment first

Check the repo's own `CLAUDE.md` / `README` for platform-specific env vars before running
anything. A cgo module that links OpenSSL needs `CGO_ENABLED=1` and a pinned OpenSSL the
Go toolchain can find (`CGO_CFLAGS`/`CGO_LDFLAGS`, or `PKG_CONFIG_PATH` pointing at the
platform's Homebrew OpenSSL) — the exact path is a local machine detail, not something to
hardcode here. If a build fails with an OpenSSL/`ld: library not found` error, that's the
first thing to check. If the repo standardizes on `gofumpt` (bao-pqc's gate does), use it
in step 1 in place of `gofmt`.

## Sequence

Run in order. Stop and surface the first failing step rather than pushing past it — a
later step's failure is often just noise once an earlier one is red. A step that is
**skipped** (tool not installed, not applicable at this stage) is **not** a PASS —
record it as NOT RUN with the reason.

1. **Format check (non-mutating)**
   ```bash
   gofmt -l .          # or: gofumpt -l .  (if the repo standardizes on gofumpt)
   goimports -l .
   ```
   Both list files that would change; **any output means FAIL**. Never run the mutating
   form (`gofmt -w` / `goimports -w`) to "fix" this in an audit context — formatting is a
   separate, deliberate commit, not something a review silently applies.

2. **Build**
   ```bash
   go build ./...
   ```
   For a cgo module, `CGO_ENABLED=1` with the OpenSSL env from above.

3. **Vet**
   ```bash
   go vet ./...
   ```

4. **Lint**
   ```bash
   golangci-lint run
   ```
   Key linters to have enabled: **staticcheck** (the correctness/simplification core),
   **gosec** (security; use `-exclude-generated` so cgo-generated intermediates don't
   produce noise findings), and **misspell**. Check the repo's own `.golangci.yml` rather
   than assuming the enabled set; treat the CI's configuration as the target bar.

5. **Full test suite with the race detector** — must be fully green. Any failure is a
   regression, not an accepted baseline to work around.
   ```bash
   go test -race -count=1 ./...
   ```
   `-count=1` defeats the test cache so you measure the real current state, not a stale
   pass. For a cgo module, `CGO_ENABLED=1` + the pinned-OpenSSL env from above.

6. **Coverage against a baseline threshold**
   ```bash
   go test -cover ./...
   ```
   Pass: coverage at or above the repo's recorded threshold. Investigate a drop as a real
   gap, not something to work around by lowering the number.

7. **Build-tagged suites** — known-answer-tests and other gated suites don't run under the
   default build; run them explicitly.
   ```bash
   go test -tags kat ./...
   ```
   Check the repo for its actual tags (`kat`, `integration`, …) and run each; a suite that
   only runs behind a tag is easy to leave un-run and call "green."

8. **Local vulnerability scan**
   ```bash
   govulncheck ./...
   ```
   This is the **local dev gate** — a fast "did I just pull in a known-vulnerable symbol"
   check. Supply-chain / release enforcement (the blocking gate, SBOM, provenance) is
   owned by `breachsafe-release`, not this skill.

## The cgo caveat

Scanners and linters see the **cgo-generated intermediate** `.go` files, not just your
source — gosec/staticcheck can flag machine-generated glue you didn't write. Use gosec's
`-exclude-generated` and confirm any surviving finding actually maps to hand-written code
before reporting it. The same intermediates are why a cgo build/test needs the OpenSSL env
set: the generated C shim is compiled and linked at `go build`/`go test` time.

## Recording a baseline

Before starting a change, capture the current pass/fail count (`go test -count=1 ./... 2>&1
| tail -5`) and the coverage number so you have something concrete to compare against when
you re-run after your change. Don't trust "still passes" from memory — re-run and compare
the actual counts.

## Report format

One line per step:

```
1. gofmt -l / goimports -l : PASS / FAIL (files listed)
2. go build ./...           : PASS / FAIL
3. go vet ./...             : PASS / FAIL
4. golangci-lint run        : PASS / FAIL (N issues)
5. go test -race -count=1   : PASS / FAIL (N passed, M failed)
6. go test -cover           : PASS / FAIL (X% vs threshold)
7. go test -tags kat        : PASS / FAIL / NOT RUN (no tagged suite)
8. govulncheck ./...        : PASS / FAIL (N vulns)

VERDICT: GREEN / BLOCKED — <reason>
```

If everything passes and the change touches cryptographic or security-relevant code, say
so explicitly and point at `breachsafe-security-audit` and `breachsafe-conformance` for
the checks this skill does not do — this skill confirms the code builds and the existing
tests pass, not that the crypto is correct or standards-conformant.
