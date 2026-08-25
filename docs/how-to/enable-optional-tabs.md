<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Enable or hide optional tabs (feature flags)

A descriptor can be gated behind a feature flag so a single image or checkout can present
different editions without forking. A gated descriptor is loaded only when its flag is on, and
its tab (and any chain button that targets it) disappears when the flag is off.

Flags are environment variables named `BREACHSAFE_UX_<FLAG>`, where `<FLAG>` is the descriptor's
`feature_flag` upper-cased. **Every flag defaults to on**; set it to `false` to hide the tab.

## How a descriptor opts in

The descriptor names its flag; the host does the gating:

```yaml
id: mint-oscal
feature_flag: mint_oscal    # gated by BREACHSAFE_UX_MINT_OSCAL (default on)
```

A `chains` entry can carry the same `feature_flag`, so a "convert" or "hand-off" button on
another tab is hidden together with the target tab.

## Turn a tab off

Set the flag to `false` on the host.

From source:

```bash
BREACHSAFE_UX_MINT_OSCAL=false uv run breachsafe-ux
```

With Docker, pass it with `-e`:

```bash
docker run -d --pull=always -p 7860:7860 \
  -e BREACHSAFE_UX_MINT_OSCAL=false \
  --name enxemble ghcr.io/breachsafe/enxemble:latest
```

## Why this matters for `--check`

`breachsafe-ux --check` only checks the tabs that are loaded. If a gated tab's tool is not
installed, leaving the flag on makes `--check` exit nonzero (the tool is `NOT FOUND`); turning
the flag off removes that tab so `--check` reflects only the tabs you actually run. This is the
clean way to run a subset of tools from a source checkout. See the
[CLI reference](../reference/cli.md) and the
[environment variables reference](../reference/environment-variables.md).

## Recognised values

The flag is on unless its value (lower-cased, trimmed) is one of `false`, `0`, `no`, or `off`.
Any other value keeps the tab on. Use `false` for clarity.
