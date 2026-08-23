<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# The local release gate

One command reproduces every blocking CI check. Run it before you push.

```bash
uv run --locked --extra dev python scripts/release_gate.py
```

It fails closed on the first breach and prints a `PASS` / `FAIL` summary. Everything runs under
`uv run --locked`, so your versions match the committed `uv.lock` exactly: the same path CI
uses. This is the authoritative local gate; the full list of checks it enforces (lint, format,
strict types, security, dependencies, tests, architecture layering, docs, size, duplication,
licensing, supply chain) is in [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §4 and is not
duplicated here.

## Set up the dev environment first

```bash
uv sync --extra dev
```

Plain `uv sync` installs only the runtime, which is enough to launch the host but not to run the
tests or gates. See [run from source](../how-to/run-from-source.md).

## Run an individual gate while iterating

```bash
uv run --locked --extra dev mypy --strict src
uv run --locked --extra dev ruff check .
uv run --locked --extra dev pytest
```

## Live-integration tests

Tests marked `@pytest.mark.live` need a real tool and Docker. CI **deselects** them with
`-m "not live"` so a skip can never hide a failure; the release gate follows the same path. Run
them locally with a plain `uv run --locked --extra dev pytest` (no `-m` filter), which includes
the live suite. See [`CONTRIBUTING.md`](../../CONTRIBUTING.md) §4.

## Documentation and size gates

Documentation is held to the same bar as code: `reuse lint` must be 100% (every first-party file
carries an Apache-2.0 SPDX header), the size policy must pass, and internal links must resolve.
The release gate runs these, so a doc-only change still runs the gate before pushing.
