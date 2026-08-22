# ADR authoring (Mode 3)

One decision per record. Written when the decision is made, not reconstructed afterward
to justify something that already shipped — a retroactive ADR should say so explicitly
("written after the fact to document an existing decision") rather than reading as if it
preceded the code.

## Contents
- Template
- Status
- Context
- Decision
- Alternatives considered
- Consequences
- Revisit when
- Rules

## Template

```markdown
# ADR-NNN: <short, decision-stated title, not a topic>

## Status
Proposed | Accepted | Superseded by ADR-MMM

## Context
What forces are in tension. State the NFRs/constraints from `system-design-workflow.md`
that this decision has to satisfy — not a narrative, the actual constraints.

## Decision
The decision, stated plainly, one sentence if possible.

## Alternatives considered
At least two real alternatives with their actual costs (not strawmen). If only one
alternative is listed, either the search was too shallow or say explicitly why no other
option was viable.

## Consequences
What gets harder, what gets easier, both directions. A consequences section that only
lists benefits is incomplete.

## Revisit when
The condition that would make this decision worth reopening (a load threshold, a team
size, a deprecation date) — not "never," almost nothing is permanent.
```

## Rules

- **Status transitions are explicit.** A "Proposed" ADR is not authorization to build;
  don't treat drafting one as if it were "Accepted." Marking one "Accepted" without the
  authorization this library already requires for write actions is itself a boundary
  violation.
- **Superseding, not editing.** When a decision changes, write a new ADR that supersedes
  the old one and update the old one's status — never silently rewrite history by editing
  an already-accepted ADR's Decision section.
- **Numbering is per-component**, following whatever sequence that component's own
  `docs/adr/` (or equivalent) already uses — check first rather than assuming ADR-001.
- **No decision without a stated alternative.** An ADR that only describes the chosen
  path and never names what else was considered isn't a decision record, it's an
  announcement.
