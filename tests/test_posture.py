"""Readiness-posture banner from findings, decoupled from the evidence badge (#1).

The badge state means 'did the external validator accept the evidence' (e.g. CBOM is
schema-valid). Readiness posture is a SEPARATE verdict read from the scan findings, so a green
'evidence valid' can never read as 'endpoint is secure' (the false-green this closes).
"""

from __future__ import annotations

import json

import yaml

from breachsafe_ux._render import _posture
from breachsafe_ux.resolve import ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "qureddy_cbom.sample.json"

_DESC = {
    "render": {
        "posture": {
            "from": "qureddy:scan.readiness",
            "cases": {
                "quantum_vulnerable": {"text": "QV", "level": "high"},
                "quantum_safe": {"text": "QS", "level": "ok"},
            },
            "default": {"text": "?", "level": "unknown"},
        }
    }
}


def _art(readiness):
    return {"metadata": {"properties": [{"name": "qureddy:scan.readiness", "value": readiness}]}}


def test_posture_maps_value():
    assert _posture(_DESC, _art("quantum_vulnerable")) == {"text": "QV", "level": "high"}
    assert _posture(_DESC, _art("quantum_safe")) == {"text": "QS", "level": "ok"}


def test_posture_default_on_unknown_value():
    assert _posture(_DESC, _art("some_new_value")) == {"text": "?", "level": "unknown"}


def test_posture_default_when_property_missing():
    assert _posture(_DESC, {"metadata": {"properties": []}}) == {"text": "?", "level": "unknown"}


def test_posture_none_when_not_declared():
    assert _posture({"render": {}}, _art("quantum_vulnerable")) is None


def test_posture_none_without_artifact():
    assert _posture(_DESC, None) is None


def test_qureddy_resolves_a_representative_cbom():
    """Drift catcher: the shipped descriptor resolves a real-shaped CBOM to a real case.
    If qureddy moves/renames scan.hndl_exposure, update the fixture — this test then flags it.
    It did exactly that when the banner moved off scan.readiness in v0.5.0."""
    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    cbom = json.loads(FIXTURE.read_text())
    p = _posture(q, cbom)
    assert p and p["level"] == "high"  # at_risk -> high
    # v0.5.0: the banner answers the harvest-now-decrypt-later question only. scan.readiness
    # collapses five independent axes into one ordinal whose precedence ranks classically_weak
    # above everything, so a PQC-capable endpoint was banner'd worst-tier off medium findings.
    # See BreachSAFE/qureddy#453.
    assert q["render"]["posture"]["from"] == "qureddy:scan.hndl_exposure"


def test_qureddy_maps_the_full_hndl_exposure_enum():
    """Every HndlExposure value qureddy can emit must map to a case, or the banner silently
    falls through to `default` and the operator sees 'could not be determined' for a scan that
    succeeded."""
    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    cases = q["render"]["posture"]["cases"]
    for v in [
        "at_risk",
        "protected_defeasible",
        "protected",
        "unknown",
    ]:
        assert v in cases, f"hndl_exposure value {v!r} not mapped (qureddy HndlExposure enum)"


def test_result_shows_banner_and_reworded_evidence_badge():
    from breachsafe_ux.app import _result

    desc = {
        "render": {
            "posture": {
                "from": "r",
                "cases": {"quantum_vulnerable": {"text": "Quantum-vulnerable", "level": "high"}},
            },
            "badge_text": {"valid": "Evidence: CBOM well-formed"},
        }
    }
    res = {
        "badge": ("valid", "ok"),
        "artifact": {"metadata": {"properties": [{"name": "r", "value": "quantum_vulnerable"}]}},
        "highlights": [],
    }
    md = _result(desc, res)[0]
    assert "Quantum-vulnerable" in md  # readiness banner present
    assert "Evidence: CBOM well-formed" in md  # evidence-specific wording
    assert "VALID" not in md  # bare 'VALID' no longer implies 'secure'


def test_result_no_banner_on_failed_run():
    from breachsafe_ux.app import _result

    desc = {"render": {"posture": {"from": "r", "cases": {"x": {"text": "X", "level": "high"}}}}}
    res = {"badge": ("unavailable", "tool timed out"), "error": "tool timed out"}
    md = _result(desc, res)[0]
    assert "X" not in md  # no artifact -> no readiness claim on a failed run
