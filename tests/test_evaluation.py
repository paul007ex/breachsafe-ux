# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Evaluation box (#199): the host renders a tool's per-axis interpretation from descriptor config.

Uses generic property names (not a specific tool's) to prove the mechanism is tool-agnostic:
the host reads whatever `render.evaluation` declares and renders it verbatim.
"""

from __future__ import annotations

from breachsafe_ux._render import _evaluation
from breachsafe_ux.render import _evaluation_text

_ART = {
    "metadata": {
        "properties": [
            {"name": "t:pqc", "value": "hybrid_observed"},
            {"name": "t:kex", "value": "hybrid"},
            {"name": "t:head", "value": "Hybrid available, legacy remains."},
        ]
    }
}
_DESC = {
    "render": {
        "evaluation": {
            "title": "Evaluation",
            "headline_prop": "t:head",
            "axes": [
                {"label": "PQC support", "find_prop": "t:pqc"},
                {"label": "Key exchange", "find_prop": "t:kex"},
            ],
        }
    }
}


def test_evaluation_reads_declared_axes_and_headline():
    ev = _evaluation(_DESC, _ART)
    assert [r["label"] for r in ev["rows"]] == ["PQC support", "Key exchange"]
    assert ev["rows"][0]["value"] == "hybrid_observed"
    assert "legacy remains" in ev["headline"] and ev["title"] == "Evaluation"


def test_evaluation_is_none_without_config_or_artifact():
    assert _evaluation({"render": {}}, _ART) is None  # no evaluation config -> no box
    assert _evaluation(_DESC, None) is None  # failed scan (no artifact) -> no box


def test_evaluation_skips_missing_props():
    art = {"metadata": {"properties": [{"name": "t:pqc", "value": "x"}]}}  # only one axis present
    ev = _evaluation(_DESC, art)
    assert [r["label"] for r in ev["rows"]] == ["PQC support"]  # unresolved axis dropped


def test_evaluation_text_renders_aligned_rows_and_headline():
    text = _evaluation_text(_evaluation(_DESC, _ART))
    lines = text.splitlines()
    assert lines[0].startswith("PQC support:") and lines[0].endswith("hybrid_observed")
    assert lines[1].startswith("Key exchange:") and lines[1].endswith("hybrid")
    # labels are padded to a common width so the values line up (aligned columns)
    assert lines[0].index("hybrid_observed") == lines[1].index("hybrid")
    assert "legacy remains" in text  # headline appended
    assert _evaluation_text(None) == ""  # nothing to show


def test_evaluation_is_none_when_no_axis_resolves():
    # Declared axes but the artifact has none of the properties -> no box (not an empty box).
    assert _evaluation(_DESC, {"metadata": {"properties": []}}) is None
