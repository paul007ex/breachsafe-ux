# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Model: locate the binaries a descriptor needs, resolve them on this system, and probe
versions. Pure Python, no Gradio. facade.py runs/validates a descriptor; this answers
"where is the tool + its deps, and what versions" — the environment() model behind the UI
provenance (#75) and the single resolver (#84/#86). Split from facade.py for the size gate.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent
TOOLS = ROOT / "tools"
_VER_RE = re.compile(r"\d+\.\d+(?:\.\d+)?(?:[-.\w]+)?")  # first version-looking token


def _tools_dir() -> Path:
    """Descriptor root; a host points here via BREACHSAFE_UX_TOOLS_DIR (read at call time)."""
    d = os.environ.get("BREACHSAFE_UX_TOOLS_DIR")
    return Path(d) if d else TOOLS


def _bin_path() -> str:
    return os.pathsep.join(str(p) for p in _tools_dir().glob("*/bin"))


def _search_path() -> str:
    """Tool-resolution PATH: per-tool bin shims first, then the ambient PATH."""
    return f"{_bin_path()}{os.pathsep}{os.environ.get('PATH', '')}"


def _resolve(cmd: str) -> str | None:
    """Absolute path of a command the way the engine runs it (shims -> PATH). Cross-platform
    (shutil.which honours PATHEXT/.exe). None if empty or not found (#84)."""
    return shutil.which(cmd, path=_search_path()) if cmd else None


def _run_env() -> dict[str, str]:
    """Subprocess environment carrying the tool-resolution PATH (per-tool bin shims -> ambient
    PATH), so a child resolves the same binaries the engine's resolver does (#116). subprocess
    computes a bare argv[0]'s candidates from this env's PATH (os.get_exec_path), matching
    run_descriptor, verify_path, run_action, and _validate on one PATH."""
    return os.environ | {"PATH": _search_path()}


def _run(
    argv: list[str], *, timeout: float, input_: str = "", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str] | None:
    """Run argv (no shell), capture text output; None on launch failure or timeout (#86). Pass
    `env` (e.g. _run_env()) to resolve/run against the augmented tool PATH; None inherits."""
    try:
        return subprocess.run(
            argv, input=input_, capture_output=True, text=True, timeout=timeout, env=env
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _tool_version(argv: list[str]) -> str | None:
    """Run a tool's own version command; return the first version-looking token (#51)."""
    exe = _resolve(argv[0]) or argv[0]
    p = _run([exe, *argv[1:]], timeout=5)
    if p is None:
        return None
    m = _VER_RE.search((p.stdout or "") + (p.stderr or ""))
    return m.group(0) if m else None


@functools.lru_cache(maxsize=64)
def _probe_version(exe: str) -> str:
    """First version-looking token from a resolved binary (try --version then version). Cached
    per exe — surfaces which openssl/python/docker a dependency actually is (#75)."""
    for flag in ("--version", "version"):
        p = _run([exe, flag], timeout=5)
        if p is not None:
            m = _VER_RE.search((p.stdout or "") + (p.stderr or ""))
            if m:
                return m.group(0)
    return ""


def _tool_source(run: dict[str, Any]) -> tuple[str, str | None]:
    """How a descriptor's tool runs here, preferring a local binary over the image:
    ("local", resolved_path) if run.base[0] is on PATH, ("image", image_ref) if run.image is
    declared (docker fallback), ("local", None) when no tool is declared, else ("missing", None).
    Single source of truth for run_descriptor, tool_available, and environment (#75).
    """
    cmd = (run.get("base") or run.get("argv") or [None])[0]
    path = _resolve(cmd) if cmd else None
    if path:
        return ("local", path)
    if run.get("image"):
        return ("image", run["image"])
    if not cmd:
        return ("local", None)  # no tool declared -> trivially runnable
    return ("missing", None)


def tool_available(desc: dict[str, Any]) -> bool:
    """Best-effort: can this descriptor's tool run here? Local binary, or the docker image as a
    fallback when docker is present (W-5 chain-button state)."""
    mode, _ = _tool_source(desc.get("run", {}))
    if mode == "image":
        return _resolve("docker") is not None
    return mode == "local"


def _validator_argvs(desc: dict[str, Any]) -> list[list[str]]:
    """The validator argv(s): singular validate.argv, or each non-null validate.by case (#43)."""
    v = desc.get("validate")
    if not isinstance(v, dict):
        return []
    if "by" in v:
        return [
            c["argv"]
            for c in (v.get("cases") or {}).values()
            if isinstance(c, dict) and c.get("argv")
        ]
    return [v["argv"]] if v.get("argv") else []


def _dep_row(role: str, cmd: str, path: str | None) -> dict[str, Any]:
    """One provenance row for a resolved (or unresolved) dependency binary (#75)."""
    return {
        "role": role,
        "cmd": cmd,
        "path": path,
        "ok": path is not None,
        "version": _probe_version(path) if path else "",
    }


def _tool_rows(desc: dict[str, Any], run: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    """The 'tool' provenance row(s): docker-image fallback, or the resolved local binary (#75)."""
    mode, loc = _tool_source(run)
    if mode == "image":
        # docker fallback: the tool runs as its image (pulled on demand); show that provenance.
        seen.add(run["image"])
        return [
            {
                "role": "tool",
                "cmd": run["image"],
                "path": f"docker run {run['image']}",
                "ok": _resolve("docker") is not None,
                "version": "(image)",
            }
        ]
    tool = (run.get("base") or run.get("argv") or [None])[0]
    if not tool:
        return []
    seen.add(tool)
    version = (desc.get("brand") or {}).get("version", "") or (_probe_version(loc) if loc else "")
    return [{"role": "tool", "cmd": tool, "path": loc, "ok": loc is not None, "version": version}]


def _validator_rows(desc: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    """Provenance rows for each validator dependency, de-duplicated against `seen` (#75)."""
    rows: list[dict[str, Any]] = []
    for argv in _validator_argvs(desc):
        if not argv:
            continue
        cmd = "python" if argv[0] == "{python}" else argv[0]
        if cmd in seen:
            continue
        seen.add(cmd)
        path = sys.executable if argv[0] == "{python}" else _resolve(argv[0])
        rows.append(_dep_row("validator", cmd, path))
    return rows


def _action_rows(desc: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    """Provenance rows for each descriptor action's binary, de-duplicated against `seen` (#75)."""
    rows: list[dict[str, Any]] = []
    for action in desc.get("actions", []):
        argv = action.get("argv") or []
        cmd = argv[0] if argv else ""
        if not cmd or cmd in seen:
            continue
        seen.add(cmd)
        rows.append(_dep_row(action.get("label", "action"), cmd, _resolve(cmd)))
    return rows


def environment(desc: dict[str, Any]) -> list[dict[str, Any]]:
    """Every binary this descriptor resolves on THIS system — tool + validator dep(s) + each
    action/preflight — as rows {role, cmd, version, path, ok}. Single source of truth for
    provenance (#75): the header line and Environment panel are thin views of this. Derives from
    existing descriptor fields (no YAML), resolves via _resolve (no re-resolution), probes each
    dependency's version, names no tool -> tool-agnostic + cross-platform.
    """
    run = desc.get("run", {})
    seen: set[str] = set()
    return _tool_rows(desc, run, seen) + _validator_rows(desc, seen) + _action_rows(desc, seen)
