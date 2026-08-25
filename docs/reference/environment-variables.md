<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Environment variables

The host is configured entirely by environment variables. Pass them inline from source, or with
`-e` to `docker run`.

| Variable | Default | Purpose |
|---|---|---|
| `BREACHSAFE_UX_PORT` | `7860` | Server port. |
| `BREACHSAFE_UX_HOST` | `127.0.0.1` from source; `0.0.0.0` in the Docker image | Bind address. |
| `BREACHSAFE_UX_TOOLS_DIR` | bundled `tools/` | Descriptor root; read at call time. |
| `BREACHSAFE_UX_RUN_ROOT` | `~/mint-proof/wizard-runs` | Per-run scratch directory. On macOS, keep it under `/Users` so Docker can bind-mount it. |
| `BREACHSAFE_UX_<FLAG>` | on | Feature flag for a descriptor or chain marked `feature_flag: <flag>`; set to `false` (or `0`/`no`/`off`) to hide it. |

## Feature flags

`BREACHSAFE_UX_<FLAG>` gates any descriptor or chain button whose `feature_flag` is `<flag>`
(matched case-insensitively). Every flag defaults to on; the tab is hidden only when the value,
lower-cased and trimmed, is `false`, `0`, `no`, or `off`. The shipped example uses
`BREACHSAFE_UX_MINT_OSCAL` to hide the OSCAL tab. See
[enable optional tabs](../how-to/enable-optional-tabs.md).

## Examples

From source:

```bash
BREACHSAFE_UX_PORT=8080 BREACHSAFE_UX_TOOLS_DIR=/path/to/my-descriptors uv run breachsafe-ux
```

With Docker:

```bash
docker run -d --pull=always -p 8080:8080 \
  -e BREACHSAFE_UX_PORT=8080 \
  -e BREACHSAFE_UX_MINT_OSCAL=false \
  --name enxemble ghcr.io/breachsafe/breachsafe-enxemble:latest
```
