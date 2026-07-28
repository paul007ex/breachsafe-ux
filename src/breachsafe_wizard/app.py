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
from pathlib import Path
import gradio as gr
from breachsafe_wizard.facade import load_descriptors, run_descriptor, ROOT
from breachsafe_wizard.brand import THEME, CSS, BRAND

DESCS = load_descriptors()
_LOGO = ROOT / "assets" / "logo.png"
_B64 = base64.b64encode(_LOGO.read_bytes()).decode() if _LOGO.exists() else ""

_ICON = {"valid": "✅", "invalid": "❌", "unavailable": "⚠️", "none": "➖"}
_HEAD = {"valid": "VALID", "invalid": "INVALID",
         "unavailable": "VALIDATOR UNAVAILABLE", "none": "NO EXTERNAL VALIDATOR"}
# colour is a REDUNDANT cue only — the icon + word already carry the state (WCAG 1.4.1).
_COLOR = {"valid": "#0ba0b6", "invalid": "#b91c1c", "unavailable": "#b45309", "none": "#475569"}
_RUN_LABEL = "▶ Run {id}"
_BUSY_LABEL = "⏳ Running…"


def _badge(state, detail, hi=(), raw=""):
    """Render the honest 3-state verdict. Never emits green markup for a non-`valid` state."""
    color = _COLOR.get(state, "#b45309")
    head = f'<span style="color:{color};font-weight:800">{_ICON.get(state, "⚠️")} {_HEAD.get(state, state.upper())}</span>'
    body = f"\n\n{detail}" if detail else ""
    h = "\n".join(f"- **{x['label']}:** `{x['value']}`" for x in hi)
    md = f"### {head}{body}" + (f"\n\n{h}" if h else "")
    return md


def _empty(desc):
    """Pre-run empty state: say what the tool does and what a result looks like (not blank)."""
    vname = desc.get("validate", {}).get("argv", ["(none)"])[0]
    return (f"### ⏳ Ready\nRun **{desc['id']}** to produce `{desc['run'].get('artifact_name', 'artifact.json')}`. "
            f"The verdict below is the real result of an external validator "
            f"(`{vname}`), reported honestly as one of "
            f"**{_ICON['valid']} VALID / {_ICON['invalid']} INVALID / {_ICON['unavailable']} VALIDATOR-UNAVAILABLE** "
            f"— never a fabricated green on an empty or failed run.")


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
        human = {"unavailable": "The tool or its validator could not run.",
                 "invalid": "The validator rejected this artifact."}.get(state, "The run did not succeed.")
        raw = f"```\n{res['error']}\n```"
        return _badge(state, f"{human} ({detail})"), None, raw, None
    return (_badge(state, detail, res.get("highlights", [])),
            res.get("artifact"), "", res.get("artifact_path"))


def _handler(desc):
    def run(*vals, progress=gr.Progress()):
        progress(0, desc=f"running {desc['id']}…")
        params = _collect(desc, vals)
        res = run_descriptor(desc, params)
        progress(1)
        badge, art, raw, path = _result(desc, res)
        return badge, art, raw, path
    return run


def _chain_handler(chain):
    target = DESCS[chain["to"]]

    def run(artifact_path, progress=gr.Progress()):
        if not artifact_path:
            return "### ⚠️ Nothing to convert\nRun the tool above first.", None, "", None
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


def build():
    with gr.Blocks(title=BRAND["name"]) as demo:
        img = f'<img src="data:image/png;base64,{_B64}" style="height:50px;width:auto" alt="{BRAND["company"]} logo"/>' if _B64 else "🛡️"
        gr.HTML(f'<div class="brandbar" style="display:flex;align-items:center;gap:14px">{img}'
                f'<div><div style="font-size:22px;font-weight:800">{BRAND["name"]} '
                f'<span style="color:#16c7d8">Wizard</span></div>'
                f'<div style="color:#64748b;font-size:12px">{BRAND["tagline"]}</div></div></div>')
        for did, desc in DESCS.items():
            with gr.Tab(desc.get("title", did)):
                gr.Markdown(desc.get("description", ""))
                widgets, advanced_widgets = [], []
                for spec in desc.get("inputs", []):
                    if spec.get("group") != "advanced":
                        widgets.append(_widget(spec))
                # Progressive disclosure: advanced params collapsed by default (NN/g).
                adv_specs = [s for s in desc.get("inputs", []) if s.get("group") == "advanced"]
                if adv_specs:
                    with gr.Accordion("Advanced options", open=False):
                        for spec in adv_specs:
                            advanced_widgets.append(_widget(spec))
                # widgets must be ordered to match desc["inputs"] for _collect's zip.
                ordered = []
                adv_iter = iter(advanced_widgets)
                basic_iter = iter(widgets)
                for spec in desc.get("inputs", []):
                    ordered.append(next(adv_iter) if spec.get("group") == "advanced" else next(basic_iter))

                run_btn = gr.Button(_RUN_LABEL.format(id=did), variant="primary")
                badge = gr.Markdown(_empty(desc))
                with gr.Accordion("Raw log", open=False):
                    raw_log = gr.Markdown("")
                out = gr.JSON(label="artifact")
                artifact_state = gr.State(None)

                heavy = desc["run"].get("timeout_s", 0) >= 60
                (run_btn.click(lambda d=did: _busy(d), None, run_btn)
                 .then(_handler(desc), ordered, [badge, out, raw_log, artifact_state],
                       show_progress="full", concurrency_limit=1 if heavy else None)
                 .then(lambda d=did: _idle(d), None, run_btn))

                for chain in desc.get("chains", []):
                    cbtn = gr.Button(chain.get("label", f"→ {chain['to']}"), variant="secondary")
                    cbadge = gr.Markdown()
                    with gr.Accordion(f"{chain['to']} raw log", open=False):
                        craw = gr.Markdown("")
                    cout = gr.JSON(label=f"{chain['to']} output")
                    cstate = gr.State(None)
                    (cbtn.click(lambda: gr.update(value=_BUSY_LABEL, interactive=False), None, cbtn)
                     .then(_chain_handler(chain), [artifact_state], [cbadge, cout, craw, cstate],
                           show_progress="full", concurrency_limit=1)
                     .then(lambda c=chain: gr.update(value=c.get("label", f"→ {c['to']}"), interactive=True),
                           None, cbtn))
    return demo


def main():
    demo = build()
    demo.queue()  # required so gr.Progress + concurrency work for long-running scans
    # Gradio 6.0 moved theme/css from the Blocks constructor to launch().
    demo.launch(theme=THEME, css=CSS,
                server_name="127.0.0.1", server_port=int(os.environ.get("WIZARD_PORT", "7860")))


if __name__ == "__main__":
    main()
