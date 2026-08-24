<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Coding rules

The authoring standards for working **on** the host. They complement, and do not duplicate,
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §5 (coding style) and §6 (dependencies); read those
first. This page collects the rules specific to the host's architecture, with enough detail to
use as a checklist. Every rule here matches how the code works today and names the gate that
enforces it, so a rule and the code cannot silently drift apart.

The host is tool-agnostic by design. That word is load-bearing throughout this page: the engine
knows nothing about any specific tool, protocol, algorithm, or domain verdict, and neither does
any rule below. A tool is described by a YAML descriptor; the host runs the same pipeline for
every one. See [why agnostic](../explanation/why-agnostic.md) for the design thesis and
[the architecture](../explanation/architecture.md) for the module map and coupling diagrams.

## Contents

1. [Keep the framework at the edge](#1-keep-the-framework-at-the-edge)
2. [Respect the host-descriptor boundary](#2-respect-the-host-descriptor-boundary)
3. [Build a typed argv, never a shell string](#3-build-a-typed-argv-never-a-shell-string)
4. [Fail closed everywhere](#4-fail-closed-everywhere)
5. [Typing](#5-typing)
6. [Docstrings and comments](#6-docstrings-and-comments)
7. [Errors and diagnostics](#7-errors-and-diagnostics)
8. [Descriptor conventions](#8-descriptor-conventions)
9. [Size ceilings](#9-size-ceilings)
10. [Style and gates](#10-style-and-gates)

## 1. Keep the framework at the edge

The host is a small MVC around an engine and a theme. The framework (Gradio) lives at one edge
only, so the model, view, and engine are testable without a browser.

- **Only `app.py` (controller) and `brand.py` (theme) may import Gradio.** The model
  (`resolve.py`, `_render.py`), the view (`render.py`), and the engine (`facade.py`) stay
  framework-free.
- New rendering or run logic belongs in the engine or the model, never in the Gradio shell.
- The layering is a contract, not a convention. `import-linter` enforces two contracts,
  configured in [`pyproject.toml`](../../pyproject.toml) under `[tool.importlinter]`:
  - A **layers** contract: `app` (controller) is above `render | brand` (view and theme), above
    `facade` (engine), above `resolve | _render` (model). A lower layer may never import a
    higher one, and the two modules joined by `|` may not import each other.
  - A **forbidden** contract: `facade`, `resolve`, `_render`, and `render` may never import
    `gradio`.

Run the contract directly while iterating:

```bash
uv run --locked --extra dev lint-imports
```

The module roles and the coupling graph are documented once in
[the architecture](../explanation/architecture.md#module-map) and
[the Gradio shell](../explanation/the-gradio-shell.md); this page does not repeat them.

## 2. Respect the host-descriptor boundary

The host owns transport and truth; the descriptor owns meaning. This is the hardest invariant in
the repository. See
[the host-descriptor boundary](../explanation/host-descriptor-boundary.md) and
[ADR-0002](../adr/0002-host-descriptor-boundary.md).

- The engine must never contain a specific tool's name, protocol, algorithm, CLI flag, output
  format, or domain verdict. `facade.py` carries zero tool-specific logic; keep it that way.
- A capability a tool needs is a **descriptor field**, added to
  [`descriptor.schema.json`](../../src/breachsafe_ux/descriptor.schema.json) and the
  [descriptor schema reference](../reference/descriptor-schema.md), never a special case in host
  code.
- The test for any host change: if it would only ever help one tool, it is on the wrong side of
  the boundary. Move it into the descriptor.

## 3. Build a typed argv, never a shell string

The engine runs every tool, validator, and action through `subprocess.run` with an argv list and
no shell. This is a security property, not a style preference.

- **A user-submitted value is always one argv element.** `facade._input_argv` emits each value as
  a single list element (`[str(v)]` for a positional, `[spec["arg"], str(v)]` for an option), and
  `subprocess.run` receives the list. A value never reaches a shell, so it can never be parsed as
  a command.
- **A value is never `${ENV}`-expanded.** Only a descriptor's declared `default` and the
  display-only `brand` block are expanded (`_expand_input_defaults`, `_expand_brand`). The value a
  user submits is passed verbatim.
- **The `--` end-of-options guard.** `facade._build_argv` emits every option first, then a literal
  `--`, then the positionals. Everything after `--` is data, so a value that begins with a dash
  (for example `--openssl=/tmp/x` typed into a host field) can no longer be read as a flag by the
  target tool. A tool whose parser does not understand `--` opts out with
  `run.no_end_of_options`, which is a documented weaker posture, not a default.

`shell=True` does not appear anywhere in the codebase and must not be introduced. `bandit`
(`B603`) still inspects every subprocess call even though the Ruff `S603` finding is muted, since
the argv-only form is the design.

## 4. Fail closed everywhere

The three-state verdict is load-bearing (see
[the three-state verdict](../explanation/three-state-verdict.md) and
[the badge reference](../reference/badge.md)). Any path that cannot prove a result reports
`VALIDATOR-UNAVAILABLE`, never a green.

- **Never render a green the validator did not give.** A tool or validator that cannot run,
  times out, or produces empty output resolves to `unavailable`. A nonzero exit is never `valid`
  even when a schema-shaped artifact was written, because the validator checks shape, not success
  (`facade._postprocess`, `_nonzero_exit_result`). A `validate.by` case with no validator badges
  `none`, never a green (`facade._select_validator`).
- **Conditions AND and default to false.** `facade._match` returns `False` for an empty condition
  or any unknown key, so a mis-typed `badge_rule` fails closed rather than passing.
- **Use specific exceptions, not bare `except`.** The engine catches the narrowest type that can
  occur: `FileNotFoundError` and `subprocess.TimeoutExpired` for a missing or slow tool,
  `(OSError, ValueError)` for a launch failure, `(json.JSONDecodeError, OSError, ValueError)` for
  an unreadable artifact.
- **The one deliberate broad catch is the fail-closed edge.** `facade._validate` wraps the
  validator launch in `except Exception` so that any validator failure becomes an `unavailable`
  badge instead of a traceback. This is the single sanctioned broad catch; Ruff's `BLE001` is
  muted project-wide for exactly this reason (see the `ignore` list in
  [`pyproject.toml`](../../pyproject.toml)). Do not add new broad catches elsewhere.
- **A malformed descriptor is a badge, not a crash.** An unresolved `{token}` or a schema
  violation raises `_DescriptorError`, which `run_descriptor` turns into an `unavailable` badge.

## 5. Typing

- Python 3.14, fully typed. `mypy --strict src` must pass with no relaxations; `strict = true`
  is set in [`pyproject.toml`](../../pyproject.toml) and every check it enables stays on.
- `from __future__ import annotations` at the top of every module.
- The one intentional typing boundary is `gradio.*`, set to `follow_imports = "skip"` because
  Gradio attaches its event methods at runtime. Do not widen this to other packages, and do not
  add bare `# type: ignore`; `warn_unused_ignores` is on, so a stale ignore fails the gate.

## 6. Docstrings and comments

- Every public module, class, and function carries a docstring. Ruff's `D` rules (Google
  convention, configured under `[tool.ruff.lint.pydocstyle]`) enforce style, and `interrogate`
  enforces a coverage floor (`fail-under` in [`pyproject.toml`](../../pyproject.toml)). Raise the
  floor as coverage grows; never lower it.
- Comments explain why, not what. The engine's comments cite the issue or advisory a guard exists
  for (for example the `--` guard, the false-green guards); keep that habit so a future reader
  knows which rule a line defends.

## 7. Errors and diagnostics

- The engine returns data, it does not print. `facade.py` and the model return result dicts or
  raise typed errors; there is no `print()` in the engine or the model. Diagnostics reach the
  user as the badge `detail` string and the captured tool output, both surfaced by the
  controller.
- Every run gets a fresh per-invocation workdir under `RUN_ROOT` (`facade._run_workdir`), so no
  two runs share a directory and no stale artifact is reused. `RUN_ROOT` is bounded to the most
  recent runs (`_prune_run_root`). A change to run-directory handling must preserve both
  properties.
- Preserve captured stdout for the validator. `_postprocess` always writes `stdout.txt` into the
  workdir so a validator can inspect it even when the artifact is written elsewhere.

## 8. Descriptor conventions

A tool is added by writing a descriptor, not by writing host code (see
[add a tool](../how-to/add-a-tool.md)). The conventions the engine relies on:

- **One file per tool.** The loader discovers `tools/<id>/<id>.yaml`
  (`resolve._tools_dir().glob("*/*.yaml")`). Each tool is its own directory with a single
  descriptor and an optional `bin/` run shim. A deployment can point the loader elsewhere with
  `BREACHSAFE_UX_TOOLS_DIR`.
- **Tokens, not string interpolation.** Argv templates use `{name}` tokens resolved by
  `facade._render`; `{{` and `}}` are literal braces. An unresolved token fails closed. The full
  namespace (`{workdir}`, `{artifact}`, `{python}`, and the input names) is documented in
  [descriptor tokens](../reference/descriptor-tokens.md); do not invent tokens in host code.
- **Feature-flag gating.** A descriptor or chain may carry `feature_flag: X`; it renders only
  when `facade.feature_enabled("X")` returns true, which reads the env var
  `BREACHSAFE_UX_<X>` (default on). This lets a deployment hide a feature without deleting its
  descriptor. Gate a new optional surface with a flag rather than a code branch.
- **Schema first.** Every descriptor is validated against
  [`descriptor.schema.json`](../../src/breachsafe_ux/descriptor.schema.json) at load time
  (`_validate_descriptor`), and a `schema_version` newer than the build supports fails closed
  (`_check_schema_version`). A new descriptor capability is a schema change plus a
  [reference](../reference/descriptor-schema.md) update.

## 9. Size ceilings

The size policy is 400 lines per file, 50 per function, 200 per class, counting logical lines
(blank lines and a leading docstring are excluded). It is enforced by
[`scripts/check_size_policy.py`](../../scripts/check_size_policy.py) and wired into the release
gate.

```bash
python3 scripts/check_size_policy.py --src-dir src/breachsafe_ux
```

The ceilings are why the model is split (`resolve.py` and `_render.py` are separate from
`facade.py`) and why `_render.py` holds the highlight and posture helpers that would otherwise
push `facade.py` over the file ceiling. When a file approaches the ceiling, split by
responsibility rather than shaving lines.

## 10. Style and gates

Formatted and linted with Ruff, with an SPDX header on every first-party file. The complete
blocking gate suite is in [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §4; reproduce all of it
locally with the [local release gate](local-release-gate.md), or run a single gate directly, for
example:

```bash
uv run --locked --extra dev ruff check src tests
uv run --locked --extra dev mypy --strict src
```

Do not weaken a gate to make it pass. A red gate is a bug to fix, not a threshold to lower. If a
rule here is genuinely wrong for the change in front of you, change the rule in a PR with
reasoning rather than working around it silently.
