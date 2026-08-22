# breachsafe-ux

[![Version](https://img.shields.io/badge/version-0.3.0-blue?style=flat-square)](CHANGELOG.md)

A config-driven single-tool UX host. Point it at a command-line tool, declare
that tool's parameters in one YAML file, and the wizard renders a web form, runs the tool,
validates the output with an external validator, and reports a three-state verdict:
VALID, INVALID, or VALIDATOR-UNAVAILABLE. It never shows a green result the validator did
not actually give.

Adding a tool is a YAML file, not new UI code. The renderer, the runner, and the
badge are written once in the engine and shared by every tool.

- Home: https://www.breachsafe.io
- Source: https://github.com/paul007ex/breachsafe-ux
- Licence: PolyForm Noncommercial 1.0.0 (see [Licence](#8-licence))

## Contents

1. [What it is](#1-what-it-is)
2. [Quickstart](#2-quickstart)
3. [Architecture](#3-architecture)
4. [The three-state badge](#4-the-three-state-badge)
5. [Add a tool (the descriptor)](#5-add-a-tool-the-descriptor)
6. [Execution backends](#6-execution-backends)
7. [Development](#7-development)
8. [Licence](#8-licence)

## 1. What it is

Every tool the wizard wraps is the same pipeline with different nouns:

```
INPUT (params/file)  ->  run the tool  ->  ARTIFACT  ->  external validator  ->  verdict
```

The wizard exists to make that pipeline pretty and, above all, accurate. The verdict is the
real result of an external validator (for example NIST oscal-cli, or the CycloneDX schema
validator), reported as one of three distinct states. A tool that failed to run, or a
validator that could not run, is never rendered as a pass.

Two tools ship as examples:

- QuReddy scans a TLS endpoint for post-quantum readiness and produces a CycloneDX 1.7 CBOM.
- mint-oscal turns a scan or CBOM into an OSCAL Plan of Action and Milestones, reached
  through the QuReddy "Convert to OSCAL" button.

## 2. Quickstart

Requires Python 3.12 and, for tools that use them, Docker.

```
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m breachsafe_ux.app     # serves http://127.0.0.1:7860
```

Open the URL, fill in the form, and run. Change the port with `BREACHSAFE_UX_PORT`. Run scratch and
Docker bind-mounts live under `~/mint-proof/wizard-runs`; on macOS this must stay under
`/Users` for Docker Desktop to mount it. Override with `WIZARD_RUN_ROOT`.

Note on the bundled examples: the QuReddy and mint-oscal shims currently expect those tools'
source trees to be present locally. Containerised execution (`run.image`) removes that
requirement and is the recommended path for a portable install; see
[Execution backends](#6-execution-backends).

## 3. Architecture

```
  tools/<tool>/<tool>.yaml              one file declares the whole tool surface
        |   inputs[], run, validate, render, chains
        v
  facade.py  (engine, no tool-specific logic)
        |   render widgets  ->  build typed argv (no shell)  ->  run tool
        |   ->  artifact  ->  external validator  ->  3-state badge
        v
  app.py  (thin Gradio shell: the type-to-widget map, written once)
        |
        v
  web surface, one tab per standalone tool
```

- facade.py is the engine. It loads descriptors, builds a typed argv (values are single argv
  elements, never a shell string, so an input can never become a command), runs the tool,
  runs the validator, and derives the badge. It carries no knowledge of any specific tool.
- app.py is the Gradio shell. It maps a parameter type to a widget once, then loops over
  descriptors. Adding a tool changes no code here.
- tools/<name>/ holds one descriptor and an optional run shim per tool.

## 4. The three-state badge

The badge is the point of the project. Its rule is declarative and auditable as data.

| State | Meaning |
|---|---|
| VALID | the validator ran and accepted the artifact |
| INVALID | the validator ran and rejected the artifact |
| VALIDATOR-UNAVAILABLE | the tool or the validator could not run (missing dependency, Docker down, timeout) |

A crashed tool, a missing validator dependency, or an empty run all resolve to
VALIDATOR-UNAVAILABLE, never to VALID. Colour is a redundant cue only; the word carries the
state as text.

## 5. Add a tool (the descriptor)

Create `tools/<name>/<name>.yaml`. Each input declares its widget and how it maps to argv by
exactly one of: `positional: true`, `arg: --x`, or `flag: --x`.

```yaml
id: mytool
title: "My Tool"
standalone: true                     # false = reached only through another tool's chain button
inputs:
  - { name: host, type: text, label: host, required: true }
  - { name: port, type: int,  label: port, default: 443, min: 1, max: 65535 }
  - { name: fast, type: bool, label: "fast mode", default: false, flag: "--fast", group: advanced }
run:
  base: [mytool, scan]
  positional_from: "{host}:{port}"   # compose one positional from several inputs
  artifact_from: stdout
  artifact_name: out.json
validate:
  argv: ["{python}", "-c", "..."]    # {python} is the running interpreter, not a bare 'python'
  badge_rule: { pass_if: { exit: 0 }, fail_if: { exit: 1 }, otherwise: unavailable }
render:
  highlights: [ { label: status, find_prop: "status" } ]
chains:
  - { to: mint-oscal, label: "Convert to OSCAL", pass_artifact_as: source_file, with: { source: cbom } }
```

Widget types: `text`, `int`, `float`, `bool`, `enum` (radio for up to three choices,
dropdown for more), and `file`. Put rarely-used inputs in `group: advanced` to place them
behind a collapsible section. Tokens available in argv: `{share}`/`{workdir}` (the per-run
dir), `{artifact}` (the artifact path), `{python}` (the running interpreter), and every
input by `{name}`.

## 6. Execution backends

A descriptor chooses one way to run its tool. The unavailable path is shared by all
of them, so a backend that cannot run yields VALIDATOR-UNAVAILABLE rather than a false verdict.

| Backend | Descriptor | Portable | Isolated | Status |
|---|---|---|---|---|
| Local binary | `run.base` on PATH | no | no | supported |
| Python shim | `{python}` plus PYTHONPATH | no | no | supported (the bundled examples) |
| Docker image | `run.image` pinned by `@sha256` | yes | yes | planned |
| Remote API | `run.endpoint` | yes | yes | future |

Multi-tool orchestration and workflows are out of scope for the wizard by design; that is
the role of the orchestration layer (Osmedeus and TAO), not a single-tool surface. Docker
images, when added, must be pinned by digest, never a floating `:latest` tag.

## 7. Development

```
.venv/bin/python -m pytest tests/ -q
```

`tests/test_badge_states.py` drives the real pipeline (real tools from source, real oscal-cli in
Docker) and asserts the load-bearing properties: a good artifact validates, a rejected one
reports INVALID, an injection attempt is argv-safe, an absent validator reports
VALIDATOR-UNAVAILABLE, and a malformed input never reports VALID.

Layout:

```
src/breachsafe_ux/   facade.py (engine), app.py (shell), brand.py (tokens)
tools/<name>/            <name>.yaml descriptor, bin/ run shim
docs/adr/                architecture decision records
tests/                   badge-state and safety tests
```

Known gaps are tracked in `docs/KNOWN-ISSUES.md`.

## 8. Licence

Source-available under PolyForm Noncommercial 1.0.0
(the `Apache-2.0` license). You may use, modify, and share it
for any noncommercial purpose. Commercial use, including inclusion in a commercial product
or service, requires a separate licence from BreachSAFE. See [LICENSE](LICENSE).
