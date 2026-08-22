<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.ai> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Changelog

[![Version](https://img.shields.io/badge/version-0.2.0-blue?style=flat-square)](CHANGELOG.md)
[![Keep a Changelog](https://img.shields.io/badge/keep%20a%20changelog-1.1.0-orange?style=flat-square)](https://keepachangelog.com/en/1.1.0/)
[![SemVer](https://img.shields.io/badge/SemVer-2.0.0-blue?style=flat-square)](https://semver.org/spec/v2.0.0.html)

All notable user-visible changes to breachsafe-ux are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and version
numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Fixed

- Badge correctness: a scan that exits 0 but produces an **empty/missing artifact**
  no longer badges VALID — it now reports "scan produced no output" (was a
  false-green). Also covered: nonzero exit, unresolved tokens, blind excepts.

## [0.2.0] - 2026-08-19

### Added

- Config-driven single-tool web UX host (form → run tool → external validator →
  three-state badge), Verify / Test-connection buttons, editable
  environment fields, and clearer failure messages.
