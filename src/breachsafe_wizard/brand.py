"""BreachSAFE brand tokens, consistent with EnXemble (ui/config/brand.ts + styles/globals.css).

Light and dark are class-based like EnXemble: light background #fdfdfd / slate-950 text,
dark background #000000 / white text, and the brand cyan #3ae7f4 primary button stays cyan
in both modes. Single source of truth; these mirror globals.css (do not re-invent per app).
"""
import gradio as gr

BRAND = {
    "name": "BreachSAFE EnXemble",
    "company": "BreachSAFE",
    "product": "EnXemble",
    "ai": "Aurelius",
    "url": "https://www.breachsafe.ai",
    "repo": "https://github.com/paul007ex/breachsafe-wizard",
    "tagline": "The unified security posture platform, starting with the post-quantum transition.",
}
# globals.css: bs-cyan-400 #3ae7f4 is THE brand cyan; navy #141414; magenta #ff0073.
BS = {"cyan": "#3ae7f4", "cyan_hover": "#68e5f6", "cyan_press": "#16c7d8",
      "navy": "#141414", "black": "#000000", "magenta": "#ff0073", "ink": "#0f172a", "paper": "#fdfdfd"}

_cyan = gr.themes.Color(c50="#ecfeff", c100="#cff9fd", c200="#a5f2fb", c300="#68e5f6",
                        c400="#3ae7f4", c500="#16c7d8", c600="#0ba0b6", c700="#107f93",
                        c800="#166577", c900="#164f5e", c950="#0a2a33")

THEME = gr.themes.Soft(primary_hue=_cyan, neutral_hue=gr.themes.colors.slate).set(
    # light
    body_background_fill="#fdfdfd",
    body_text_color="#0f172a",
    button_primary_background_fill="#3ae7f4",
    button_primary_background_fill_hover="#68e5f6",
    button_primary_text_color="#141414",
    button_large_radius="10px",
    button_small_radius="8px",
    # dark, matching EnXemble: black background, white text, cyan button stays cyan
    body_background_fill_dark="#000000",
    body_text_color_dark="#ffffff",
    block_background_fill_dark="#0b0b0b",
    block_border_color_dark="#1f2937",
    button_primary_background_fill_dark="#3ae7f4",
    button_primary_background_fill_hover_dark="#68e5f6",
    button_primary_text_color_dark="#141414",
)

CSS = (
    ".gradio-container{font-family:-apple-system,Segoe UI,Roboto,sans-serif}"
    "footer{visibility:hidden}"
    ".brandbar{border-bottom:2px solid #3ae7f4;padding-bottom:10px;margin-bottom:10px}"
    # cyan glow on the primary button in dark mode, like EnXemble
    ".dark .primary{box-shadow:0 0 10px rgba(58,231,244,.35)}"
    ".bs-footer{border-top:1px solid #1f293733;margin-top:20px;padding-top:12px;"
    "color:#64748b;font-size:12px;display:flex;gap:16px;align-items:center}"
    ".bs-footer a{color:#0ba0b6;text-decoration:none}"
)
