"""Feature-flag gating for OSS/Pro decoupling (#67).

A descriptor or chain marked `feature_flag: X` renders only when BREACHSAFE_UX_<X> is not
disabled (default ON). Flipping the flag off previews the OSS base edition without deleting code.
"""

from __future__ import annotations

import yaml

from breachsafe_ux.facade import ROOT, feature_enabled, load_descriptors


def test_default_on(monkeypatch):
    monkeypatch.delenv("BREACHSAFE_UX_MINT_OSCAL", raising=False)
    assert feature_enabled("mint_oscal") is True


def test_off_values(monkeypatch):
    for v in ("false", "0", "no", "off", "FALSE", "Off"):
        monkeypatch.setenv("BREACHSAFE_UX_MINT_OSCAL", v)
        assert feature_enabled("mint_oscal") is False


def test_on_values(monkeypatch):
    for v in ("true", "1", "yes", "anything-else"):
        monkeypatch.setenv("BREACHSAFE_UX_MINT_OSCAL", v)
        assert feature_enabled("mint_oscal") is True


def test_mint_oscal_loaded_when_flag_on(monkeypatch):
    monkeypatch.delenv("BREACHSAFE_UX_MINT_OSCAL", raising=False)
    assert "mint-oscal" in load_descriptors()


def test_mint_oscal_hidden_when_flag_off(monkeypatch):
    monkeypatch.setenv("BREACHSAFE_UX_MINT_OSCAL", "false")
    descs = load_descriptors()
    assert "mint-oscal" not in descs  # gated descriptor not loaded
    assert "qureddy" in descs  # base tool still there


def test_shipped_descriptors_declare_the_flag():
    mo = yaml.safe_load((ROOT / "tools" / "mint-oscal" / "mint-oscal.yaml").read_text())
    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    assert mo.get("feature_flag") == "mint_oscal"
    assert q["chains"][0].get("feature_flag") == "mint_oscal"
