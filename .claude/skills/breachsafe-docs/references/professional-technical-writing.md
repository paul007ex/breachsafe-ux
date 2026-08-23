# BreachSAFE Professional Technical Writing Standard

This reference defines the writing standard for BreachSAFE product, security,
architecture, reference, and release documentation. It is intended for technical
readers who need reliable facts, executable procedures, and traceable evidence.

## Contents

1. [Purpose](#purpose)
2. [Source order](#source-order)
3. [Claim classes](#claim-classes)
4. [Document architecture](#document-architecture)
5. [Section design](#section-design)
6. [Sentence and paragraph rules](#sentence-and-paragraph-rules)
7. [Terminology and capitalization](#terminology-and-capitalization)
8. [Punctuation and formatting](#punctuation-and-formatting)
9. [Banned filler and slop](#banned-filler-and-slop)
10. [Evidence language](#evidence-language)
11. [Command and output examples](#command-and-output-examples)
12. [Tables and diagrams](#tables-and-diagrams)
13. [Accessibility and navigation](#accessibility-and-navigation)
14. [Review checklist](#review-checklist)

## Purpose

Documentation must let a reader answer four questions without reading source code:

1. What capability is available in the shipped artifact?
2. What inputs, outputs, limits, and failure states define it?
3. Which command or configuration produces the described behavior?
4. What evidence supports the claim, and what remains unverified?

Write for a practitioner who is evaluating, installing, operating, integrating, or
auditing the product. State the contract before the rationale. Put limitations beside
the capability they qualify.

## Source order

Resolve conflicting statements using this order:

1. Executable behavior from the final artifact under review
2. Normative standards and pinned schemas
3. Tests that exercise the public contract
4. Accepted ADRs and issue acceptance criteria
5. Repository metadata and release records
6. Existing documentation
7. Scratch notes, handoffs, and planning prose

When the sources disagree, record the discrepancy and correct the lower authority.
Never silently convert an intended design into a shipped claim.

## Claim classes

Mark claims internally during review as one of these classes:

| Class | Meaning | Permitted wording |
| --- | --- | --- |
| Shipped | Present in the artifact and part of the supported interface | “QuReddy provides…” |
| Verified | Exercised by a named command, fixture, schema, or external target | “The release check verified…” |
| Designed | Accepted design with implementation still incomplete | “The accepted design specifies…” |
| Planned | Tracked work with no accepted implementation | “Issue #N tracks…” |
| Blocked | Required work cannot proceed because a named dependency or decision is absent | “The rehearsal remains blocked by…” |
| Historical | Retained for traceability and no longer current | “The previous release used…” |
| Unknown | The available evidence cannot establish the result | “The current evidence does not establish…” |

Do not use present tense for designed, planned, blocked, or historical behavior.

## Document architecture

Use the smallest document that fully serves its audience. A product documentation set
should normally contain:

| Area | Required content |
| --- | --- |
| Orientation | Product purpose, supported surfaces, status, and quick navigation |
| Tutorial | One verified first-use path from a clean installation |
| How-to | Goal-oriented procedures for scans, formats, troubleshooting, and evidence |
| Reference | Commands, options, schemas, fields, exit codes, environment variables |
| Explanation | Architecture, trust boundaries, design decisions, limitations |
| Security | Threat model, data handling, dependencies, reporting boundaries |
| Operations | Installation, upgrades, diagnostics, reproducible release checks |
| Contribution | Local workflow, quality gates, review rules, issue process |
| Release | Version history, artifact evidence, compatibility, publication procedure |

Keep tutorial, how-to, reference, explanation, contributor, and release material in
separate pages. A README may orient and link; it should not become an unbounded manual.

## Section design

Use a predictable order within a page:

1. Scope and audience
2. Outcome or contract
3. Prerequisites
4. Procedure or interface
5. Examples
6. Failure states and limits
7. Evidence and verification
8. Related references

Every heading must answer a reader question. Avoid headings that only describe the
author’s activity, such as “What We Did” or “Why This Matters.”

## Sentence and paragraph rules

- Write in the register of a senior platform engineer or architect documenting for peers:
  precise, declarative, and assuming technical fluency. No marketing, sales, or motivational
  tone. State the fact or procedure; do not sell it.
- Prefer one main idea per sentence.
- Use active voice when the actor is known.
- Use present tense for current behavior and past tense for recorded evidence.
- Put the subject and verb near the start of the sentence.
- Prefer concrete nouns and precise verbs.
- Define an abbreviation at first use, then use the short form consistently.
- Keep paragraphs to one claim or one procedure step.
- Use a numbered list for an ordered procedure and a table for exact mappings.
- Use “must” for a requirement, “may” for permission, and “can” for capability.
- Avoid rhetorical questions, jokes, metaphors, anthropomorphism, and motivational prose.
- State the technical fact, decision, or procedure directly. Avoid contrast constructions
  such as “this, not that,” “not X but Y,” and “rather than X, Y” when the first clause
  adds no boundary needed for correctness or safety.
- Use a contrast only when it records a real boundary, rejected alternative, compatibility
  condition, or security constraint. Name the boundary and its evidence.
- Remove meta-commentary that announces importance, clarity, or completeness instead of
  supplying the relevant fact.

## Terminology and capitalization

Use product names exactly as registered: BreachSAFE, QuReddy, Qurum, QuCrypt,
QuCert, and QuCustody. Use “CycloneDX” and “PyPI” with their official capitalization.
Use sentence case for headings unless a repository style guide explicitly requires
another convention. Use code formatting for commands, identifiers, option names,
environment variables, paths, field names, schema versions, and issue numbers.

Prefer one term for one concept. For example, use “target” for the remote endpoint,
“collector tool” for local OpenSSL, “observation” for captured evidence, and “finding”
for an interpreted result. Do not use “asset,” “endpoint,” and “target” as synonyms in
the same contract.

## Punctuation and formatting

- Do not use em dashes, en dashes, double hyphens, or decorative dash separators.
- Use a period, colon, semicolon, or a new sentence instead.
- Use hyphens only inside established technical compounds, package names, flags, and
  identifiers where the spelling requires them.
- Use Markdown headings in a single hierarchy with no skipped levels.
- Include a blank line before lists and after headings.
- Use fenced code blocks with a language tag when syntax is known.
- Keep tables narrow enough to read on a normal laptop viewport.
- Avoid bold text for ordinary emphasis. Reserve it for labels in tables or warnings.
- Never place secrets, live tokens, private keys, or unredacted headers in examples.

## Banned filler and slop

Remove these words or phrases unless they have a precise technical meaning in context:

| Category | Avoid |
| --- | --- |
| Inflated importance | crucial, pivotal, groundbreaking, transformative, game changing, vital |
| Vague motion | leverage, empower, unlock, elevate, streamline, foster, harness |
| Research theater | delve, deep dive, landscape, tapestry, ecosystem, journey |
| Unsupported praise | robust, seamless, elegant, comprehensive, world class, best in class |
| Generic conclusions | in conclusion, overall, ultimately, moving forward, at the end of the day |
| Artificial transitions | moreover, furthermore, additionally, notably, importantly |
| Template claims | designed to, built to, aims to, allows you to, helps you to |
| Empty nouns | functionality, solution, framework, paradigm, approach, methodology |
| Slop markers | it is worth noting, it should be noted, this demonstrates, this highlights, testament |
| Decorative closure | “This is more than…”, “not just… but…”, “from X to Y”, “whether you are…” |
| Negative parallelism | “this, not that”, “not X but Y”, “rather than X, Y” when no technical boundary is being stated |
| Rhetorical virtue | honesty, honest, truth, truthful, authentic, genuine, real, transparent, trustworthy used as praise instead of a verifiable property. State the checked fact and its source; do not assert the virtue. |

This table is a review trigger, not a blind replacement list. Retain a term when it is
required by a standard, API name, product name, or precise technical statement. Replace
vague praise with evidence. Replace vague verbs with the operation performed. Replace a
generic conclusion with the decision or result.

## Evidence language

Tie every material claim to a source:

| Evidence | Wording pattern |
| --- | --- |
| Local deterministic test | “`command` passed with exit code `0` in…” |
| Installed artifact | “Wheel `<hash>` installed into a fresh Python `<version>` environment…” |
| Live target | “The target returned `<observed result>` on `<date>`; this observation is supplementary…” |
| Standards validator | “Final bytes passed `<validator>` version `<version>` against schema `<digest>`…” |
| Missing evidence | “No release evidence is recorded for…” |

Separate observation, interpretation, and decision. A successful network connection is
an observation. A protocol classification is an interpretation. A release gate result
is a decision based on both plus the acceptance criteria.

## Command and output examples

Every command example must identify prerequisites and expected result. Prefer a complete
command that can be copied from a clean checkout or installed environment. State whether
the example requires network access, OpenSSL, credentials, a service, or a particular
platform.

For machine output examples, document all three streams:

| Field | Requirement |
| --- | --- |
| Exit code | Match the public failure contract |
| stdout | One parseable document for JSON and CBOM modes |
| stderr | Human diagnostics only when the documented mode permits them |

Do not use ellipses in JSON, CBOM, YAML, or shell output that a reader is expected to
copy. Redact values explicitly and preserve valid syntax.

## Tables and diagrams

Use a table for repeated exact comparisons, mappings, status matrices, or compatibility
data. Use a diagram only when ownership, sequence, or dependency is materially easier to
understand visually. Every diagram needs a nearby text explanation and a plain text path.

Do not use a diagram to decorate a short procedure. Keep labels concrete and avoid
unexplained abbreviations.

## Accessibility and navigation

- Use descriptive link text.
- Do not use “click here.”
- Keep heading anchors stable after publication.
- Give images meaningful alternative text.
- Keep color from being the only status signal.
- Provide a full contents section for documents longer than three major sections.
- Link every page back to its documentation index.
- Test links from the repository location where readers will see them.

## Review checklist

### Truth

- [ ] Every shipped claim appears in code, tests, or a verified artifact.
- [ ] Planned and blocked work is labeled with its issue and dependency.
- [ ] Unknown results remain unknown.
- [ ] Versions, links, commands, options, and schema names match the final artifact.

### Structure

- [ ] The page has a clear audience and outcome.
- [ ] Content is in the correct Diátaxis area.
- [ ] The contents section matches headings and anchors.
- [ ] Navigation links resolve.

### Style

- [ ] Sentences are direct and concrete.
- [ ] Banned filler was reviewed and removed where it adds no technical meaning.
- [ ] No em dash, en dash, double hyphen, decorative separator, or rhetorical padding remains.
- [ ] Product names and technical terms use the approved spelling.

### Evidence

- [ ] Safe examples were executed from the intended installation surface.
- [ ] Exit code, stdout, and stderr were checked separately.
- [ ] External and mutable observations are labeled with date and scope.
- [ ] Secrets and volatile identifiers are absent or redacted.
- [ ] Remaining unverified claims are listed in the handoff.
