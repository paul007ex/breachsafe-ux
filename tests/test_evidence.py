# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Unit coverage for the Go evidence-export boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from breachsafe_ux import evidence, evidence_ui


def _chain() -> dict:
    return {
        "profile": "breachsafe/community",
        "argv": [
            "breachsafe-evidence",
            "render",
            "--request",
            "{request}",
            "--scan-json",
            "{scan}",
            "--cbom",
            "{inventory}",
            "--pdf",
            "{pdf}",
            "--result",
            "{result}",
            "--log",
            "{log}",
            "--zip",
            "{archive}",
        ],
        "artifact_files": {"scan": "scan.json", "inventory": "scan.cdx.json"},
        "request_artifacts": {
            "scan": {"request_key": "scan"},
            "inventory": {"request_key": "cbom"},
        },
        "request_template": {"identity": {}, "scan": {}, "cbom": {}},
        "output_files": {
            "pdf": "report.pdf",
            "result": "report.result.json",
            "log": "pdf-render.log",
            "archive": "results.zip",
        },
    }


def test_workspace_and_request_hashes(tmp_path: Path) -> None:
    chain = _chain()
    (tmp_path / "scan.json").write_text(json.dumps({"target": {"host": "a/b.example"}}))
    (tmp_path / "scan.cdx.json").write_text("{}")
    workdir, paths, request_path, outputs = evidence._evidence_workspace(
        chain, str(tmp_path / "scan.json")
    )
    generated = evidence._write_report_request(chain, workdir, paths, request_path)
    assert generated.tzinfo is not None
    request = json.loads(request_path.read_text())
    assert request["scan"]["expected_sha256"]
    named = evidence._name_report_outputs(paths, outputs, generated)
    assert named["archive"].name.startswith("a-b.example.breachsafe.")
    assert named["pdf"].name.endswith(".pdf")
    no_archive = {"pdf": tmp_path / "report.pdf"}
    assert evidence._name_report_outputs(paths, no_archive, generated) is no_archive


def test_workspace_rejects_escape(tmp_path: Path) -> None:
    chain = _chain()
    chain["artifact_files"]["scan"] = "../outside.json"
    (tmp_path / "scan.cdx.json").write_text("{}")
    with pytest.raises(ValueError, match="escapes run directory"):
        evidence._evidence_workspace(chain, str(tmp_path / "scan.cdx.json"))


def test_report_argv_and_success(monkeypatch, tmp_path: Path) -> None:
    chain = _chain()
    (tmp_path / "scan.json").write_text(json.dumps({"target": {"host": "example.com"}}))
    (tmp_path / "scan.cdx.json").write_text("{}")

    def fake_run(argv, **kwargs):
        for flag in ("--pdf", "--result", "--log", "--zip"):
            Path(argv[argv.index(flag) + 1]).write_text("artifact")
        return type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    monkeypatch.setattr(evidence.subprocess, "run", fake_run)
    ok, output = evidence.run_evidence_report(chain, str(tmp_path / "scan.json"))
    assert ok
    assert output["status"] == "exported"
    assert output["log"] == "ok"

    monkeypatch.setattr(
        evidence.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 1, "stdout": "", "stderr": "bad"}
        )(),
    )
    ok, output = evidence.run_evidence_report(chain, str(tmp_path / "scan.json"))
    assert not ok and "bad" in output["error"]


def test_report_rejects_missing_cli_outputs(monkeypatch, tmp_path: Path) -> None:
    chain = _chain()
    (tmp_path / "scan.json").write_text(json.dumps({"target": {"host": "example.com"}}))
    (tmp_path / "scan.cdx.json").write_text("{}")
    monkeypatch.setattr(
        evidence.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )
    ok, output = evidence.run_evidence_report(chain, str(tmp_path / "scan.json"))
    assert not ok and "did not create" in output["error"]


def test_report_failures_are_safe(tmp_path: Path) -> None:
    assert evidence.run_evidence_report(_chain(), None) == (
        False,
        {"error": "Run the scan first; no scan artifact is available."},
    )
    ok, output = evidence.run_evidence_report(_chain(), str(tmp_path / "missing.json"))
    assert not ok
    assert "Missing scan artifacts" in output["error"]


def test_presentation_helpers_and_handler(monkeypatch, tmp_path: Path) -> None:
    assert evidence_ui.pdf_preview_html(None) == ""
    assert evidence_ui.pdf_open_link(None) == ""
    outside = tmp_path / "report.pdf"
    outside.write_bytes(b"not a pdf")
    assert evidence_ui.pdf_preview_html(str(outside)) == ""
    assert 'target="_blank"' in evidence_ui.pdf_open_link(str(outside))

    monkeypatch.setattr(
        evidence_ui, "run_evidence_report", lambda _chain, _path: (False, {"error": "no"})
    )
    failed = evidence_ui.evidence_chain_handler(_chain())(None, lambda *_args, **_kwargs: None)
    assert failed[0] == "### Export failed\nno"
    monkeypatch.setattr(
        evidence_ui,
        "run_evidence_report",
        lambda _chain, _path: (True, {"archive": "bundle.zip", "pdf": None, "log": "ok"}),
    )
    ready = evidence_ui.evidence_chain_handler(_chain())(None, lambda *_args, **_kwargs: None)
    assert ready[0] == ""


def test_presentation_pdf_render(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"pdf")
    monkeypatch.setattr(evidence_ui, "RUN_ROOT", tmp_path)
    monkeypatch.setattr(evidence_ui.shutil, "which", lambda _name: None)
    assert evidence_ui.pdf_preview_html(str(pdf)) == ""
    monkeypatch.setattr(evidence_ui.shutil, "which", lambda _name: "/usr/bin/pdftoppm")
    preview = tmp_path / "pdf-preview"
    preview.mkdir(exist_ok=True)
    (preview / "page-old.png").write_bytes(b"old")

    def fake_run(_argv, **_kwargs):
        (preview / "page-01.png").write_bytes(b"png")

    monkeypatch.setattr(evidence_ui.subprocess, "run", fake_run)
    rendered = evidence_ui.pdf_preview_html(str(pdf))
    assert "Rendered PDF preview" in rendered
    assert "PDF page 1" in rendered
    monkeypatch.setattr(
        evidence_ui.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("no")),
    )
    assert evidence_ui.pdf_preview_html(str(pdf)) == ""


def test_app_skips_builtin_evidence_chain_button() -> None:
    from breachsafe_ux.app import _wire_chain

    assert _wire_chain({"to": "qureddy", "kind": "pdf_export"}, {}, None) is None
