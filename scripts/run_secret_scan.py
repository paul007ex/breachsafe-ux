#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Run a pinned, checksum-verified full-history secret scan.

The Gitleaks binary is downloaded from its official GitHub release, its SHA-256
digest is verified against ``scripts/release-tools.json`` before it is ever
executed, and the archive is re-extracted on every run so a stale or tampered
extraction is never trusted. The scan covers the complete Git history (``HEAD``).
"""

from __future__ import annotations

import subprocess

from _release_support import ROOT, download_tool

SCAN_TIMEOUT = 300


def main() -> int:
    """Scan the complete current Git history with the pinned Gitleaks binary."""
    cache = ROOT / ".cache" / "release-tools"
    cache.mkdir(parents=True, exist_ok=True)
    gitleaks = download_tool("gitleaks", cache)
    completed = subprocess.run(
        [str(gitleaks), "git", "--no-banner", "--log-opts=HEAD", str(ROOT)],
        cwd=ROOT,
        check=False,
        timeout=SCAN_TIMEOUT,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
