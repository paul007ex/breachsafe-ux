# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Un-gated unit tests for the engine's run/validate/provenance helpers.

These exercise :func:`run_descriptor`, :func:`_validate`, and the ``resolve``/``_render``
helpers directly with cheap real binaries (``true``/``false``/python ``-c``) and a temp
RUN_ROOT — no Docker, no mint-oscal, so they run everywhere (unlike the live-integration
suite in ``test_badge_states.py`` which the whole module skips without those tools).
"""

from __future__ import annotations

import sys

import pytest

from breachsafe_ux import facade, resolve
from breachsafe_ux._argv import _input_argv  # moved out of facade in #186
from breachsafe_ux._render import _find_prop, _search_children
from breachsafe_ux.facade import (
    _apply_badge_rule,
    _expand_brand,
    _fail_detail,
    _match,
    _validate,
    run_descriptor,
)

PY = sys.executable


@pytest.fixture(autouse=True)
def _tmp_run_root(tmp_path, monkeypatch):
    """Keep every run's workdir inside the test's tmp dir, never the user's home."""
    monkeypatch.setattr(facade, "RUN_ROOT", tmp_path / "runs")


def _desc(argv, **run):
    return {"id": "unit", "run": {"argv": argv, **run}}


# --- run_descriptor: the full pipeline over cheap real binaries -----------------------------


def test_run_descriptor_success_parses_json_artifact():
    """stdout artifact + no validator -> parsed artifact, 'none' badge, highlights present."""
    desc = _desc([PY, "-c", "print('{\"k\": 1}')"], artifact_from="stdout", artifact_name="a.json")
    res = run_descriptor(desc, {})
    assert res["artifact"] == {"k": 1}
    assert res["badge"][0] == "none"  # no external validator declared
    assert res["highlights"] == []


def test_run_descriptor_returns_tool_stderr_as_log():
    """#190: the tool's stderr (its diagnostic log) is returned so Raw log can show it."""
    prog = "import sys; sys.stdout.write('{}'); sys.stderr.write('scan.start\\nprobe.done')"
    desc = _desc([PY, "-c", prog], artifact_from="stdout", artifact_name="a.json")
    res = run_descriptor(desc, {})
    assert res["artifact"] == {}  # successful run
    assert res["log"] == "scan.start\nprobe.done"  # stderr carried through, not discarded


def test_run_descriptor_non_json_artifact_is_tolerated():
    """A non-JSON but non-empty artifact is fine (art_json=None), badge still from validator."""
    desc = _desc([PY, "-c", "print('not json')"], artifact_from="stdout", artifact_name="a.json")
    res = run_descriptor(desc, {})
    assert res["artifact"] is None
    assert res["badge"][0] == "none"


def test_run_descriptor_nonzero_exit_is_unavailable_with_tool_diag():
    """A nonzero exit is never valid; the badge surfaces the tool's own last stderr line (#10)."""
    desc = _desc([PY, "-c", "import sys; sys.stderr.write('BOOM last\\n'); sys.exit(3)"])
    res = run_descriptor(desc, {})
    assert res["badge"] == ("unavailable", "BOOM last")


def test_run_descriptor_nonzero_exit_without_stderr():
    """Nonzero exit with empty stderr falls back to a generic 'scan failed (exit N)'."""
    desc = _desc([PY, "-c", "import sys; sys.exit(4)"])
    res = run_descriptor(desc, {})
    assert res["badge"] == ("unavailable", "scan failed (exit 4)")


def test_run_descriptor_empty_output_is_unavailable():
    """exit 0 but no artifact written -> 'scan produced no output', never a green (#15)."""
    desc = _desc([PY, "-c", "pass"], artifact_name="a.json")
    res = run_descriptor(desc, {})
    assert res["badge"] == ("unavailable", "scan produced no output")


def test_run_descriptor_missing_tool_is_unavailable():
    """A tool that isn't on PATH -> 'tool not found', a badge not a traceback."""
    res = run_descriptor(_desc(["/no/such/binary/xyz"]), {})
    assert res["badge"][0] == "unavailable"
    assert "not found" in res["error"]


def test_run_descriptor_nul_byte_is_unavailable_not_traceback():
    """#183: a NUL byte in the argv makes subprocess raise ValueError -> unavailable badge."""
    desc = {"id": "n", "run": {"base": ["echo"], "positional_from": "{host}"}}
    res = run_descriptor(desc, {"host": "x\x00y"})
    assert res["badge"] == ("unavailable", "tool could not be launched")


def test_run_descriptor_descriptor_error_is_unavailable():
    """An unresolved {token} in the argv is a descriptor bug -> unavailable, never shipped."""
    desc = {"id": "d", "run": {"base": ["echo"], "positional_from": "{missing}"}}
    res = run_descriptor(desc, {})
    assert res["badge"][0] == "unavailable"
    assert "descriptor error" in res["badge"][1]


def test_run_descriptor_timeout_is_unavailable():
    """A tool that outruns its timeout -> 'tool timed out', a badge not a hang."""
    desc = _desc([PY, "-c", "import time; time.sleep(30)"], timeout_s=1)
    res = run_descriptor(desc, {})
    assert res["badge"] == ("unavailable", "tool timed out")


def test_run_descriptor_image_backend_rewrites_to_docker(monkeypatch):
    """When the local binary is absent but run.image is set, the engine runs it via docker."""
    captured = {}

    def fake_launch(argv, run, workdir, env):
        captured["argv"] = argv
        return {"error": "x", "badge": ("unavailable", "no docker")}

    monkeypatch.setattr(resolve, "_resolve", lambda c: None)  # nothing on PATH -> image mode
    monkeypatch.setattr(facade, "_launch", fake_launch)
    desc = {"id": "img", "run": {"base": ["qureddy", "scan"], "image": "ghcr.io/x/qureddy:1"}}
    run_descriptor(desc, {})
    assert captured["argv"][:5] == ["docker", "run", "--rm", "--pull=always", "ghcr.io/x/qureddy:1"]


# --- _validate: the 3-state badge state machine --------------------------------------------


def test_validate_no_validator_declared(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    assert _validate({"id": "t"}, tmp_path, art)[0] == "none"


def test_validate_selector_with_no_match_is_none(tmp_path):
    """#43: a validate.by whose key matches no case and has no default is 'none', never green."""
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"id": "t", "validate": {"by": ["fmt"], "cases": {}}}
    assert _validate(desc, tmp_path, art, {"fmt": "json"})[0] == "none"


def test_validate_missing_validator_binary_is_unavailable(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"id": "t", "validate": {"argv": ["nonexistent-xyz"], "badge_rule": {"pass_if": {}}}}
    assert _validate(desc, tmp_path, art)[0] == "unavailable"


def test_validate_pass_fail_and_unavailable_rules(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    # `true` exits 0 -> pass_if matches -> valid
    ok = {"id": "t", "validate": {"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}}}
    assert _validate(ok, tmp_path, art)[0] == "valid"
    # `false` exits 1 -> fail_if matches -> invalid
    bad = {
        "id": "t",
        "validate": {
            "argv": ["false"],
            "badge_rule": {"fail_if": {"exit": 1}, "otherwise": "none"},
        },
    }
    assert _validate(bad, tmp_path, art)[0] == "invalid"
    # unavailable_if wins first
    infra = {
        "id": "t",
        "validate": {"argv": ["true"], "badge_rule": {"unavailable_if": {"exit": 0}}},
    }
    assert _validate(infra, tmp_path, art)[0] == "unavailable"


def test_validate_otherwise_default_when_nothing_matches(tmp_path):
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"id": "t", "validate": {"argv": ["true"], "badge_rule": {"fail_if": {"exit": 9}}}}
    # nothing matched -> otherwise defaults to 'invalid'
    assert _validate(desc, tmp_path, art)[0] == "invalid"


def test_validate_exception_is_unavailable(tmp_path, monkeypatch):
    art = tmp_path / "a.json"
    art.write_text("{}")

    def boom(*a, **k):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(facade.subprocess, "run", boom)
    desc = {"id": "t", "validate": {"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}}}
    assert _validate(desc, tmp_path, art) == ("unavailable", "validator error: RuntimeError")


def test_apply_badge_rule_fail_detail_grep():
    rule = {"fail_if": {"stdout_contains": "ERR"}, "fail_detail_grep": "ERR", "otherwise": "none"}
    state, detail = _apply_badge_rule(rule, "line1\nERR: something bad\nline3", 0)
    assert state == "invalid"
    assert "ERR: something bad" in detail


def test_fail_detail_without_grep_is_empty():
    assert _fail_detail({}, "anything") == ""


# --- _match: fail-closed condition evaluation ----------------------------------------------


def test_match_unknown_key_fails_closed():
    assert _match({"stdout_has": "x"}, "x", 0) is False  # typo'd key -> never a green
    assert _match({}, "x", 0) is False  # empty condition -> never a green


def test_match_each_subcondition():
    assert _match({"stdout_contains": "ok"}, "all ok", 0) is True
    assert _match({"stdout_contains_any": ["a", "b"]}, "has b", 0) is True
    assert _match({"stdout_not_contains": "bad"}, "all good", 0) is True
    assert _match({"stdout_not_contains": "bad"}, "is bad", 0) is False
    assert _match({"exit": 0}, "", 0) is True
    assert _match({"exit": 0}, "", 1) is False


# --- _expand_brand / _input_argv ------------------------------------------------------------


def test_expand_brand_version_cmd(monkeypatch):
    monkeypatch.setattr(facade, "_tool_version", lambda argv: "9.9.9")
    d = {"brand": {"name": "x", "version_cmd": ["tool", "--version"]}}
    _expand_brand(d)
    assert d["brand"]["version"] == "9.9.9"
    assert "version_cmd" not in d["brand"]


def test_expand_brand_without_version_cmd_expands_env(monkeypatch):
    monkeypatch.setenv("BS_UX_TEST_VER", "1.2.3")
    d = {"brand": {"version": "${BS_UX_TEST_VER}"}}
    _expand_brand(d)
    assert d["brand"]["version"] == "1.2.3"


def test_input_argv_shapes():
    assert _input_argv({"name": "p", "positional": True}, {"p": "v"}) == ([], ["v"])
    assert _input_argv({"name": "p", "positional": True}, {"p": ""}) == ([], [])
    assert _input_argv({"name": "f", "flag": "--f"}, {"f": True}) == (["--f"], [])
    assert _input_argv({"name": "f", "flag": "--f"}, {"f": False}) == ([], [])
    assert _input_argv({"name": "a", "arg": "--a"}, {"a": "x"}) == (["--a", "x"], [])
    assert _input_argv({"name": "a", "arg": "--a"}, {"a": False}) == ([], [])
    assert _input_argv({"name": "n"}, {}) == ([], [])  # unmapped input contributes nothing


# --- _render helpers ------------------------------------------------------------------------


def test_find_prop_nested_dict_and_list():
    doc = {"a": [{"x": 1}, {"name": "target", "value": 42}]}
    assert _find_prop(doc, "target") == 42
    assert _find_prop(doc, "missing") is None
    assert _find_prop("scalar", "target") is None


def test_search_children_empty():
    assert _search_children([], "x") is None


# --- resolve.environment: provenance rows ---------------------------------------------------


def test_environment_local_tool_and_validator(monkeypatch):
    monkeypatch.setattr(
        resolve, "_resolve", lambda c: f"/usr/bin/{c}" if c in ("mytool", "checker") else None
    )
    monkeypatch.setattr(resolve, "_probe_version", lambda p: "1.0")
    desc = {
        "run": {"base": ["mytool", "scan"]},
        "validate": {"argv": ["checker", "--in", "{artifact}"], "badge_rule": {}},
        "actions": [{"label": "Ping", "argv": ["mytool", "ping"]}],
    }
    rows = resolve.environment(desc)
    roles = {r["role"]: r for r in rows}
    assert roles["tool"]["cmd"] == "mytool" and roles["tool"]["ok"] is True
    assert roles["validator"]["cmd"] == "checker"
    # the action reuses `mytool` (already seen) so it does not add a duplicate row
    assert [r["cmd"] for r in rows] == ["mytool", "checker"]


def test_environment_image_fallback(monkeypatch):
    monkeypatch.setattr(resolve, "_resolve", lambda c: "/usr/bin/docker" if c == "docker" else None)
    desc = {"run": {"base": ["qureddy"], "image": "ghcr.io/x/qureddy:1"}}
    rows = resolve.environment(desc)
    assert rows[0]["cmd"] == "ghcr.io/x/qureddy:1"
    assert rows[0]["version"] == "(image)" and rows[0]["ok"] is True


def test_environment_python_validator_and_action(monkeypatch):
    monkeypatch.setattr(resolve, "_resolve", lambda c: None)  # nothing resolves
    monkeypatch.setattr(resolve, "_probe_version", lambda p: "")
    desc = {
        "run": {},  # no tool declared
        "validate": {"argv": ["{python}", "-c", "..."], "badge_rule": {}},
        "actions": [{"label": "Act", "argv": ["someaction"]}, {"label": "Empty", "argv": []}],
    }
    rows = resolve.environment(desc)
    cmds = [r["cmd"] for r in rows]
    assert "python" in cmds  # {python} validator resolves to the interpreter
    assert "someaction" in cmds
    py_row = next(r for r in rows if r["cmd"] == "python")
    assert py_row["path"] == sys.executable  # {python} resolves to the running interpreter
