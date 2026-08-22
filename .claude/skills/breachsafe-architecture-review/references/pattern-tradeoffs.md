# Pattern and technology trade-offs (Mode 4)

Framed as questions to ask about *this* system, not answers to assert universally. Every
row below has real production use on both sides — the "right" choice depends on the NFRs
gathered in Mode 1, not on which pattern is currently fashionable.

## Contents
- Monolith vs. services
- Synchronous request/response vs. event-driven
- Shared-nothing vs. shared-state
- Build vs. adopt (pattern-level, not implementation-level)

## Monolith vs. services

| Ask | Favors monolith | Favors services |
|---|---|---|
| Team count/size | One team | Multiple teams needing independent deploy cadence |
| Scaling need | Uniform across the app | One hot path needs to scale independently |
| Data consistency | Strong, cross-domain transactions common | Domains genuinely independent, eventual consistency acceptable |
| Operational maturity | Limited ops capacity | Has the platform investment (observability, on-call, deploy automation) to run N services |

A monolith with clean internal module boundaries is a legitimate, often better, choice
for a single team — not a stepping stone that must eventually become services.

## Synchronous request/response vs. event-driven

| Ask | Favors sync | Favors event-driven |
|---|---|---|
| Caller needs the result now | Yes | No — fire-and-forget or eventual is fine |
| Failure handling | Caller can retry directly | Need durable retry/backoff/dead-letter handling |
| Coupling cost | Direct dependency acceptable | Producer shouldn't need to know every consumer |

Event-driven adds a real operational cost (a broker, delivery-guarantee semantics,
debugging a flow that's no longer a single call stack) — don't reach for it just because
it "decouples," reach for it when the coupling cost of sync calls is the actual problem.

## Shared-nothing vs. shared-state

- Shared-nothing (each instance/component independent, coordination only through
  external stores or messages) scales more predictably and fails more predictably.
- Shared-state (in-memory coordination, sticky sessions, local caches as source of truth)
  is simpler until an instance dies or the system needs to scale past one node.
- If a component claims to be "horizontally scalable" verify it has no in-memory state
  that isn't replicated or externalized — this is the single most common gap between a
  documented scaling strategy and what the deployment actually does.

## Build vs. adopt (pattern-level, not implementation-level)

- A load-bearing pattern borrowed from another BQP component (see `breachsafe-pqc-pm`'s
  reuse-review criteria) still needs its own trade-off statement here — reuse is a
  starting point for the analysis, not a substitute for it.
- Prefer standard, externally-legible contracts at integration boundaries (the same
  principle `breachsafe-pqc-pm`'s integration doctrine applies platform-wide) over a
  proprietary pattern that only this component understands.
