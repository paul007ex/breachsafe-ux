#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE
# SPDX-License-Identifier: Apache-2.0
"""Enforce a file/function/class size ceiling on a Python source tree.

Generalized from qureddy's `scripts/check_size_policy.py` (`breachsafe/qureddy`),
which hardcoded `src/qureddy` and fixed 400/50/200 ceilings. This version takes the
source root and ceilings as arguments — same parameterization discipline as
`release/validate_release_archive.sh`'s `--binary <name>`.

Counts *logical* lines (skips blank lines and a leading docstring), not raw line
count, so a well-documented function isn't penalized for its own docstring.

Usage:
    python3 check_size_policy.py --src-dir src/mypackage
    python3 check_size_policy.py --src-dir src/mypackage \
        --file-ceiling 500 --function-ceiling 60 --class-ceiling 250
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

DEFAULT_FILE_CEILING = 400
DEFAULT_FUNCTION_CEILING = 50
DEFAULT_CLASS_CEILING = 200


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


def violations(
    source_root: Path,
    file_ceiling: int = DEFAULT_FILE_CEILING,
    function_ceiling: int = DEFAULT_FUNCTION_CEILING,
    class_ceiling: int = DEFAULT_CLASS_CEILING,
) -> list[str]:
    """Return stable descriptions of source-size ceiling breaches under source_root."""
    failures: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        tree = ast.parse(source)
        line_count = _logical_line_count(lines, tree)
        try:
            relative = path.relative_to(source_root.parent)
        except ValueError:
            relative = path
        if line_count > file_ceiling:
            failures.append(f"{relative}: {line_count} lines exceeds {file_ceiling}")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                limit = function_ceiling
            elif isinstance(node, ast.ClassDef):
                limit = class_ceiling
            else:
                continue
            logical_lines = _logical_line_count(lines, node)
            if logical_lines > limit:
                failures.append(
                    f"{relative}:{node.lineno} {node.name}: {logical_lines} lines exceeds {limit}"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src-dir", type=Path, required=True, help="Python source root to walk (e.g. src/mypackage)"
    )
    parser.add_argument("--file-ceiling", type=int, default=DEFAULT_FILE_CEILING)
    parser.add_argument("--function-ceiling", type=int, default=DEFAULT_FUNCTION_CEILING)
    parser.add_argument("--class-ceiling", type=int, default=DEFAULT_CLASS_CEILING)
    args = parser.parse_args()

    if not args.src_dir.is_dir():
        print(f"error: --src-dir {args.src_dir} is not a directory", file=sys.stderr)
        return 2

    failures = violations(
        args.src_dir, args.file_ceiling, args.function_ceiling, args.class_ceiling
    )
    if failures:
        print("File/function/class size policy failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("File/function/class size policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
