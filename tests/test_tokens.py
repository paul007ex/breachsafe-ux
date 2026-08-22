"""Substitution token namespace, escaping, and fail-closed behavior (#50)."""
from __future__ import annotations

import pytest

from breachsafe_ux.facade import _build_argv, _DescriptorError, _render


def test_resolves_named_tokens():
    assert _render(["{a}", "x{b}y"], {"a": "1", "b": "2"}) == ["1", "x2y"]


def test_literal_braces_are_escaped():
    # {{ -> {  and  }} -> }  ; and an escaped token is NOT substituted or flagged
    assert _render(["--filter={{ .Name }}"], {}) == ["--filter={ .Name }"]
    assert _render(["{{host}}"], {"host": "SHOULD_NOT_APPEAR"}) == ["{host}"]


def test_unresolved_token_fails_closed():
    with pytest.raises(_DescriptorError, match="unresolved token"):
        _render(["{host}:{prt}"], {"host": "h"})   # {prt} typo -> raise, never ship literal


def test_engine_tokens_pass_through_when_present():
    m = {"artifact": "/w/a.json", "stdout_file": "/w/stdout.txt"}
    assert _render(["validate", "{artifact}", "{stdout_file}"], m) == \
        ["validate", "/w/a.json", "/w/stdout.txt"]


def test_build_argv_positional_from_is_a_template_resolved_once():
    desc = {"id": "t", "run": {"base": ["s", "scan"], "positional_from": "{host}:{port}"},
            "inputs": [{"name": "host", "type": "text"}, {"name": "port", "type": "int"}]}
    mapping = {"host": "h", "port": 443}
    # positional_from is a positional, so it lands after the #9 end-of-options guard.
    assert _build_argv(desc, mapping, mapping) == ["s", "scan", "--", "h:443"]


def test_build_argv_unresolved_positional_from_fails_closed():
    desc = {"id": "t", "run": {"base": ["s"], "positional_from": "{host}:{prt}"},
            "inputs": [{"name": "host", "type": "text"}]}
    with pytest.raises(_DescriptorError, match="unresolved token"):
        _build_argv(desc, {"host": "h"}, {"host": "h"})
