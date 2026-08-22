<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.ai> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Tool descriptors

Each tool is one YAML descriptor at `tools/<id>/<id>.yaml`. Adding or changing a tool is data,
not code — see `docs/adr/0001-breachsafe-wizard.md` and
`src/breachsafe_ux/descriptor.schema.json` for the contract.

Point breachsafe-ux at a descriptor directory with `BREACHSAFE_UX_TOOLS_DIR`; it defaults to
this `tools/` directory.

## How the tool binary is resolved

The engine runs the command in `run.base` / `run.argv` by name, resolving it against
`tools/<id>/bin/` first, then the system `PATH`. So there are two ways to make a tool runnable:

1. **Install it on your `PATH`** (the normal path for a released tool, e.g. `pip install
   breachsafe-qureddy`). No shim needed.
2. **Drop a local shim** at `tools/<id>/bin/<id>` that execs your build or checkout. This is
   handy for developing against an uninstalled source tree.

`tools/*/bin/` is git-ignored: shims are per-developer wiring and must not be committed (they
would hardcode a local path and break for everyone else). A shim is just an executable, e.g.:

```bash
#!/usr/bin/env bash
exec /path/to/your/venv/bin/python -m qureddy "$@"
```
