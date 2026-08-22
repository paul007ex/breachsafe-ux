# Multi-reviewer / arbiter workflow (Mode 2 extension)

For a repo where more than one agent (multiple Claude sessions, Codex, a human) may
review the same issue or PR concurrently. Generalized from QuReddy's
`python-oss-crypto-reviewer` skill, which had this fully worked out before this pattern
existed anywhere in the canonical library — verify against that repo's live convention
before assuming these exact label strings if you're working in QuReddy specifically.

## Contents
- Why this exists
- Two modes, same standards
- Verdict and decision vocabulary
- Record-keeping rules
- Adopting this in a new repo

## Why this exists

Without it, N reviewers post N contradictory comments and nothing tells the merge gate
(CI or a human) which one is binding. The pattern splits review into two tiers so
multiple opinions can coexist without blocking on consensus, but exactly one signal
gates merge.

## Two modes, same standards

| Mode | Who runs it | Verdict means | Labels applied |
|---|---|---|---|
| **Reviewer** (default) | Any reviewer — any agent instance, any human | Recommendation, non-binding | `review:<role>-<instance>:<verdict>` |
| **Arbiter** | One designated role per repo (state which, in the repo's own governance doc — don't assume Codex, don't assume the same role across repos) | Binding, gates merge | `arbiter:<role>:<verdict>` + `decision:<outcome>` |

**Instance suffixing** — if the same agent type can run multiple concurrent sessions on
one repo (e.g. two Claude sessions reviewing in parallel), each needs a distinct label
suffix (`review:claude-1:*`, `review:claude-2:*`) so they don't overwrite each other's
label. A bare `review:claude:*` is ambiguous the moment two sessions run at once.

Reviewer mode runs freely, any number of times, from any reviewer — none of them gate
merge. Arbiter mode runs once relevant reviewers have weighed in (or after a stated
timeout), reads every prior reviewer comment, settles disagreements explicitly (quote
each position, state which prevails or synthesize a third, cite the rule/test that
justifies the call — never "both have a point, going with X" with no reason), and
produces the one binding decision. If arbiter and a reviewer disagree on a real
correctness/security invariant and the reviewer was right, the arbiter concedes with a
one-line acknowledgment and adopts the reviewer's verdict as binding — arbitration is a
deliberate bottleneck, not a rubber stamp, and being slow and right beats being fast and
wrong.

## Verdict and decision vocabulary

Verdicts: `approve`, `approve-with-changes`, `reject`. Decision outcomes (arbiter only):
`approved`, `needs-changes`, `rejected`. Keep these two vocabularies distinct in the
label scheme — a reviewer's `approve` is advisory, only the arbiter's `decision:approved`
is binding.

## Record-keeping rules

- Post each review as a structured comment ending in a signature block (role, reviewer
  identity, verdict, date) so the audit trail ties back to a known reviewer
  unambiguously.
- Never edit a prior review comment — supersede with a new one, same as ADRs
  (`adr-authoring.md` in `breachsafe-architecture-review` follows the identical
  supersede-don't-edit rule).
- Never remove another reviewer's label when arbitrating — the arbiter's label sits
  alongside prior reviewer labels as the audit trail, not in place of them.
- If a review needs more than roughly 50 lines of justification, it's stopped being a
  review and become a decision record — write it as an ADR or a long-form doc instead
  and link it from the issue/PR comment.

## Adopting this in a new repo

1. Confirm the repo actually has enough concurrent-reviewer traffic to need two tiers —
   a repo with one steady reviewer doesn't need arbiter labels at all; don't add process
   overhead a repo's actual review volume doesn't justify.
2. Name the arbiter role explicitly in that repo's own governance doc (a `CLAUDE.md`
   Governance section or equivalent) — this skill does not assume who arbitrates.
3. Create the six labels (`review:<role>:{approve,approve-with-changes,reject}`,
   `arbiter:<role>:{approve,approve-with-changes,reject}`) plus the three binding
   `decision:{approved,needs-changes,rejected}` labels via `gh label create`, matching
   that repo's own naming, not copied verbatim from another repo.
