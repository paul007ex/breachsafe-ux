# breachsafe-ux

[![Version](https://img.shields.io/badge/version-0.3.3-blue?style=flat-square)](CHANGELOG.md)

BreachSAFE EnXemble is a config-driven UX host for command-line tools. Declare a tool's
parameters in one YAML file and it renders a web tab, runs the tool, validates the output with
an external validator, and reports a three-state verdict: VALID, INVALID, or
VALIDATOR-UNAVAILABLE. It never shows a green result the validator did not actually give.

Adding a tool is a YAML file, not new UI code. The renderer, the runner, and the badge are
written once in the engine and shared by every tool tab.

- Home: https://www.breachsafe.io
- Source: https://github.com/paul007ex/breachsafe-ux
- Licence: Apache-2.0 (open source) — see [Licence](#8-licence)

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

Three tabs ship as examples:

- Quantum Audit scans a TLS endpoint for post-quantum readiness and produces a CycloneDX 1.7 CBOM.
- SSH Audit does the same for an SSH endpoint.
- Compliance (OSCAL) turns a scan or CBOM into an OSCAL Plan of Action and Milestones (also
  reached from a scan tab's "Convert to OSCAL" button). Enterprise; gated by `BREACHSAFE_UX_MINT_OSCAL`.

## 2. Quickstart

### Docker (recommended)

The image is self-contained (QuReddy + openssl inside), multi-arch, and public — copy-paste and
your browser opens on it:

```
docker run -d --rm --pull=always -p 7860:7860 --name enxemble ghcr.io/paul007ex/qureddy-ux:latest
sleep 10 && open http://localhost:7860       # macOS  ·  Linux: xdg-open  ·  Windows: start
```

`--pull=always` fetches the newest image first, so copy-paste always runs the latest. The
**Quantum Audit** tab opens with the host prefilled — click **Run**. No login, no docker socket,
works on Intel and Apple Silicon. Stop it with `docker stop enxemble`. (`:edge` tracks the tip of
`main`; `:latest` is the newest release.)

### From source (Python 3.12)

Install the tool it fronts (qureddy on PATH), then the host:

```
git clone https://github.com/breachsafe/qureddy && (cd qureddy && uv sync)
export PATH="$PWD/qureddy/.venv/bin:$PATH"
git clone https://github.com/paul007ex/breachsafe-ux && cd breachsafe-ux
uv sync
uv run breachsafe-ux            # http://127.0.0.1:7860
uv run breachsafe-ux --check    # verify every tab's tool + validator resolves (exit != 0 if missing)
```

| Variable | Default | Purpose |
|---|---|---|
| `BREACHSAFE_UX_PORT` | 7860 | server port |
| `BREACHSAFE_UX_HOST` | 127.0.0.1 (0.0.0.0 in Docker) | bind address |
| `BREACHSAFE_UX_TOOLS_DIR` | bundled `tools/` | descriptor root |
| `BREACHSAFE_UX_MINT_OSCAL` | true | show the Enterprise OSCAL tab |
| `BREACHSAFE_UX_RUN_ROOT` | `~/mint-proof/wizard-runs` | per-run scratch (macOS: keep under `/Users` for Docker) |

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
| Local binary | `run.base` on PATH | no | no | supported (preferred when present) |
| Docker image | `run.image` (`docker run --pull=always`) | yes | yes | supported |
| Remote API | `run.endpoint` | yes | yes | future |

A descriptor can declare both `run.base` and `run.image`: the engine runs the **local binary
when it resolves on PATH**, and falls back to the **docker image** otherwise (so local dev uses
the binary; the Docker deployment uses the image). `--pull=always` keeps the tool current; pin
by digest (`@sha256`) instead of `:latest` when reproducibility matters more than freshness.

Multi-tool orchestration and workflows are out of scope by design; that is the role of the
orchestration layer (Osmedeus and TAO).

## 7. Development

```
uv run --locked pytest -q
```

`tests/test_badge_states.py` drives the real pipeline (real tools from source, real oscal-cli in
Docker) and asserts the load-bearing properties: a good artifact validates, a rejected one
reports INVALID, an injection attempt is argv-safe, an absent validator reports
VALIDATOR-UNAVAILABLE, and a malformed input never reports VALID.

Layout:

```
src/breachsafe_ux/   facade.py (engine), resolve.py + _render.py (model), render.py (view),
                     app.py (controller / Gradio shell), brand.py (theme)
tools/<name>/            <name>.yaml descriptor, optional bin/ run shim
docs/adr/                architecture decision records
tests/                   badge-state and safety tests
```

Known gaps are tracked in `docs/KNOWN-ISSUES.md`.

## 8. Licence

Apache-2.0 (open source). You may use, modify, distribute, and use it commercially under the
terms of the licence. See [LICENSE](LICENSE). (The tools it fronts carry their own licences.)
