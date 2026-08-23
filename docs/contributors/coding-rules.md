<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Coding rules

The authoring standards for working **on** the host. These complement, and do not duplicate,
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §5 (coding style) and §6 (dependencies) — read those
first. This page collects the rules specific to the host's architecture.

## Keep the framework at the edge

The host is a small MVC around an engine and a theme (see
[architecture](../explanation/architecture.md)):

- **Only `app.py` (controller) and `brand.py` (theme) may import Gradio.** The model
  (`resolve.py`, `_render.py`), the view (`render.py`), and the engine (`facade.py`) stay
  framework-free so they are testable without a browser. `import-linter` enforces this layering
  as a gate. See [the Gradio shell](../explanation/the-gradio-shell.md) for why the framework
  lives at this single edge.
- New rendering or run logic belongs in the engine or model, not in the Gradio shell.

## Respect the host↔descriptor boundary

The host owns transport and truth; the descriptor owns meaning (see
[the host↔descriptor boundary](../explanation/host-descriptor-boundary.md) and
[ADR-0002](../adr/0002-host-descriptor-boundary.md)). Concretely:

- The engine must never contain a specific tool's name, protocol, algorithm, CLI flag, or domain
  verdict. If a change needs host code to support a new tool, it is on the wrong side of the
  boundary.
- A new capability that a tool needs should be a **descriptor field**, added to
  [`descriptor.schema.json`](../../src/breachsafe_ux/descriptor.schema.json) and the
  [descriptor schema reference](../reference/descriptor-schema.md), not a special case in the
  engine.

## Fail closed

The three-state verdict is load-bearing (see
[the three-state verdict](../explanation/three-state-verdict.md)):

- Never render a green result the validator did not give. A tool or validator that cannot run is
  `VALIDATOR-UNAVAILABLE`, never `VALID`.
- Use specific exceptions, not bare `except`, except where the host deliberately fails closed.
- Build a typed argv; never assemble a shell string from input.

## Style and gates

Python 3.12, fully typed under `mypy --strict src`, formatted and linted with Ruff, with an SPDX
header on every first-party file. The complete blocking gate suite is in
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §4; reproduce it locally with the
[local release gate](local-release-gate.md). Do not weaken a gate to make it pass — a red gate is
a bug to fix.
