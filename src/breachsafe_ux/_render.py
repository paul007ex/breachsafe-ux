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


def _prop_rows(art: Any, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """label+value rows for each spec whose `find_prop` resolves in the artifact (read-only)."""
    out: list[dict[str, Any]] = []
    for s in specs:
        val = _find_prop(art, s["find_prop"]) if "find_prop" in s else None
        if val is not None:
            out.append({"label": s["label"], "value": val})
    return out


def _highlights(desc: dict[str, Any], art: Any) -> list[dict[str, Any]]:
    if art is None:
        return []
    return _prop_rows(art, desc.get("render", {}).get("highlights", []))


def _evaluation(desc: dict[str, Any], art: Any) -> dict[str, Any] | None:
    """The per-axis evaluation the tool itself produced, for a display box (#199/#59).

    Config-driven like `_highlights`: `render.evaluation` names each axis label + the property to
    read (find_prop), and an optional headline property. The host renders whatever the tool
    reports; it never computes a verdict (OSS scope). Returns None when nothing resolves (e.g. a
    failed scan or a tool that declares no evaluation), so the box simply does not appear.
    """
    cfg = desc.get("render", {}).get("evaluation")
    if not cfg or art is None:
        return None
    rows = _prop_rows(art, cfg.get("axes", []))
    if not rows:
        return None
    headline = _find_prop(art, cfg["headline_prop"]) if "headline_prop" in cfg else None
    return {"title": cfg.get("title", "Evaluation"), "rows": rows, "headline": headline}


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
    result: dict[str, Any] | None
    if val is None:
        result = p.get("default")
    else:
        result = p.get("cases", {}).get(str(val)) or p.get("default")
    return result
