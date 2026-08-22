# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Regression tests for GHSA-6ffp-258g-fvp5 (engine-level false-VALID paths).

Two engine paths could badge VALID a validator never actually gave, breaking the "never a
false green" contract. These exercise the real pipeline with cheap real binaries
(``true``/python ``-c``) and a temp RUN_ROOT — no Docker, no bundled tools:

  * **S1 — stale-artifact false-green.** The per-run workdir must be unique per invocation, so a
    second run of the same descriptor+params whose tool now writes nothing can never validate the
    previous run's artifact.
  * **S2 — VALID from a failed validator.** A ``pass_if`` match must also require the validator to
    have exited 0, unless the descriptor explicitly pins ``exit`` in ``pass_if`` (opt-out).
"""

from __future__ import annotations

import sys

import pytest

from breachsafe_ux import facade
from breachsafe_ux.facade import _validate, run_descriptor

PY = sys.executable


@pytest.fixture(autouse=True)
def _tmp_run_root(tmp_path, monkeypatch):
    """Keep every run's workdir inside the test's tmp dir, never the user's home."""
    monkeypatch.setattr(facade, "RUN_ROOT", tmp_path / "runs")


# --- S1: unique per-invocation workdir -> no stale-artifact reuse ---------------------------


def test_s1_second_run_does_not_reuse_prior_artifact(tmp_path):
    """A tool that writes a valid artifact once, then soft-fails (exit 0, writes nothing) on a
    re-run with identical params, must NOT badge the prior run's artifact VALID again.

    Pre-fix the workdir was deterministic (uuid5 of id+params) and never cleaned, so run 2 saw
    run 1's ``artifact.json`` and false-greened. With a unique per-invocation workdir, run 2 gets
    a fresh empty dir -> "scan produced no output" -> unavailable, never valid.
    """
    counter = tmp_path / "invocations"
    # argv[1] = artifact path; argv[2] = the cross-invocation counter file. Write the artifact only
    # on the very first invocation; every later run exits 0 having written nothing (soft-fail).
    tool_src = (
        "import os, sys\n"
        "c = sys.argv[2]\n"
        "n = int(open(c).read()) if os.path.exists(c) else 0\n"
        "open(c, 'w').write(str(n + 1))\n"
        "if n == 0:\n"
        "    open(sys.argv[1], 'w').write('{\"ok\": true}')\n"
    )
    desc = {
        "id": "stale",
        "run": {
            "argv": [PY, "-c", tool_src, "{artifact}", str(counter)],
            "artifact_name": "a.json",
        },
        "validate": {"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}},
    }
    params = {"host": "example.com"}

    first = run_descriptor(desc, params)
    assert first["badge"][0] == "valid", first["badge"]

    second = run_descriptor(desc, params)  # identical params, tool now writes nothing
    assert second["badge"][0] == "unavailable", second["badge"]
    assert second["badge"][0] != "valid"


def test_s1_repeated_runs_get_distinct_workdirs(tmp_path):
    """Two runs of the same descriptor+params never share a workdir (also kills the #104 race)."""
    desc = {
        "id": "u",
        "run": {
            "argv": [PY, "-c", "print('{}')"],
            "artifact_from": "stdout",
            "artifact_name": "a.json",
        },
    }
    params = {"host": "h"}
    one = run_descriptor(desc, params)["artifact_path"]
    two = run_descriptor(desc, params)["artifact_path"]
    assert one != two


# --- S2: a validator must exit 0 to badge VALID (unless pass_if pins exit) -------------------


def test_s2_nonzero_validator_with_valid_in_stdout_is_not_valid(tmp_path):
    """A validator that PRINTS "is valid" but exits nonzero must not badge VALID (#GHSA S2).

    ``pass_if`` here is a naive substring with no pinned ``exit``; pre-fix the substring match
    alone returned valid, so a crashing validator whose output merely contained the token
    false-greened. With the fix, a nonzero exit falls through to ``fail_if`` -> invalid.
    """
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "id": "t",
        "validate": {
            "argv": [
                PY,
                "-c",
                "import sys; sys.stdout.write('the artifact is valid'); sys.exit(1)",
            ],
            "badge_rule": {
                "pass_if": {"stdout_contains": "valid"},
                "fail_if": {"exit": 1},
                "otherwise": "invalid",
            },
        },
    }
    state, _ = _validate(desc, tmp_path, art)
    assert state == "invalid", state
    assert state != "valid"


def test_s2_zero_exit_substring_pass_still_valid(tmp_path):
    """Guard the guard: a validator that exits 0 and matches an (exit-less) substring ``pass_if``
    is still VALID — the fix only rejects the nonzero case, it does not break legitimate passes."""
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "id": "t",
        "validate": {
            "argv": [PY, "-c", "import sys; sys.stdout.write('is valid')"],  # exits 0
            "badge_rule": {"pass_if": {"stdout_contains": "valid"}},
        },
    }
    assert _validate(desc, tmp_path, art)[0] == "valid"


def test_s2_pass_if_pinning_exit_still_valid(tmp_path):
    """The opt-out: a descriptor that explicitly pins ``exit`` in ``pass_if`` keeps working — this
    is exactly what the two bundled qureddy CBOM descriptors do (``pass_if: {exit: 0}``)."""
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"id": "t", "validate": {"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}}}
    assert _validate(desc, tmp_path, art)[0] == "valid"
