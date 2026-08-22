#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Fail on any HIGH/CRITICAL Threagile risk that is not consciously handled.

Reads a Threagile ``risks.json`` and exits non-zero if any risk has severity
``high`` or ``critical`` while its ``risk_status`` is ``unchecked`` or
``in-discussion``. Risks tracked as ``accepted`` / ``mitigated`` / ``in-progress``
/ ``false-positive`` in the model's ``risk_tracking`` block pass the gate. A full
severity breakdown is printed (and written to the GitHub step summary when run in
CI) so the model's risks are always listed, not just the failing ones.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

BLOCKING_SEVERITIES = {"high", "critical"}
UNMITIGATED_STATUSES = {"unchecked", "in-discussion"}


def evaluate(risks: list[dict]) -> tuple[list[str], list[str]]:
    """Return (report_lines, blocking_ids) for the given risks."""
    counts = Counter(r.get("severity", "unknown") for r in risks)
    report = [f"Threagile risks: {len(risks)} total"]
    for severity in ("critical", "high", "elevated", "medium", "low"):
        if counts.get(severity):
            report.append(f"  {severity}: {counts[severity]}")

    blocking: list[str] = []
    for risk in risks:
        severity = risk.get("severity", "unknown")
        status = risk.get("risk_status", "unchecked")
        if severity in BLOCKING_SEVERITIES and status in UNMITIGATED_STATUSES:
            blocking.append(f"{severity}/{status}: {risk.get('synthetic_id', '<no-id>')}")
    return report, blocking


def _write_summary(lines: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    """Print the risk breakdown and return nonzero on a blocking risk."""
    path = Path(argv[1]) if len(argv) > 1 else Path("threagile-out/risks.json")
    if not path.exists():
        print(f"Threagile gate: risks file not found: {path}", file=sys.stderr)
        return 2

    risks = json.loads(path.read_text(encoding="utf-8"))
    report, blocking = evaluate(risks)

    out = list(report)
    if blocking:
        out.append("")
        out.append(f"FAIL: {len(blocking)} HIGH/CRITICAL risk(s) unmitigated:")
        out.extend(f"  {item}" for item in blocking)
        out.append("")
        out.append(
            "Handle each by mitigating the model or tracking it (accepted/mitigated/...) "
            "in the risk_tracking block of threat-model/threagile.yaml."
        )
    else:
        out.append("")
        out.append("PASS: no HIGH/CRITICAL unmitigated risks.")

    print("\n".join(out))
    _write_summary(out)
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
