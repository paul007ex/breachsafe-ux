<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# ADR-0002 — The host↔descriptor boundary: keeping breachsafe-ux generic under hardening

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** BreachSAFE (paul)
- **Extends:** [ADR-0001](0001-breachsafe-wizard.md) (the facade decision; resolves its open
  question on the trust/auth model). Supersedes the in-code "ADR wizard #5" note at
  `facade.py:115` and folds in the intent of #5 (descriptor-declared buttons as argv, not
  function references).
- **Related issues:** #1, #5, #7, #9, #14, #16, #21, #22, #25. Introduces #43 (`validate.by`),
  #44 (`artifact: optional`), #45 (dual-consumer pressure-test).

## Context

breachsafe-ux is a reusable host: any BreachSAFE tool becomes a UX by dropping a YAML
descriptor under `tools/<name>/<name>.yaml` and pointing `BREACHSAFE_UX_TOOLS_DIR` at it.
The engine's stated contract (`facade.py:5`) is that zero tool-specific logic lives in it.
Two real consumers exist and are both kept as living pressure-tests of the boundary:
`tools/qureddy/` (a scan tool) and `tools/mint-oscal/` (a convert tool that may get its own
UX built on this host).

A batch of hardening and correctness fixes is queued. Some can, if implemented carelessly,
move tool-specific meaning *into* the host and quietly break reuse. Before writing that code we
fix the boundary so each change lands on the correct side of it:

- **Already a violation.** `test_connection` (`facade.py:109`) hardcodes
  `openssl s_client -connect` inside the engine. The code comment already admits this
  contradicts the module contract (#21).
- **Genericity-critical fixes.** The result headline (#1) and the argv model + `--` guard (#9)
  touch the contract every descriptor depends on.
- **Boundary-confirming fixes.** The format/validator mismatch (#16) and the mint-oscal
  exit-code mis-badge (#14) are descriptor/rule bugs, not engine bugs — evidence the seam is
  mostly right, but they expose a real gap: a validator that must vary by input value (#43).
- **Pure host concerns.** Off-loopback bind with no auth (#7) and CSRF/host-header (#22) are
  server properties with no tool coupling. ADR-0001 left this as an open question; it is
  answered here.

## Decision

### 1. The boundary is a hard invariant

**The host owns transport and truth; the descriptor owns meaning.**

| Layer | Owns | Must never contain |
|---|---|---|
| **Host** (`facade.py`, `app.py`) | how a tool is run and reported: argv assembly, no-shell exec, timeouts, the 3-state badge state machine, server bind/auth, widget rendering | the name of any specific tool, protocol, algorithm, CLI flag, or domain verdict ("quantum-vulnerable", "CBOM", "TLS", "openssl") |
| **Descriptor** (`<name>.yaml`) | what the tool means: its argv, inputs, validator, badge rule, headline text, preflight command, chains | Python; exec logic; anything that would need a host code change to add a new tool |

Test for any host change: **a new tool must plug in with only a new YAML.** Both existing
descriptors are the standing regression witnesses (#45): `qureddy` (scan, stdout artifact,
format-selected validator, TLS/SSH preflight) and `mint-oscal` (convert, file input, Docker
backend, exit-code validator, chain target). A change that needs host code to support either is
a boundary violation. **On #25:** mint-oscal stays in-repo as the second witness; keeping it
Pro-only is a packaging/capability concern (which tab renders for which edition), not a reason
to delete the descriptor.

### 2. Contract extensions (one per queued fix)

**2a. Preflight is descriptor-driven — retire the hardcoded openssl (#21).**
The `preflight` block already declares which fields bind (`host`/`port`/`openssl`); the engine
hardcodes the command. Generalize to a `preflight.argv` template resolved through `_subst`,
exactly as `run.argv` and `validate.argv` already are. `test_connection`'s OpenSSL/TLS string
moves out of `facade.py` and into `tools/qureddy/qureddy.yaml`. This also realizes #5's intent
(buttons are descriptor argv, not host functions).

```yaml
preflight:
  label: "Test connection"          # button text (host has no default verb)
  argv: ["{openssl}", "s_client", "-connect", "{host}:{port}"]
  binds: { host: target_host, port: target_port, openssl: openssl_bin }
  ok_if: { exit: 0 }
```

**2b. The headline is descriptor-driven — the host never computes posture (#1).**
The host renders only the badge *state* it can defend (`valid` / `invalid` / `unavailable` /
`none`). Any domain posture ("quantum-vulnerable", "PQC-ready") is tool meaning and comes from
the descriptor, mapped over the badge state and/or artifact highlights. The host must not read
an artifact to decide a domain headline.

```yaml
render:
  headline:
    invalid: "Quantum-vulnerable — this endpoint failed PQC readiness"
    valid:   "PQC-ready — validator accepted the evidence"
    unavailable: "Could not determine readiness"
```

**2c. Validators are selected by input value — `validate.by`, multi-key, fail-closed (#43).**
Today `validate` is singular, so `qureddy.yaml` offering `format=[cbom,json,rich]` while its
validator only understands CBOM produces a false verdict (#16); mint-oscal shows the same class
from the exit-code side (#14). Select a validator by **one or more** inputs, and **fail
closed**: if the selected variant has no validator, the badge is `none`, never a green.

```yaml
validate:
  by: [format]                       # one OR MORE input names; keys on the tuple of values
  cases:
    "cbom":  { argv: [...], badge_rule: {...} }
    "json":  { argv: [...], badge_rule: {...} }
    "rich":  null                    # explicit opt-out -> badge ("none", "no validator ...")
  default:   null                    # optional; used when no case matches
```

Multi-key keys on values joined with `|` (e.g. `by: [format, profile]` → `"cbom|strict"`). A
simpler descriptor keeps the singular `validate:` form; `by:` is optional sugar.

**2d. argv is a canonical ordered model with an end-of-options guard (#9).**
`_build_argv` emits **all options first, then a literal `--`, then positionals**. A
leading-dash field value can no longer be parsed as a flag by the target tool. This is a
one-time ordering change applied uniformly to every descriptor, not a per-tool patch. Tools
that do not accept `--` opt out with `run.no_end_of_options: true` (documented as a weaker
posture).

**2e. The artifact may be optional (#44).**
The #15 empty-artifact guard assumes every tool writes a file. A tool whose validity is
exit-code/stdout-based sets `run.artifact: optional`; the guard is then skipped and the badge
comes from the validator against stdout. Symmetric to the existing
`run.trust_artifact_on_nonzero` escape hatch.

### 3. Trust/auth: loopback default, operator-owned exposure (#7, #22)

Reaching the UI equals reaching a process spawner, so exposure is a deployment decision, not a
host feature. For a source-available tool that runs mostly in Docker, the host keeps this
deliberately thin:

- **Default bind is loopback** (`127.0.0.1`, `app.py:293`). A local `pip` run is reachable only
  from the same machine.
- **Exposure is the operator's boundary.** In Docker the container binds `0.0.0.0` so the port
  can be mapped; the trust boundary is the container network namespace and the operator's
  explicit `-p` mapping / reverse proxy, not code in the host. The host does **not** refuse to
  start on a non-loopback bind (that would break the Docker default) and does **not** inject
  host-header / DNS-rebinding middleware.
- **No built-in auth.** Put auth at the boundary you already run (reverse proxy, Docker network,
  VPN) when you expose it. An in-process Basic Auth or host-header allowlist adds code and
  fights the Docker `0.0.0.0` norm for little gain on a local single-tool surface.

**Decision (2026-08-22): #7 and #22 are closed as wontfix under this posture.** Path-field
Verify buttons still give a local user feedback. If a hosted, multi-tenant surface is ever
built, auth belongs in that control plane (Phase 4 in ADR-004), not in this single-tool host.

## Consequences

**Positive**
- The invariant is testable ("new tool, YAML only") with two standing witnesses of different
  shapes (#45).
- Every queued fix has a defined side of the boundary, so hardening does not erode reuse.
- `facade.py` loses its last protocol-specific code (the openssl preflight), matching its own
  docstring.

**Negative / cost**
- 2a, 2c, 2d change the descriptor schema, so both existing descriptors need a migration edit
  (small, mechanical, covered by tests).
- `validate.by` and per-state `render.headline` add descriptor surface; kept optional so simple
  tools stay one-liners.

## Sequencing (implementation follows this ADR)

1. **Generic contract PR** — #1 (descriptor headline) + #9 (canonical argv + `--`), with both
   descriptors migrated and #45 regression-checked.
2. **Retire the debt** — #21 (`preflight.argv`) + #43 (`validate.by`, closes #16/#14) + #44
   (`artifact: optional`).
3. Rev to 0.3.0 with a CHANGELOG entry once the above land.

Server hardening (#7, #22) is intentionally out of scope — see §3.

## Open questions

- Whether the SSH descriptor (qureddy's second scanner) lands as a third consumer that further
  stress-tests 2a, before or after this pass.
- Whether `run.no_end_of_options` (2d) needs a per-argument form for tools with mixed parsers.
