# breachsafe-wizard

A **config-driven, honest single-tool UX harness** for BreachSAFE tools. One tool = one YAML
descriptor; the engine builds a typed argv (no shell), runs the tool, runs its **external**
validator, and reports an honest **3-state** verdict:

| Badge | Meaning |
|---|---|
| ✅ **VALID** | the external validator ran **and accepted** the artifact |
| ❌ **INVALID** | the external validator ran **and rejected** it |
| ⚠️ **VALIDATOR UNAVAILABLE** | the validator (or tool) **could not run** — infra/absent |

The verdict is never a fabricated green: an empty run, a failed tool, or a missing validator
is reported as `unavailable`/`invalid`, not `valid`. That honesty is the product.

Built on [Gradio](https://gradio.app) (Apache-2.0). See
[`docs/adr/0001-breachsafe-wizard.md`](docs/adr/0001-breachsafe-wizard.md) for the rationale.

## Install

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .        # gradio, pyyaml, cyclonedx-python-lib
```

## Run

```bash
breachsafe-wizard                 # console-script entry point
# or:
python -m breachsafe_wizard.app
```

Serves on `http://127.0.0.1:7860` (override with `WIZARD_PORT`). Run scratch (and Docker
bind-mounts for validators like `oscal-cli`) live under `~/mint-proof/wizard-runs` — on
macOS this must stay under `/Users` for Docker Desktop to mount it. Override with
`WIZARD_RUN_ROOT`.

## Test

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -q
```

`tests/test_honesty.py` drives the real pipeline (real `mint-oscal`, real `oscal-cli` in
Docker) and asserts the honesty/safety properties: good input → valid; an OSCAL-invalid
timestamp → invalid; a shell-metachar `source` value spawns **no** command (argv-safe); an
absent validator → unavailable; malformed input → never `valid`.

## Add a tool

Drop a descriptor at `tools/<name>/<name>.yaml` and a run shim at `tools/<name>/bin/<name>`
(so the wizard runs the tool without installing its source tree). No UI code changes.

```yaml
order: 1                         # tab order; ties broken by id
id: mytool
title: "My Tool — what it does"
description: "One-line summary shown above the inputs."
inputs:
  # each input becomes a widget AND maps to argv by EXACTLY ONE of:
  #   positional: true   -> value only
  #   flag: "--x"        -> emits the token when the value is truthy
  #   arg:  "--x"        -> emits ["--x", value] when set
  - { name: target, type: text,  label: "target", positional: true, required: true,
      placeholder: "example.com:443", info: "shown under the field" }
  - { name: format, type: enum,  label: "format", choices: [cbom, json], default: cbom, arg: "--format" }
  - { name: timeout, type: int,  label: "timeout (s)", widget: slider, min: 1, max: 300, default: 30, arg: "--timeout" }
  - { name: fast,   type: bool,  label: "fast mode", default: false, flag: "--fast", group: advanced }
run:
  base: [mytool, scan]           # or a fully-static `argv: [...]` with {token} substitution
  artifact_from: stdout          # capture stdout as the artifact
  artifact_name: out.json
  timeout_s: 180
validate:                        # the EXTERNAL check that produces the badge
  argv: [some-validator, "{artifact}"]
  timeout_s: 60
  badge_rule:
    unavailable_if: { stdout_contains_any: ["Cannot connect", "Unable to find image"] }
    pass_if:        { exit: 0 }
    otherwise:      invalid      # ran but didn't bless → invalid (honest)
render:
  highlights:                    # pull scalar props out of the artifact for a summary
    - { label: "status", find_prop: "mytool:status" }
chains:                          # optional: hand the artifact to another tool
  - { to: other-tool, label: "Do next →", pass_artifact_as: source_file, with: { source: mytool } }
```

**Widget types:** `text`, `enum` (Radio for ≤3 choices, Dropdown otherwise), `int`/`float`
(`widget: slider` for a slider, else a number box), `bool` (checkbox), `file`. Mark rare
params `group: advanced` to place them behind a collapsed "Advanced options" accordion.

**Tokens** available in `run`/`validate` argv: `{share}`/`{workdir}` (the per-run dir),
`{artifact}` (the artifact path), plus every input by `{name}`. Values substitute into a
single argv element — never a shell string — so they can never become a new command.

## License

Source-available under **PolyForm Noncommercial 1.0.0** — see [`LICENSE`](LICENSE).
