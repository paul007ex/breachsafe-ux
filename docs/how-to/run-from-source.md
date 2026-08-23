<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Run the host from source

Run the EnXemble host from a source checkout when you are developing the host itself, wrapping a
tool that is not in a prebuilt image, or pointing the host at your own descriptor directory. The
host is a Python package; the tools it wraps are separate programs it resolves on `PATH` (or
falls back to a Docker image when a descriptor declares one).

EnXemble is **not** published to PyPI or TestPyPI. Install it from a source checkout with
[`uv`](https://github.com/astral-sh/uv).

## Requirements

- Python 3.12 or newer.
- `uv`.
- Docker, only if a descriptor uses the image execution backend or a Docker-based validator.

## Install and launch

```bash
git clone https://github.com/paul007ex/breachsafe-ux && cd breachsafe-ux
uv sync                          # runtime only (enough to launch)
uv run breachsafe-ux             # serves http://127.0.0.1:7860
```

`uv sync` installs just the runtime. To run the tests and quality gates as well, use
`uv sync --extra dev` (see [the local release gate](../contributors/local-release-gate.md)).

Open <http://127.0.0.1:7860> in your browser. The host binds loopback by default from source, so
it is reachable only from the same machine.

## Make the wrapped tools resolvable

The host runs the command a descriptor names by resolving it against `tools/<id>/bin/` first,
then the system `PATH`. A tool is runnable when either is true:

- **It is on your `PATH`** — install it however it ships. For the bundled reference descriptors,
  put the scanner on `PATH`, for example by cloning and syncing it:

  ```bash
  git clone https://github.com/breachsafe/qureddy && (cd qureddy && uv sync)
  export PATH="$PWD/qureddy/.venv/bin:$PATH"
  ```

- **A descriptor declares `run.image`** — the host runs the local binary when it resolves on
  `PATH` and falls back to `docker run --pull=always <image>` otherwise. The bundled reference
  descriptors declare an image, so their tabs work from a bare checkout as long as Docker is
  running, even with nothing extra on `PATH`.

- **You drop a local shim** at `tools/<id>/bin/<id>` that execs your build. `tools/*/bin/` is
  git-ignored, so a shim is per-developer wiring. See [`tools/README.md`](../../tools/README.md).

## Verify the environment

```bash
uv run breachsafe-ux --check     # prints each tab's tool/validator/path; exit != 0 if any is missing
```

From a bare checkout, tabs whose descriptor declares a Docker image report `ok` via the image
fallback. A tab whose tool is neither on `PATH` nor image-backed reports `NOT FOUND`, and
`--check` exits nonzero. Hide an optional tab you do not need with its feature flag, for example
`BREACHSAFE_UX_MINT_OSCAL=false`, so `--check` reflects only the tabs you run. See
[enable optional tabs](enable-optional-tabs.md) and the [CLI reference](../reference/cli.md).

## Point the host at your own descriptors

Set `BREACHSAFE_UX_TOOLS_DIR` to a directory of descriptors to render your own tools instead of
the bundled ones:

```bash
BREACHSAFE_UX_TOOLS_DIR=/path/to/my-descriptors uv run breachsafe-ux
```

To author a descriptor, see [add a tool](add-a-tool.md).
