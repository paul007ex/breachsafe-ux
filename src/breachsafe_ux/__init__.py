"""breachsafe-ux — a config-driven single-tool UX host.

One tool = one YAML descriptor under ``tools/<name>/<name>.yaml``. The engine
(:mod:`breachsafe_ux.facade`) builds a typed argv (no shell), runs the tool,
runs its external validator, and derives a 3-state badge
(``valid`` / ``invalid`` / ``unavailable``). The Gradio shell
(:mod:`breachsafe_ux.app`) renders every descriptor as widgets.
"""

from importlib.metadata import PackageNotFoundError, version

from breachsafe_ux.facade import load_descriptors, run_descriptor

try:
    # Single-source the version from the installed dist metadata (#115); pyproject is the one
    # source of truth, so a hardcoded literal here can never drift from [project].version.
    __version__ = version("breachsafe-ux")
except PackageNotFoundError:  # running from a source tree without an installed dist
    __version__ = "0.0.0"

__all__ = ["__version__", "load_descriptors", "run_descriptor"]
