---
name: breachsafe-architecture-review
description: Macro/system-level architecture design and review for a single BQP component — component boundaries and data flow, pattern and technology trade-offs, API contract design, data-store/schema architecture (including PostgreSQL-specific choices), data flow diagrams with trust boundaries, and Architecture Decision Records. Use when designing a new system or component, reviewing an existing one's structure, choosing between architectural patterns or data stores, designing an API's resource/versioning/error contract, drawing or updating a DFD, or writing an ADR. Not cross-repo sequencing, not code-level anti-patterns, not crypto-correctness, not implementation.
---

# breachsafe-architecture-review

**Applies to:** the structural design of one BQP component at a time — component/service
boundaries, data flow, pattern choice, API contract shape, data-store architecture, and
the ADRs that record those decisions.

## Contents
- Stay in its lane
- Authorization gate
- The seven modes
- Ground rules
- References

## Stay in its lane

Not cross-repo sequencing or portfolio-level roadmap ADRs (`breachsafe-pqc-pm` — decides
*what and in what order* across the platform; this skill decides *how one component is
structured* once pqc-pm has authorized the work). Not generic code-level anti-patterns or
PR hygiene (`breachsafe-quality-review`). Not crypto-correctness, memory/timing safety, or
threat-model execution (`breachsafe-security-audit` — this skill draws the trust boundaries
a threat model starts from, it doesn't run the threat model itself). Not writing the code,
the OpenAPI YAML, or tuning a live query (`breachsafe-implement` — this skill decides the
resource model and the data-store choice; turning that into working code and running
`EXPLAIN ANALYZE` against it is implementation, not design). Not supply-chain/release
readiness (`breachsafe-release`).

Rule of thumb: if changing the answer would change what gets *built*, it's implementation.
If changing the answer would change what gets built *the same way everywhere it recurs* —
a boundary, a contract, a data-store choice, a pattern — it's this skill.

## Authorization gate

Design and review only. Draft ADRs, diagrams, and recommendations; present trade-offs
explicitly. Never opens a PR, commits an ADR as "Accepted," changes a label, or edits
another component's contract without explicit in-conversation authorization for that
specific action.

## The seven modes

1. **New system/component design** — requirements (functional + non-functional) →
   pattern selection → component diagram → draft ADRs. Never skip straight to a diagram
   without stating the NFRs it's supposed to satisfy. `references/system-design-workflow.md`.
2. **Existing architecture review** — component boundaries, coupling/cohesion, data
   ownership, scalability headroom against *stated* load, technical-debt assessment.
   Security-architecture placement (where auth happens, where secrets live, where trust
   boundaries cross) is in scope here; crypto-correctness inside those boundaries is
   `breachsafe-security-audit`'s job, not this skill's. `references/architecture-review-checklist.md`.
3. **ADR authoring** — one decision per record, written when the decision is made, not
   reconstructed afterward to justify something already shipped. `references/adr-authoring.md`.
4. **Pattern/technology trade-offs** — monolith vs. services, sync request/response vs.
   event-driven, shared-nothing vs. shared-state — evaluated against *this system's*
   stated constraints, never asserted as universally correct. `references/pattern-tradeoffs.md`.
5. **API contract design** — resource modeling, versioning, pagination, and error-contract
   shape for REST/GraphQL/gRPC surfaces. Stops at the contract; writing the OpenAPI/proto
   file and generating server code is `breachsafe-implement`. `references/api-design.md`.
6. **Data-store and schema architecture** — normalization/denormalization trade-offs,
   relational vs. document vs. columnar choice, PostgreSQL-specific architectural
   decisions (partitioning strategy, read-replica topology, logical vs. physical
   replication, extension adoption like PostGIS/pgvector as a *design* commitment).
   Query-level tuning and `EXPLAIN` work is implementation, not this skill.
   `references/data-architecture.md`.
7. **Data flow diagrams (DFD) with trust boundaries** — leveled context/level-0/level-1
   DFDs in Yourdon/Gane-Sarson notation, with trust boundaries marked at every place data
   crosses a privilege or network boundary. This is the artifact `breachsafe-security-audit`
   starts a STRIDE pass from; producing it is this skill's job, running the threat model
   against it is theirs. `references/data-flow-diagrams.md`.

## Ground rules

State the NFRs and constraints a recommendation is answering *before* recommending a
pattern — a trade-off with no stated requirement behind it is an opinion, not an
architecture decision. Never invent a specific-sounding outcome metric ("40% faster,"
"30% less complex") that wasn't measured; a design recommendation is a reasoned trade-off,
not a forecast with fabricated precision. Present at least two real alternatives with
their actual costs before naming a recommendation — a review that only describes the
chosen option isn't a review. Diagram before prose where a diagram would settle the
question faster (component diagram, sequence diagram, DFD — mermaid is fine). Read the
component's own existing ADRs and docs before proposing a new one; a decision that
contradicts an accepted ADR needs to say so explicitly, not silently override it. No
hardcoded absolute paths. Recommendations are drafts for the project lead, not executed
decisions, unless told otherwise for this conversation.

## References

- `references/system-design-workflow.md` — requirements → NFRs → pattern → diagram → ADRs.
- `references/architecture-review-checklist.md` — boundaries, coupling, scalability,
  security-architecture placement, technical debt, for an already-built system.
- `references/adr-authoring.md` — ADR template and the rules for writing one honestly.
- `references/pattern-tradeoffs.md` — architecture pattern trade-off tables, framed as
  questions to ask, not answers to assert.
- `references/api-design.md` — REST/GraphQL/gRPC resource modeling, versioning,
  pagination, error-contract design.
- `references/data-architecture.md` — schema/data-store trade-offs and PostgreSQL-specific
  architectural decisions (partitioning, replication topology, extensions).
- `references/data-flow-diagrams.md` — DFD notation, leveling, and trust-boundary marking.
