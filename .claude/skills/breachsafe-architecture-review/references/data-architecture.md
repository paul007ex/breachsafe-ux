# Data-store and schema architecture (Mode 6)

Design-level only. Choosing the partitioning strategy is this skill's job; running
`EXPLAIN ANALYZE` against a live query and tuning an index is `breachsafe-implement`'s.

## Contents
- Relational vs. document vs. columnar
- Normalization trade-offs
- PostgreSQL-specific architectural decisions
- When the answer is "not PostgreSQL"

## Relational vs. document vs. columnar

- Relational (PostgreSQL as the default BQP choice unless stated otherwise): data has
  clear entities and relationships, needs transactional consistency across them, query
  patterns aren't known fully in advance. Normalize first; denormalize only against a
  measured read pattern, not speculatively.
- Document store: data is naturally nested/schema-variable per record, accessed mostly
  by a single key, relationships between documents are rare or handled at the
  application layer.
- Columnar/analytical store: workload is read-heavy aggregation over large volumes
  (reporting, analytics), not transactional per-row access.
- A system that needs both transactional and analytical access patterns often needs two
  stores (OLTP + a read-replica or ETL'd analytical store), not one store stretched to
  do both badly.

## Normalization trade-offs

- Normalize to eliminate update anomalies by default. Denormalize a specific, measured
  hot read path — and state which normalized form it's giving up and why the read
  frequency justifies the write/consistency cost.
- A denormalized field needs an explicit owner and update path; an unowned denormalized
  copy is how data quietly goes stale.

## PostgreSQL-specific architectural decisions

These are commitments made at design time, not implementation-time tuning:

- **Partitioning strategy** — range (time-series, append-heavy), list (discrete
  categories), or hash (even distribution, no natural range/list key). Decide the
  partition key against the actual query/retention pattern (e.g., a time-range partition
  key is only useful if most queries and the retention policy both filter on that range).
- **Replication topology** — streaming replication for read scaling and failover
  (replicas are physical copies, simplest to reason about); logical replication when
  a subset of tables needs to flow to a different schema/version or a different system
  entirely (e.g., feeding an analytical store). Decide failover ownership (who promotes a
  replica, how) as part of the design, not as an incident-time improvisation.
- **Extension adoption** (PostGIS, pgvector, pg_trgm, etc.) is a design commitment with
  an operational cost (upgrade coordination, backup/restore compatibility, hosting
  provider support) — treat it the same as adopting a new dependency elsewhere in the
  platform, not a free feature flag.
- **Multi-tenancy shape**, if applicable — separate database per tenant (strongest
  isolation, highest operational overhead), separate schema per tenant, or shared
  tables with a tenant-id column and row-level security. State the isolation requirement
  driving the choice explicitly; this is a security-architecture decision as much as a
  data one, and the trust boundary it creates belongs on the DFD (`data-flow-diagrams.md`).

## When the answer is "not PostgreSQL"

State explicitly what requirement PostgreSQL can't meet before recommending an
alternative — "team familiarity with X" is a real factor but a different one than "the
access pattern doesn't fit a relational model." Conflating the two produces a
recommendation nobody can evaluate.
