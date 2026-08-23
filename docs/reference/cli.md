<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# CLI reference

The host is a web application with one command, `breachsafe-ux`. It has two behaviours: launch
the server (the default), or resolve the environment and exit (`--check`). There is **no**
`--help` or `--version` subcommand — the host is a web UX, not a CLI tool.

## `breachsafe-ux`

Builds the app (a tab per standalone descriptor) and launches the Gradio server.

```bash
uv run breachsafe-ux
```

- Binds `BREACHSAFE_UX_HOST` (default `127.0.0.1` from source, `0.0.0.0` in the Docker image) on
  `BREACHSAFE_UX_PORT` (default `7860`).
- Serves until interrupted. See the
  [environment variables reference](environment-variables.md) for all configuration.

Passing any argument other than `--check` still launches the server; unrecognised flags are not
parsed as options.

## `breachsafe-ux --check`

Resolves every loaded descriptor's environment, prints a per-tab table, and exits nonzero if any
tool or validator is missing. This is the real health signal — a `curl` on `/` is false-healthy
because the web server serves even when the underlying tool is absent.

```bash
uv run breachsafe-ux --check          # from a source checkout
docker exec enxemble breachsafe-ux --check   # inside a running container
```

For each tab it prints a Markdown table with one row per role — the tool, the validator, and any
connection-test command — showing the resolved binary, version, and path, plus an `ok` /
`NOT FOUND` status. It ends with `OK` or `MISSING TOOLS`.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Every loaded tab's tool and validator resolved (`OK`). |
| `1` | At least one tool or validator is missing (`MISSING TOOLS`). |

`--check` only inspects the tabs that are **loaded**. A tab gated off by a feature flag is not
checked, so hiding an optional tab whose tool you have not installed keeps `--check` green — see
[enable optional tabs](../how-to/enable-optional-tabs.md).

### Example

Running `--check` against the shipped reference example image, where all tools resolve:

```
## qureddy
| role | binary | version | path | status |
|---|---|---|---|---|
| tool | qureddy | 0.2.40 | /usr/local/bin/qureddy | ok |
| validator | python | 3.14.7 | /usr/local/bin/python3.14 | ok |
| Test connection | openssl | 3.5.7 | /opt/openssl/bin/openssl | ok |
...
OK
```

The exact tools, versions, and paths depend on the descriptors loaded and the host they run on.
