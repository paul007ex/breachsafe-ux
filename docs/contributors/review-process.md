<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Review process

How a change lands. This is the short version; the authoritative workflow is
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §3 (workflow) and §8 (commits).

## The flow

1. **Open an issue first** for non-trivial work, so scope is confirmed before code.
2. **Branch from `main`.** Branch naming is `<type>/<short-description>` (for example
   `feat/descriptor-tokens`, `fix/badge-state-parse`). Never commit directly to `main`.
3. **One thing per PR.** Do not bundle a refactor with a feature with a bug fix.
4. **Run the [local release gate](local-release-gate.md)** before pushing.
5. **Open a PR** and fill out the template; **self-review your own diff** first.
6. **CI must pass** before merge; **squash-and-merge** is the default.

## What a reviewer checks

Beyond the automated gates (which are blocking, not advisory — see
[`CONTRIBUTING.md`](../../CONTRIBUTING.md) §4), a reviewer confirms:

- The change is on the correct side of the
  [host↔descriptor boundary](../explanation/host-descriptor-boundary.md): no tool-specific
  knowledge leaked into the engine, and a new tool capability is a descriptor field rather than a
  special case.
- The [three-state verdict](../explanation/three-state-verdict.md) still fails closed: no path
  can render a green a validator did not give.
- The MVC/engine layering holds: only `app.py` and `brand.py` import Gradio (see
  [coding rules](coding-rules.md)).
- Documentation is updated with behaviour, and every command in the docs was executed against
  the real product.

## Commits

Conventional Commits (`feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`, `perf`,
`security`). See [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §8 for the exact format and examples.

## Security

Do not open a public issue for a vulnerability. Follow [`SECURITY.md`](../../SECURITY.md) for
private disclosure.
