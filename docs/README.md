<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# EnXemble documentation

This directory follows **[Diátaxis](https://diataxis.fr)**. Each page belongs to one of four
quadrants and has one job: tutorials teach, how-to guides solve a goal, reference states the
exact contract, and explanation gives the rationale.

Every page describes the **host** — the generic, config-driven UX host for command-line tools —
not any one tool. The packaged `qureddy-ux` image appears only as a labelled shipped reference
example; for what that specific scanner does, see the
[`breachsafe/qureddy` documentation](https://github.com/breachsafe/qureddy).

## Contents

1. [The four quadrants](#1-the-four-quadrants)
2. [Tutorials](#2-tutorials)
3. [How-to guides](#3-how-to-guides)
4. [Reference](#4-reference)
5. [Explanation](#5-explanation)
6. [Contributor documentation](#6-contributor-documentation)
7. [Decision records and known issues](#7-decision-records-and-known-issues)

## 1. The four quadrants

|  | Theoretical (concept) | Practical (action) |
|---|---|---|
| **Studying** (learning) | [Explanation](explanation/) | [Tutorials](tutorials/) |
| **Working** (doing) | — | [How-to guides](how-to/) and [Reference](reference/) |

## 2. Tutorials

Learning-oriented walkthroughs for someone new to the host.

- [Your first run](tutorials/your-first-scan.md) — launch the host, run a tool, read the verdict.

## 3. How-to guides

Task-oriented recipes for someone who already knows the basics.

- [Run a tool-UX image with Docker](how-to/run-with-docker.md)
- [Run the host from source](how-to/run-from-source.md)
- [Add a tool (write a descriptor)](how-to/add-a-tool.md) — the core recipe, with a generic
  example tool.
- [White-label the branding](how-to/white-label-branding.md)
- [Enable or hide optional tabs](how-to/enable-optional-tabs.md)

## 4. Reference

Look-it-up information. Comprehensive, accurate, dry.

- [Descriptor schema](reference/descriptor-schema.md) — every descriptor field.
- [Descriptor tokens](reference/descriptor-tokens.md) — the argv substitution namespace.
- [Environment variables](reference/environment-variables.md) — every host setting.
- [Execution backends](reference/execution-backends.md) — local binary, Docker image, fallback.
- [The three-state badge](reference/badge.md) — the verdict contract.
- [CLI reference](reference/cli.md) — `breachsafe-ux` and `--check`.

## 5. Explanation

Conceptual discussion. Why the host is built the way it is.

- [Architecture](explanation/architecture.md) — the MVC engine and theme, with a component-coupling graph.
- [The Gradio shell](explanation/the-gradio-shell.md) — the web-UI framework edge and the type→widget map.
- [The host↔descriptor boundary](explanation/host-descriptor-boundary.md) — the ADR-0002 thesis.
- [Why the verdict has three states](explanation/three-state-verdict.md) — fail-closed by design.
- [Why the host is agnostic](explanation/why-agnostic.md) — the design thesis.
- [The threat model](explanation/threat-model.md) — the operator-owned trust boundary, no-shell argv, fail-closed validation, and the accepted risks.

## 6. Contributor documentation

The rules for working *on* the host, kept separate from user-facing docs.

- [Coding rules](contributors/coding-rules.md)
- [The local release gate](contributors/local-release-gate.md)
- [Review process](contributors/review-process.md)

See also [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## 7. Decision records and known issues

- [Architecture decision records](adr/) — the settled decisions (0001–0003).
- [Known issues](KNOWN-ISSUES.md)

## Editorial rules

1. **One quadrant per page.** If a page does two jobs, split it.
2. **Host, not tool.** Every page describes the host generically; a specific tool appears only as
   a labelled example, and tool-specific detail links out to that tool's own docs.
3. **Tutorials never reference; reference never explains.** A pointer is fine; mixing content is
   not.
4. **Explanation has no commands.** Worked commands belong in tutorials or how-to guides.
5. **Every command is executed against the real product** before it is documented.
6. **Front-load the answer.** Each page opens with what it covers in one or two sentences.
