#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Enforce breachsafe-ux's per-file line ceiling over src and tests.

The ceiling counts *logical* lines only: blank lines and the module/function/
class docstring are excluded, so formatting and documentation never push a file
over the limit. A single hard ceiling keeps files reviewable; refactor a file
that breaches it rather than raising the number.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FILE_CEILING = 400
ROOT = Path(__file__).resolve().parents[1]
SCOPE = (ROOT / "src" / "breachsafe_ux", ROOT / "tests")


def _docstring_range(node: ast.AST) -> range:
    body = getattr(node, "body", [])
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        end_lineno = body[0].end_lineno or body[0].lineno
        return range(body[0].lineno, end_lineno + 1)
    return range(0)


def _logical_line_count(lines: list[str], node: ast.AST) -> int:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", len(lines))
    docstring_lines = _docstring_range(node)
    return sum(
        1
        for number, line in enumerate(lines[start - 1 : end], start=start)
        if line.strip() and number not in docstring_lines
    )


def violations(scope: tuple[Path, ...] = SCOPE) -> list[str]:
    """Return stable descriptions of per-file line-ceiling breaches."""
    failures: list[str] = []
    for root in scope:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
            tree = ast.parse(source)
            line_count = _logical_line_count(lines, tree)
            relative = path.relative_to(ROOT)
            if line_count > FILE_CEILING:
                failures.append(f"{relative}: {line_count} lines exceeds {FILE_CEILING}")
    return failures


def main() -> int:
    """Print policy results and return nonzero on any ceiling breach."""
    failures = violations()
    if failures:
        print("File size policy failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("File size policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
