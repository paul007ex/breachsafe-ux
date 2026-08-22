#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Run the fail-closed, authoritative breachsafe-ux release gate.

This is the single local command that reproduces every blocking CI check for a
release candidate: lint, type-check, tests, the file-size policy, the
single-source version check, license (reuse) compliance, a build, and a
full-history secret scan. Every static tool runs under a checksum-pinned ``uv``
with ``uv run --locked`` so the versions match the committed lockfile exactly.

The gate is fail-closed: the first failing check stops the run with a nonzero
exit and a stable, greppable summary line.
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from _release_support import ROOT, download_tool

if TYPE_CHECKING:
    from pathlib import Path

COMMAND_TIMEOUT = 600


def _run(name: str, command: list[str]) -> None:
    print(f"::group::{name}", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False, timeout=COMMAND_TIMEOUT)
    print("::endgroup::", flush=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed (exit {completed.returncode})")


def _gates(uv: Path) -> None:
    run = [str(uv), "run", "--locked", "--python", "3.12"]
    # --extra dev installs the gate toolchain (ruff/mypy/bandit/deptry/pip-audit); without it the
    # `uv run` gate steps fail to spawn those tools (they live in the dev optional-dependency group).
    _run("sync", [str(uv), "sync", "--locked", "--python", "3.12", "--extra", "dev"])
    _run("ruff", [*run, "ruff", "check", "src", "tests"])
    _run("ruff-format", [*run, "ruff", "format", "--check", "."])
    _run("mypy", [*run, "mypy", "src"])
    _run("bandit", [*run, "bandit", "-c", "pyproject.toml", "-r", "-ll", "src", "scripts"])
    _run("pip-audit", [*run, "pip-audit"])
    _run("deptry", [*run, "deptry", "."])
    _run("tests", [*run, "pytest", "tests/", "-q", "--cov=breachsafe_ux", "--cov-fail-under=70"])
    _run("file-size", [*run, "python", "scripts/check_size_policy.py"])
    _run("version", [*run, "python", "scripts/bump_version.py", "--check"])
    _run("reuse", [*run, "reuse", "lint"])
    _run("build", [str(uv), "build"])  # uv build (matches CI); no `build` module dependency
    _run("secrets", [sys.executable, "scripts/run_secret_scan.py"])


def main() -> int:
    """Run every blocking local release check, fail-closed on the first breach."""
    if sys.version_info[:2] != (3, 12):
        print("release gate requires Python 3.12", file=sys.stderr)
        return 2
    cache = ROOT / ".cache" / "release-tools"
    cache.mkdir(parents=True, exist_ok=True)
    try:
        uv = download_tool("uv", cache)
        _gates(uv)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"release gate FAIL: {exc}", file=sys.stderr)
        return 1
    print("release gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
