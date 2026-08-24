<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Architecture

EnXemble is a small MVC around a rendering engine and a theme layer, with a thin evidence-export
adapter at the product edge. This page explains the module map, external image dependencies, and
why the pieces are split the way they are. For the settled decisions, see
[ADR-0001](../adr/0001-breachsafe-wizard.md) and
[ADR-0002](../adr/0002-host-descriptor-boundary.md).

## The pipeline every tab shares

Every tool the host wraps is the same pipeline with different nouns:

```mermaid
flowchart LR
    input["INPUT (form fields / file)"] --> argv["build a typed argv (no shell)"]
    argv --> run["run the tool"]
    run --> artifact["ARTIFACT"]
    artifact --> validator["external validator"]
    validator --> verdict{"three-state verdict"}
    verdict --> valid["VALID"]
    verdict --> invalid["INVALID"]
    verdict --> unavail["VALIDATOR-UNAVAILABLE"]
    classDef valid       fill:#d4edda,stroke:#28a745,color:#155724;
    classDef invalid     fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef unavailable fill:#fff3cd,stroke:#fd7e14,color:#7a4a00;
    classDef process     fill:#cce5ff,stroke:#0d6efd,color:#0a3678;
    classDef artifact    fill:#e2e3e5,stroke:#6c757d,color:#2f3336;
    classDef external    fill:#e7d6ff,stroke:#6f42c1,color:#3d1a78;
    class input,argv,run,verdict process;
    class artifact artifact;
    class validator external;
    class valid valid;
    class invalid invalid;
    class unavail unavailable;
```

The value of the host is that this pipeline is written once and shared by every tab, and that
the verdict is the real result of an external validator, reported as one of three states, never
a green the validator did not give.

## Module map

| Module | Role | Imports Gradio? |
|---|---|---|
| `resolve.py`, `_render.py` | **Model**: resolve descriptors, build the render model | no |
| `render.py` | **View**: turn the model into view structures | no |
| `app.py` | **Controller**: wire model → view into the running app; the Gradio shell | yes |
| `facade.py` | **Engine**: load descriptors, build argv, run, validate, derive the badge | no |
| `brand.py` | **Theme**: branding and white-label tokens | yes |
| `evidence.py` | **Evidence boundary**: safe paths, request hashes, subprocess invocation, output naming | no |
| `evidence_ui.py` | **Presentation adapter**: Gradio preview/open/download surfaces | yes |
| `tools/*/yaml` | **Descriptor data**: scan and evidence-export argv, inputs, outputs | no |
| `breachsafe-evidence` | **Go composer**: renders through `breachsafe-pdf` and owns ZIP packaging | external binary |

`app.py`, `brand.py`, and the presentation-only `evidence_ui.py` import Gradio. The framework
dependency remains at the controller/presentation edge; the model, view, engine, and evidence
orchestrator stay framework-free so they are testable in isolation without a browser. That edge is explained in detail in
[the Gradio shell](the-gradio-shell.md).

## Component coupling

How the modules depend on one another. An arrow reads "uses / depends on"; the dashed box is the
Gradio boundary: everything inside it imports the framework, everything outside stays
framework-free.

```mermaid
flowchart TD
    tools["tools/ — descriptors + bin/ shims"]
    desc["descriptor.yaml"]
    resolve["resolve.py — Model (resolve + probe binaries)"]
    facade["facade.py — Engine (run, artifact, validate, badge)"]
    evidence["evidence.py — safe Go composer boundary"]
    evidenceui["evidence_ui.py — preview/download adapter"]
    composer["breachsafe-evidence (Go)"]
    pdf["breachsafe-pdf"]
    bundle["timestamped PDF + ZIP"]
    rendermodel["_render.py — Model (highlights + posture)"]
    view["render.py — View (HTML / markdown)"]
    validators["external validators (subprocess)"]

    subgraph gradio["Gradio boundary"]
        app["app.py — Controller"]
        evidenceui
        brand["brand.py — Theme"]
    end

    tools --> desc
    facade --> tools
    facade --> resolve
    facade --> rendermodel
    facade --> validators
    app --> facade
    app --> resolve
    app --> view
    app --> rendermodel
    app --> brand
    app --> evidenceui
    evidenceui --> evidence
    evidence --> composer
    composer --> pdf
    composer --> bundle
    view --> rendermodel
    style gradio stroke-dasharray: 5 5
    classDef valid       fill:#d4edda,stroke:#28a745,color:#155724;
    classDef invalid     fill:#f8d7da,stroke:#dc3545,color:#721c24;
    classDef unavailable fill:#fff3cd,stroke:#fd7e14,color:#7a4a00;
    classDef process     fill:#cce5ff,stroke:#0d6efd,color:#0a3678;
    classDef artifact    fill:#e2e3e5,stroke:#6c757d,color:#2f3336;
    classDef external    fill:#e7d6ff,stroke:#6f42c1,color:#3d1a78;
    class app,brand,evidenceui process;
    class tools,desc,resolve,facade,rendermodel,view,evidence,composer,pdf,bundle artifact;
    class validators external;
```

Reading the graph:

- **`facade.py` (engine)** loads descriptors from `tools/`, resolves and runs each tool through
  `resolve.py`, invokes the external validator as a subprocess, and derives the badge. It carries
  no knowledge of any specific tool.
- **`app.py` (controller)** is the only caller that ties everything together: it calls the engine
  to run a descriptor, `resolve.py` for the environment probe, and the view plus `_render.py` to
  build the surface, and it imports the theme from `brand.py`.
- **`resolve.py`, `_render.py`, `render.py`** have no dependency on the controller or on Gradio, so
  they are unit-testable on their own.
- **`evidence.py`** is the thin OSS boundary for report export. It validates that scan artifacts
  remain inside the run directory, writes the evidence request and SHA-256 expectations, expands
  the descriptor argv, invokes the Go composer without a shell, and verifies every declared output.
- **`evidence_ui.py`** is presentation only. It renders an optional page-image preview and a normal
  browser-open link; it never creates PDFs or ZIPs.
- **`breachsafe-evidence`** owns the artifact contract. It calls `breachsafe-pdf` for PDF rendering
  and uses Go's `archive/zip` for the portable download. ePack is not required on the OSS UX host;
  enterprise evidence workflows can consume the standalone evidence image separately.

## Runtime image dependency graph

The published UX image is self-contained and multi-architecture:

```text
ghcr.io/breachsafe/qureddy:latest
  └─ qureddy + Python 3.14 + OpenSSL
       └─ ghcr.io/paul007ex/qureddy-ux:v0.9.2
            ├─ breachsafe-ux wheel + YAML descriptors
            ├─ breachsafe-evidence (Go)
            └─ breachsafe-pdf
```

The Dockerfile copies the two evidence binaries from
`ghcr.io/paul007ex/breachsafe-evidence-go:latest` at build time. Runtime scanning and export use
local binaries; there is no Docker socket, runtime package download, or customer-side ePack
installation. `:latest` is rebuilt for freshness, while version tags are immutable release
references.

## The engine

`facade.py` is the engine and carries no knowledge of any specific tool. It loads descriptors,
builds a typed argv (values are single argv elements, never a shell string, so an input can never
become a command), runs the tool by the chosen [execution backend](../reference/execution-backends.md),
runs the external validator, and derives the [three-state badge](../reference/badge.md). It is
the ~85%-backend part of the system and the place the correctness properties live.

## The shell

`app.py` is the Gradio shell. It maps a parameter type to a widget once, then loops over the
loaded descriptors to build one tab per standalone tool. Adding a tool changes no code here:
the tab is generated from the [descriptor](../reference/descriptor-schema.md). It also handles
the `--check` environment probe (see the [CLI reference](../reference/cli.md)).

## Repository layout

```
src/breachsafe_ux/   facade.py (engine), resolve.py + _render.py (model), render.py (view),
                     app.py (controller / Gradio shell), brand.py (theme)
tools/<id>/          <id>.yaml descriptor, optional bin/ run shim
docs/adr/            architecture decision records
tests/               badge-state and safety tests
```

Because the framework lives only at the edge and the engine is tool-agnostic, the same host
serves any tool that can be described by a descriptor. That agnosticism is the design thesis.
See [why agnostic](why-agnostic.md).
