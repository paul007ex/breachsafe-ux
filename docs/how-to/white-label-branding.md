<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# White-label the branding

The host's look is a single theme layer, `src/breachsafe_ux/brand.py`. It is the one source of
the product name, colours, theme, and CSS, so re-skinning the host means editing that one module
rather than hunting styles across the app. Only the UI-edge modules (`app.py`, `brand.py`, and `evidence_ui.py`)
theme) import Gradio; the model, view, and engine stay framework-free.

`brand.py` ships the BreachSAFE EnXemble identity. To white-label the host under your own brand,
change the values in this module.

## What `brand.py` exposes

| Name | What it controls |
|---|---|
| `BRAND` | Text identity: product name, company, URL, repository link, tagline. `BRAND["name"]` is the browser tab title and the header lockup. |
| `BS` | The brand colour tokens (the primary accent, hover/press shades, background, and text colours). |
| `THEME` | The Gradio theme built from those tokens: light and dark backgrounds, text, and the primary button fill. |
| `GRADIENT` | The accent gradient used for the header bar. |
| `CSS` | Custom CSS injected at launch (header bar, button sizing, footer). |

## Change the text identity

Edit the `BRAND` dictionary:

```python
BRAND = {
    "name": "Acme Security Console",
    "company": "Acme",
    "product": "Security Console",
    "url": "https://acme.example",
    "repo": "https://github.com/acme/console",
    "tagline": "Your one-line product tagline.",
}
```

`BRAND["name"]` sets the window title (`gr.Blocks(title=...)`) and the header.

## Change the colours and theme

`THEME` is a `gradio.themes` object. Retint it by editing the colour ramp and the theme
`.set(...)` overrides: the primary button fill, the light and dark backgrounds, and the text
colours. Keep a light and a dark value for each so both modes stay legible; the host defaults to
dark on load and offers a Light/Dark toggle. `CSS` carries the header-bar rule and the button
sizing; adjust it to match your design system.

## Keep third-party assets under their own licence

The bundled icon set is third-party (Lucide, ISC) and stays under its original licence. Do not
relabel vendored assets as your own when you re-skin. If you swap in your own icons, add them
with their correct licence and update `REUSE.toml` accordingly.

## Verify

Run the host from source and open it in a browser to see the new identity:

```bash
uv run breachsafe-ux
```

Because branding is one module, this is the whole change: no per-tab edits, and the descriptor
contract is untouched.
