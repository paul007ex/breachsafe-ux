"""Descriptor-selected validators: validate.by, multi-key, fail-closed (#43)."""

from __future__ import annotations

import sys

from breachsafe_ux.facade import _select_validator, _validate, _validator


def test_singular_validate_passes_through():
    v = {"argv": ["x"], "badge_rule": {}}
    assert _select_validator(v, {}) is v


def test_by_selects_matching_case():
    v = {"by": ["format"], "cases": {"cbom": {"argv": ["c"], "badge_rule": {}}, "json": None}}
    assert _select_validator(v, {"format": "cbom"})["argv"] == ["c"]
    assert _select_validator(v, {"format": "json"}) is None  # explicit null -> no validator
    assert _select_validator(v, {"format": "rich"}) is None  # unmatched, no default


def test_by_uses_default_when_no_case_matches():
    v = {
        "by": ["format"],
        "cases": {"cbom": {"argv": ["c"], "badge_rule": {}}},
        "default": {"argv": ["d"], "badge_rule": {}},
    }
    assert _select_validator(v, {"format": "zzz"})["argv"] == ["d"]


def test_multi_key_joins_with_pipe():
    v = {"by": ["format", "profile"], "cases": {"cbom|strict": {"argv": ["cs"], "badge_rule": {}}}}
    assert _select_validator(v, {"format": "cbom", "profile": "strict"})["argv"] == ["cs"]
    assert _select_validator(v, {"format": "cbom", "profile": "lax"}) is None


def test_validate_is_none_for_null_case(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"validate": {"by": ["format"], "cases": {"json": None}}}
    state, msg = _validate(desc, tmp_path, art, {"format": "json"})
    assert state == "none" and "no validator" in msg


def test_validate_runs_selected_case(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "validate": {
            "by": ["format"],
            "cases": {
                "cbom": {
                    "argv": [sys.executable, "-c", "import sys; sys.exit(0)"],
                    "badge_rule": {"pass_if": {"exit": 0}},
                }
            },
        }
    }
    assert _validate(desc, tmp_path, art, {"format": "cbom"})[0] == "valid"


def test_schema_rejects_validate_with_both_argv_and_by():
    d = {
        "schema_version": 1,
        "id": "t",
        "run": {"base": ["x"]},
        "validate": {
            "argv": ["a"],
            "badge_rule": {"pass_if": {"exit": 0}},
            "by": ["format"],
            "cases": {},
        },
    }
    assert list(_validator().iter_errors(d)), "oneOf should reject singular+by mixed"


def test_qureddy_json_and_rich_have_no_validator():
    import yaml

    from breachsafe_ux.resolve import ROOT

    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    cases = q["validate"]["cases"]
    assert cases["json"] is None and cases["rich"] is None
    assert cases["cbom"]["argv"]  # cbom keeps a real validator
