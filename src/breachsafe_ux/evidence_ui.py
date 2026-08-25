# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Gradio presentation adapters for the descriptor-declared evidence export."""

from __future__ import annotations

import html
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import gradio as gr

from breachsafe_ux.evidence import run_evidence_report
from breachsafe_ux.facade import RUN_ROOT

if TYPE_CHECKING:
    from collections.abc import Callable


def build_evidence_tabs(
    desc: dict[str, Any],
    auto_chain: dict[str, Any] | None,
    code_box: Callable[[str | None], Any],
) -> tuple[list[Any], Any, list[Any], tuple[Any, Any, Any, Any, Any, Any] | None]:
    """Build the shared evidence tab layout and return its output components."""
    eval_cfg = desc.get("render", {}).get("evaluation")
    eval_outs: list[Any] = []
    outs: list[Any] = []
    artifacts = desc["run"].get("artifacts", [])
    export_outputs: tuple[Any, Any, Any, Any, Any, Any] | None = None
    with gr.Tabs():
        if auto_chain:
            with gr.Tab("Executive Summary"):
                export_outputs = (
                    gr.Markdown(visible=False),
                    gr.JSON(visible=False),
                    gr.Code(visible=False),
                    None,
                    gr.HTML(visible=False),
                    gr.HTML(visible=False),
                )
        if eval_cfg:
            with gr.Tab("Technical Summary"):
                eval_outs.append(code_box(eval_cfg.get("language", "yaml")))
        for art in artifacts:
            if art["name"] == "rich":
                with gr.Tab("Output"):
                    outs.append(code_box("yaml"))
                continue
            label = {"json": "JSON", "jsonl": "Findings"}.get(
                art["name"], art.get("label", art["name"])
            )
            with gr.Tab(label):
                language = "json" if art["name"] == "jsonl" else art.get("language", "json")
                outs.append(code_box(language))
        if not artifacts:
            with gr.Tab("Artifact"):
                outs.append(gr.JSON(label="artifact"))
        with gr.Tab("Raw Log"):
            raw_log = code_box("yaml")
    return eval_outs, raw_log, outs, export_outputs


def order_widgets(
    desc: dict[str, Any], widgets: list[Any], advanced_widgets: list[Any]
) -> list[Any]:
    """Interleave basic and advanced widgets in descriptor order for handler wiring."""
    ordered: list[Any] = []
    adv_iter = iter(advanced_widgets)
    basic_iter = iter(widgets)
    for spec in desc.get("inputs", []):
        ordered.append(next(adv_iter) if spec.get("group") == "advanced" else next(basic_iter))
    return ordered


def wire_actions(
    desc: dict[str, Any],
    ordered: list[Any],
    output: Any,
    panel: Any,
    buttons: list[Any],
    action_md: Callable[..., str],
) -> None:
    """Wire descriptor-declared action buttons to the shared output surface."""
    for index, action in enumerate(desc.get("actions", [])):
        button = buttons[index]
        event = button.click(lambda *vals, a=action: action_md(desc, a, vals), ordered, output)
        event.then(lambda: gr.update(visible=True), None, panel)


def evidence_chain_handler(chain: dict[str, Any]) -> Callable[..., tuple[Any, ...]]:
    """Adapt the Go evidence composer result to the Gradio output components."""

    def run(artifact_path: str | None, progress: Any = gr.Progress()) -> tuple[Any, ...]:
        progress(0, desc="building evidence PDF and export bundle…")
        ok, output = run_evidence_report(chain, artifact_path)
        progress(1)
        if not ok:
            return (
                f"### Export failed\n{output.get('error', 'unknown error')}",
                output,
                output.get("log", ""),
                gr.update(interactive=False, visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            )
        return (
            "",
            output,
            output.get("log", ""),
            gr.update(
                value=output.get("archive"), interactive=bool(output.get("archive")), visible=True
            ),
            gr.update(value=pdf_preview_html(output.get("pdf")), visible=bool(output.get("pdf"))),
            gr.update(value=pdf_open_link(output.get("pdf")), visible=bool(output.get("pdf"))),
        )

    return run


def pdf_preview_html(path: str | None) -> str:
    """Render PDF pages as in-app images, avoiding browser PDF viewer chrome."""
    if not path:
        return ""
    pdf = Path(path).resolve()
    root = RUN_ROOT.resolve()
    if not pdf.is_file() or not pdf.is_relative_to(root):
        return ""
    preview_dir = pdf.parent / "pdf-preview"
    try:
        pdftoppm = shutil.which("pdftoppm")
        if not pdftoppm:
            return ""
        preview_dir.mkdir(exist_ok=True)
        for old in preview_dir.glob("page-*.png"):
            old.unlink()
        subprocess.run(
            [pdftoppm, "-png", "-r", "120", str(pdf), str(preview_dir / "page")],
            check=True,
            capture_output=True,
            timeout=60,
        )
        pages = sorted(preview_dir.glob("page-*.png"))
    except OSError, subprocess.SubprocessError:
        return ""
    images = "".join(
        f'<img alt="PDF page {i}" src="/gradio_api/file={quote(str(page), safe="")}" '
        'style="display:block;width:min(100%,900px);height:auto;margin:0 auto 18px;" />'
        for i, page in enumerate(pages, 1)
    )
    return (
        '<div aria-label="Rendered PDF preview" '
        'style="max-height:780px;overflow-y:auto;padding:18px;background:#1b1b1b;" '
        f'data-pages="{len(pages)}">{images}</div>'
        if pages
        else ""
    )


def pdf_open_link(path: str | None) -> str:
    """Expose the generated PDF as a normal browser-openable link."""
    if not path:
        return ""
    return (
        '<a class="pdf-open-button" target="_blank" rel="noopener" '
        'style="display:block;text-align:center;padding:12px;margin-top:12px;'
        'border:1px solid #94a3b8;border-radius:8px;color:inherit;text-decoration:none;" '
        f'href="/gradio_api/file={quote(path, safe="")}">'
        f"{html.escape('PDF')}<span> ↗</span></a>"
    )


def wire_auto_evidence(
    chain: dict[str, Any],
    run_event: Any,
    artifact_state: Any,
    outputs: tuple[Any, Any, Any, Any, Any, Any],
) -> None:
    """Attach PDF/export generation to the PDF report tab.

    Metadata and the export log are still produced by the composer and included in the archive,
    but their hidden components are not part of the primary UX surface.
    """
    cbadge, cout, craw, cdl, preview, pdf_link = outputs
    run_event.then(
        evidence_chain_handler(chain),
        [artifact_state],
        [cbadge, cout, craw, cdl, preview, pdf_link],
        show_progress="full",
        concurrency_limit=1,
    )
