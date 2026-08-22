"""Descriptor-declared action buttons (#5): generic argv, not host functions."""

from __future__ import annotations

import sys

import yaml

from breachsafe_ux.facade import ROOT, load_descriptors, run_action


def test_action_ok_on_exit_zero():
    ok, msg = run_action({"label": "x", "argv": [sys.executable, "-c", "print('hi')"]}, {})
    assert ok is True
    assert "hi" in msg


def test_action_fail_on_nonzero():
    ok, _ = run_action(
        {"label": "x", "argv": [sys.executable, "-c", "import sys; sys.exit(2)"]}, {}
    )
    assert ok is False


def test_action_ok_if_stdout_contains():
    action = {
        "label": "x",
        "argv": [sys.executable, "-c", "print('READY')"],
        "ok_if": {"stdout_contains": "READY"},
    }
    assert run_action(action, {})[0] is True
    action["ok_if"] = {"stdout_contains": "NOPE"}
    assert run_action(action, {})[0] is False


def test_action_renders_input_tokens():
    # {host} comes from params; a value that would hang on stdin can't (stdin is closed)
    ok, msg = run_action(
        {
            "label": "echo",
            "argv": [sys.executable, "-c", "import sys; print(sys.argv[1])", "{host}"],
        },
        {"host": "example.com"},
    )
    assert ok and "example.com" in msg


def test_action_unresolved_token_is_reported_not_raised():
    ok, msg = run_action({"label": "x", "argv": ["echo", "{missing}"]}, {})
    assert ok is False
    assert "unresolved token" in msg


def test_action_bad_command_never_raises():
    ok, msg = run_action({"label": "x", "argv": ["/no/such/binary/xyz"]}, {})
    assert ok is False
    assert "could not run" in msg


def test_qureddy_declares_test_connection_action():
    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    labels = [a["label"] for a in q.get("actions", [])]
    assert "Test connection" in labels


def test_app_build_smoke():
    """The Gradio shell renders every shipped descriptor (incl. actions) without error."""
    from breachsafe_ux.app import build

    demo = build()
    assert demo is not None
    # sanity: descriptors actually loaded through the validated path
    assert set(load_descriptors()) == {"qureddy", "mint-oscal"}
