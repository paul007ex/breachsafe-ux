# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Unit-level badge-state guards for the breachsafe-ux engine.

These prove the 3-state badge cannot fabricate a green, and they need **no Docker and no
tool source** — the validator is `true` and the runner is `echo`. They were written as
regressions for two real engine bugs (breachsafe/qureddy#182, #183).

They previously lived in ``test_badge_states.py``, which carries a module-level ``live``
mark so CI deselects it (``-m "not live"``). That meant these guards executed in no
pipeline at all: deselected in CI, deselected in the release gate, and skipped locally
when the live tooling is absent. Extracted here so they run on every commit (#142).

The genuinely live end-to-end cases (t1-t5, real mint-oscal + oscal-cli in Docker) stay
in ``test_badge_states.py``.
"""

from __future__ import annotations

import pytest

from breachsafe_ux import facade
from breachsafe_ux.facade import run_descriptor


@pytest.mark.parametrize(
    "rule",
    [
        {"pass_if": {}, "otherwise": "invalid"},  # empty condition
        {
            "pass_if": {"stdout_has": "ok"},
            "otherwise": "invalid",
        },  # typo'd key (was stdout_contains)
    ],
)
def test_t6_validate_fails_closed_on_malformed_pass_if(tmp_path, rule):
    """#182: an empty or all-unrecognized ``pass_if`` must NEVER vacuously return ``valid``.

    The validator here (`true`) runs and exits 0 with no output; the badge must come from the
    RULE, and a rule that checks nothing is a descriptor bug, not a green.
    """
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {"id": "t", "validate": {"argv": ["true"], "badge_rule": rule, "timeout_s": 10}}
    state, _ = facade._validate(desc, tmp_path, art)
    assert state != "valid", f"fail-open false-green on {rule!r}"


def test_t6b_validate_still_valid_on_wellformed_rule(tmp_path):
    """Guard the guard: a real, well-formed ``exit: 0`` rule must still pass (no over-fix)."""
    art = tmp_path / "a.json"
    art.write_text("{}")
    desc = {
        "id": "t",
        "validate": {
            "argv": ["true"],
            "badge_rule": {
                "pass_if": {"exit": 0},
                "fail_if": {"exit": 1},
                "otherwise": "unavailable",
            },
            "timeout_s": 10,
        },
    }
    assert facade._validate(desc, tmp_path, art)[0] == "valid"


def test_t7_nul_param_is_unavailable_not_traceback():
    """#183: a NUL byte in a param must degrade to an ``unavailable`` badge, never raise.

    ``subprocess.run`` raises ``ValueError: embedded null byte``; the engine must catch it and
    return the result dict so the UI shows a badge, not a raw traceback.
    """
    desc = {
        "id": "t2",
        "run": {"base": ["echo"], "positional_from": "{host}"},
        "inputs": [{"name": "host", "type": "text"}],
    }
    res = run_descriptor(desc, {"host": "example.com\x00"})  # must not raise
    assert res["badge"][0] == "unavailable", res["badge"]
