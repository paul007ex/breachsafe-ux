"""BreachSAFE brand tokens (single source of truth = EnXemble ui/config/brand.ts + globals.css)."""
import gradio as gr

BRAND = {
    "name": "BreachSAFE EnXemble",
    "company": "BreachSAFE",
    "product": "EnXemble",
    "ai": "Aurelius",
    "tagline": "The unified security posture platform, starting with the post-quantum transition.",
}
# from globals.css: THE brand cyan is bs-cyan-400 #3ae7f4; navy #141414; magenta #ff0073
BS = {"cyan": "#3ae7f4", "cyan_hover": "#68e5f6", "cyan_press": "#16c7d8",
      "navy": "#141414", "black": "#000000", "magenta": "#ff0073"}

_cyan = gr.themes.Color(c50="#ecfeff", c100="#cff9fd", c200="#a5f2fb", c300="#68e5f6",
                        c400="#3ae7f4", c500="#16c7d8", c600="#0ba0b6", c700="#107f93",
                        c800="#166577", c900="#164f5e", c950="#0a2a33")
THEME = gr.themes.Soft(primary_hue=_cyan, neutral_hue=gr.themes.colors.slate).set(
    button_primary_background_fill="#3ae7f4",
    button_primary_background_fill_hover="#68e5f6",
    button_primary_text_color="#141414",
)
CSS = (".gradio-container{font-family:-apple-system,Segoe UI,sans-serif}"
       "footer{visibility:hidden}"
       ".brandbar{border-bottom:2px solid #3ae7f4;padding-bottom:8px;margin-bottom:10px}")
