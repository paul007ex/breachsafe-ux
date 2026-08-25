"""Container health checks for every configured EnXemble tool descriptor."""

from __future__ import annotations

from itertools import starmap

from breachsafe_ux.facade import load_descriptors
from breachsafe_ux.render import _env_panel_md
from breachsafe_ux.resolve import environment


def _check_descriptor(did: str, desc: dict[str, object]) -> bool:
    """Print one descriptor's environment and return whether it is complete."""
    rows = environment(desc)
    print(f"\n## {did}\n{_env_panel_md(rows)}")
    return all(row["ok"] for row in rows)


def check() -> int:
    """Print tool availability and return nonzero when any dependency is missing."""
    results = list(starmap(_check_descriptor, load_descriptors().items()))
    ok = all(results)
    print("\nOK" if ok else "\nMISSING TOOLS")
    return 0 if ok else 1
