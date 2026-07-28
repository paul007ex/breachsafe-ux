"""Honesty / safety pressure tests for the breachsafe-wizard engine.

These exercise the REAL pipeline end-to-end through :func:`run_descriptor` — the real
`mint-oscal` tool (run from source via the ``tools/mint-oscal/bin`` wrapper) and its real
external validator (`oscal-cli` in Docker). Nothing here is mocked; the whole point is to
prove the 3-state badge is honest:

  * validator ran and blessed the artifact        -> ``valid``
  * validator ran and rejected the artifact        -> ``invalid``   (NOT a fabricated green)
  * validator could not run (infra/absent)         -> ``unavailable`` (NOT a fabricated green)

Requirements to run green: Docker up + ``ghcr.io/metaschema-framework/oscal-cli:latest``
pulled, and the tool source trees at ``/Users/paul/claude/{qureddy,breachsafe-oscal}/src``.
Docker Desktop on macOS can only bind-mount paths under ``/Users``; the engine's default run
root (``~/mint-proof/wizard-runs``) already lives there, so we do NOT override it.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from breachsafe_wizard.facade import load_descriptors, run_descriptor

# A minimal, well-formed QuReddy scan.v1 document with a tz-aware timestamp. mint-oscal's
# ``qureddy`` adapter turns this into an OSCAL POA&M that oscal-cli accepts.
GOOD_SCAN = {
    "target": {"locator": "h:443", "host": "h", "port": 443, "scheme": "tls"},
    "scan": {"completed_at": "2026-07-28T02:00:00+00:00"},
    "evidence": [
        {
            "id": "e1",
            "source": "openssl",
            "observation_type": "OBSERVED",
            "probe_result": {"stdout_sha256": "abc", "return_code": 0},
        }
    ],
    "findings": [
        {
            "id": "f1",
            "title": "t",
            "description": "d",
            "severity": "low",
            "readiness": "transitional_hybrid",
            "evidence_ids": ["e1"],
        }
    ],
}

PWNED = Path("/tmp/WIZ_PWNED")


@pytest.fixture(scope="module")
def mint():
    return load_descriptors()["mint-oscal"]


@pytest.fixture()
def fixtures_dir():
    # Docker (macOS) only mounts under /Users, so keep everything under $HOME, not /var-tmp.
    d = Path(tempfile.mkdtemp(prefix="wiz-fixtures-", dir=Path.home()))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _write(d: Path, name: str, obj) -> str:
    p = d / name
    p.write_text(json.dumps(obj))
    return str(p)


def test_t1_good_scan_is_valid(mint, fixtures_dir):
    """A good tz-aware scan.v1 -> oscal-cli accepts the POA&M -> badge == valid."""
    src = _write(fixtures_dir, "good.json", GOOD_SCAN)
    res = run_descriptor(mint, {"source_file": src, "source": "qureddy"})
    assert res["badge"][0] == "valid", res["badge"]


def test_t2_oscal_invalid_timestamp_is_invalid(mint, fixtures_dir):
    """An OSCAL-invalid timestamp is faithfully emitted -> oscal-cli REJECTS it -> invalid.

    (The prototype used a *naive* timestamp; the current mint-oscal normalizes naive values
    to UTC, so that case now legitimately passes. Year 0001 is outside OSCAL's supported
    dateTime range, so it exercises the same honesty property: the external validator RAN
    and rejected the artifact — an honest ``invalid``, never ``unavailable`` or a fake green.)
    """
    bad = copy.deepcopy(GOOD_SCAN)
    bad["scan"]["completed_at"] = "0001-01-01T00:00:00"
    src = _write(fixtures_dir, "bad_ts.json", bad)
    res = run_descriptor(mint, {"source_file": src, "source": "qureddy"})
    assert res["badge"][0] == "invalid", res["badge"]


def test_t3_source_injection_is_argv_safe(mint, fixtures_dir):
    """A shell-metachar-laden ``source`` value can never spawn a command (argv, never shell)."""
    if PWNED.exists():
        PWNED.unlink()
    src = _write(fixtures_dir, "good.json", GOOD_SCAN)
    res = run_descriptor(mint, {"source_file": src, "source": "qureddy; touch /tmp/WIZ_PWNED"})
    assert not PWNED.exists(), "shell injection executed — engine is NOT argv-safe"
    assert res["badge"][0] != "valid", res["badge"]


def test_t4_absent_validator_is_unavailable(mint, fixtures_dir):
    """If the validator binary does not exist, the badge is honestly ``unavailable`` — not green."""
    broken = copy.deepcopy(mint)
    broken["validate"]["argv"][0] = "nonexistent-validator-xyz"
    src = _write(fixtures_dir, "good.json", GOOD_SCAN)
    res = run_descriptor(broken, {"source_file": src, "source": "qureddy"})
    assert res["badge"][0] == "unavailable", res["badge"]


def test_t5_malformed_input_is_not_valid(mint, fixtures_dir):
    """Malformed input makes the tool fail; the badge is never a fabricated ``valid``."""
    src = _write(fixtures_dir, "junk.json", {"not": "a bom"})
    res = run_descriptor(mint, {"source_file": src, "source": "cbom"})
    assert res["badge"][0] != "valid", res["badge"]


# --- Unit-level honesty guards (no Docker / no tool source needed). Regressions for
#     the two engine bugs found on the [ui] track: breachsafe/qureddy#182, #183. ---

from breachsafe_wizard import facade  # noqa: E402


@pytest.mark.parametrize("rule", [
    {"pass_if": {}, "otherwise": "invalid"},                       # empty condition
    {"pass_if": {"stdout_has": "ok"}, "otherwise": "invalid"},     # typo'd key (was stdout_contains)
])
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
    desc = {"id": "t", "validate": {"argv": ["true"],
            "badge_rule": {"pass_if": {"exit": 0}, "fail_if": {"exit": 1}, "otherwise": "unavailable"},
            "timeout_s": 10}}
    assert facade._validate(desc, tmp_path, art)[0] == "valid"


def test_t7_nul_param_is_unavailable_not_traceback():
    """#183: a NUL byte in a param must degrade to an honest ``unavailable`` badge, never raise.

    ``subprocess.run`` raises ``ValueError: embedded null byte``; the engine must catch it and
    return the honest dict so the UI shows a badge, not a raw traceback.
    """
    desc = {"id": "t2", "run": {"base": ["echo"], "positional_from": "{host}"},
            "inputs": [{"name": "host", "type": "text"}]}
    res = run_descriptor(desc, {"host": "example.com\x00"})  # must not raise
    assert res["badge"][0] == "unavailable", res["badge"]
