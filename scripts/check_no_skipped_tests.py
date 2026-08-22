#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Fail if any JUnit XML report contains a skipped test.

Generalized from the skim-check inside qureddy's `scripts/audit_phase.py`
(`breachsafe/qureddy`). That script's other checks (phase-2 coverage, phase-4 live-test
exact-name matching, phase-5 self-scan target matching, phase-6 dist-artifact checks)
are hardcoded to qureddy's own CI artifact layout and canonical test/target lists —
copy-pasting them elsewhere would produce dead code that always "passes" because it's
checking for qureddy-specific things that don't exist in another repo. This file only
extracts the one check that's genuinely repo-agnostic.

Why this exists as its own gate rather than trusting `pytest`'s exit code: a marker like
`@pytest.mark.skip` (or an xfail/xpass) still lets the test run report SUCCESS while
quietly not exercising anything. qureddy's own review-process.md documents the concrete
cost of trusting exit codes alone: a PR displayed "192 passed" while 5 tests were
hard-failing under a rerun-masking bug (issue #15) — this check, plus a rerun-aware CI
config (see testing/README.md's pytest-rerunfailures guidance), is the fix.

Usage:
    python3 check_no_skipped_tests.py path/to/junit.xml [more.xml ...]
    python3 check_no_skipped_tests.py --glob "ci-artifacts/**/*junit*.xml"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# defusedxml, not stdlib xml.etree: JUnit XML here comes from third-party test-runner
# output (pytest-produced, but the parser shouldn't assume that trust boundary holds
# forever) -- same rationale as qureddy's own audit_phase.py used this substitution.
from defusedxml import ElementTree as ET  # type: ignore[import-untyped]  # noqa: N817


def count_skipped(junit_path: Path) -> int:
    """Return the total `skipped` count across all <testsuite> elements in one file."""
    try:
        tree = ET.parse(junit_path)
    except ET.ParseError as exc:
        msg = f"malformed JUnit XML at {junit_path}: {exc}"
        raise ValueError(msg) from exc
    return sum(int(suite.get("skipped", "0")) for suite in tree.iter("testsuite"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="JUnit XML file(s) to check")
    parser.add_argument(
        "--glob",
        help="Glob pattern (relative or absolute, ** supported) to collect JUnit XML "
        "files from, e.g. 'ci-artifacts/**/*junit*.xml'",
    )
    args = parser.parse_args()

    files = list(args.paths)
    if args.glob:
        # stdlib `glob.glob`, not Path.glob -- Path.glob rejects absolute patterns
        # ("Non-relative patterns are unsupported"), and CI callers commonly pass an
        # absolute --glob (e.g. a downloaded-artifact directory outside the repo).
        import glob as glob_module

        files.extend(sorted(Path(p) for p in glob_module.glob(args.glob, recursive=True)))

    if not files:
        print("error: no JUnit XML files given (pass paths or --glob)", file=sys.stderr)
        return 2

    total_skipped = 0
    for path in files:
        if not path.is_file():
            print(f"error: not a file: {path}", file=sys.stderr)
            return 2
        try:
            total_skipped += count_skipped(path)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if total_skipped > 0:
        print(
            f"FAIL: {total_skipped} skipped test(s) found across {len(files)} file(s). "
            "A skip marker lets a test report success without exercising anything.",
            file=sys.stderr,
        )
        return 1

    print(f"PASS: no skipped tests across {len(files)} JUnit XML file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
