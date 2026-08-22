# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Artifact-reading render helpers: highlights and the readiness posture (#1).

Split out of facade.py to keep the engine under the per-file size ceiling. These read values
out of a parsed artifact (a CBOM/JSON dict) by property name; they never run anything.
"""

from __future__ import annotations

from typing import Any


def _search_children(children: Any, name: str) -> Any:
    """First non-None `_find_prop` hit across an iterable of child nodes (dict values / list)."""
    for child in children:
        r = _find_prop(child, name)
        if r is not None:
            return r
    return None


def _find_prop(obj: Any, name: str) -> Any:
    """Depth-first search for the value of a CBOM/JSON `{name, value}` property (read-only)."""
    if isinstance(obj, dict):
        if obj.get("name") == name and "value" in obj:
            return obj["value"]
        return _search_children(obj.values(), name)
    if isinstance(obj, list):
        return _search_children(obj, name)
    return None


def _highlights(desc: dict[str, Any], art: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if art is None:
        return out
    for h in desc.get("render", {}).get("highlights", []):
        val = _find_prop(art, h["find_prop"]) if "find_prop" in h else None
        if val is not None:
            out.append({"label": h["label"], "value": val})
    return out


def _posture(desc: dict[str, Any], art: Any) -> dict[str, Any] | None:
    """Readiness banner derived from the scan FINDINGS, decoupled from the evidence badge (#1).

    Reads `render.posture.from` out of the artifact and maps the value to a {text, level} case.
    Returns None when no posture is declared or there is no artifact — the host never invents a
    readiness verdict, and a green 'evidence valid' badge no longer stands in for 'secure'.
    """
    p = desc.get("render", {}).get("posture")
    if not p or art is None:
        return None
    val = _find_prop(art, p["from"])
    if val is None:
        return p.get("default")
    return p.get("cases", {}).get(str(val)) or p.get("default")
