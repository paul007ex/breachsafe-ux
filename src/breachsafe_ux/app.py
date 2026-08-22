"""Gradio shell: renders each tool descriptor as its own 10/10 surface (all params as widgets).

The type->widget map is written ONCE here; every tool is a YAML. Adding a tool = a YAML.

UX contract (NN/g, GOV.UK, WCAG 2.2, Gradio docs):
  * persistent labels + `info=` hints (placeholders are examples only);
  * progressive disclosure (advanced params behind an Accordion);
  * honest, never-green-on-failure 3-state badge (icon + word + colour, never colour alone);
  * long-run feedback (queue + Progress + Run-button busy state) for 30s-2min scans;
  * per-run data lives in `gr.State`, never in a module global that could leak across users.
"""
from __future__ import annotations

import base64
import os

import gradio as gr

from breachsafe_ux.brand import BRAND, CSS, THEME
from breachsafe_ux.facade import (
    ROOT,
    load_descriptors,
    run_action,
    run_descriptor,
    tool_available,
    verify_path,
)

# Descriptors are loaded LAZILY inside build() (W-1/W-2), never at import, so a host package
# that sets BREACHSAFE_UX_TOOLS_DIR before calling main() gets its own tools rendered.
_LOGO = ROOT / "assets" / "logo.png"
_B64 = base64.b64encode(_LOGO.read_bytes()).decode() if _LOGO.exists() else ""
_HDR_DEFAULT = {"product": "BreachSAFE UX", "version": "0.1.0",
                "url": "https://www.breachsafe.ai", "repo": ""}


def _header_brand(descs):
    # Header brand comes from the primary standalone tool (this deployment fronts one tool).
    return next((d["brand"] for d in descs.values()
                 if d.get("standalone") is not False and d.get("brand")), None) or _HDR_DEFAULT
_LICENSE = "Apache-2.0 (open source)"
def _link(u, t):
    return f'<a href="{u}" target="_blank" rel="noopener" style="color:#0ba0b6;text-decoration:none">{t}</a>' if u else t
# lucide icons, the same set EnXemble uses (ISC). SVGs use currentColor so they inherit the badge colour.
_ICON_DIR = ROOT / "assets" / "icons"
def _svg(name, px=20):
    p = _ICON_DIR / f"{name}.svg"
    return p.read_text().replace('width="24" height="24"', f'width="{px}" height="{px}" style="vertical-align:middle"') if p.exists() else ""
_STATUS_SVG = {"valid": _svg("shield-check"), "invalid": _svg("circle-x"), "unavailable": _svg("triangle-alert"), "none": ""}
_ICON = {"run": str(_ICON_DIR / "scan.svg"), "convert": str(_ICON_DIR / "arrow-right.svg")}

_HEAD = {"valid": "VALID", "invalid": "INVALID",
         "unavailable": "UNAVAILABLE", "none": "NO EXTERNAL VALIDATOR"}
# No emoji (house rule). The word carries the state as text; colour is a redundant cue (WCAG 1.4.1).
_COLOR = {"valid": "#0ba0b6", "invalid": "#b91c1c", "unavailable": "#b45309", "none": "#475569"}
_RUN_LABEL = "Run {id}"
_BUSY_LABEL = "Running..."


def _badge(state, detail, hi=(), raw=""):
    """Render the honest 3-state verdict. Never emits green markup for a non-`valid` state."""
    color = _COLOR.get(state, "#b45309")
    head = (f'<span style="color:{color};font-weight:800;display:inline-flex;align-items:center;gap:8px">'
            f'{_STATUS_SVG.get(state, "")}{_HEAD.get(state, state.upper())}</span>')
    body = f"\n\n{detail}" if detail else ""
    h = "\n".join(f"- **{x['label']}:** `{x['value']}`" for x in hi)
    md = f"### {head}{body}" + (f"\n\n{h}" if h else "")
    return md


def _empty(desc):
    """Pre-run empty state: say what the tool does and what a result looks like (not blank)."""
    return (f"### Ready\nRun **{desc['id']}** to produce `{desc['run'].get('artifact_name', 'artifact.json')}`. "
            f"The verdict below is the real result of an external validator, reported honestly as one of "
            f"**VALID / INVALID / VALIDATOR-UNAVAILABLE**. "
            f"It is never a fabricated green on an empty or failed run.")


def _widget(spec):
    t, lab = spec["type"], spec.get("label", spec["name"])
    info = spec.get("info")
    req = spec.get("required", False)
    if t == "file":
        # gr.File has no `info` kwarg in Gradio 6 — fold the hint into the label.
        return gr.File(label=lab + (f" — {info}" if info else ""), file_types=spec.get("accept"))
    if t == "enum":
        choices = spec["choices"]
        # Radio for 2-3 options (all visible), Dropdown for more (GOV.UK / NN/g).
        if len(choices) <= 3:
            return gr.Radio(choices, value=spec.get("default"), label=lab, info=info)
        return gr.Dropdown(choices, value=spec.get("default"), label=lab, info=info)
    if t in ("int", "float"):
        if spec.get("widget") == "slider":
            step = 1 if t == "int" else 0.1
            return gr.Slider(spec.get("min", 0), spec.get("max", 100),
                             value=spec.get("default", 0), step=step, label=lab, info=info)
        return gr.Number(value=spec.get("default"), label=lab,
                         precision=0 if t == "int" else None, info=info)
    if t == "bool":
        return gr.Checkbox(value=spec.get("default", False), label=lab, info=info)
    return gr.Textbox(value=spec.get("default", ""), label=lab + (" *" if req else ""),
                      placeholder=spec.get("placeholder", ""), info=info)


def _collect(desc, vals):
    params = {}
    for spec, v in zip(desc.get("inputs", []), vals):
        params[spec["name"]] = (v.name if (v is not None and spec["type"] == "file")
                                else (v if v is not None else ""))
    return params


def _result(desc, res):
    """(badge_md, artifact_json, raw_log_md, artifact_path). Honest on every branch."""
    state, detail = res["badge"]
    if "error" in res:
        # detail now carries the specific reason (which tool, or the tool's own error line);
        # show it directly. The full stderr is in the Raw log below.
        raw = f"```\n{res['error']}\n```"
        return _badge(state, detail), None, raw, None
    return (_badge(state, detail, res.get("highlights", [])),
            res.get("artifact"), "", res.get("artifact_path"))


def _handler(desc):
    def run(*vals, progress=gr.Progress()):
        progress(0, desc=f"running {desc['id']}…")
        params = _collect(desc, vals)
        res = run_descriptor(desc, params)
        progress(1)
        badge, art, raw, path = _result(desc, res)
        # Reset the Run button here, atomic with the result, so it always clears "Running…"
        # (a trailing .then could be skipped; _result never raises, so this return always runs).
        reset = gr.update(value=_RUN_LABEL.format(id=desc["id"]), interactive=True)
        return badge, art, raw, path, reset
    return run


def _chain_handler(chain, descs):
    target = descs[chain["to"]]

    def run(artifact_path, progress=gr.Progress()):
        if not artifact_path:
            # Pre-run guard (no artifact yet): mirror _empty()'s honest, emoji-free surface
            # rather than a validator verdict — nothing has been validated to badge.
            return ("### Nothing to convert yet\nRun the tool above first, then use this "
                    "button to convert its output.", None, "", None)
        progress(0, desc=f"running {target['id']}…")
        params = dict(chain.get("with", {})) | {chain["pass_artifact_as"]: artifact_path}
        res = run_descriptor(target, params)
        progress(1)
        return _result(target, res)
    return run


def _busy(did):
    return gr.update(value=_BUSY_LABEL, interactive=False)


def _idle(did):
    return gr.update(value=_RUN_LABEL.format(id=did), interactive=True)


def _diag_md(ok, text):
    color = "#0ba0b6" if ok else "#b45309"
    return f'<span style="color:{color};font-weight:700">{"OK" if ok else "FAILED"}</span>: {text}'


def _verify_md(value, argv_template):
    ok, line = verify_path(value, argv_template)
    return _diag_md(ok, line)


def _action_md(desc, action, vals):
    # A descriptor-declared action button (#5): run its argv against the current inputs.
    ok, msg = run_action(action, _collect(desc, vals))
    return _diag_md(ok, msg)


def build():
    descs = load_descriptors()
    hdr = _header_brand(descs)
    with gr.Blocks(title=BRAND["name"]) as demo:
        img = f'<img src="data:image/png;base64,{_B64}" style="height:50px;width:auto" alt="{BRAND["company"]} logo"/>' if _B64 else ""
        with gr.Row(equal_height=True):
            with gr.Column(scale=8):
                gr.HTML(f'<div class="brandbar" style="display:flex;align-items:center;gap:14px">{img}'
                        f'<div style="flex:1"><div style="font-size:22px;font-weight:800">{hdr["product"]} '
                        f'<span style="color:#16c7d8">v{hdr["version"]}</span></div>'
                        f'<div style="color:#64748b;font-size:12px">'
                        f'{_link(hdr["url"], "breachsafe.ai")} &nbsp;&middot;&nbsp; '
                        f'{_link(hdr["repo"], "GitHub")} &nbsp;&middot;&nbsp; {_LICENSE}</div></div></div>')
            with gr.Column(scale=1, min_width=130):
                theme_btn = gr.Button("Light / Dark", size="sm")
        # class-based dark mode, like EnXemble (next-themes .dark). Toggles the theme's _dark tokens.
        theme_btn.click(fn=None, inputs=None, outputs=None,
                        js="() => { const el = document.querySelector('gradio-app') || document.body; el.classList.toggle('dark'); }")
        for did, desc in descs.items():
            if desc.get("standalone") is False:
                continue  # chain-only tool (e.g. mint-oscal): reached via a Convert button, not its own tab
            with gr.Tab(desc.get("title", did)):
                gr.Markdown(desc.get("description", ""))
                widgets, advanced_widgets = [], []
                name2widget = {}
                for spec in desc.get("inputs", []):
                    if spec.get("group") != "advanced":
                        w = _widget(spec)
                        widgets.append(w)
                        name2widget[spec["name"]] = w
                # Progressive disclosure: advanced params collapsed by default (NN/g).
                adv_specs = [s for s in desc.get("inputs", []) if s.get("group") == "advanced"]
                if adv_specs:
                    with gr.Accordion("Advanced options", open=False):
                        for spec in adv_specs:
                            # The field is directly editable (pre-populated); `verify_argv` adds a
                            # short Verify button next to it that runs the tool's own check.
                            w = _widget(spec)
                            advanced_widgets.append(w)
                            name2widget[spec["name"]] = w
                            if spec.get("verify_argv"):
                                vb = gr.Button("Verify", size="sm", variant="secondary")
                                vr = gr.Markdown()
                                vb.click(lambda v, t=spec["verify_argv"]: _verify_md(v, t), w, vr)
                # widgets must be ordered to match desc["inputs"] for _collect's zip.
                ordered = []
                adv_iter = iter(advanced_widgets)
                basic_iter = iter(widgets)
                for spec in desc.get("inputs", []):
                    ordered.append(next(adv_iter) if spec.get("group") == "advanced" else next(basic_iter))

                # Descriptor-declared action buttons (#5): each runs its own argv against the
                # inputs and shows OK/FAIL. Replaces the old hardcoded 'Test connection' preflight.
                for action in desc.get("actions", []):
                    ab = gr.Button(action["label"], size="sm", variant="secondary")
                    ar = gr.Markdown()
                    ab.click(lambda *vals, a=action, d=desc: _action_md(d, a, vals), ordered, ar)

                run_btn = gr.Button(_RUN_LABEL.format(id=did), variant="primary", icon=_ICON["run"])
                badge = gr.Markdown(_empty(desc))
                dl = gr.DownloadButton("Download output", visible=False)
                with gr.Accordion("Raw log", open=False):
                    raw_log = gr.Markdown("")
                out = gr.JSON(label="artifact")
                artifact_state = gr.State(None)

                heavy = desc["run"].get("timeout_s", 0) >= 60
                # run_btn is a handler OUTPUT so the reset is atomic with the result; no trailing
                # .then that could be skipped and leave the button stuck on "Running…".
                (run_btn.click(lambda d=did: _busy(d), None, run_btn)
                 .then(_handler(desc), ordered, [badge, out, raw_log, artifact_state, run_btn],
                       show_progress="full", concurrency_limit=1 if heavy else None)
                 .then(lambda p: gr.update(value=p, visible=bool(p)), artifact_state, dl))

                for chain in desc.get("chains", []):
                    target = descs.get(chain["to"])
                    clabel = chain.get("label", chain["to"])
                    if target is None or not tool_available(target):
                        # W-5: honest, not a dead button. Disable it and say why it cannot run
                        # (e.g. a qureddy-only [ui] install has no mint-oscal for OSCAL conversion).
                        need = (target or {}).get("run", {}).get("base", [chain["to"]])[0]
                        gr.Button(f"{clabel} (unavailable)", variant="secondary",
                                  icon=_ICON["convert"], interactive=False)
                        gr.Markdown(f"_Requires `{need}`, which is not installed in this deployment._")
                        continue
                    cbtn = gr.Button(clabel, variant="secondary", icon=_ICON["convert"])
                    cbadge = gr.Markdown()
                    cdl = gr.DownloadButton("Download output", visible=False)
                    with gr.Accordion(f"{chain['to']} raw log", open=False):
                        craw = gr.Markdown("")
                    cout = gr.JSON(label=f"{chain['to']} output")
                    cstate = gr.State(None)
                    (cbtn.click(lambda: gr.update(value=_BUSY_LABEL, interactive=False), None, cbtn)
                     .then(_chain_handler(chain, descs), [artifact_state], [cbadge, cout, craw, cstate],
                           show_progress="full", concurrency_limit=1)
                     .then(lambda p: gr.update(value=p, visible=bool(p)), cstate, cdl)
                     .then(lambda c=chain: gr.update(value=c.get("label", c["to"]), interactive=True),
                           None, cbtn))
        gr.HTML(
            '<div class="bs-footer">'
            f'<span>{hdr["product"]} v{hdr["version"]}</span>'
            f'{_link(hdr["url"], "breachsafe.ai")}'
            f'{_link(hdr["repo"], "GitHub")}'
            f'<span>{_LICENSE}</span></div>')
    return demo


def main():
    demo = build()
    demo.queue()  # required so gr.Progress + concurrency work for long-running scans
    # Gradio 6.0 moved theme/css from the Blocks constructor to launch().
    demo.launch(theme=THEME, css=CSS, allowed_paths=[str(_ICON_DIR)],
                server_name=os.environ.get("BREACHSAFE_UX_HOST", "127.0.0.1"),
                server_port=int(os.environ.get("BREACHSAFE_UX_PORT", "7860")))


if __name__ == "__main__":
    main()
