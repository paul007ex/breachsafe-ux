"""Canonical argv model + end-of-options guard (#9): base, options, --, positionals."""

from __future__ import annotations

from breachsafe_ux.facade import _build_argv


def _desc(inputs, **run):
    return {"id": "t", "run": {"base": ["tool"], **run}, "inputs": inputs}


def _argv(desc, params):
    return _build_argv(desc, params, dict(params))


def test_order_is_base_options_dashdash_positionals():
    d = _desc(
        [
            {"name": "target", "type": "text", "positional": True},
            {"name": "fmt", "type": "enum", "arg": "--format", "choices": ["a"]},
            {"name": "flg", "type": "bool", "flag": "--flag"},
        ]
    )
    assert _argv(d, {"target": "example.com", "fmt": "a", "flg": True}) == [
        "tool",
        "--format",
        "a",
        "--flag",
        "--",
        "example.com",
    ]


def test_leading_dash_positional_is_guarded():
    d = _desc([{"name": "target", "type": "text", "positional": True}])
    argv = _argv(d, {"target": "--openssl=/tmp/x"})
    assert argv == ["tool", "--", "--openssl=/tmp/x"]
    assert argv.index("--") < argv.index("--openssl=/tmp/x")  # value can't be parsed as a flag


def test_no_positionals_means_no_dashdash():
    d = _desc([{"name": "flg", "type": "bool", "flag": "--flag"}])
    argv = _argv(d, {"flg": True})
    assert "--" not in argv and argv == ["tool", "--flag"]


def test_no_end_of_options_opt_out():
    d = _desc([{"name": "target", "type": "text", "positional": True}], no_end_of_options=True)
    assert _argv(d, {"target": "x"}) == ["tool", "x"]


def test_positional_from_lands_after_dashdash():
    d = _desc(
        [{"name": "host", "type": "text"}, {"name": "port", "type": "int"}],
        positional_from="{host}:{port}",
    )
    assert _argv(d, {"host": "h", "port": 443}) == ["tool", "--", "h:443"]


def test_static_argv_is_untouched():
    d = {"id": "t", "run": {"argv": ["tool", "--flag", "{v}"]}}
    assert _build_argv(d, {}, {"v": "1"}) == ["tool", "--flag", "1"]


def test_empty_and_false_values_are_omitted():
    d = _desc(
        [
            {"name": "opt", "type": "text", "arg": "--opt"},
            {"name": "pos", "type": "text", "positional": True},
            {"name": "flg", "type": "bool", "flag": "--flag"},
        ]
    )
    assert _argv(d, {"opt": "", "pos": "", "flg": False}) == ["tool"]
