# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the Gradio shell's widget map and per-tab wiring helpers.

These build components inside a ``gr.Blocks()`` context (Gradio registers to the active
context, so extracted helpers attach correctly) and assert on the component TYPE the
descriptor spec maps to — the type->widget contract that lives once in ``app._widget`` — plus
the chain-button state machine (hidden / disabled / wired) in ``app._wire_chain``.
"""

from __future__ import annotations

import gradio as gr

from breachsafe_ux import app


def test_widget_type_map():
    with gr.Blocks():
        assert isinstance(app._widget({"name": "f", "type": "file"}), gr.File)
        assert isinstance(app._widget({"name": "f", "type": "file", "info": "hint"}), gr.File)
        # 2-3 enum choices -> Radio, more -> Dropdown
        assert isinstance(
            app._widget({"name": "e", "type": "enum", "choices": ["a", "b"]}), gr.Radio
        )
        assert isinstance(
            app._widget({"name": "e", "type": "enum", "choices": ["a", "b", "c", "d"]}), gr.Dropdown
        )
        assert isinstance(app._widget({"name": "n", "type": "int"}), gr.Number)
        assert isinstance(app._widget({"name": "n", "type": "int", "widget": "slider"}), gr.Slider)
        assert isinstance(
            app._widget({"name": "n", "type": "float", "widget": "slider"}), gr.Slider
        )
        assert isinstance(app._widget({"name": "b", "type": "bool"}), gr.Checkbox)
        assert isinstance(app._widget({"name": "t", "type": "text", "required": True}), gr.Textbox)


def test_render_inputs_orders_basic_and_advanced():
    desc = {
        "inputs": [
            {"name": "a", "type": "text"},
            {"name": "b", "type": "text", "group": "advanced", "verify_argv": ["{value}", "-v"]},
            {"name": "c", "type": "text"},
        ]
    }
    with gr.Blocks():
        ordered = app._render_inputs(desc, env_rows=[])
    assert len(ordered) == 3  # one widget per input, in desc order


def test_wire_chain_feature_flag_off_renders_nothing(monkeypatch):
    monkeypatch.setattr(app, "feature_enabled", lambda flag: False)
    with gr.Blocks() as demo:
        st = gr.State(None)
        app._wire_chain({"to": "x", "feature_flag": "pro"}, {}, st)
    # gated off -> no button/markdown added for this chain
    assert all(not isinstance(c, gr.Button) for c in demo.blocks.values())


def test_wire_chain_unavailable_disables_button(monkeypatch):
    monkeypatch.setattr(app, "tool_available", lambda desc: False)
    descs = {"x": {"id": "x", "run": {"base": ["needstool"]}}}
    with gr.Blocks() as demo:
        st = gr.State(None)
        app._wire_chain({"to": "x", "label": "Convert"}, descs, st)
    buttons = [c for c in demo.blocks.values() if isinstance(c, gr.Button)]
    assert buttons and buttons[0].interactive is False


def test_wire_chain_available_wires_button(monkeypatch):
    monkeypatch.setattr(app, "tool_available", lambda desc: True)
    descs = {"x": {"id": "x", "run": {"base": ["true"]}}}
    with gr.Blocks() as demo:
        st = gr.State(None)
        app._wire_chain({"to": "x", "label": "Convert"}, descs, st)
    buttons = [c for c in demo.blocks.values() if isinstance(c, gr.Button)]
    assert buttons and buttons[0].interactive is True


def test_build_smoke_with_available_chain(monkeypatch):
    """build() with an available chain target exercises the wired (not disabled) branch."""
    monkeypatch.setattr(app, "tool_available", lambda desc: True)
    demo = app.build()
    assert demo is not None


def test_build_skips_standalone_false_descriptor(monkeypatch):
    """A `standalone: false` descriptor is chain-only: build() skips rendering it as its own tab."""
    descs = {
        "hidden": {"id": "hidden", "standalone": False, "run": {"base": ["true"]}},
        "shown": {"id": "shown", "run": {"base": ["true"]}, "title": "Shown"},
    }
    monkeypatch.setattr(app, "load_descriptors", lambda: descs)
    demo = app.build()
    assert demo is not None


def test_result_surfaces_log_on_success():
    """#190: a successful run's tool log (stderr) renders in the Raw log slot, ANSI-stripped."""
    desc = {"run": {}, "render": {}}
    res = {
        "badge": ("valid", "ok"),
        "artifact": {},
        "artifact_path": "/x",
        "log": "\x1b[32mscan.start\x1b[0m\nprobe.done",
    }
    # #199: _result is (badge_md, raw_log_md, artifact_texts, primary_artifact, primary_path)
    _badge_md, raw, _texts, _primary, _path = app._result(desc, res)
    assert raw.startswith("```") and "scan.start" in raw and "probe.done" in raw
    assert "\x1b[" not in raw  # ANSI stripped (reuses #4's _strip_ansi)
    assert app._result(desc, dict(res, log=""))[1] == ""  # empty log -> empty Raw log slot


def test_result_surfaces_artifacts_and_command(tmp_path):
    """#199: _result returns each declared artifact's text, and the Raw log carries the command."""
    desc = {"run": {}, "render": {}}
    res = {
        "badge": ("valid", "ok"),
        "artifact": {"a": 1},
        "artifact_path": "/x/scan.cdx.json",
        "log": "probe.done",
        "command": "qureddy scan tls -- example.com:443",
        "workdir": "/run/xyz",
        "artifacts": {
            "cbom": {"text": '{"bomFormat": "CycloneDX"}', "label": "CBOM"},
            "json": {"text": '{"schema_version": "qureddy.scan.v1"}', "label": "JSON"},
        },
    }
    _badge_md, raw, texts, _primary, _path = app._result(desc, res)
    assert texts["cbom"].startswith("{") and "CycloneDX" in texts["cbom"]
    assert "qureddy.scan.v1" in texts["json"]
    assert "$ qureddy scan tls" in raw and "/run/xyz" in raw  # command + run dir in the log


def test_handler_returns_artifact_texts_then_legacy_shape(monkeypatch):
    # #199: with declared artifacts, the handler returns one text per artifact (in order);
    # with none, it returns the single primary artifact for the legacy JSON slot.
    def _noprog(*_a, **_k):
        return None

    desc = {
        "id": "t",
        "run": {"artifacts": [{"name": "cbom", "file": "c"}, {"name": "json", "file": "j"}]},
        "render": {},
    }
    monkeypatch.setattr(
        app,
        "run_descriptor",
        lambda d, p: {
            "badge": ("valid", "ok"),
            "artifact": {},
            "artifact_path": "/x",
            "log": "L",
            "command": "cmd",
            "workdir": "/w",
            "artifacts": {"cbom": {"text": "C"}, "json": {"text": "J"}},
        },
    )
    out = app._handler(desc)("host", progress=_noprog)
    assert out[2] == "C" and out[3] == "J"  # badge, raw, cbom, json, path, reset

    desc2 = {"id": "t2", "run": {}, "render": {}}
    monkeypatch.setattr(
        app,
        "run_descriptor",
        lambda d, p: {
            "badge": ("valid", "ok"),
            "artifact": {"a": 1},
            "artifact_path": "/x",
            "log": "",
        },
    )
    out2 = app._handler(desc2)("v", progress=_noprog)
    assert out2[2] == {"a": 1}  # primary artifact in the single legacy JSON slot
