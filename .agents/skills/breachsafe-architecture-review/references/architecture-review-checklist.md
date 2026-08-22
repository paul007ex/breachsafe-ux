# Architecture review checklist (Mode 2)

For a system that already exists. The job is to evaluate the structure that's actually
there against what it claims to need — not against a generic "best practice" list.

## Contents
- Component boundaries and ownership
- Coupling and cohesion
- Scalability, against stated load
- Security-architecture placement
- Technical debt

## Component boundaries and ownership

- Does each component have a single, statable reason to exist? A component whose job
  can't be described in one sentence without "and" is a boundary smell.
- Who owns each piece of data — is there exactly one writer per data domain, or do
  multiple components write the same table/topic/state?
- Where does a change in one component force a change in another that has no obvious
  reason to care? That's coupling worth naming, not just noting.

## Coupling and cohesion

- Trace one real request/data path end to end. Count how many components it touches and
  whether each hop is necessary or incidental (grew there historically, no longer needed).
- Look for cyclic dependencies between components — a real defect, not a style nit.
- Distinguish coupling that's inherent to the domain (two things that must change
  together because the business rule requires it) from coupling that's accidental
  (they change together only because of how the code happens to be organized).

## Scalability, against stated load

- Get the actual current and projected load numbers before assessing scalability — a
  scalability opinion with no load figure behind it is a guess dressed as an assessment.
- Identify the actual bottleneck component (the one that would break first under 10x
  load), not a generic "the database might be slow" statement.
- Check whether the scaling strategy claimed in docs/ADRs matches what the current
  deployment topology can actually do (e.g., a doc says "horizontally scalable" but the
  component holds in-memory state with no replication).

## Security-architecture placement

This is *placement*, not crypto-correctness (`breachsafe-security-audit` owns that):

- Where does authentication happen, and is there exactly one place, or does trust get
  re-established inconsistently across components?
- Where do secrets/credentials live, and does every component that needs one get it
  through the same mechanism?
- Where do trust boundaries cross component or network lines? Mark them — this feeds
  directly into `data-flow-diagrams.md` and the STRIDE pass `breachsafe-security-audit`
  runs from that diagram.

## Technical debt

- Distinguish "outdated but load-bearing and risky to touch" from "outdated and safe to
  modernize incrementally" — the remediation priority differs completely between the two.
- Look for a pattern that was correct for the system's original scale/team size and is
  now wrong for its current one (the most common source of real architectural debt,
  as opposed to just old code).
- State the actual cost of leaving something as-is (an incident that already happened, a
  velocity tax that's measurable) rather than a generic "this could cause problems."
