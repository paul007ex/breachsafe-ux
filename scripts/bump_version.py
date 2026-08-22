#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Single-source version tooling for breachsafe-ux.

`pyproject.toml [project].version` is the ONE source of truth. Every other place
that repeats the version is derived from it here:

  * the README version badge
  * the CHANGELOG version badge + a `## [<version>] - <date>` section

Usage:
  scripts/bump_version.py --check          verify README + CHANGELOG match pyproject
  scripts/bump_version.py --set X.Y.Z      set pyproject version + sync badges

`--check` is wired into the release gate: a release cannot cut unless the
CHANGELOG documents the current version.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

_SEMVER = re.compile(r"^\d+\.\d+\.\d+([-+].+)?$")
_BADGE = re.compile(r"version-[0-9][^-\s)]*-blue")


def current_version() -> str:
    """Return the single-source version from `pyproject.toml [project].version`."""
    return tomllib.loads(PYPROJECT.read_text())["project"]["version"]


def _changelog_has(version: str) -> bool:
    return (
        re.search(
            rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}", CHANGELOG.read_text(), re.M
        )
        is not None
    )


def check() -> int:
    """Verify the README and CHANGELOG match pyproject; return 0 on match, 1 otherwise."""
    v = current_version()
    errs: list[str] = []
    if README.exists() and f"version-{v}-blue" not in README.read_text():
        errs.append(f"README version badge is not {v}")
    if not CHANGELOG.exists():
        errs.append("CHANGELOG.md is missing")
    elif f"version-{v}-blue" not in CHANGELOG.read_text():
        errs.append(f"CHANGELOG version badge is not {v}")
    elif not _changelog_has(v):
        errs.append(f"CHANGELOG has no '## [{v}] - <date>' section")
    if errs:
        print("bump_version --check FAILED:")
        for e in errs:
            print("  -", e)
        return 1
    print(f"bump_version --check OK (version {v})")
    return 0


def _sync_badge(path: Path, version: str) -> None:
    if path.exists():
        path.write_text(_BADGE.sub(f"version-{version}-blue", path.read_text()))


def set_version(version: str) -> int:
    """Set the pyproject version and sync the README/CHANGELOG badges; return an exit code."""
    if not _SEMVER.match(version):
        print(f"not a semver: {version}", file=sys.stderr)
        return 2
    text = PYPROJECT.read_text()
    text = re.sub(r'^(version\s*=\s*)"[^"]+"', rf'\1"{version}"', text, count=1, flags=re.M)
    PYPROJECT.write_text(text)
    _sync_badge(README, version)
    _sync_badge(CHANGELOG, version)
    today = _dt.datetime.now(_dt.UTC).date().isoformat()
    print(
        f"set version {version}; add a '## [{version}] - {today}' CHANGELOG section, then --check"
    )
    return 0


def main() -> int:
    """Parse --check/--set and dispatch to the matching command; return its exit code."""
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--set", metavar="X.Y.Z")
    args = ap.parse_args()
    return check() if args.check else set_version(args.set)


if __name__ == "__main__":
    raise SystemExit(main())
