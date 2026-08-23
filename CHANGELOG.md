<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Changelog

[![Version](https://img.shields.io/badge/version-0.3.12-blue?style=flat-square)](CHANGELOG.md)
[![Keep a Changelog](https://img.shields.io/badge/keep%20a%20changelog-1.1.0-orange?style=flat-square)](https://keepachangelog.com/en/1.1.0/)
[![SemVer](https://img.shields.io/badge/SemVer-2.0.0-blue?style=flat-square)](https://semver.org/spec/v2.0.0.html)

All notable user-visible changes to breachsafe-ux are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and version
numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.12] - 2026-08-23

### Added
- Evaluation box: the qureddy tabs show the tool's own per-axis interpretation (PQC support,
  key exchange, downgrade resistance, authentication, protocol hygiene) plus a headline, under
  the badge. Config-driven via `render.evaluation`; the host renders it verbatim. (#199, #59)

### Changed
- Python baseline is now 3.14 (dev, CI, and config; the runtime image already ran on 3.14). (#100)

## [0.3.11] - 2026-08-23

### Changed
- The qureddy TLS and SSH tabs now show CBOM and JSON together from one scan, each in a
  collapsed, copyable box, with no output-format toggle. One scan writes both correlated
  documents via qureddy `--output-dir`; there is no second scan. (#199)
- The Raw log now shows the executable command and the run directory before the tool output. (#199)

### Added
- An agnosticism gate: a test fails if a host module hardcodes a tool identifier, so the host
  stays config-driven as tools are added. (#200)
- Engine support for multi-artifact tools: `run.output_dir_flag` + `run.artifacts[]` render one
  copyable box per declared artifact using its label. (#199)

## [0.3.10] - 2026-08-23

### Changed
- Rebuilt the qureddy-ux image against qureddy 0.2.50 (image tracks qureddy latest, unpinned).

## [0.3.9] - 2026-08-23

### Added
- Log verbosity is a level (0-3) in the qureddy TLS and SSH Advanced settings, mapping to
  `-v` / `-vv` / `-vvv`. Level 3 shows every subprocess start and completion in the Raw log.
  The engine gained a `repeat_flag` input mapping to express a repeated short flag; previously
  verbose was a single on/off `-v` and the higher levels could not be reached from the UI. (#3)

### Changed
- Extracted the argv builders (`_render` / `_input_argv` / `_build_argv`) into an internal
  `_argv` module so the engine module stays under the size ceiling; behavior is unchanged. (#186)

## [0.3.8] - 2026-08-23

### Fixed
- The Raw log accordion now shows the tool's diagnostic log (stderr) on a successful run, not
  only on failure. The engine carries the tool's stderr through to the result, and the qureddy
  TLS/SSH tabs default to verbose so the per-subprocess log appears; turn verbose off in Advanced
  for a quiet run. (#190)

## [0.3.7] - 2026-08-23

### Security
- The release workflow no longer interpolates the Git tag name into a shell `run:` step. The
  tag and repository flow through `env` variables, closing a script-injection shape where a tag
  name with shell metacharacters could run in the signing job. (#175)

### Fixed
- A numeric `0` (or `0.0`) on an `arg`-mapped input is no longer silently dropped from the argv.
  The old omit check treated `0` as absent because `0 == False` in Python, so `--retries 0`,
  `--maxfail 0`, and similar were never passed. (#171)
- `schema_version` now fails closed for a YAML float such as `2.0`, and an unresolved `{token}`
  in `validate.argv` badges the run unavailable instead of raising to the UI. (#104)
- A single malformed descriptor no longer downs the whole host. `load_descriptors` skips an
  invalid descriptor with a warning and loads its valid siblings. (#174)
- Console/ANSI escape sequences in tool output are stripped before display, so `rich` or coloured
  output reads cleanly in the web view instead of as escape-code garbage. (#4)

### Changed
- Raised the test coverage floor to 85%. (#142)

### Docs
- Removed em and en dashes from all product-doc prose (README and docs/**), matching the
  anti-slop writing standard in the breachsafe-docs skill. (#170)

## [0.3.6] - 2026-08-23

### Fixed
- **qureddy-ux image build was broken** (`pip: not found`) after the base qureddy runtime dropped
  pip/setuptools (breachsafe/qureddy#385), which froze the bundled scanner at qureddy 0.2.40. The
  EnXemble host wheel now installs in a pip-capable builder stage and is copied onto the pip-free
  qureddy base; qureddy still comes from the base image. Bundled qureddy is now the current release
  (0.2.43). (#166, #167)
- Documented commands that did not work as written: `README.md` §7 `pytest` now includes
  `--extra dev` (pytest is a dev extra), `CONTRIBUTING.md` uses `uv sync --extra dev` plus
  `breachsafe-ux --check` to verify a dev setup, and `--help` is not a CLI command (web UX).
  Every documented command was run against the real product.

### Changed
- Renamed the `reproducible` toggle to `deterministic` in the TLS and SSH descriptors, matching
  qureddy's renamed `--deterministic` flag (breachsafe/qureddy#388).

### Removed
- The TestPyPI publishing job in `release.yml` (added in 0.3.4, #19). breachsafe-ux is
  Docker-first and is not published to any package index; only qureddy is on TestPyPI. The
  signed, provenance-attested wheel and sdist remain attached to each GitHub Release as
  downloadable assets.

### Docs
- Deepened the contributor docs toward qureddy parity: `docs/contributors/coding-rules.md`
  (51→206 lines — no-shell argv, fail-closed discipline, MVC layering, typing/docstrings,
  descriptor conventions, size ceilings) and `review-process.md` (42→116, with a reviewer
  checklist + review-flow diagram). (#157)
- Expanded `NOTICE` from a stub into a full third-party attribution record (runtime dependencies
  and their licenses, the bundled Lucide icons under ISC, and the dev-only skills). (#158)
- Documented the `breachsafe-ux --check` exit behavior and failure categories (`ok` / `NOT FOUND`
  / summary `OK` / `MISSING TOOLS`) in the CLI reference, with a decision diagram. (#159)
- Added `docs/explanation/threat-model.md` — a host-level, tool-agnostic threat-model explainer
  grounded in `threat-model/threagile.yaml` and ADR-0002, with a colored trust-boundary diagram
  (linked from the docs index and ADR-0002). (#160)
- Added a consistent, accessible semantic colour palette to the Mermaid diagrams via `classDef`
  (green VALID, red INVALID, orange VALIDATOR-UNAVAILABLE, blue process, grey artifact, purple
  external), so colour carries meaning at a glance; diagram content is unchanged. (#156)
- Added rich Mermaid diagrams across the docs (rendered natively on GitHub) and a dedicated
  Gradio page. New `docs/explanation/the-gradio-shell.md` explains the web-UI framework edge
  (only `app.py` and `brand.py` import Gradio), the type→widget map, and theming, linked from the
  docs index, `architecture.md`, and `contributors/coding-rules.md`. `architecture.md` gains a
  component-coupling dependency graph (with the Gradio boundary drawn as a dashed subgraph).
  Added Mermaid diagrams to `README.md` (pipeline + MVC), `three-state-verdict.md` (fail-closed
  decision flow), `why-agnostic.md`, `host-descriptor-boundary.md`, `execution-backends.md`
  (local→image→unavailable resolution), `reference/badge.md` (state diagram), `how-to/add-a-tool.md`
  (descriptor→tab→run→verdict lifecycle), and `tutorials/your-first-scan.md` (user flow); the ASCII
  pipeline in `architecture.md` is now Mermaid. Every diagram matches the real MVC boundary,
  backend resolution, and badge logic, and stays host-generic. (#154)
- Restructured `docs/` into the Diátaxis quadrants (`tutorials/`, `how-to/`, `reference/`,
  `explanation/`, `contributors/`) with a `docs/README.md` index, and rewrote `README.md` in the
  task-first BreachSAFE style with a badge row and a slim overview that points into `docs/`. All
  content is host-generic: the `qureddy-ux` image appears only as a labelled shipped reference
  example, and `docs/how-to/add-a-tool.md` uses a non-BreachSAFE example tool to demonstrate that
  the host is tool-agnostic. Moved `docs/first-scan.md` to `docs/tutorials/your-first-scan.md` and
  `docs/descriptor-tokens.md` to `docs/reference/descriptor-tokens.md`. Added how-to guides
  (Docker, from source, add a tool, white-label branding, optional tabs), reference pages
  (descriptor schema, environment variables, execution backends, badge, CLI), explanation pages
  (architecture, host↔descriptor boundary, three-state verdict, why agnostic), and contributor
  pages (coding rules, local release gate, review process). Every command example was executed
  against the real product. (#152)
- `CONTRIBUTING.md` now documents the real gate suite and the single authoritative local command
  (`scripts/release_gate.py`) instead of an outdated six-check list.
- Added `AGENTS.md` (agent guidance for Codex and other assistants) and the first-scan
  walkthrough, linked from the README. Corrected residual "wizard" naming and completed the
  argv-token list in the README.

## [0.3.5] - 2026-08-22

### Changed
- The engine and Gradio shell are now fully `mypy --strict` (no relaxations) with google-style
  docstrings enforced by pydocstyle `D`, completing gate parity with QuReddy (#74).

### Docs
- The Docker quickstart is now re-runnable: it clears any container already holding port 7860
  before launching, so copy-pasting it twice no longer fails with "port is already allocated",
  and the stale "click Run" was corrected to the actual button label (#146).

### Fixed
- The `qureddy-ux` image now ships the **current** scanner. Its base was written as
  `ghcr.io/breachsafe/qureddy:latest@sha256:80ebc9bd…` — the tag read "latest" but the digest
  overrode it, freezing the image at **qureddy 0.2.34 / Python 3.12** while upstream reached
  **0.2.40 / Python 3.14**. The digest is removed, the image workflow gained a daily schedule
  so a new scanner release lands within 24h, and both build steps set `pull: true` so the
  layer cache cannot rebuild on a stale base. Reproducibility is preserved by the immutable
  per-release `qureddy-ux` version tags. (#138)

### Changed
- The badge-state guards that need no Docker or tool source (`t6`, `t6b`, `t7`) moved to
  `tests/test_badge_guards.py`. They previously sat in a `live`-marked module, so they were
  deselected in CI and in the release gate and executed in no pipeline at all. 120 passed ->
  124 passed; coverage 89.74% -> 90.49%. (#142)

## [0.3.4] - 2026-08-22

### Changed
- The audit tabs now name the threat they measure instead of the technology involved:
  **"Quantum Audit" -> "HNDL Audit (TLS)"** and **"SSH Audit" -> "HNDL Audit (SSH)"**
  (Harvest Now, Decrypt Later). Traffic captured today can be decrypted once a
  cryptographically relevant quantum computer exists, so an endpoint offering classical-only
  key exchange is a present-day confidentiality risk. The posture banner already said
  "harvest-now, decrypt-later risk" for the top-severity case; the tab label now agrees with
  the result. Both tabs were renamed together so one no longer names a threat while the other
  names a protocol. (#140)
- Tab descriptions lead with why the finding matters, and state the axes that are **not**
  harvest-now-decrypt-later — certificate signature algorithms are an authentication concern
  and legacy protocol offers are classical hygiene — so the HNDL label does not over-claim
  what the scan covers. (#140)

### Fixed
- `tools/qureddy/qureddy.yaml` was missing its SPDX header while the SSH descriptor carried
  one. (#17)

### Added
- Signed release pipeline (#34): publishing a GitHub Release now builds the wheel and sdist,
  attests SLSA build provenance, cosign-signs each artifact with keyless OIDC, attaches the
  signed artifacts to the Release, and runs a verify-signing job that fails the release unless
  both the wheel and sdist carry a `.sigstore` bundle. Ported from breachsafe/qureddy.
- TestPyPI publishing job (#19), guarded off by default. Enable it by registering a TestPyPI
  trusted publisher and setting the repo variable `PUBLISH_TESTPYPI=true`. Real PyPI remains a
  deliberate future step (Docker-first today).

## [0.3.3] - 2026-08-22

### Security
- Each tool run now writes to a unique per-invocation working directory. A re-run whose tool
  exits 0 without producing an artifact now validates against nothing instead of a previous
  run's leftover artifact, closing a stale-artifact false-VALID path (GHSA-6ffp-258g-fvp5,
  CWE-345, #135).
- A VALID badge now requires the external validator to exit 0 in addition to matching its pass
  rule. A validator that exits nonzero whose output happens to contain the pass string now
  badges invalid (GHSA-6ffp-258g-fvp5, CWE-345, #135). Descriptors that pin `exit` in `pass_if`
  keep their existing behavior; the bundled qureddy CBOM descriptors pin `exit: 0` and are
  unchanged.
- The unique-workdir change also resolves the concurrent-run collision where two short-timeout
  runs with identical parameters shared one deterministic directory (#104, part 3).

## [0.3.2] - 2026-08-22

### Fixed
- `__version__` is now derived from installed dist metadata instead of a hardcoded literal that
  drifted from `pyproject` (#115).
- Action buttons, the Verify button, and the external validator now resolve their tools via the
  same augmented PATH (per-tool `bin` shims + ambient PATH) as the main runner (#116).
- Artifact-derived strings are HTML-escaped before entering the badge/posture markup, and the
  per-run scratch dir (`RUN_ROOT`) is now capped to the most recent runs (#121).

### Changed
- CI: the container image is built once and published by digest, so the pushed bytes are the
  smoke-tested bytes; the release gate no longer duplicates the full suite on every PR (#117, #118).
- Supply chain: base images are digest-pinned; published images now carry an SBOM + provenance,
  pass a Trivy scan that fails on fixable HIGH/CRITICAL, and are cosign-signed; `packages: write`
  is scoped to the push job (#119).
- Scripts: shared tool-bootstrap + safe-extract helpers factored into `scripts/_release_support.py`
  (#122).

### Docs
- ADR-0003 trued up to the shipped self-contained multi-arch image; `KNOWN-ISSUES.md` refreshed (#120).

## [0.3.1] - 2026-08-22

### Added

- Self-contained, multi-arch Docker image: `docker run -p 7860:7860 ghcr.io/paul007ex/qureddy-ux:latest`
  — QuReddy, the host, and the descriptors in one public image (amd64 + arm64), no login, no docker
  socket. A `run.image` backend also lets the engine run a tool as its published image, always
  latest (`docker run --pull=always`), when the binary isn't on PATH.
- SSH Audit tab — scan an SSH endpoint (`qureddy scan ssh`) alongside TLS (#68).
- Environment / provenance model + `breachsafe-ux --check`: each tab shows (and the CLI reports)
  which binary, version, and resolved path it uses; `--check` exits non-zero when a declared tool
  or validator is missing — the real container health signal (#75).
- Host version in the header ("BreachSAFE EnXemble v<version>") (#95).
- Feature flags: a descriptor or chain marked `feature_flag: X` renders only when
  `BREACHSAFE_UX_<X>` is not disabled (default on); `mint_oscal` gates the OSCAL tab (#67).
- Default dark theme on load (the Light/Dark button still toggles).

### Changed

- Product identity is **BreachSAFE EnXemble**, a multi-tool host: tabs are "Quantum Audit" (TLS),
  "SSH Audit", and "Compliance (OSCAL)" (Enterprise); run buttons dropped the "Run" prefix.
- Action buttons show the tool's actual output — "Test connection" is the real openssl / ssh
  handshake, not a canned line (#97).
- Dropped the browser-broken `rich` output format (#69); plainer, declarative UI copy.
- Engine refactored into an MVC split (resolve / render / facade / app); only `app.py` and
  `brand.py` import Gradio.
- CI: added jscpd, a coverage threshold, `pytest-rerunfailures`, and a thicker release gate; runs
  ubuntu-only.
- Website URL `https://www.breachsafe.io`, single-sourced via `BRAND["url"]`; removed AI-slop
  phrasing from docs, code, and tests (#40).
- `tools/*/bin` shims are git-ignored local operator wiring; live integration tests skip cleanly
  when the tool or Docker are absent, so the suite is portable for a public checkout.

### Fixed

- Manual file upload on the Compliance (OSCAL) tab (Gradio 6 `gr.File` returns a path string) (#101).
- Spurious mypy "Button has no attribute click" from Gradio's `py.typed` (treat gradio as untyped).
- Release gate repaired: installs the dev toolchain (`--extra dev`), ignores the cached uv
  download, and builds with `uv build`.

## [0.3.0] - 2026-08-22

### Changed

- Renamed the package `breachsafe_wizard` → `breachsafe_ux` (module, dist name,
  entry point `breachsafe-ux`, env vars `WIZARD_*` → `BREACHSAFE_UX_*`).
- Relicensed to **Apache-2.0** (from PolyForm-Noncommercial) as the deliberate
  OSS exception so breachsafe-ux can be a public shared dependency of the OSS
  QuReddy `[ux]`. REUSE 3.3 compliant; bundled Lucide icons kept ISC.

### Added

- CI (ruff / pytest / build / reuse) and this changelog + release discipline.
- Formal JSON Schema for tool descriptors (`descriptor.schema.json`) with fail-closed
  load-time validation: a malformed descriptor now fails at load with the offending file and
  JSON path, instead of a silent drop or a mid-run surprise (#48).
- `schema_version` handshake: descriptors declare `schema_version: 1`; a version newer than the
  engine understands fails closed with a "needs a newer breachsafe-ux" message (#49).
- Documented substitution token namespace with `{{`/`}}` literal-brace escaping and a first-class
  validate-only `{stdout_file}` token (captured tool stdout); unresolved tokens still fail closed
  (#50, see docs/descriptor-tokens.md).
- Generic descriptor-declared `actions[]` buttons (label + argv + `ok_if`), replacing the
  hardcoded openssl "Test connection" preflight with a descriptor-supplied argv; the engine no
  longer contains any protocol-specific button code (#5, #21).
- `brand.version_cmd`: single-source the shown version from the installed tool (e.g.
  `["qureddy", "--version"]`) instead of a drifting literal; falls back to `version` (#51).

### Fixed

- Canonical argv model with an end-of-options guard: the engine now emits all options, then a
  literal `--`, then positionals, so a leading-dash field value cannot be parsed as a flag by the
  target tool (argument-injection hardening). Opt out with `run.no_end_of_options` (#9).
- Descriptor-selected validators via `validate.by` (multi-key, fail-closed to `none`): a variant
  with no validator no longer false-badges. QuReddy `format=json/rich` now report "no external
  validator" instead of a bogus INVALID/UNAVAILABLE (#43, closes #16); mint-oscal's badge now
  requires validator exit 0, closing a nonzero-exit false-green (#14).
- Result headline no longer false-greens: readiness posture is now a separate banner derived
  from the scan findings (`render.posture`), and the evidence badge can be reworded per state
  (`render.badge_text`) so a schema-valid CBOM reads "Evidence: CBOM well-formed", never as a
  security verdict. A quantum-vulnerable endpoint no longer renders green (#1).
- Badge correctness: a scan that exits 0 but produces an **empty/missing artifact**
  no longer badges VALID — it now reports "scan produced no output" (was a
  false-green). Also covered: nonzero exit, unresolved tokens, blind excepts.

## [0.2.0] - 2026-08-19

### Added

- Config-driven single-tool web UX host (form → run tool → external validator →
  three-state badge), Verify / Test-connection buttons, editable
  environment fields, and clearer failure messages.
