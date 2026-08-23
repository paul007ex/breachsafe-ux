<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Why the verdict has three states

Most tool UIs report two outcomes: pass or fail. EnXemble reports three, and the third one is
the whole point. This page explains why the host fails closed and never shows a false green. For
the states themselves, see the [badge reference](../reference/badge.md); for the states in a
first run, see [your first run](../tutorials/your-first-scan.md).

## The two-state trap

A pass/fail badge silently conflates two very different situations:

- the validator ran and rejected the artifact, and
- the validator could not run at all.

If both collapse into "fail", a missing validator looks the same as a real rejection — annoying,
but at least not dangerous. The dangerous version is the opposite: when a tool crashes, produces
nothing, or the validator is absent, and the UI shows **green** anyway because "no error was
reported". That is a false green, and in a compliance or security context it is the worst
possible outcome — it tells you something was checked and passed when nothing was checked at all.

## The third state

EnXemble adds `VALIDATOR-UNAVAILABLE` precisely so that "could not run" can never masquerade as a
pass:

- `VALID` — the validator ran and accepted the artifact.
- `INVALID` — the validator ran and rejected the artifact.
- `VALIDATOR-UNAVAILABLE` — the tool or the validator could not run.

A crashed tool, a missing dependency, a Docker daemon that is down, a timeout, or an empty run
all resolve to `VALIDATOR-UNAVAILABLE`. A green appears only when a real external validator
really accepted a real artifact.

## Fail-closed, by construction

The host derives the state from the descriptor's badge rule, and the rule is fail-closed:

- an empty or unmatched condition never passes;
- a run that produces no artifact does not badge green;
- a descriptor that declares no validator for a given output badges `none` (an honest "nothing
  was checked"), not a pass.

The state is also carried as **text**, not colour alone — colour is a redundant cue — so the
verdict survives a screenshot, a colour-blind reader, or a monochrome print.

## The host defends the state, not the meaning

The host defends only the three-state verdict; it does not compute a domain judgement. A tab may
show a plain-language summary or reword a state, but that text is declared in the tool's
descriptor and mapped over the badge state or an artifact value — the host never invents it. This
separation keeps the verdict trustworthy across every tool. See
[the host↔descriptor boundary](host-descriptor-boundary.md).
