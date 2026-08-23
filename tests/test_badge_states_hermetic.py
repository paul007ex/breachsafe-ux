# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Hermetic badge-state contract — the "never a false green" property, run in EVERY pipeline (#142).

`tests/test_badge_states.py` proves the same 3-state badge end-to-end through the REAL mint-oscal
tool + oscal-cli-in-Docker, so it is marked ``live`` and is DESELECTED by CI/the release gate
(``-m "not live"``) and skipped on a fresh clone — i.e. the core correctness property this product
is built on executes in no pipeline. These tests exercise the identical engine contract through the
real ``run_descriptor``/``_validate`` pipeline with cheap fake tools/validators (``true``/``false``/
python ``-c``, an absent binary) — no tool, no Docker, no network — so the contract is verified on
every run. The live suite remains as a deeper end-to-end integration check.

Contract (facade.run_descriptor / _validate):
  * validator ran and blessed the artifact      -> ``valid``
  * validator ran and rejected the artifact      -> ``invalid``      (never a fabricated green)
  * validator could not run (absent binary)       -> ``unavailable``  (never a fabricated green)
  * the tool itself failed / produced no output   -> ``unavailable``  (never ``valid``)
  * a malicious input value is passed as argv data, never shell-interpreted
"""

from __future__ import annotations

import sys

import pytest

from breachsafe_ux import facade
from breachsafe_ux.facade import run_descriptor

PY = sys.executable

# A tool that writes a well-formed artifact to {artifact} and exits 0.
_WRITES_ARTIFACT = "import sys; open(sys.argv[1], 'w').write('{\"ok\": true}')"


@pytest.fixture(autouse=True)
def _tmp_run_root(tmp_path, monkeypatch):
    """Keep every run's workdir inside the test's tmp dir, never the user's home."""
    monkeypatch.setattr(facade, "RUN_ROOT", tmp_path / "runs")


def _desc(validate: dict | None) -> dict:
    """A descriptor whose tool writes a good artifact; the validator behavior is the variable."""
    desc: dict = {
        "id": "hermetic-badge",
        "run": {"argv": [PY, "-c", _WRITES_ARTIFACT, "{artifact}"], "artifact_name": "a.json"},
    }
    if validate is not None:
        desc["validate"] = validate
    return desc


def test_validator_blessed_artifact_is_valid():
    """Tool writes an artifact and the validator exits 0 -> VALID is reachable (t1)."""
    desc = _desc({"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}})
    res = run_descriptor(desc, {"host": "example.com"})
    assert res["badge"][0] == "valid", res["badge"]


def test_validator_rejected_artifact_is_invalid():
    """Validator RAN and rejected (nonzero) -> INVALID, never a fabricated green (t2)."""
    desc = _desc(
        {"argv": ["false"], "badge_rule": {"pass_if": {"exit": 0}, "fail_if": {"exit": 1}}}
    )
    res = run_descriptor(desc, {"host": "example.com"})
    assert res["badge"][0] == "invalid", res["badge"]
    assert res["badge"][0] != "valid"


def test_absent_validator_is_unavailable():
    """Validator binary does not exist -> UNAVAILABLE, never green (t4)."""
    desc = _desc(
        {"argv": ["breachsafe-no-such-validator-xyz"], "badge_rule": {"pass_if": {"exit": 0}}}
    )
    res = run_descriptor(desc, {"host": "example.com"})
    assert res["badge"][0] == "unavailable", res["badge"]
    assert res["badge"][0] != "valid"


def test_tool_failure_is_never_valid():
    """The tool itself fails (nonzero exit, no artifact) -> never VALID (t5)."""
    desc = {
        "id": "hermetic-badge",
        "run": {"argv": [PY, "-c", "import sys; sys.exit(3)"], "artifact_name": "a.json"},
        "validate": {"argv": ["true"], "badge_rule": {"pass_if": {"exit": 0}}},
    }
    res = run_descriptor(desc, {"host": "example.com"})
    assert res["badge"][0] != "valid", res["badge"]


def test_no_external_validator_is_none_not_valid():
    """A descriptor with no `validate` block badges `none` (no external validator), never green."""
    res = run_descriptor(_desc(None), {"host": "example.com"})
    assert res["badge"][0] == "none", res["badge"]
    assert res["badge"][0] != "valid"
