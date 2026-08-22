"""Descriptor-declared action buttons (#5): generic argv, not host functions."""

from __future__ import annotations

import sys

import yaml

from breachsafe_ux.facade import load_descriptors, run_action
from breachsafe_ux.resolve import ROOT


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
    assert set(load_descriptors()) == {"qureddy", "qureddy-ssh", "mint-oscal"}


def test_collect_file_input_is_filepath_string():
    """gr.File (Gradio 6, type=filepath) yields the upload's path as a str; _collect must pass it
    through — not call `.name` (the pre-6 file-object API), which broke manual upload on the
    mint-oscal tab. Regression for that AttributeError.
    """
    from breachsafe_ux.app import _collect

    desc = {
        "inputs": [
            {"name": "source", "type": "enum"},
            {"name": "source_file", "type": "file"},
        ]
    }
    params = _collect(desc, ["cbom", "/tmp/uploaded/cbom.json"])
    assert params == {"source": "cbom", "source_file": "/tmp/uploaded/cbom.json"}


def test_tool_source_prefers_local_then_image(monkeypatch):
    """The engine runs a local binary if it resolves, else falls back to run.image (docker),
    else reports missing. Backs run_descriptor / tool_available / environment (#docker-backend).
    """
    from breachsafe_ux import resolve

    run = {"base": ["qureddy", "scan", "tls"], "image": "ghcr.io/breachsafe/qureddy:latest"}
    monkeypatch.setattr(
        resolve, "_resolve", lambda c: "/usr/local/bin/qureddy" if c == "qureddy" else None
    )
    assert resolve._tool_source(run)[0] == "local"
    monkeypatch.setattr(resolve, "_resolve", lambda c: None)  # nothing on PATH
    assert resolve._tool_source(run) == ("image", "ghcr.io/breachsafe/qureddy:latest")
    assert resolve._tool_source({"base": ["qureddy"]})[0] == "missing"  # no image, not on PATH
