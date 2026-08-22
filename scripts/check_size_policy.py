#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Enforce breachsafe-ux's file/function/class size ceilings over src and tests.

Thin repo-specific entrypoint over the vendored breachsafe-common size gate
(``scripts/_size_policy.py``, copied verbatim from ``breachsafe-common``'s
``quality-gates/check_size_policy.py`` for drift-checkability — #91). This wrapper
keeps the no-argument call contract every existing caller relies on
(``file-size-gate.yml``, ``release_gate.py``, ``CLAUDE.md``) while applying the
BreachSAFE ceilings to both the package and its tests.

The ceilings count *logical* lines only: blank lines and the module/function/class
docstring are excluded, so formatting and documentation never push code over the
limit. Refactor a file/function/class that breaches a ceiling rather than raising
the number.
"""

from __future__ import annotations

import sys
from pathlib import Path

from _size_policy import violations

FILE_CEILING = 400
FUNCTION_CEILING = 50
CLASS_CEILING = 200
ROOT = Path(__file__).resolve().parents[1]
SCOPE = (ROOT / "src" / "breachsafe_ux", ROOT / "tests")


def all_violations() -> list[str]:
    """Return ceiling breaches across every in-scope source root."""
    failures: list[str] = []
    for root in SCOPE:
        if not root.exists():
            continue
        failures.extend(violations(root, FILE_CEILING, FUNCTION_CEILING, CLASS_CEILING))
    return failures


def main() -> int:
    """Print policy results and return nonzero on any ceiling breach."""
    failures = all_violations()
    if failures:
        print("File/function/class size policy failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("File/function/class size policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
