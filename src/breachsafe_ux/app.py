"""Gradio shell: renders each tool descriptor as its own 10/10 surface (all params as widgets).

The type->widget map is written ONCE here; every tool is a YAML. Adding a tool = a YAML.

UX contract (NN/g, GOV.UK, WCAG 2.2, Gradio docs):
  * persistent labels + `info=` hints (placeholders are examples only);
  * progressive disclosure (advanced params behind an Accordion);
  * never-green-on-failure 3-state badge (icon + word + colour, never colour alone);
  * long-run feedback (queue + Progress + Run-button busy state) for 30s-2min scans;
  * per-run data lives in `gr.State`, never in a module global that could leak across users.
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import gradio as gr

from breachsafe_ux.brand import BRAND, CSS, THEME
from breachsafe_ux.facade import (
    RUN_ROOT,
    feature_enabled,
    load_descriptors,
    run_action,
    run_descriptor,
    run_evidence_report,
    verify_path,
)
from breachsafe_ux.render import (
    _B64,
    _ICON,
    _ICON_DIR,
    _LICENSE,
    _action_output_md,
    _diag_md,
    _empty,
    _env_advanced_md,
    _env_panel_md,
    _link,
    _result,
)
from breachsafe_ux.resolve import environment, tool_available

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

try:
    _HOST_VERSION = _pkg_version("breachsafe-ux")  # the EnXemble UX host's own version (#95)
except PackageNotFoundError:  # running from a source tree without an installed dist
    _HOST_VERSION = "0.0.0"

# Descriptors are loaded LAZILY inside build() (W-1/W-2), never at import, so a host package
# that sets BREACHSAFE_UX_TOOLS_DIR before calling main() gets its own tools rendered.
_RUN_LABEL = "{id}"  # fallback button label; descriptors set their own run_label
_BUSY_LABEL = "Working…"
_RADIO_MAX = 3  # <= this many enum choices render as radios, else a dropdown
_HEAVY_TIMEOUT_S = 60  # a tool timeout at/above this serializes runs (concurrency_limit=1)
# class-based dark mode, like EnXemble (next-themes .dark). Toggles the theme's _dark tokens.
_THEME_TOGGLE_JS = (
    "() => { const el = document.querySelector('gradio-app') || document.body; "
    "el.classList.toggle('dark'); }"
)
_DARK_ON_LOAD_JS = (
    "() => { const el = document.querySelector('gradio-app') || document.body; "
    "el.classList.add('dark'); }"
)


def _code_box(language: str | None = None) -> Any:
    """A read-only text box with download + copy buttons.

    Every output surface in a tool tab is one of these: Evaluation, Raw log, and one per declared
    artifact. `gr.Code` is chosen over `gr.Markdown` because it supplies download and copy; a scan
    log and a CBOM are evidence and have to be savable without selecting text in a browser.

    `show_label=False` because the enclosing Accordion already names the box, and `wrap_lines=True`
    because these are wide machine outputs the operator should not have to scroll horizontally.
    Both were repeated at four call sites before this existed. `language=None` renders plain, which
    is correct for a tool log, since it is not any one syntax.
    """
    return gr.Code(language=language, show_label=False, wrap_lines=True)


def _enum_widget(spec: dict[str, Any], lab: str, info: str | None) -> gr.Component:
    # Radio for 2-3 options (all visible), Dropdown for more (GOV.UK / NN/g).
    choices = spec["choices"]
    if len(choices) <= _RADIO_MAX:
        return gr.Radio(choices, value=spec.get("default"), label=lab, info=info)
    return gr.Dropdown(choices, value=spec.get("default"), label=lab, info=info)


def _number_widget(spec: dict[str, Any], lab: str, info: str | None) -> gr.Component:
    t = spec["type"]
    if spec.get("widget") == "slider":
        step = 1 if t == "int" else 0.1
        return gr.Slider(
            spec.get("min", 0),
            spec.get("max", 100),
            value=spec.get("default", 0),
            step=step,
            label=lab,
            info=info,
        )
    return gr.Number(
        value=spec.get("default"), label=lab, precision=0 if t == "int" else None, info=info
    )


def _text_widget(spec: dict[str, Any], lab: str, info: str | None) -> gr.Component:
    return gr.Textbox(
        value=spec.get("default", ""),
        label=lab + (" *" if spec.get("required", False) else ""),
        placeholder=spec.get("placeholder", ""),
        info=info,
    )


def _widget(spec: dict[str, Any]) -> gr.Component:
    t, lab, info = spec["type"], spec.get("label", spec["name"]), spec.get("info")
    if t == "file":
        # gr.File has no `info` kwarg in Gradio 6 — fold the hint into the label.
        return gr.File(label=lab + (f" — {info}" if info else ""), file_types=spec.get("accept"))
    if t == "enum":
        return _enum_widget(spec, lab, info)
    if t in ("int", "float"):
        return _number_widget(spec, lab, info)
    if t == "bool":
        return gr.Checkbox(value=spec.get("default", False), label=lab, info=info)
    return _text_widget(spec, lab, info)


def _collect(desc: dict[str, Any], vals: Sequence[Any]) -> dict[str, Any]:
    # gr.File (Gradio 6, type="filepath") already yields the uploaded file's path as a str, like
    # every other widget yields its value — so a file input needs no special handling. (The old
    # `.name` assumed the pre-6 file-object return and broke manual upload on the mint-oscal tab.)
    params = {}
    for spec, v in zip(desc.get("inputs", []), vals, strict=False):
        params[spec["name"]] = v if v is not None else ""
    return params


def _handler(desc: dict[str, Any]) -> Callable[..., tuple[Any, ...]]:
    art_names = [a["name"] for a in desc["run"].get("artifacts", [])]
    has_eval = bool(desc.get("render", {}).get("evaluation"))

    def run(*vals: Any, progress: Any = gr.Progress()) -> tuple[Any, ...]:
        progress(0, desc=f"running {desc['id']}…")
        params = _collect(desc, vals)
        res = run_descriptor(desc, params)
        progress(1)
        badge, evaluation, raw, art_texts, primary, path = _result(desc, res)
        # Reset the Run button here, atomic with the result, so it always clears "Running…"
        # (a trailing .then could be skipped; _result never raises, so this return always runs).
        reset = gr.update(value=_run_label(desc), interactive=True)
        # Output order mirrors _wire_run: badge, [evaluation box], raw log, one box per declared
        # artifact (or the single legacy JSON), then the primary-artifact path + reset.
        eval_out = (evaluation,) if has_eval else ()
        if art_names:
            return (badge, *eval_out, raw, *(art_texts.get(n, "") for n in art_names), path, reset)
        return (badge, *eval_out, raw, primary, path, reset)

    return run


def _chain_handler(chain: dict[str, Any], descs: dict[str, Any]) -> Callable[..., tuple[Any, ...]]:
    target = descs[chain["to"]]

    def run(artifact_path: str | None, progress: Any = gr.Progress()) -> tuple[Any, ...]:
        if not artifact_path:
            # Pre-run guard (no artifact yet): mirror _empty()'s emoji-free surface
            # rather than a validator verdict — nothing has been validated to badge.
            return (
                "### Nothing to convert yet\nRun the tool above first, then use this "
                "button to convert its output.",
                None,
                "",
                None,
            )
        progress(0, desc=f"running {target['id']}…")
        params = dict(chain.get("with", {})) | {chain["pass_artifact_as"]: artifact_path}
        res = run_descriptor(target, params)
        progress(1)
        # The chain surface has 4 outputs [cbadge, cout, craw, cstate]; adapt _result's richer
        # tuple to them (the evaluation/per-artifact boxes are the primary tab's surfaces, not the
        # chain's). cout shows the primary artifact.
        badge, _evaluation, raw, _art_texts, primary, path = _result(target, res)
        return (badge, primary, raw, path)

    return run


def _evidence_chain_handler(chain: dict[str, Any]) -> Callable[..., tuple[Any, ...]]:
    """Adapter for the YAML-declared Export to PDF action (no tool-specific UI code)."""

    def run(artifact_path: str | None, progress: Any = gr.Progress()) -> tuple[Any, ...]:
        progress(0, desc="building evidence PDF and export bundle…")
        ok, output = run_evidence_report(chain, artifact_path)
        progress(1)
        if not ok:
            return (
                f"### Export failed\n{output.get('error', 'unknown error')}",
                output,
                output.get("log", ""),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
            )
        return (
            "### Report ready",
            output,
            output.get("log", ""),
            gr.update(value=output.get("archive"), visible=bool(output.get("archive"))),
            gr.update(value=_pdf_preview_html(output.get("pdf")), visible=bool(output.get("pdf"))),
            gr.update(value=_pdf_open_link(output.get("pdf")), visible=bool(output.get("pdf"))),
        )

    return run


def _pdf_preview_html(path: str | None) -> str:
    """Render PDF pages as in-app images, avoiding the browser PDF viewer chrome."""
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


def _pdf_open_link(path: str | None) -> str:
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


def _run_label(desc: dict[str, Any]) -> str:
    # Descriptor-set run-button label (e.g. "HNDL Audit (TLS)"), else "Run <id>". Lets two
    # tabs backed by the same tool (qureddy TLS + SSH) read distinctly, not "Run qureddy" twice.
    return desc.get("run_label") or _RUN_LABEL.format(id=desc["id"])


def _busy(_did: str) -> Any:
    return gr.update(value=_BUSY_LABEL, interactive=False)


def _verify_md(value: str, argv_template: list[str]) -> str:
    ok, line = verify_path(value, argv_template)
    return _diag_md(ok, line)


def _action_md(desc: dict[str, Any], action: dict[str, Any], vals: Sequence[Any]) -> str:
    # A descriptor-declared action button (#5): run its argv against the current inputs and show
    # the tool's actual output (#97), not a canned summary.
    ok, output = run_action(action, _collect(desc, vals))
    return _action_output_md(ok, output)


def _header() -> None:
    """Brandbar row: logo + product/version + links, plus the Light/Dark toggle button."""
    img = (
        f'<img src="data:image/png;base64,{_B64}" style="height:50px;width:auto" alt="{BRAND["company"]} logo"/>'
        if _B64
        else ""
    )
    with gr.Row(equal_height=True):
        with gr.Column(scale=8):
            gr.HTML(
                f'<div class="brandbar" style="display:flex;align-items:center;gap:14px">{img}'
                f'<div style="flex:1"><div style="font-size:22px;font-weight:800">{BRAND["name"]} '
                f'<span style="color:#16c7d8">v{_HOST_VERSION}</span></div>'
                f'<div style="color:#64748b;font-size:12px">'
                f"{_link(BRAND['url'], 'breachsafe.io')} &nbsp;&middot;&nbsp; "
                f"{_link(BRAND['repo'], 'GitHub')} &nbsp;&middot;&nbsp; {_LICENSE}</div></div></div>"
            )
        with gr.Column(scale=1, min_width=130):
            theme_btn = gr.Button("Light / Dark", size="sm")
    theme_btn.click(fn=None, inputs=None, outputs=None, js=_THEME_TOGGLE_JS)


def _footer() -> None:
    """Footer HTML: product + version + brand/repo links + license."""
    gr.HTML(
        '<div class="bs-footer">'
        f"<span>{BRAND['name']} v{_HOST_VERSION}</span>"
        f"{_link(BRAND['url'], 'breachsafe.io')}"
        f"{_link(BRAND['repo'], 'GitHub')}"
        f"<span>{_LICENSE}</span></div>"
    )


def _order_widgets(
    desc: dict[str, Any], widgets: list[Any], advanced_widgets: list[Any]
) -> list[Any]:
    """Interleave basic + advanced widgets back into desc['inputs'] order for _collect's zip."""
    ordered = []
    adv_iter = iter(advanced_widgets)
    basic_iter = iter(widgets)
    for spec in desc.get("inputs", []):
        ordered.append(next(adv_iter) if spec.get("group") == "advanced" else next(basic_iter))
    return ordered


def _render_inputs(desc: dict[str, Any], env_rows: list[dict[str, Any]]) -> list[Any]:
    """Render a tab's editable widgets and return them in descriptor order.

    Basic widgets render inline, advanced behind an Accordion with the binary provenance panel.
    Returns the desc-ordered widget list for the handler wiring.
    """
    widgets, advanced_widgets = [], []
    for spec in desc.get("inputs", []):
        if spec.get("group") != "advanced":
            widgets.append(_widget(spec))
    # Progressive disclosure: advanced params collapsed by default (NN/g). The binary provenance
    # (#75) lives here too — greyed, read-only, below the editable params.
    adv_specs = [s for s in desc.get("inputs", []) if s.get("group") == "advanced"]
    if adv_specs or env_rows:
        with gr.Accordion("Advanced options", open=False):
            for spec in adv_specs:
                # Directly editable (pre-populated); `verify_argv` adds a short Verify button
                # next to it that runs the tool's own check.
                w = _widget(spec)
                advanced_widgets.append(w)
                if spec.get("verify_argv"):
                    vb = gr.Button("Verify", size="sm", variant="secondary")
                    vr = gr.Markdown()
                    vb.click(lambda v, t=spec["verify_argv"]: _verify_md(v, t), w, vr)
            gr.HTML(_env_advanced_md(env_rows))  # greyed read-only lines; "" when no rows
    return _order_widgets(desc, widgets, advanced_widgets)


def _wire_actions(desc: dict[str, Any], ordered: list[Any]) -> None:
    """Wire the descriptor-declared action buttons (#5).

    Each runs its own argv against the current inputs and shows the tool's actual output.
    Replaces the old hardcoded 'Test connection' preflight.
    """
    actions = desc.get("actions", [])
    if not actions:
        return
    # Connection probes are diagnostic affordances, not part of the primary scan path. Keep the
    # main surface to Run -> Export while retaining the tool's real preflight for troubleshooting.
    with gr.Accordion("Diagnostics", open=False):
        for action in actions:
            ab = gr.Button(action["label"], size="sm", variant="secondary")
            ar = gr.Markdown()
            ab.click(lambda *vals, a=action, d=desc: _action_md(d, a, vals), ordered, ar)


def _wire_run(
    desc: dict[str, Any], did: str, ordered: list[Any], auto_chain: dict[str, Any] | None = None
) -> Any:
    """Wire the primary Run button + result surfaces (badge/JSON/raw-log/download).

    The button reset is an atomic handler OUTPUT (no trailing .then that could leave it stuck on
    'Running…').
    """
    run_btn = gr.Button(_run_label(desc), variant="primary", icon=_ICON["run"])
    badge = gr.Markdown(_empty(desc))
    # Consistent output surfaces (#199): every box is a collapsed, copyable gr.Code accordion.
    # The Evaluation box (the tool's own interpretation, config-driven) sits alongside the CBOM/
    # JSON boxes with the same structure. Order: Evaluation, Raw log, then one box per artifact.
    eval_cfg = desc.get("render", {}).get("evaluation")
    eval_outs: list[Any] = []
    if eval_cfg:
        with gr.Accordion(
            eval_cfg.get("title", "Evaluation"),
            open=bool(eval_cfg.get("open", False)),
        ):
            # Syntax-highlight the `label: value` lines like the CBOM/JSON boxes (default yaml,
            # config-overridable). The tool's evaluation is aligned key:value text, which the yaml
            # lexer colours (keys vs values) the same way the artifact boxes colour JSON.
            eval_outs.append(_code_box(eval_cfg.get("language", "yaml")))
    with gr.Accordion("Raw log", open=False):
        raw_log = _code_box()
    artifacts = desc["run"].get("artifacts", [])
    outs: list[Any] = []
    if artifacts:
        for art in artifacts:
            with gr.Accordion(art.get("label", art["name"]), open=False):
                # Per-artifact language, defaulting to json for the existing CBOM/JSON boxes.
                # qureddy 0.2.59 also writes scan.jsonl and scan.rich.txt; highlighting a
                # rendered text report or a newline-delimited stream as one JSON document
                # mis-colours it, since neither is a single JSON value.
                outs.append(_code_box(art.get("language", "json")))
    else:  # legacy single-artifact tool: keep one JSON view
        outs.append(gr.JSON(label="artifact"))
    artifact_state = gr.State(None)
    heavy = desc["run"].get("timeout_s", 0) >= _HEAVY_TIMEOUT_S
    run_event = run_btn.click(lambda d=did: _busy(d), None, run_btn).then(
        _handler(desc),
        ordered,
        [badge, *eval_outs, raw_log, *outs, artifact_state, run_btn],
        show_progress="full",
        concurrency_limit=1 if heavy else None,
    )
    if auto_chain:
        _wire_auto_evidence(auto_chain, run_event, artifact_state)
    return artifact_state


def _wire_auto_evidence(chain: dict[str, Any], run_event: Any, artifact_state: Any) -> None:
    """Attach PDF/export generation to a successful scan; expose only finished outputs."""
    cbadge = gr.Markdown()
    with gr.Accordion("export metadata", open=False):
        cout = gr.JSON()
    with gr.Accordion("evidence export raw log", open=False):
        craw = _code_box()
    with gr.Accordion("Preview report", open=False):
        preview = gr.HTML(visible=False)
    pdf_link = gr.HTML(visible=False)
    cdl = gr.DownloadButton("Download", visible=False)
    run_event.then(
        _evidence_chain_handler(chain),
        [artifact_state],
        [cbadge, cout, craw, cdl, preview, pdf_link],
        show_progress="full",
        concurrency_limit=1,
    )


def _wire_chain(chain: dict[str, Any], descs: dict[str, Any], artifact_state: Any) -> None:
    """Wire one Convert-to-next-tool button (#5/W-5).

    Gated off -> hidden; target missing/unavailable -> a disabled button that says why; otherwise
    wired to run the target on the upstream artifact.
    """
    if chain.get("feature_flag") and not feature_enabled(chain["feature_flag"]):
        return  # #67: gated off -> hide the button entirely (OSS base edition)
    if chain.get("kind") in ("evidence_report", "pdf_export"):
        return
    target = descs.get(chain["to"])
    clabel = chain.get("label", chain["to"])
    if target is None or not tool_available(target):
        # W-5: reflect the real state, not a dead button — say why it cannot run (e.g. a
        # qureddy-only [ui] install has no mint-oscal for OSCAL conversion).
        need = (target or {}).get("run", {}).get("base", [chain["to"]])[0]
        gr.Button(
            f"{clabel} (unavailable)",
            variant="secondary",
            icon=_ICON["convert"],
            interactive=False,
        )
        gr.Markdown(f"_Requires `{need}`, which is not installed in this deployment._")
        return
    cbtn = gr.Button(clabel, variant="secondary", icon=_ICON["convert"])
    cbadge = gr.Markdown()
    cdl = gr.DownloadButton("Download output", visible=False)
    with gr.Accordion(f"{chain['to']} raw log", open=False):
        craw = _code_box()
    cout = gr.JSON(label=f"{chain['to']} output")
    cstate = gr.State(None)
    (
        cbtn.click(lambda: gr.update(value=_BUSY_LABEL, interactive=False), None, cbtn)
        .then(
            _chain_handler(chain, descs),
            [artifact_state],
            [cbadge, cout, craw, cstate],
            show_progress="full",
            concurrency_limit=1,
        )
        .then(lambda p: gr.update(value=p, visible=bool(p)), cstate, cdl)
        .then(
            lambda c=chain: gr.update(value=c.get("label", c["to"]), interactive=True),
            None,
            cbtn,
        )
    )


def _build_tab(did: str, desc: dict[str, Any], descs: dict[str, Any]) -> None:
    """Render one descriptor as its own tab.

    Renders the description, inputs, actions, the Run surface, and any Convert-to-next-tool chain
    buttons.
    """
    with gr.Tab(desc.get("title", did)):
        gr.Markdown(desc.get("description", ""))
        env_rows = environment(desc)
        ordered = _render_inputs(desc, env_rows)
        _wire_actions(desc, ordered)
        auto_chain = next(
            (chain for chain in desc.get("chains", []) if chain.get("kind") == "pdf_export"),
            None,
        )
        artifact_state = _wire_run(desc, did, ordered, auto_chain)
        for chain in desc.get("chains", []):
            if chain is not auto_chain:
                _wire_chain(chain, descs, artifact_state)


def build() -> gr.Blocks:
    """Build the Gradio Blocks app: a tab per standalone descriptor, plus header and footer."""
    descs = load_descriptors()
    with gr.Blocks(title=BRAND["name"]) as demo:
        _header()
        for did, desc in descs.items():
            if desc.get("standalone") is False:
                continue  # chain-only tool (e.g. mint-oscal): reached via a Convert button, not a tab
            _build_tab(did, desc, descs)
        _footer()
        # Default to dark on load (EnXemble .dark tokens); the Light/Dark button still toggles it.
        demo.load(fn=None, inputs=None, outputs=None, js=_DARK_ON_LOAD_JS)
    return demo


def _check() -> int:
    """Resolve every descriptor's environment, print it, and exit nonzero if any is missing.

    `breachsafe-ux --check`. A curl on `/` is false-healthy — the Gradio shell serves even when
    the underlying tool is absent — so this is the real Docker HEALTHCHECK signal: it verifies
    the binaries the descriptors declare actually resolve on this system (#75).
    """
    ok = True
    for did, desc in load_descriptors().items():
        rows = environment(desc)
        print(f"\n## {did}\n{_env_panel_md(rows)}")
        if any(not r["ok"] for r in rows):
            ok = False
    print("\nOK" if ok else "\nMISSING TOOLS")
    return 0 if ok else 1


def main() -> None:
    """Entry point (`breachsafe-ux`): handle --check, else build and launch the Gradio app."""
    if "--check" in sys.argv[1:]:
        raise SystemExit(_check())
    demo = build()
    demo.queue()  # required so gr.Progress + concurrency work for long-running scans
    # Gradio 6.0 moved theme/css from the Blocks constructor to launch().
    demo.launch(
        theme=THEME,
        css=CSS,
        # Generated artifacts live under RUN_ROOT; Gradio must be allowed to copy them to the
        # DownloadButton cache after the evidence job completes.
        allowed_paths=[str(_ICON_DIR), str(RUN_ROOT)],
        server_name=os.environ.get("BREACHSAFE_UX_HOST", "127.0.0.1"),
        server_port=int(os.environ.get("BREACHSAFE_UX_PORT", "7860")),
    )


if __name__ == "__main__":
    main()
