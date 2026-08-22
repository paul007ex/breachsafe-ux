# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Vulture allowlist (#127): names that are intentionally kept but can read as "dead" to static
dead-code analysis. Passed to vulture as a scan target so these references count as usage:

    uv run --locked vulture --min-confidence 80 src/breachsafe_ux .vulture_allowlist.py

Keep this list tight and commented — it is an escape hatch for genuine false positives (public
API re-exports, framework-attached callbacks, documented constants), never a way to hide real
dead code. Each entry is a bare name/attribute reference that vulture counts as "used".
"""

# Public API re-exported from the package __init__ (used by consumers/tests, not intra-package).
load_descriptors  # noqa: F821,B018 — re-exported in breachsafe_ux.__all__
run_descriptor  # noqa: F821,B018 — re-exported in breachsafe_ux.__all__

# Documented brand palette (brand.py): the single-source-of-truth hex reference mirrored from
# EnXemble globals.css. Kept as living documentation next to the derived gr.themes.Color even
# though the theme is currently built from the literals; do not silently drop it.
BS  # noqa: F821,B018

# Gradio attaches event methods (.click/.then) and passes handler args at runtime; the inner
# `run`/`repl` closures and their params (e.g. progress=gr.Progress()) can look unused to a
# static reader. Listed defensively so a lower-confidence sweep stays green.
progress  # noqa: F821,B018
