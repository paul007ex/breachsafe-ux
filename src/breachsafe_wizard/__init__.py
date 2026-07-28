"""breachsafe-wizard — a config-driven, honest single-tool UX harness.

One tool = one YAML descriptor under ``tools/<name>/<name>.yaml``. The engine
(:mod:`breachsafe_wizard.facade`) builds a typed argv (no shell), runs the tool,
runs its external validator, and derives an honest 3-state badge
(``valid`` / ``invalid`` / ``unavailable``). The Gradio shell
(:mod:`breachsafe_wizard.app`) renders every descriptor as widgets.
"""

__version__ = "0.1.0"

from breachsafe_wizard.facade import load_descriptors, run_descriptor  # noqa: E402,F401

__all__ = ["__version__", "load_descriptors", "run_descriptor"]
