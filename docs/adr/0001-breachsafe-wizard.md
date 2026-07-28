# ADR-0001 — breachsafe-wizard: a config-driven, honest single-tool UX facade

- **Status:** Proposed (draft)
- **Date:** 2026-07-28
- **Deciders:** BreachSAFE (paul)
- **Codename:** Gizmo · **Product name:** breachsafe-wizard
- **Related:** breachsafe-ux-frameworks + breachsafe-build-vs-buy skills; TAO/Osmedeus
  ExecutionProvider (orchestration boundary); mint-oscal #30 (productize the facade).

## Context

Every BreachSAFE tool (QuReddy, mint-oscal, Qurum, QuCert, QuCrypt) is the same pipeline
with different nouns:

```
INPUT (params/file) → run CLI tool → ARTIFACT → external validator → honest ✅/❌/⚠️ + pretty output
```

We need a **nice UX per tool** that exposes *all* a tool's parameters and reports an
**honest** result. Three forces constrain the choice:

1. **Honesty is the differentiator.** The verdict must be a real external-validator result
   with three states — `valid` / `invalid` / **`validator-unavailable`** — never a green a
   validator didn't give. No generic tool-UI enforces this; it is the compliance value.
2. **Claude is weak at bespoke UX code.** Minimize hand-authored UI; prefer prebuilt widgets
   driven by **config**, not per-tool UI code.
3. **Do not rebuild orchestration.** Multi-tool workflows/DAG/history/batch are Osmedeus/TAO's
   job (an already-adopted ExecutionProvider); our own doctrine forbids overlapping it.

## Decision

Adopt **breachsafe-wizard**: a **config-driven, descriptor-based, single-tool UX facade**
rendered on **Gradio** (Apache-2.0), with an honest 3-state validation badge and BreachSAFE
brand tokens.

- **One tool = one YAML descriptor** under `tools/<name>/<name>.yaml`. Adding or changing a
  tool is data, not UI code. The descriptor declares every input
  (type/widget/min-max/choices/default/validation), how each maps to argv, the external
  validator, the badge rule, the output render, and optional chains.
- **The engine (`facade.py`) is ~85% backend** (Claude's strength): typed argv build (no
  shell), run, validate, 3-state badge, render. The Gradio shell is a thin loop over the
  descriptor — the only UI code, written once.
- **Scope = a single tool, done to 10/10.** Multi-tool orchestration is explicitly OUT — that
  is Osmedeus/TAO (rebranded BreachSAFE). breachsafe-wizard may hand an artifact to another
  tool via a declared `chain` (e.g. QuReddy CBOM → "Convert to OSCAL"), but it is not a DAG
  engine.

## Design (contract summary)

```yaml
id: qureddy
inputs:                       # → widgets, and → argv
  - {name: target, type: text, positional: true, required: true}
  - {name: format, type: enum, choices: [cbom,json,rich], default: cbom, arg: "--format"}
  - {name: timeout, type: int, min: 1, max: 300, default: 30, widget: slider, arg: "--timeout"}
  - {name: reproducible, type: bool, default: false, flag: "--reproducible"}
run:      { base: [qureddy, scan, tls], artifact_from: stdout, artifact_name: cbom.json }
validate: { argv: [...cyclonedx/oscal-cli...], badge_rule: {unavailable_if, pass_if, otherwise: invalid} }
chains:   [ { to: mint-oscal, label: "Convert to OSCAL →", pass_artifact_as: source_file } ]
```

Each input maps to argv by **exactly one** of: `positional: true` (value only), `flag: "--x"`
(token if truthy), or `arg: "--x"` (`[--x, value]` when set). The tool binary is resolved
from a per-tool `tools/<name>/bin/` shim on `PATH`, so the wizard never touches or installs
the tool's source tree.

Non-negotiables baked into the engine:
- **argv, never a shell** — params substitute into single argv elements; injection-safe.
- **3-state honesty** — `validator-ran-but-rejected → invalid`; `validator-couldn't-run →
  unavailable`; only a real pass → `valid`. Declarative `badge_rule`, auditable as data.
- **Engine-owned paths / pinned validator images / upload bounds / timeouts.**
- **Brand from a single source** (EnXemble `brand.ts` tokens: bs-cyan `#3ae7f4`, lockup).

## Consequences

**Positive**
- Add a tool = one descriptor; the UI is generated → near-zero Claude UX code per tool.
- Honest verdict is uniform and audit-by-data across every tool.
- Apache-2.0 foundation → ship & sell; BreachSAFE code stays PolyForm-Noncommercial.
- Clean seam with TAO: breachsafe-wizard = single-tool honesty; Osmedeus = multi-tool
  orchestration.

**Negative / cost**
- One-time engine + Gradio-shell code (the only UI Claude writes).
- Gradio ceilings: long-running scans need `gr.Progress`; theming is "good," not pixel-perfect
  to the Next.js product. Acceptable for a tool surface; if a customer surface needs the full
  EnXemble look, that graduates to the Next.js app (out of scope here).

## Alternatives considered (weighted; see breachsafe-build-vs-buy)

- **A Build fresh (FastAPI+JS):** most control, but most Claude UX code + risks reinventing an
  OSS platform (secureCodeBox/Osmedeus overlap). Rejected for single-tool scope.
- **B Strip Osmedeus UX:** MIT, but UI source absent (compiled bundle) and a "tool" is a
  workflow-DAG → HIGH-effort hard-fork. Rejected (harvest pattern, not code).
- **C script-server:** Apache, config-only, but admin-looking and no first-class honest badge.
  Adopted as the *inspiration*, not the engine (Gradio looks better + we own the thin layer).
- **D Osmedeus/TAO:** the multi-tool orchestration answer — **kept for that layer**, not for
  single-tool surfaces.
- **Chosen:** Gradio descriptor-facade = C's config-driven model + A's honest-badge layer, on
  a permissive base, minimal Claude UX code.

## Open questions
- Final name (breachsafe-wizard vs Facet vs codename Gizmo).
- Home repo: its own repo vs `breachsafe-common/` (tooling) vs a `ux/` package.
- Trust/auth model before any non-localhost deployment (reaching the UI == a process-spawner).
