# Data flow diagrams with trust boundaries (Mode 7)

The artifact `breachsafe-security-audit` starts a STRIDE threat-model pass from. Producing
it is this skill's job; running the threat model against it is theirs.

## Contents
- Notation (Yourdon/Gane-Sarson)
- Leveling
- Trust boundaries
- Common mistakes worth checking for

## Notation (Yourdon/Gane-Sarson)

Four element types, nothing else:

- **External entity** (rectangle) — a person or system outside the boundary of what's
  being designed; originates or consumes data but isn't part of the system itself.
- **Process** (rounded rectangle or circle) — transforms input data flows into output
  data flows. Named with a verb phrase ("Validate order"), not a component name.
- **Data store** (open rectangle/two horizontal lines) — data at rest: a database, a
  queue, a file, a cache.
- **Data flow** (labeled arrow) — data in motion between the above. Label it with what
  the data *is*, not the mechanism ("Order confirmation," not "HTTP POST").

No other symbol types. A DFD that starts adding decision diamonds or control-flow
constructs has drifted into a flowchart, which answers a different question (sequence of
control) than a DFD does (path of data).

## Leveling

- **Context diagram** — the whole system as one process, every external entity around
  it, nothing else. This is the "what talks to us and what do we exchange" view.
- **Level 0** — the system's top-level processes and stores, still coarse-grained.
- **Level 1+** — decompose one Level-0 process further only if its internal data flow
  is itself worth reasoning about (a process with a real internal trust boundary, or
  complex enough that "what happens inside it" is a live design question). Don't
  decompose uniformly to some fixed depth — decompose where it earns its complexity.
- Every process at a given level must balance: the flows into and out of a decomposed
  process at Level 1 must match what that process showed at Level 0. A DFD that doesn't
  balance is a modeling error, not a stylistic choice.

## Trust boundaries

Mark a trust boundary (a dashed line crossing the diagram) at every place a data flow
crosses:

- A network boundary (public internet ↔ internal network, internal ↔ third-party).
- A privilege boundary (unauthenticated ↔ authenticated, user-scoped ↔ admin-scoped).
- An organizational boundary (this component's data ↔ another team's system, this
  platform ↔ an external vendor/SaaS dependency).

Every flow that crosses a trust boundary is a candidate STRIDE entry point — this is the
handoff point to `breachsafe-security-audit`. This skill's job stops at drawing the
boundary accurately and completely; it does not enumerate the threats against it.

## Common mistakes worth checking for

- A trust boundary drawn around the wrong thing (e.g., around a service instead of
  around the actual privilege change, which might happen mid-request via an internal
  token exchange rather than at the network edge).
- A data store treated as trusted by default — a database a compromised process can
  write to is inside that process's trust boundary, not automatically safe because it's
  "just storage."
- Missing external entities — a monitoring/logging pipeline, a third-party auth
  provider, a CI/CD system with deploy credentials are all external entities with real
  data flows, frequently left off because they're not "the product."
