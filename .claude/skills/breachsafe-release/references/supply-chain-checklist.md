# Supply-chain checklist

Audit only. This checks whether the dependency tree is scanned for known vulnerabilities,
license problems, and provenance gaps, and — more importantly — whether that scan is wired
so a finding actually **fails the build**. A tool that runs but exits 0 on findings enforces
nothing.

Run the section matching the ecosystem(s) detected (`Cargo.toml` / `pyproject.toml` /
`go.mod`). See `SKILL.md` for the dispatch check and the authorization gate.

## Contents

- Rust (cargo audit + deny + vet + CI enforcement)
- Python (pip-audit + deptry + reuse lint + gitleaks + CI enforcement)
- Go (govulncheck + go mod verify + replace audit + cgo native-lib pin + CI enforcement)
- Cross-ecosystem honesty rules

---

## Rust (cargo audit + deny + vet + CI enforcement)

### Setup

```bash
cd <crate root>
# Validate tools are installed — do not assume they are:
cargo audit --version || echo "MISSING: cargo install cargo-audit"
cargo deny  --version || echo "MISSING: cargo install cargo-deny"
cargo vet   --version || echo "MISSING: cargo install cargo-vet"
```

### Step 1 — cargo audit (RustSec advisory DB)

```bash
# Lockfile must exist and be committed, or version matching is unreliable:
test -f Cargo.lock && git ls-files --error-unmatch Cargo.lock >/dev/null 2>&1 \
  && echo "Cargo.lock committed: OK" || echo "FINDING: Cargo.lock missing or untracked"

cargo audit 2>&1 | tail -20
# In CI this MUST use --deny warnings, or a finding still exits 0:
cargo audit --deny warnings; echo "exit=$?"   # exit!=0 means it would fail CI (good)
```

- [ ] `Cargo.lock` present AND committed
- [ ] `cargo audit` clean (no RUSTSEC advisories on the resolved tree)
- [ ] CI invokes `cargo audit --deny warnings` (not bare `cargo audit`) — otherwise
      findings pass CI silently

### Step 2 — cargo deny (licenses, sources, bans, advisories)

```bash
# The config MUST be named exactly deny.toml (or .cargo/deny.toml). A misnamed file
# silently falls back to cargo-deny's default config — a real historical bug in this
# codebase family; verify current state, don't assume either the bug or the fix:
ls deny.toml .cargo/deny.toml 2>/dev/null || echo "FINDING: no deny.toml (check for a typo'd filename)"
find . -maxdepth 2 -iname '*deny*toml' -not -path './target/*'

cargo deny check 2>&1 | tail -30; echo "exit=$?"
# A "falling back to default config" message = the config isn't loading.
# A "failed to deserialize" error = obsolete schema (check [advisories]/[bans] shape
# against the installed cargo-deny version's current docs).
```

- [ ] Config file named exactly `deny.toml` (not a typo'd variant)
- [ ] `cargo deny check` loads the config (no "falling back to default")
- [ ] Config parses under the installed cargo-deny's current schema
- [ ] License allow-list matches the crate's actual dependency licenses
- [ ] CI invokes `cargo deny check` and the step can fail the build

### Step 3 — cargo vet (dependency provenance / review)

```bash
test -d supply-chain && echo "cargo-vet initialized" || echo "NOTE: cargo vet not set up"
cargo vet --locked 2>&1 | tail -20; echo "exit=$?"
# This step only AUDITS whether cargo-vet exists and passes — it does not run
# `cargo vet init` or record new exemptions; that's a maintainer decision.
```

- [ ] `supply-chain/` (cargo-vet store) exists for a crate aiming at high assurance
      (government/finance/infrastructure-grade, or any PQC/crypto-primitive crate)
- [ ] `cargo vet` passes (all deps audited or exempted with rationale)
- [ ] Note: if cargo-vet is absent because CI itself doesn't exist yet, don't treat the
      missing cargo-vet as the critical finding — sequence it behind "no CI at all," since
      vet without CI to run it is the same enforcement gap either way.

### Step 4 — CI enforcement (the gate that makes the above non-optional)

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null || echo "FINDING: no CI workflows"

grep -rn 'cargo audit\|cargo deny\|cargo vet\|fmt\|clippy\|--deny\|fail-under' \
  .github/workflows/ 2>/dev/null || echo "CI present but no supply-chain/quality gates found"

# Local-only enforcement doesn't count for shared safety:
grep -rln 'cargo audit\|cargo deny' scripts/hooks/ .git/hooks/ 2>/dev/null \
  && echo "NOTE: gate found in a local hook only — skippable, not enforced for all contributors"
```

Recommended minimum CI gate order (for a findings report, not to implement here):
`cargo fmt --check` → `cargo clippy --all-targets -- -D warnings` → `cargo test`
(matrix over supported toolchains) → `cargo audit --deny warnings` → `cargo deny check` →
optional coverage gate → `cargo vet`.

- [ ] CI exists (`.github/workflows/`)
- [ ] Gates run in CI, not just a local hook
- [ ] Each gate can actually FAIL the build (`-D warnings`, `--deny warnings`, non-zero exit)
- [ ] Toolchain matrix matches the crate's declared MSRV (`rust-version` in `Cargo.toml`)

---

## Python (pip-audit + deptry + reuse lint + gitleaks + CI enforcement)

The Python-ecosystem components in this family (QuReddy, Qurum) use `pip-audit` for
vulnerability scanning, `deptry` for unused/missing-dependency detection, `reuse lint` for
SPDX license-header compliance, and `gitleaks` (or `trufflehog`) for secret scanning — the
direct equivalents of the Rust `audit`/`deny`(-partial)/vet stack. Same trap applies: a tool
that runs but doesn't gate the merge enforces nothing.

### Setup

```bash
cd <package root>
pip-audit --version 2>/dev/null || echo "MISSING: pip install pip-audit"
deptry --version    2>/dev/null || echo "MISSING: pip install deptry"
reuse --version      2>/dev/null || echo "MISSING: pip install reuse"
gitleaks version     2>/dev/null || echo "MISSING: install gitleaks (or use trufflehog)"
```

### Step 1 — pip-audit (dependency CVEs)

```bash
test -f pyproject.toml && echo "pyproject.toml present" || echo "FINDING: no pyproject.toml"
pip-audit 2>&1 | tail -30; echo "exit=$?"
```

- [ ] `pip-audit` clean, or any findings are explicitly HIGH/CRITICAL-gated in CI (a known
      LOW/MEDIUM upstream CVE with no fix available is a legitimate accepted-risk case;
      an unreviewed HIGH/CRITICAL is not)
- [ ] A lockfile (`uv.lock`, `poetry.lock`, or equivalent) is committed so the resolved tree
      is reproducible

### Step 2 — deptry (unused / missing / transitive-misuse dependencies)

```bash
deptry . 2>&1 | tail -30; echo "exit=$?"
```

- [ ] No unused declared dependencies (dead weight in the supply-chain surface)
- [ ] No missing dependencies (imported but not declared — works today, breaks on a clean
      install elsewhere)
- [ ] No transitive dependency used as if it were direct

### Step 3 — reuse lint (SPDX / license-header compliance)

```bash
reuse lint 2>&1 | tail -30; echo "exit=$?"
```

- [ ] `reuse lint` passes — every source file has a valid `SPDX-License-Identifier` header
      (or is covered by `REUSE.toml`/`.reuse/dep5` for files that can't carry a header)
- [ ] The declared license matches the `license` field in `pyproject.toml` and the LICENSE
      file(s) actually present at repo root

### Step 4 — Secret scanning

```bash
gitleaks detect --no-git -v 2>&1 | tail -30; echo "exit=$?"
# Or, scanning history rather than just the working tree:
gitleaks detect -v 2>&1 | tail -30
```

- [ ] Clean secret scan on the current tree
- [ ] CI runs this on the diff (or full history periodically) — a clean local run today
      doesn't prove it's enforced

### Step 5 — CI tiering and enforcement

Per-PR vs. per-release tiering is a legitimate cost/noise tradeoff at small dependency-tree
scale — but only if it's a deliberate, documented split, not an accidental gap. Verify which
tier each gate is actually in, and that HIGH/CRITICAL findings do gate something real:

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null || echo "FINDING: no CI workflows"
grep -rn 'pip-audit\|deptry\|reuse\|gitleaks\|trufflehog\|bandit' \
  .github/workflows/ 2>/dev/null || echo "CI present but no supply-chain gates found"
```

- [ ] Each gate above runs in CI (per-PR, per-release, or both — state which)
- [ ] HIGH/CRITICAL `pip-audit` findings can actually block (a merge gate or a release gate,
      not just a report artifact nobody reads)
- [ ] If gates are split per-PR (cheap/fast: lint, format, unit tests, secret scan) vs.
      per-release (heavier: full `pip-audit`, license sweep, build verification), that split
      is documented somewhere a contributor would find it — an undocumented split reads the
      same as an accidental gap from the outside

---

## Go (govulncheck + go mod verify + replace audit + cgo native-lib pin + CI enforcement)

The Go-ecosystem component in this family (bao-pqc — an OpenBao PQC plugin, cgo-linked to
OpenSSL) uses `govulncheck` for vulnerability scanning and Go's built-in `go mod verify` for
checksum integrity — the direct equivalents of the Rust `audit`/`deny` stack. Two things Go
adds that Rust/Python don't: a `replace` directive can silently repoint any dependency
(including crypto) at an unaudited local/fork path, and a cgo build pulls in a **native**
library (OpenSSL) that is not a Go module and so escapes every Go-module scanner. Both are
supply-chain surface. Same trap applies: a tool that runs but doesn't gate the merge
enforces nothing.

### Setup

```bash
cd <module root>
go version                                                   # toolchain itself is pinned material
govulncheck -version 2>/dev/null || echo "MISSING: go install golang.org/x/vuln/cmd/govulncheck@latest"
cyclonedx-gomod version 2>/dev/null || echo "NOTE: no cyclonedx-gomod (SBOM step)"
go-licenses --help >/dev/null 2>&1  || echo "NOTE: no go-licenses (license step)"
```

### Step 1 — govulncheck (Go vulnerability DB) — MANDATORY release gate

```bash
test -f go.sum && git ls-files --error-unmatch go.sum >/dev/null 2>&1 \
  && echo "go.sum committed: OK" || echo "FINDING: go.sum missing or untracked"

# govulncheck is call-graph aware: it reports only vulns actually reachable from your code.
govulncheck ./... 2>&1 | tail -30; echo "exit=$?"   # non-zero = reachable vuln = must fail CI
```

- [ ] `go.sum` present AND committed
- [ ] `govulncheck ./...` clean (no reachable advisory on the resolved tree)
- [ ] CI invokes `govulncheck ./...` as a **required** job (not an optional/`continue-on-error`
      step, not a local-only run) — a reachable vuln must fail the build
- [ ] cgo caveat: govulncheck analyzes Go call graphs, **not** the linked C library — it will
      NOT catch an OpenSSL CVE; that is Step 5's job, not this one

### Step 2 — go.sum integrity + reproducible module graph

```bash
go mod verify 2>&1 | tail -5; echo "exit=$?"          # "all modules verified" or a hash mismatch
# The graph must be reproducible: a tidy tree leaves go.mod/go.sum unchanged.
go mod tidy && git diff --exit-code go.mod go.sum \
  && echo "graph reproducible: OK" || echo "FINDING: go mod tidy dirties go.mod/go.sum"
# GONOSUMCHECK / GOFLAGS=-insecure / GONOSUMDB=* / a permissive GOPRIVATE that covers a real
# dependency all defeat the checksum DB — verify none are set in CI env or a checked-in .env:
grep -rn 'GONOSUMCHECK\|GOFLAGS\|GONOSUMDB\|GOPRIVATE\|GOINSECURE' \
  .github/workflows/ Makefile* .env* 2>/dev/null || echo "no sumdb-weakening env found"
```

- [ ] `go mod verify` reports all modules verified (exit 0)
- [ ] `go mod tidy` is a no-op on a clean tree (graph is already tidy and reproducible)
- [ ] CI builds with `-mod=readonly` (or `-mod=vendor` if vendored) so a build can't silently
      mutate the graph
- [ ] No env (`GONOSUMCHECK`, `GOFLAGS=-insecure`, over-broad `GOPRIVATE`/`GOINSECURE`) disables
      checksum-DB verification for a genuine dependency

### Step 3 — `replace` directive audit (release blocker)

A `replace` repointing a dependency — especially crypto — at an unaudited local path or a
personal fork means the version in `go.sum` is NOT what ships. **This is directly live here:**
bao-pqc pins the OpenBao SDK via a local `replace` today.

```bash
# Enumerate every replace directive (empty output = none, which is the clean state):
go mod edit -json | python3 -c 'import json,sys; [print(r["Old"]["Path"],"=>",r["New"].get("Path"),r["New"].get("Version","(local path)")) for r in (json.load(sys.stdin).get("Replace") or [])]'
# Any New.Path without a Version, or pointing at ../ or a non-canonical fork, is unaudited:
grep -n '^\s*replace\|=>' go.mod
```

- [ ] Every `replace` is enumerated and accounted for (none is the cleanest state)
- [ ] No `replace` points crypto (or any dependency) at a local filesystem path (`../`, absolute)
      for a release build — a local path is unreproducible and unaudited
- [ ] Each surviving `replace` is either **removed before release** or **explicitly justified**
      (why the fork/pin exists) **and pinned to an exact version/commit** (not a branch or a
      floating `latest`)
- [ ] If a `replace` must ship (e.g. an upstream fix not yet released), it targets a pinned fork
      commit whose provenance is recorded, not a local working copy

### Step 4 — retract / pinned-version hygiene

```bash
# Go pins exact versions in go.mod, but pseudo-versions off a branch and unretracted bad
# releases are the floating equivalents:
go mod edit -json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("retract:",d.get("Retract")); print("go:",d.get("Go"))'
grep -n 'v0.0.0-\|+incompatible' go.mod   # pseudo-versions / non-module-aware deps to eyeball
```

- [ ] No dependency floats on a branch pseudo-version where a tagged release exists
- [ ] Known-bad own releases are `retract`ed in `go.mod` so downstreams don't resolve them
- [ ] The `go` directive pins a specific language/toolchain version (reproducible builds)
- [ ] The cgo-linked native lib is NOT floating — see Step 5 (no "whatever OpenSSL the builder
      happens to have")

### Step 5 — cgo native library (OpenSSL) provenance — pin AND record

The linked C library is part of the supply chain and invisible to every Go-module scanner.
**Directly live here:** bao-pqc pins exactly OpenSSL 3.5.7 LTS. An OpenSSL CVE is a bao-pqc CVE regardless of
what `govulncheck` says.

```bash
grep -rn 'CGO_ENABLED\|#cgo\|pkg-config\|LDFLAGS.*ssl\|LDFLAGS.*crypto' \
  . --include='*.go' --include='Dockerfile*' --include='Makefile*' 2>/dev/null | tail -20
# Where is the OpenSSL VERSION pinned? A bare `apt-get install openssl` / `apk add openssl`
# with no version is a floating native dep:
grep -rn 'openssl' Dockerfile* .github/workflows/ 2>/dev/null | grep -iv '#' | tail -20
```

- [ ] The OpenSSL (or other cgo-linked) version is **pinned** to an exact version in the build
      (Dockerfile pin, vendored source, or a locked base image digest) — not `apt-get install
      openssl` with no version
- [ ] That pinned version and its provenance (source, digest/checksum) are **recorded** where a
      reviewer can find them (build manifest, ADR, or the SBOM in Step 6)
- [ ] The pinned native version is itself free of known CVEs at release time (check the
      OpenSSL advisory list for that exact version — govulncheck will not)
- [ ] `CGO_ENABLED` and link flags are explicit in the build, not left to the host default

### Step 6 — SBOM / license

Match the Rust/Python bar: a component SBOM and a clean license posture.

```bash
cyclonedx-gomod mod -json -output-file bom.json 2>&1 | tail -5; echo "exit=$?"
# The Go SBOM covers Go modules only — the cgo native lib (Step 5) MUST be added to it
# manually, or the SBOM understates the real dependency surface.
go-licenses check ./... 2>&1 | tail -20; echo "exit=$?"
```

- [ ] An SBOM (CycloneDX/SPDX) is generated for the module and includes the cgo native lib,
      not just the Go modules
- [ ] `go-licenses check ./...` passes (no forbidden/unknown licenses in the resolved tree)
- [ ] The declared module license matches the LICENSE file(s) actually at repo root

### Step 7 — CI enforcement (the gate that makes the above non-optional)

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null || echo "FINDING: no CI workflows"
grep -rn 'govulncheck\|go mod verify\|go vet\|staticcheck\|golangci-lint\|-mod=readonly' \
  .github/workflows/ 2>/dev/null || echo "CI present but no Go supply-chain/quality gates found"
grep -rln 'govulncheck\|go mod verify' scripts/hooks/ .git/hooks/ 2>/dev/null \
  && echo "NOTE: gate found in a local hook only — skippable, not enforced for all contributors"
```

Recommended minimum CI gate order (for a findings report, not to implement here):
`gofmt -l` (must be empty) → `go vet ./...` → `staticcheck`/`golangci-lint` → `go test ./...`
→ `go mod verify` + tidy-check → `govulncheck ./...` → `replace`-audit gate → SBOM/license.

- [ ] CI exists (`.github/workflows/`)
- [ ] `govulncheck`, `go mod verify`, and the `replace`/native-pin checks run in CI, not just a
      local hook
- [ ] Each gate can actually FAIL the build (required job, non-zero exit, no `continue-on-error`)
- [ ] The `go` toolchain version in CI matches the `go` directive in `go.mod`

---

## Cross-ecosystem honesty rules

- Report exit codes, not descriptions. "Ran clean" without the exit code isn't verified.
- A finding that's only enforced in a local hook (pre-commit, `.git/hooks/`) is not
  enforced — anyone can skip a local hook; treat it as equivalent to "not enforced in CI."
- When both a Rust and Python surface exist in the same repo (e.g. a Rust core with a Python
  binding crate), audit both independently and say which ecosystem each finding belongs to.
