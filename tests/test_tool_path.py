"""Augmented tool-PATH consistency (#116).

run_descriptor runs subprocesses with the tool-resolution PATH (per-tool ``<tool>/bin`` shims
prepended to the ambient PATH). verify_path, run_action, and _validate must resolve the SAME
way — a bare command that lives only in a tool's ``bin`` shim (not on the ambient PATH) must be
found by all of them, not just run_descriptor.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from breachsafe_ux import facade
from breachsafe_ux.facade import run_action, verify_path


@pytest.fixture
def shim_tools_dir(tmp_path, monkeypatch):
    """A tools dir with one tool whose ``bin`` shim holds a command NOT on the ambient PATH."""
    binp = tmp_path / "mytool" / "bin"
    binp.mkdir(parents=True)
    shim = binp / "shimonly"
    shim.write_text("#!/bin/sh\necho SHIM-RAN\n")
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("BREACHSAFE_UX_TOOLS_DIR", str(tmp_path))
    # Prove the shim is NOT reachable via the ambient PATH, only via the tool bin shim.
    assert not any((Path(d) / "shimonly").exists() for d in os.environ["PATH"].split(os.pathsep))
    return tmp_path


def test_run_action_resolves_via_tool_bin_shim(shim_tools_dir):
    """run_action finds a bare command that lives only in a tool's bin shim (#116)."""
    ok, out = run_action({"label": "x", "argv": ["shimonly"]}, {})
    assert ok is True
    assert "SHIM-RAN" in out


def test_verify_path_resolves_via_tool_bin_shim(shim_tools_dir):
    """verify_path resolves a bare tool name against the augmented tool PATH, like the engine (#116)."""
    ok, line = verify_path("shimonly", ["{value}"])
    assert ok is True
    assert "SHIM-RAN" in line


def test_verify_path_missing_command_still_reports_not_raises(shim_tools_dir):
    """A command in neither the shim nor the ambient PATH still degrades cleanly, never raises."""
    ok, _ = verify_path("no-such-command-xyz", ["{value}"])
    assert ok is False


def test_validate_resolves_validator_via_tool_bin_shim(shim_tools_dir, tmp_path):
    """_validate resolves + runs its validator against the augmented tool PATH (#116): a validator
    present only as a tool bin shim badges from the RULE, not a false 'validator not installed'."""
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "id": "t",
        "validate": {
            "argv": ["shimonly", "{artifact}"],
            "badge_rule": {"pass_if": {"exit": 0}, "otherwise": "invalid"},
            "timeout_s": 10,
        },
    }
    assert facade._validate(desc, tmp_path, art)[0] == "valid"
