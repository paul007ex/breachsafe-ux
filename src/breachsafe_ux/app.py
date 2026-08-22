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

import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

import gradio as gr

from breachsafe_ux._render import _posture
from breachsafe_ux.brand import BRAND, CSS, THEME
from breachsafe_ux.facade import (
    feature_enabled,
    load_descriptors,
    run_action,
    run_descriptor,
    verify_path,
)
from breachsafe_ux.render import (
    _B64,
    _ICON,
    _ICON_DIR,
    _LICENSE,
    _action_output_md,
    _badge,
    _diag_md,
    _empty,
    _env_advanced_md,
    _env_panel_md,
    _link,
    _posture_md,
)
from breachsafe_ux.resolve import environment, tool_available

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


def _enum_widget(spec, lab, info):
    # Radio for 2-3 options (all visible), Dropdown for more (GOV.UK / NN/g).
    choices = spec["choices"]
    if len(choices) <= _RADIO_MAX:
        return gr.Radio(choices, value=spec.get("default"), label=lab, info=info)
    return gr.Dropdown(choices, value=spec.get("default"), label=lab, info=info)


def _number_widget(spec, lab, info):
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


def _text_widget(spec, lab, info):
    return gr.Textbox(
        value=spec.get("default", ""),
        label=lab + (" *" if spec.get("required", False) else ""),
        placeholder=spec.get("placeholder", ""),
        info=info,
    )


def _widget(spec):
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


def _collect(desc, vals):
    # gr.File (Gradio 6, type="filepath") already yields the uploaded file's path as a str, like
    # every other widget yields its value — so a file input needs no special handling. (The old
    # `.name` assumed the pre-6 file-object return and broke manual upload on the mint-oscal tab.)
    params = {}
    for spec, v in zip(desc.get("inputs", []), vals, strict=False):
        params[spec["name"]] = v if v is not None else ""
    return params


def _result(desc, res):
    """(badge_md, artifact_json, raw_log_md, artifact_path). Defined result on every branch.

    The badge_md is a readiness-posture banner (from the findings, #1) followed by the evidence
    badge, whose word can be reworded per state so a green badge states what was checked rather
    than implying a security verdict.
    """
    state, detail = res["badge"]
    head_text = desc.get("render", {}).get("badge_text", {}).get(state)
    if "error" in res:
        # A failed run has no artifact, so no posture banner — we never claim readiness on failure.
        raw = f"```\n{res['error']}\n```"
        return _badge(state, detail, head_text=head_text), None, raw, None
    banner = _posture_md(_posture(desc, res.get("artifact")))
    return (
        banner + _badge(state, detail, res.get("highlights", []), head_text=head_text),
        res.get("artifact"),
        "",
        res.get("artifact_path"),
    )


def _handler(desc):
    def run(*vals, progress=gr.Progress()):
        progress(0, desc=f"running {desc['id']}…")
        params = _collect(desc, vals)
        res = run_descriptor(desc, params)
        progress(1)
        badge, art, raw, path = _result(desc, res)
        # Reset the Run button here, atomic with the result, so it always clears "Running…"
        # (a trailing .then could be skipped; _result never raises, so this return always runs).
        reset = gr.update(value=_run_label(desc), interactive=True)
        return badge, art, raw, path, reset

    return run


def _chain_handler(chain, descs):
    target = descs[chain["to"]]

    def run(artifact_path, progress=gr.Progress()):
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
        return _result(target, res)

    return run


def _run_label(desc):
    # Descriptor-set run-button label (e.g. "HNDL Audit (TLS)"), else "Run <id>". Lets two
    # tabs backed by the same tool (qureddy TLS + SSH) read distinctly, not "Run qureddy" twice.
    return desc.get("run_label") or _RUN_LABEL.format(id=desc["id"])


def _busy(_did):
    return gr.update(value=_BUSY_LABEL, interactive=False)


def _verify_md(value, argv_template):
    ok, line = verify_path(value, argv_template)
    return _diag_md(ok, line)


def _action_md(desc, action, vals):
    # A descriptor-declared action button (#5): run its argv against the current inputs and show
    # the tool's actual output (#97), not a canned summary.
    ok, output = run_action(action, _collect(desc, vals))
    return _action_output_md(ok, output)


def _header():
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


def _footer():
    """Footer HTML: product + version + brand/repo links + license."""
    gr.HTML(
        '<div class="bs-footer">'
        f"<span>{BRAND['name']} v{_HOST_VERSION}</span>"
        f"{_link(BRAND['url'], 'breachsafe.io')}"
        f"{_link(BRAND['repo'], 'GitHub')}"
        f"<span>{_LICENSE}</span></div>"
    )


def _order_widgets(desc, widgets, advanced_widgets):
    """Interleave basic + advanced widgets back into desc['inputs'] order for _collect's zip."""
    ordered = []
    adv_iter = iter(advanced_widgets)
    basic_iter = iter(widgets)
    for spec in desc.get("inputs", []):
        ordered.append(next(adv_iter) if spec.get("group") == "advanced" else next(basic_iter))
    return ordered


def _render_inputs(desc, env_rows):
    """Render a tab's editable widgets (basic inline, advanced behind an Accordion with the binary
    provenance panel), returning the desc-ordered widget list for the handler wiring."""
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


def _wire_actions(desc, ordered):
    """Descriptor-declared action buttons (#5): each runs its own argv against the current inputs
    and shows the tool's actual output. Replaces the old hardcoded 'Test connection' preflight."""
    for action in desc.get("actions", []):
        ab = gr.Button(action["label"], size="sm", variant="secondary")
        ar = gr.Markdown()
        ab.click(lambda *vals, a=action, d=desc: _action_md(d, a, vals), ordered, ar)


def _wire_run(desc, did, ordered):
    """The primary Run button + result surfaces (badge/JSON/raw-log/download), wired so the button
    reset is an atomic handler OUTPUT (no trailing .then that could leave it stuck on 'Running…')."""
    run_btn = gr.Button(_run_label(desc), variant="primary", icon=_ICON["run"])
    badge = gr.Markdown(_empty(desc))
    dl = gr.DownloadButton("Download output", visible=False)
    with gr.Accordion("Raw log", open=False):
        raw_log = gr.Markdown("")
    out = gr.JSON(label="artifact")
    artifact_state = gr.State(None)
    heavy = desc["run"].get("timeout_s", 0) >= _HEAVY_TIMEOUT_S
    (
        run_btn.click(lambda d=did: _busy(d), None, run_btn)
        .then(
            _handler(desc),
            ordered,
            [badge, out, raw_log, artifact_state, run_btn],
            show_progress="full",
            concurrency_limit=1 if heavy else None,
        )
        .then(lambda p: gr.update(value=p, visible=bool(p)), artifact_state, dl)
    )
    return artifact_state


def _wire_chain(chain, descs, artifact_state):
    """One Convert-to-next-tool button (#5/W-5). Gated off -> hidden; target missing/unavailable ->
    a disabled button that says why; otherwise wired to run the target on the upstream artifact."""
    if chain.get("feature_flag") and not feature_enabled(chain["feature_flag"]):
        return  # #67: gated off -> hide the button entirely (OSS base edition)
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
        craw = gr.Markdown("")
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


def _build_tab(did, desc, descs):
    """Render one descriptor as its own tab: description, inputs, actions, the Run surface, and
    any Convert-to-next-tool chain buttons."""
    with gr.Tab(desc.get("title", did)):
        gr.Markdown(desc.get("description", ""))
        env_rows = environment(desc)
        ordered = _render_inputs(desc, env_rows)
        _wire_actions(desc, ordered)
        artifact_state = _wire_run(desc, did, ordered)
        for chain in desc.get("chains", []):
            _wire_chain(chain, descs, artifact_state)


def build():
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
    """`breachsafe-ux --check`: resolve every descriptor's environment, print it, and exit nonzero
    if any tool or validator is missing. A curl on `/` is false-healthy — the Gradio shell serves
    even when the underlying tool is absent — so this is the real Docker HEALTHCHECK signal: it
    verifies the binaries the descriptors declare actually resolve on this system (#75).
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
    if "--check" in sys.argv[1:]:
        raise SystemExit(_check())
    demo = build()
    demo.queue()  # required so gr.Progress + concurrency work for long-running scans
    # Gradio 6.0 moved theme/css from the Blocks constructor to launch().
    demo.launch(
        theme=THEME,
        css=CSS,
        allowed_paths=[str(_ICON_DIR)],
        server_name=os.environ.get("BREACHSAFE_UX_HOST", "127.0.0.1"),
        server_port=int(os.environ.get("BREACHSAFE_UX_PORT", "7860")),
    )


if __name__ == "__main__":
    main()
