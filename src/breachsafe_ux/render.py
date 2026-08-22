# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""View: pure HTML/markdown string builders. No Gradio, no logic — given model data, return the
markup app.py hands to gr.HTML/gr.Markdown. Split from app.py so the controller stays wiring-only.
"""

from __future__ import annotations

import base64
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"  # bundled in the package (works installed)
_LOGO = _ASSETS / "logo.png"
_B64 = base64.b64encode(_LOGO.read_bytes()).decode() if _LOGO.exists() else ""
_ICON_DIR = _ASSETS / "icons"
_LICENSE = "Apache-2.0 (open source)"
_HEAD = {
    "valid": "VALID",
    "invalid": "INVALID",
    "unavailable": "UNAVAILABLE",
    "none": "NO EXTERNAL VALIDATOR",
}
_COLOR = {"valid": "#0ba0b6", "invalid": "#b91c1c", "unavailable": "#b45309", "none": "#475569"}
_LEVEL_COLOR = {"high": "#b91c1c", "medium": "#b45309", "ok": "#0ba0b6", "unknown": "#475569"}


def _svg(name: str, px: int = 20) -> str:
    p = _ICON_DIR / f"{name}.svg"
    return (
        p.read_text().replace(
            'width="24" height="24"', f'width="{px}" height="{px}" style="vertical-align:middle"'
        )
        if p.exists()
        else ""
    )


_STATUS_SVG = {
    "valid": _svg("shield-check"),
    "invalid": _svg("circle-x"),
    "unavailable": _svg("triangle-alert"),
    "none": "",
}
_ICON = {"run": str(_ICON_DIR / "scan.svg"), "convert": str(_ICON_DIR / "arrow-right.svg")}


def _link(u: str, t: str) -> str:
    return (
        f'<a href="{u}" target="_blank" rel="noopener" '
        f'style="color:#0ba0b6;text-decoration:none">{t}</a>'
        if u
        else t
    )


def _diag_md(ok: bool, text: str) -> str:
    color = "#0ba0b6" if ok else "#b45309"
    verdict = "OK" if ok else "FAILED"
    return f'<span style="color:{color};font-weight:700">{verdict}</span>: {text}'


def _action_output_md(ok: bool, output: str) -> str:
    """Action result (#97): the OK/FAILED verdict plus the tool's actual captured output in a code
    block, so 'Test connection' shows the real openssl handshake — not a canned one-liner."""
    color = "#0ba0b6" if ok else "#b45309"
    verdict = "OK" if ok else "FAILED"
    fence = output.replace("```", "'''")  # keep tool output from breaking the code fence
    return f'<span style="color:{color};font-weight:700">{verdict}</span>\n\n```\n{fence}\n```'


def _posture_md(posture: dict | None) -> str:
    """Readiness banner from the findings, or "" when the descriptor declares none (#1)."""
    if not posture:
        return ""
    color = _LEVEL_COLOR.get(posture.get("level", ""), "#475569")
    return (
        f'<div style="border-left:5px solid {color};padding:8px 14px;margin:0 0 12px">'
        f'<span style="color:{color};font-weight:800">{posture.get("text", "")}</span></div>\n\n'
    )


def _badge(state: str, detail: str, hi: tuple = (), head_text: str | None = None) -> str:
    """3-state evidence verdict; never green markup for a non-valid state. head_text overrides the
    state word so a descriptor states what was checked, not a bare VALID that implies security (#1).
    """
    color = _COLOR.get(state, "#b45309")
    head = (
        f'<span style="color:{color};font-weight:800;'
        'display:inline-flex;align-items:center;gap:8px">'
        f"{_STATUS_SVG.get(state, '')}{head_text or _HEAD.get(state, state.upper())}</span>"
    )
    body = f"\n\n{detail}" if detail else ""
    h = "\n".join(f"- **{x['label']}:** `{x['value']}`" for x in hi)
    return f"### {head}{body}" + (f"\n\n{h}" if h else "")


def _empty(desc: dict) -> str:
    """Pre-run empty state: what the tool does + what a result looks like (not blank)."""
    artifact = desc["run"].get("artifact_name", "artifact.json")
    return (
        f"### Ready\nRun **{desc['id']}** to produce `{artifact}`. The verdict below is the real "
        "result of an external validator, reported as one of "
        "**VALID / INVALID / VALIDATOR-UNAVAILABLE**. It is never a fabricated green on an empty "
        "or failed run."
    )


_CHIP = (
    "background:rgba(148,163,184,.14);padding:1px 7px;border-radius:5px;"
    "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px"
)


def _env_advanced_md(rows: list[dict]) -> str:
    """Environment provenance as greyed, read-only lines for the Advanced accordion — the binary,
    version, and resolved path behind each descriptor role (#75). Muted so it reads as reference,
    not editable input; the tool row also appears at-a-glance in the header (_env_line)."""
    if not rows:
        return ""
    head = (
        '<div style="color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:.04em;'
        'margin-top:12px;padding-top:10px;border-top:1px solid rgba(148,163,184,.15)">'
        "environment (read-only)</div>"
    )
    out = [head]
    for r in rows:
        mark = (
            '<span style="color:#0ba0b6">&#10003;</span>'
            if r["ok"]
            else '<span style="color:#b45309">&#10007;</span>'
        )
        ver = f" {r['version']}" if r["version"] else ""
        path = (
            f'<code style="{_CHIP};color:#64748b">{r["path"]}</code>'
            if r["path"]
            else '<span style="color:#b45309;font-size:12px">not found on PATH</span>'
        )
        out.append(
            '<div style="color:#64748b;font-size:12px;padding:4px 0;display:flex;'
            'align-items:center;gap:8px;flex-wrap:wrap">'
            '<span style="min-width:78px;text-transform:uppercase;font-size:10px;'
            f'letter-spacing:.04em">{r["role"]}</span>'
            f'<b style="color:#94a3b8">{r["cmd"]}{ver}</b>{mark}{path}</div>'
        )
    return "".join(out)


def _env_panel_md(rows: list[dict]) -> str:
    """Environment model as a plaintext table for `breachsafe-ux --check` (terminal/CI/HEALTHCHECK).
    The UI uses _env_advanced_md; this stays text so the CLI output is readable (#75)."""
    if not rows:
        return "(no tool declared for this descriptor)"
    header = "| role | binary | version | path | status |\n|---|---|---|---|---|\n"
    body = "\n".join(
        f"| {r['role']} | {r['cmd']} | {r['version'] or '-'} | "
        f"{r['path'] or '-'} | {'ok' if r['ok'] else 'NOT FOUND'} |"
        for r in rows
    )
    return header + body
