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


def test_numeric_zero_arg_is_kept():
    # #171: a numeric 0 / 0.0 must reach the argv. The old `v not in (None, "", False)` check
    # dropped it because 0 == False in Python (e.g. --retries 0, --maxfail 0 were silently lost).
    d = _desc(
        [
            {"name": "maxfail", "type": "int", "arg": "--maxfail"},
            {"name": "delay", "type": "float", "arg": "--delay"},
        ]
    )
    assert _argv(d, {"maxfail": 0, "delay": 0.0}) == ["tool", "--maxfail", "0", "--delay", "0.0"]
    # a nonzero still works and the empty sentinel is still dropped
    assert _argv(d, {"maxfail": 3, "delay": ""}) == ["tool", "--maxfail", "3"]


def test_repeat_flag_emits_verbosity_level():
    # #3: a count input emits its short flag N times, collapsed to one getopt-style token so a
    # level of 3 reaches qureddy as -vvv, not three separate -v tokens the UI could not express.
    d = _desc([{"name": "verbosity", "type": "int", "repeat_flag": "-v"}])
    assert _argv(d, {"verbosity": 0}) == ["tool"]  # 0 = quiet, flag omitted
    assert _argv(d, {"verbosity": 1}) == ["tool", "-v"]
    assert _argv(d, {"verbosity": 3}) == ["tool", "-vvv"]


def test_repeat_flag_long_form_repeats_as_separate_tokens():
    # A long flag cannot collapse (--verboseverbose is meaningless), so it repeats as tokens.
    d = _desc([{"name": "v", "type": "int", "repeat_flag": "--verbose"}])
    assert _argv(d, {"v": 2}) == ["tool", "--verbose", "--verbose"]


def test_repeat_flag_ignores_non_numeric_level():
    # A stray non-int level must not crash the argv build; treat it as absent.
    d = _desc([{"name": "verbosity", "type": "int", "repeat_flag": "-v"}])
    assert _argv(d, {"verbosity": None}) == ["tool"]
    assert _argv(d, {"verbosity": "x"}) == ["tool"]
