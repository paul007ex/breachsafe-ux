"""Single-source descriptor version via brand.version_cmd (#51)."""

from __future__ import annotations

import sys

import yaml

from breachsafe_ux.facade import ROOT, _tool_version, load_descriptors


def test_tool_version_parses_a_version_token():
    v = _tool_version([sys.executable, "--version"])  # "Python 3.12.x"
    assert v and v[0].isdigit()


def test_tool_version_none_on_bad_command():
    assert _tool_version(["/no/such/binary/xyz", "--version"]) is None


def _write(tmp_path, brand):
    tool = tmp_path / "vt"
    tool.mkdir()
    (tool / "vt.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "id": "vt",
                "run": {"base": ["x"]},
                "brand": {"product": "VT", **brand},
            }
        )
    )


def test_version_cmd_resolves_and_is_stripped(tmp_path, monkeypatch):
    _write(
        tmp_path, {"version_cmd": [sys.executable, "-c", "print('tool 9.9.9')"], "version": "0.0.0"}
    )
    monkeypatch.setenv("BREACHSAFE_UX_TOOLS_DIR", str(tmp_path))
    brand = load_descriptors()["vt"]["brand"]
    assert brand["version"] == "9.9.9"
    assert "version_cmd" not in brand  # resolved and removed


def test_version_cmd_falls_back_on_failure(tmp_path, monkeypatch):
    _write(tmp_path, {"version_cmd": ["/no/such/xyz"], "version": "fallback-1.0"})
    monkeypatch.setenv("BREACHSAFE_UX_TOOLS_DIR", str(tmp_path))
    assert load_descriptors()["vt"]["brand"]["version"] == "fallback-1.0"


def test_qureddy_single_sources_its_version():
    q = yaml.safe_load((ROOT / "tools" / "qureddy" / "qureddy.yaml").read_text())
    assert q["brand"].get("version_cmd") == ["qureddy", "--version"]
