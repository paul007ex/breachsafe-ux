<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

## Summary

<!-- One paragraph describing what this PR does and why. -->

## Type of change

<!-- Check exactly one. One thing per PR. -->

- [ ] feat — new feature
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] test — test changes only
- [ ] refactor — internal restructure, no behavior change
- [ ] build — build/dependency change
- [ ] ci — CI/workflow change
- [ ] chore — other maintenance
- [ ] perf — performance improvement
- [ ] security — security fix or hardening

## Related issue

<!-- Link to the issue this PR addresses. If none, explain why. -->

Fixes #

## Decisions made

<!-- List every micro-decision a future maintainer would ask "why did they do
     that?" about. One line each. -->

-

## Quality gates

<!-- Run each command or `just`-style local gate. State PASS / FAIL / NOT RUN with reason. -->

- [ ] `uv run ruff check src tests` — PASS / FAIL / NOT RUN:
- [ ] `uv run ruff format --check .` — PASS / FAIL / NOT RUN:
- [ ] `uv run mypy src` — PASS / FAIL / NOT RUN:
- [ ] `uv run pytest tests/ -q` — PASS / FAIL / NOT RUN:
- [ ] `uv run python -m build` — PASS / FAIL / NOT RUN:
- [ ] `uvx --from 'reuse[charset-normalizer]' reuse lint` — PASS / FAIL / NOT RUN:

## Checklist

### Scope

- [ ] One thing per PR
- [ ] No out-of-scope work bundled in
- [ ] Changes respect the host/descriptor boundary (see `docs/adr/`)

### Code

- [ ] New first-party files carry the SPDX header (`reuse lint` passes)
- [ ] The three-state verdict is preserved: no green result the validator did not give
- [ ] No `print()` in library code (only output adapters and the CLI write to stdout)

### Tests

- [ ] Every new function with non-trivial logic has at least one test
- [ ] Error paths and boundary values are tested, not just happy paths

### Documentation

- [ ] `CHANGELOG.md` updated under `[Unreleased]` if this PR changes user-visible behavior
- [ ] Internal documentation links verified (point at real files / real anchors)

### Dependencies

<!-- Only relevant if pyproject.toml or uv.lock changed. -->

- [ ] Every new dependency justified (actively maintained, redistribution-compatible license, recognizable maintainer)
- [ ] No GPL, AGPL, or LGPL dependencies introduced

### Security exceptions

<!-- Only if a security rule is being waived. Permanent exceptions are forbidden. -->

- [ ] No security exception in this PR
- [ ] Security exception accepted, documented as `SECURITY EXCEPTION ACCEPTED: <rule>, because <reason>, expires <date or issue>`

## Reviewer notes

<!-- Anything you want the reviewer to focus on. Out-of-scope flags. Open questions. -->

-

---

By submitting this PR I confirm:

- [ ] I read [`CONTRIBUTING.md`](../CONTRIBUTING.md) before writing this code
- [ ] I am the author of this code, or it is sourced with provenance and terms compatible with this release (Apache-2.0)
