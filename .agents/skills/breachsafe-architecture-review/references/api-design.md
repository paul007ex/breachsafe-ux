# API contract design (Mode 5)

Contract-level design only. Writing the OpenAPI/proto file, generating server stubs, and
implementing handlers is `breachsafe-implement`'s job — this mode decides the shape those
files will have to conform to.

## Contents
- Resource modeling
- Versioning and evolution
- Pagination
- Error contract
- Authentication and authorization surface

## Resource modeling

- Model nouns (resources), not verbs. `/users/{id}/deactivate` (POST) beats
  `/deactivateUser?id=`. If an operation genuinely isn't resource-shaped (a bulk import, a
  computation trigger), say so explicitly and choose a deliberate action-endpoint pattern
  rather than forcing it into a fake resource.
- One writer per resource, matching the "one writer per data domain" check in
  `architecture-review-checklist.md` — if two services can write the same resource, the
  API design and the data-ownership design disagree with each other.
- Decide REST vs. GraphQL vs. gRPC against actual client needs (many independent clients
  with varying data needs → GraphQL's flexibility earns its complexity; internal
  service-to-service with strict schemas and low latency needs → gRPC; general external
  API surface → REST remains the safest default for broad client compatibility).

## Versioning and evolution

- Decide the versioning strategy (URI path, header, or content-negotiation-based) before
  the first client integrates — retrofitting versioning after clients exist is far more
  expensive than choosing wrong up front.
- Additive changes (new optional field, new endpoint) don't need a version bump; anything
  that changes a client's existing expectation does. State which category a given change
  falls into rather than treating all changes as equally breaking or equally safe.
- A deprecation needs a stated sunset date and a migration path communicated before
  removal, not just a changelog entry after the fact.

## Pagination

- Every collection endpoint gets a pagination decision at design time, not "we'll add it
  when it's slow." Cursor-based for large/frequently-mutated collections (stable under
  concurrent writes); offset-based only for small, rarely-changing collections where
  simplicity outweighs the drift risk.
- State the page-size default and maximum explicitly — an unbounded collection endpoint
  is a scalability gap, not a convenience.

## Error contract

- One consistent error shape across the whole API (RFC 7807 problem-details is a
  reasonable default) — inconsistent error shapes between endpoints is one of the most
  common, most avoidable API design defects.
- Error responses need to be actionable: what went wrong, and for client errors, what the
  caller can do about it. A bare `{"error": "failed"}` is not a contract.
- Decide which errors are retryable and say so in the contract (a `Retry-After` header, a
  documented retryable-error-code list) — don't leave clients to guess.

## Authentication and authorization surface

- State where auth is enforced (gateway vs. each service) — this needs to agree with the
  "where does authentication happen" check in `architecture-review-checklist.md`, not
  contradict it.
- Document required scopes/permissions per endpoint as part of the contract, not as a
  separate document that can drift from the actual API.
