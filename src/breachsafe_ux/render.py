# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""View: pure HTML/markdown string builders.

No Gradio, no logic — given model data, return the markup app.py hands to gr.HTML/gr.Markdown.
Split from app.py so the controller stays wiring-only.
"""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from breachsafe_ux._render import _evaluation, _posture

if TYPE_CHECKING:
    from collections.abc import Sequence

# #4: a tool's captured stdout/stderr can carry ANSI escape sequences (e.g. `rich` colour,
# cursor moves), which render as escape-code garbage in the web view. Strip them from any
# human-readable text before display. Host-generic — no tool-specific logic. Never applied to
# artifact JSON (that is structured data), only to output/detail strings shown to the user.
_ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]"  # CSI / SGR (colour, style, cursor moves)
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC (e.g. window title), BEL- or ST-terminated
    r"|\x1b[@-Z\\-_]"  # other 2-char C1 escapes
    r"|\x1b"  # a lone/leftover ESC
)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences so console/`rich` output reads cleanly in the web view (#4).

    Pure and host-generic: handles CSI/SGR, OSC, and single-char C1 escapes plus a lone ESC.
    Newlines and all other content are preserved.
    """
    return _ANSI_RE.sub("", text)


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
    """Render an action result (#97): the OK/FAILED verdict plus the tool's captured output.

    The tool's actual captured output is shown in a code block, so 'Test connection' shows the
    real openssl handshake — not a canned one-liner.
    """
    color = "#0ba0b6" if ok else "#b45309"
    verdict = "OK" if ok else "FAILED"
    # #4: strip ANSI escapes from the tool's captured output so console/`rich` output reads
    # cleanly, then keep it from breaking the code fence.
    fence = _strip_ansi(output).replace("```", "'''")
    return f'<span style="color:{color};font-weight:700">{verdict}</span>\n\n```\n{fence}\n```'


def _posture_md(posture: dict[str, Any] | None) -> str:
    """Readiness banner from the findings, or "" when the descriptor declares none (#1)."""
    if not posture:
        return ""
    color = _LEVEL_COLOR.get(posture.get("level", ""), "#475569")
    # #121: escape the interpolated text (artifact-derived in principle) so it can never inject
    # markup into the banner; the static styling we build around it is left untouched.
    text = html.escape(str(posture.get("text", "")))
    return (
        f'<div style="border-left:5px solid {color};padding:8px 14px;margin:0 0 12px">'
        f'<span style="color:{color};font-weight:800">{text}</span></div>\n\n'
    )


def _evaluation_text(ev: dict[str, Any] | None) -> str:
    """The tool's per-axis evaluation as plain, aligned `label: value` text, or "" when none (#199).

    Rendered in a copyable code box (consistent with the CBOM/JSON boxes), so it is exactly the
    label + value the tool reported, then the headline. The host adds no interpretation; it stays
    tool-agnostic. Plain text (no markup), so no escaping is needed.
    """
    if not ev or not ev.get("rows"):
        return ""
    width = max(len(str(r["label"])) for r in ev["rows"])
    lines = [f"{str(r['label']) + ':':<{width + 1}} {r['value']}" for r in ev["rows"]]
    text = "\n".join(lines)
    headline = ev.get("headline")
    if headline:
        text += f"\n\n{headline}"
    return text


def _badge(
    state: str,
    detail: str,
    hi: Sequence[dict[str, Any]] = (),
    head_text: str | None = None,
) -> str:
    """Render the 3-state evidence verdict; never green markup for a non-valid state.

    head_text overrides the state word so a descriptor states what was checked, not a bare VALID
    that implies security (#1).
    """
    color = _COLOR.get(state, "#b45309")
    head = (
        f'<span style="color:{color};font-weight:800;'
        'display:inline-flex;align-items:center;gap:8px">'
        f"{_STATUS_SVG.get(state, '')}{head_text or _HEAD.get(state, state.upper())}</span>"
    )
    # #121: `detail` (validator output) and the highlight label/value (artifact-derived) are
    # untrusted strings; escape them before they land in the markdown/HTML the UI renders, so a
    # `<script>`-ish artifact value cannot inject markup. The static markup here is left as-is.
    # #4: strip ANSI escapes from the validator `detail` (tool-derived) before escaping it, so
    # console/`rich` output reads cleanly rather than as escape-code garbage.
    body = f"\n\n{html.escape(_strip_ansi(detail))}" if detail else ""
    h = "\n".join(
        f"- **{html.escape(str(x['label']))}:** `{html.escape(str(x['value']))}`" for x in hi
    )
    return f"### {head}{body}" + (f"\n\n{h}" if h else "")


def _empty(desc: dict[str, Any]) -> str:
    """Pre-run empty state: what the tool produces + how to read the verdict."""
    artifact = desc["run"].get("artifact_name", "artifact.json")
    return (
        f"### Ready\nProduces `{artifact}`. The verdict below shows the external validator "
        "result: VALID, INVALID, or VALIDATOR-UNAVAILABLE."
    )


_CHIP = (
    "background:rgba(148,163,184,.14);padding:1px 7px;border-radius:5px;"
    "font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px"
)


def _env_advanced_md(rows: list[dict[str, Any]]) -> str:
    """Environment provenance as greyed, read-only lines for the Advanced accordion (#75).

    Shows the binary, version, and resolved path behind each descriptor role. Muted so it reads
    as reference, not editable input; the tool row also appears at-a-glance in the header
    (_env_line).
    """
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


def _env_panel_md(rows: list[dict[str, Any]]) -> str:
    """Environment model as a plaintext table for `breachsafe-ux --check`.

    Used for terminal/CI/HEALTHCHECK output. The UI uses _env_advanced_md; this stays text so the
    CLI output is readable (#75).
    """
    if not rows:
        return "(no tool declared for this descriptor)"
    header = "| role | binary | version | path | status |\n|---|---|---|---|---|\n"
    body = "\n".join(
        f"| {r['role']} | {r['cmd']} | {r['version'] or '-'} | "
        f"{r['path'] or '-'} | {'ok' if r['ok'] else 'NOT FOUND'} |"
        for r in rows
    )
    return header + body


def _raw_log_text(res: dict[str, Any], body: str) -> str:
    """Raw log as PLAIN text: invocation + run dir header (#199), then ANSI-stripped tool text.

    Unfenced on purpose. This feeds a `gr.Code` box, which supplies its own download and copy
    buttons, the same affordance the Evaluation and CBOM/JSON boxes already have. It previously
    returned a markdown fence for a `gr.Markdown` widget, which gave the operator a copy button
    and no way to save the log. A scan log is evidence; it should be savable without selecting
    text in a browser.
    """
    cmd, workdir = res.get("command"), res.get("workdir")
    header = f"$ {cmd}\n# ran in: {workdir}\n\n" if cmd else ""
    text = _strip_ansi(body.strip())
    return f"{header}{text}" if (text or header) else ""


def _result(
    desc: dict[str, Any], res: dict[str, Any]
) -> tuple[str, str, str, dict[str, str], Any, str | None]:
    """(badge_md, evaluation_text, raw_log_md, artifact_texts, primary_artifact, primary_path).

    Defined on every branch. The evaluation is the tool's own per-axis interpretation, shown in
    its own copyable code box (same structure as the CBOM/JSON boxes, #199); "" when the tool
    declares none. artifact_texts maps each declared artifact name -> its raw text.
    """
    state, detail = res["badge"]
    head_text = desc.get("render", {}).get("badge_text", {}).get(state)
    if "error" in res:
        # A failed run has no artifact, so no posture banner — we never claim readiness on failure.
        return (
            _badge(state, detail, head_text=head_text),
            "",
            _raw_log_text(res, res["error"]),
            {},
            None,
            None,
        )
    banner = _posture_md(_posture(desc, res.get("artifact")))
    # #199: the tool's own per-axis evaluation, config-driven + agnostic, shown in its own box.
    evaluation = _evaluation_text(_evaluation(desc, res.get("artifact")))
    # #190/#199: the Raw log carries the tool's stderr on success too, prefixed with the command.
    raw = _raw_log_text(res, res.get("log") or "")
    art_texts = {name: a.get("text", "") for name, a in res.get("artifacts", {}).items()}
    return (
        banner + _badge(state, detail, res.get("highlights", []), head_text=head_text),
        evaluation,
        raw,
        art_texts,
        res.get("artifact"),
        res.get("artifact_path"),
    )
