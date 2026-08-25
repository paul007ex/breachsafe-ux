<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Contributing to breachsafe-ux

[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-FE5196?style=flat-square&logo=conventionalcommits&logoColor=white)](https://www.conventionalcommits.org)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-D7FF64?style=flat-square&logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)
[![Type Checked: mypy](https://img.shields.io/badge/type%20check-mypy-blue?style=flat-square)](https://mypy-lang.org/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](LICENSE)

Thanks for considering a contribution. This document covers what you need to know.

## Contents

1. [Before you contribute](#1-before-you-contribute)
2. [Set up a development environment](#2-set-up-a-development-environment)
3. [Workflow](#3-workflow)
4. [Quality gates](#4-quality-gates)
5. [Coding style](#5-coding-style)
6. [Dependencies](#6-dependencies)
7. [Security](#7-security)
8. [Commits](#8-commits)
9. [License](#9-license)

## 1. Before you contribute

Read these in order:

1. [`README.md`](README.md); what breachsafe-ux is and what state it's in.
2. [`docs/adr/`](docs/adr/); the settled architecture decisions, especially the
   host/descriptor boundary.

breachsafe-ux is a config-driven single-tool UX host: point it at a
command-line tool, declare that tool's parameters in one YAML descriptor, and
the host renders a web form, runs the tool, validates the output with an
external validator, and reports a three-state verdict. Adding a tool is a YAML
file, not new UI code; keep changes on the right side of the host/descriptor
boundary.

## 2. Set up a development environment

```bash
# Clone
git clone https://github.com/breachsafe/enxemble.git
cd breachsafe-ux

# Install uv if you don't have it
# https://github.com/astral-sh/uv

# Create the dev environment (project + the dev tooling the gates need)
uv sync --extra dev

# Verify the install and that each tab's tool + validator resolves
uv run breachsafe-ux --check
```

The project targets **Python 3.14+**. `uv sync --extra dev` provisions the
interpreter and the dev tooling for you. (Plain `uv sync` installs only the
runtime, which is enough to launch the app but not to run the tests or gates.)
`--check` prints each tab's tool/version/path and exits non-zero if any is missing.

## 3. Workflow

1. **Open an issue first** for non-trivial changes. We will confirm it is in
   scope before you write code.
2. **Branch from `main`.** Branch naming: `<type>/<short-description>` (e.g.
   `feat/descriptor-tokens`, `fix/badge-state-parse`).
3. **One thing per PR.** Do not bundle a refactor with a feature with a bug fix.
4. **Run the gates locally** before pushing (see below).
5. **Open a PR** and fill out the PR template.
6. **Self-review your own diff** before requesting review.
7. **CI must pass** before merge.
8. **Squash-and-merge** is the default merge strategy.

## 4. Quality gates

**One command reproduces every blocking CI check.** It is the authoritative local gate; run
it before you push:

```bash
uv run --locked --extra dev python scripts/release_gate.py
```

It fails closed on the first breach and prints a `PASS`/`FAIL` summary. Everything runs under
`uv run --locked` so your versions match the committed `uv.lock` exactly — the same path CI uses.

The full suite CI enforces (all fail closed; none are advisory):

| Category | Gate |
|---|---|
| Lint / format | `ruff check .`, `ruff format --check .` |
| Types | `mypy --strict src` (no relaxations) |
| Security | `bandit -ll`, `pip-audit`, secret scan (gitleaks) |
| Dependencies | `deptry .` |
| Tests | `pytest -m "not live"`, no-skipped-tests gate, `diff-cover` (100% of changed lines) |
| Architecture | `import-linter` (MVC/engine layering), `xenon` (complexity), `refurb`, `vulture` |
| Docs / size | `interrogate` (docstrings), `pydocstyle D`, size policy (400 file / 50 fn / 200 class) |
| Duplication | `jscpd` (0 clones in `src/`) |
| Licensing | `reuse lint` (100%), version single-source (`bump_version --check`) |
| Supply chain | CodeQL, OpenSSF Scorecard, Trivy + cosign + SBOM on the image, signed releases |

Run an individual gate directly when iterating, e.g. `uv run --locked --extra dev mypy --strict src`
or `uv run --locked --extra dev ruff check .`. Do not weaken a gate to make it pass: a red gate
is a bug to fix, not a threshold to lower.

Live-integration tests (marked `@pytest.mark.live`, e.g. `tests/test_badge_states.py`) need a
real tool + Docker; CI **deselects** them with `-m "not live"` so a skip can never hide a
failure. Run them locally with a plain `uv run --locked --extra dev pytest`.

## 5. Coding style

- Python 3.14, fully typed (`mypy --strict src`), formatted (`ruff format`), linted (`ruff check`)
- Ruff is configured in `pyproject.toml`; do not add per-file `# noqa` without a reason
- Specific exceptions, not bare `except`, except where the host deliberately
  fails CLOSED (a validator or artifact that cannot run is never reported as a pass)
- The three-state verdict (VALID / INVALID / VALIDATOR-UNAVAILABLE) is
  load-bearing: never render a green result the validator did not give
- SPDX header on every first-party source file (see [License](#9-license))

## 6. Dependencies

Adding a runtime dependency requires PR justification:

- Replaces a meaningful amount of code we would otherwise write and maintain
- Actively maintained (commit in the last 12 months)
- License and distribution terms compatible with Apache-2.0; preserve all
  upstream notices
- Recognizable maintainer

GPL, AGPL, and LGPL runtime dependencies do not meet the dependency policy.

## 7. Security

If you find a vulnerability, **do not open a public issue.** See
[`SECURITY.md`](SECURITY.md) for the disclosure process.

Insecure shortcuts are forbidden in PRs. If you need to disable validation, log
secrets, or take any other insecure shortcut to make something pass, the PR will
be rejected. The right answer is to fix the underlying problem or to fail CLOSED.

## 8. Commits

Conventional Commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types we use: `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`,
`perf`, `security`.

Examples:

- `feat(descriptor): support enum parameters`
- `fix(badge): render VALIDATOR-UNAVAILABLE when oscal-cli is missing`
- `docs(readme): clarify the host/descriptor boundary`

## 9. License

By contributing, you confirm that you have authority to contribute the material
and agree that your contribution is licensed under the Apache License 2.0. Every
first-party source file must carry an SPDX header:

```python
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
```

Use the comment syntax appropriate to the file type (`<!-- ... -->` for
Markdown). `reuse lint` enforces this in CI.
