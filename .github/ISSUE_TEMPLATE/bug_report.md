<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
---
name: Bug report
about: Something is broken or behaves unexpectedly
title: "[bug] "
labels: ["bug", "triage"]
assignees: []
---

## Summary

<!-- One sentence describing the bug. -->

## Severity

- [ ] **Security vulnerability** — STOP. Do not file a public issue. See [`SECURITY.md`](../../SECURITY.md) for the private disclosure process.
- [ ] Critical — the host crashes, renders a wrong verdict, or silently fails
- [ ] High — the host produces misleading output but does not crash
- [ ] Medium — a feature works but is hard to use or under-documented
- [ ] Low — cosmetic, minor inconvenience

## Reproduction

**Steps:**

1.
2.
3.

**Expected:**

<!-- What you expected to happen. -->

**Actual:**

<!-- What actually happened. Paste the output below if relevant. -->

```text
<paste output here>
```

## Environment

- breachsafe-ux version (commit SHA or release tag):
- Python version (`python --version`):
- OS and version:
- Tool descriptor involved (if any):
- Install method: `pip` / `uv` / editable source

## Logs

<!-- Paste the relevant log lines. Do NOT paste secrets or full sensitive
     output. Sanitize before posting. -->

```text
<paste sanitized logs>
```

## Anything else

<!-- Other context, screenshots, or related issues. -->
