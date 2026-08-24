# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Unit coverage for the Go evidence-export boundary."""

from __future__ import annotations

import json
from pathlib import Path

from breachsafe_ux import evidence


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


def test_report_failures_are_safe(tmp_path: Path) -> None:
    assert evidence.run_evidence_report(_chain(), None) == (
        False,
        {"error": "Run the scan first; no scan artifact is available."},
    )
    ok, output = evidence.run_evidence_report(_chain(), str(tmp_path / "missing.json"))
    assert not ok
    assert "Missing scan artifacts" in output["error"]
