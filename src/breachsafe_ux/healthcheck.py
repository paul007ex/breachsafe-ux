"""Container health checks for every configured EnXemble tool descriptor."""

from __future__ import annotations

from breachsafe_ux.facade import load_descriptors
from breachsafe_ux.render import _env_panel_md
from breachsafe_ux.resolve import environment


def check() -> int:
    """Print tool availability and return nonzero when any dependency is missing."""
    ok = True
    for did, desc in load_descriptors().items():
        rows = environment(desc)
        print(f"\n## {did}\n{_env_panel_md(rows)}")
        ok = ok and all(row["ok"] for row in rows)
    print("\nOK" if ok else "\nMISSING TOOLS")
    return 0 if ok else 1
