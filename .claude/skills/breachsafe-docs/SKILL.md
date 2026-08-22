---
name: breachsafe-docs
description: Create, repair, and release-proof documentation in BreachSAFE repositories. Use when updating README, CLI/reference docs, tutorials, how-to guides, architecture explanations, ADR ledgers, changelogs, badges, release notes, issue/PR links, or repository guidance after product behavior has shipped or changed. Reconciles prose against executable product evidence and preserves Diátaxis placement; it is not a generic copywriting skill.
---

# breachsafe-docs

Make repository documentation a truthful, executable view of the shipped product.

## Contents
- Authorization gate
- Stay in its lane
- Workflow
- Release-document rules
- Anti-patterns
- Deliverable

## Authorization gate

May inspect code, issues, standards, built artifacts, and docs; may edit local documentation
when the user asks for a docs change. Never commits, pushes, opens a PR, publishes release
notes, or posts tracker content without explicit authorization for that action. Run examples
only when safe and non-destructive.

## Stay in its lane

- Audit-only doc drift belongs to `breachsafe-quality-review` Mode 4.
- Product implementation belongs to `breachsafe-implement`.
- Release mechanics and registry criteria belong to `breachsafe-release`.
- Architecture and milestone decisions belong to `breachsafe-pqc-pm`.
- This skill owns the local documentation repair after those authorities establish truth.

## Workflow

1. Read repository instructions, the applicable ADRs, public CLI/API/schema, tests, issues,
   changelog, and current Git status.
2. Build a source-of-truth map before editing. Prefer standards and executable behavior over
   issues, roadmap prose, handoffs, or scratch.
3. Classify each claim as shipped, verified, designed, planned, blocked, or historical.
   Preserve `UNKNOWN`; never promote intent into fact.
4. Place content by Diátaxis: tutorial = learning path, how-to = goal recipe, reference =
   exact contract, explanation = rationale. Keep contributor/process docs separate.
5. Execute every safe command example against a built artifact in an isolated temporary
   environment. Never add test-only behavior to production code to make docs pass.
6. Update the smallest coherent documentation slice. Keep product identity, versions,
   badges, commands, output formats, exit codes, schema versions, and milestone status
   single-sourced where possible.
7. Verify internal links and anchors, issue/PR repository ownership, ADR identifiers/status,
   changelog/version/tag coherence, Markdown formatting, and the documented clean-install
   path.
8. Run the repository doc checks plus the truth-gate checklist in
   [repository-doc-truth-gate.md](references/repository-doc-truth-gate.md).
9. Apply the prose and structure rules in
   [professional-technical-writing.md](references/professional-technical-writing.md).

## Release-document rules

- A changelog entry names observable user behavior and links the correct issue and PR in the
  correct repository. A live but unrelated issue link is worse than a 404.
- Do not claim PyPI, TestPyPI, Docker, signatures, provenance, badges, or platform support
  until the corresponding artifact or external setting is verified.
- Use commit-to-commit compare links when release tags have unrelated history.
- Keep examples free of volatile IDs, timestamps, durations, and network-dependent verdicts
  unless explicitly labeled as illustrative captures.
- Document limitations beside the capability they constrain, not only in a roadmap.

## Anti-patterns

- Editing prose from a stale handoff without checking code.
- Describing shipped capability as planned, or planned capability as shipped.
- Copying CLI help, enums, issue numbers, counts, or versions into many files without a
  drift check.
- Mixing tutorial, reference, architecture, and contributor policy in one page.
- Rewriting product behavior to satisfy documentation.
- Testing an editable checkout when the docs promise an installable distribution.
- Hiding broken examples behind `skip`, ellipses, or unmarked aspirational text.
- Renumbering or deleting historical ADRs to conceal collisions; preserve history and record
  supersession.

## Deliverable

Report changed files, truth sources, commands/examples executed with exit codes, link and
Markdown checks, claims intentionally left unverified, and any release wording still blocked
on external evidence.
