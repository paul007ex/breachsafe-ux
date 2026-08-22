<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Changelog

[![Version](https://img.shields.io/badge/version-0.3.1-blue?style=flat-square)](CHANGELOG.md)
[![Keep a Changelog](https://img.shields.io/badge/keep%20a%20changelog-1.1.0-orange?style=flat-square)](https://keepachangelog.com/en/1.1.0/)
[![SemVer](https://img.shields.io/badge/SemVer-2.0.0-blue?style=flat-square)](https://semver.org/spec/v2.0.0.html)

All notable user-visible changes to breachsafe-ux are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and version
numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
