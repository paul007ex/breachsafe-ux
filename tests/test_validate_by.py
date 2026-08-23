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


def test_validate_unresolved_token_badges_unavailable(tmp_path):
    # #104: an unresolved {token} in validate.argv must not raise (run_descriptor calls _validate
    # outside its own try/except); it badges unavailable instead of reaching the UI.
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "validate": {
            "argv": [sys.executable, "-c", "{nonexistent_token}"],
            "badge_rule": {"pass_if": {"exit": 0}},
        }
    }
    state, msg = _validate(desc, tmp_path, art, {})
    assert state == "unavailable" and "descriptor error" in msg


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


def test_qureddy_emits_both_formats_and_validates_the_cbom():
    # #199: one scan writes both correlated documents via --output-dir, so there is no format
    # toggle; validate always runs the single CBOM (primary) validator, not a per-format case.
    import yaml

    from breachsafe_ux.resolve import ROOT

    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    assert not any(i["name"] == "format" for i in q.get("inputs", []))  # format toggle removed
    assert q["run"]["output_dir_flag"] == "--output-dir"
    arts = {a["name"]: a for a in q["run"]["artifacts"]}
    assert arts["cbom"]["file"] == "scan.cdx.json" and arts["cbom"]["primary"] is True
    assert arts["json"]["file"] == "scan.json"
    assert q["validate"]["argv"] and "cases" not in q["validate"]  # single direct CBOM validator
