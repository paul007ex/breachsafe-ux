# System design workflow (Mode 1)

For a new system or component, in order. Skipping a step and going straight to a diagram
is the most common way a design ends up unable to answer "why did we build it this way."

## Contents
- 1. Requirements, split in two
- 2. Identify patterns, don't default to one
- 3. Component diagram
- 4. Draft ADRs for each real decision
- 5. State what wasn't decided

## 1. Requirements, split in two

- **Functional** — what the system does, from the caller's point of view.
- **Non-functional (NFRs)** — the constraints the functional behavior has to survive:
  expected load (requests/sec, data volume, growth rate), latency budget, availability
  target, consistency requirements, compliance/data-residency constraints, team size and
  operational capacity to run whatever gets chosen. Gather these explicitly; don't infer
  them from the pattern you already want to use. If an NFR is genuinely unknown, say so —
  "assumed: X, unverified" — rather than picking a comfortable default silently.

## 2. Identify patterns, don't default to one

Match the *gathered* NFRs to candidate patterns (see `pattern-tradeoffs.md`). A system
with one team, moderate load, and no independent-scaling requirement rarely needs
microservices; a system that must scale one hot path independently from the rest often
does. State which NFR is driving the pattern choice, not just the choice itself.

## 3. Component diagram

Draw the boundaries: what the components are, what owns which data, how they
communicate (sync call, event, shared store — and why). A mermaid `graph` or
`sequenceDiagram` is sufficient; the point is making the boundary decision visible and
falsifiable, not producing polished art. If the system has any place where data crosses
a trust or privilege boundary, produce a DFD instead of (or in addition to) the component
diagram — see `data-flow-diagrams.md`.

## 4. Draft ADRs for each real decision

Write one ADR per decision that would be expensive to reverse (pattern choice, data
store, sync/async boundary, a load-bearing third-party dependency) — see
`adr-authoring.md`. Skip ADRs for reversible, low-cost choices; an ADR for every minor
decision buries the ones that matter.

## 5. State what wasn't decided

List open questions and explicitly deferred decisions rather than presenting the design
as fully resolved. A design that silently glosses over an unresolved NFR (e.g., no stated
consistency model for a multi-region write path) will surface as a production incident,
not a review comment.
