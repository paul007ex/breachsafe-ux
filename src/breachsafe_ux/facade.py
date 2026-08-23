"""Engine: config-driven single-tool runner.

A tool is a YAML descriptor under tools/<name>/<name>.yaml. The engine renders it, builds a
typed argv (no shell), runs the tool, runs its external validator, and derives a
3-state badge (valid / invalid / validator-unavailable). Zero tool-specific logic lives here.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from breachsafe_ux._render import _highlights  # used by run_descriptor; _posture lives in _render
from breachsafe_ux.resolve import (
    _resolve,
    _run,
    _run_env,
    _tool_source,
    _tool_version,
    _tools_dir,
)

PKG = Path(__file__).resolve().parent
RUN_ROOT = Path(
    os.environ.get("BREACHSAFE_UX_RUN_ROOT", str(Path.home() / "mint-proof" / "wizard-runs"))
)
# Substitution grammar (#50): `{{`/`}}` are literal braces; `{name}` is a token.
_SUBST = re.compile(r"\{\{|\}\}|\{([a-zA-Z0-9_]+)\}")
_RUN_KEEP = 20  # #121: cap RUN_ROOT at the most-recent N per-run workdirs


def _prune_run_root(keep: int = _RUN_KEEP) -> None:
    """Bound RUN_ROOT growth (#121): keep the most-recent workdirs, drop older; best-effort."""
    try:
        runs = [d for d in RUN_ROOT.iterdir() if d.is_dir()]
        if len(runs) <= keep:
            return
        runs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        for stale in runs[keep:]:
            shutil.rmtree(stale, ignore_errors=True)
    except OSError:
        return


class _DescriptorError(Exception):
    """A descriptor is malformed (e.g. an unresolved {token} in run argv).

    Surfaced as an 'unavailable' badge rather than shipped as literal text to the tool (wizard #8).
    """


_SCHEMA_PATH = PKG / "descriptor.schema.json"


@functools.lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """The compiled descriptor JSON Schema, loaded once. See descriptor.schema.json (#48)."""
    return Draft202012Validator(json.loads(_SCHEMA_PATH.read_text()))


SUPPORTED_SCHEMA_VERSION = 1


def _check_schema_version(doc: dict[str, Any], path: Path) -> None:
    """Version handshake (#49): a too-new schema_version fails CLOSED asking for a newer build."""
    ver = doc.get("schema_version") if isinstance(doc, dict) else None
    if ver is None:
        warnings.warn(
            f"{path.name}: no schema_version; assuming {SUPPORTED_SCHEMA_VERSION}", stacklevel=2
        )
        return
    # #104: numeric compare (not isinstance int). A YAML float 2.0 passes `type:integer` but is not
    # an int, so int-only let a too-new descriptor load; a bool cannot exceed 1 so it self-excludes.
    if isinstance(ver, (int, float)) and ver > SUPPORTED_SCHEMA_VERSION:
        raise _DescriptorError(
            f"{path.name}: schema_version {ver} needs a newer breachsafe-ux "
            f"(this build supports up to {SUPPORTED_SCHEMA_VERSION})"
        )


def _validate_descriptor(doc: dict[str, Any], path: Path) -> None:
    """Fail closed (#48): a descriptor that does not match descriptor.schema.json must not render.

    Raise naming the file and the JSON path of the first problem, so a typo is a clear load-time
    error, not a silent drop or a mid-run surprise.
    """
    _check_schema_version(doc, path)  # #49: version first, so a too-new descriptor says so
    errs = sorted(_validator().iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        loc = "/".join(map(str, errs[0].path)) or "<root>"
        raise _DescriptorError(f"{path.name}: invalid descriptor at '{loc}': {errs[0].message}")


def _expand_brand(d: dict[str, Any]) -> None:
    """Expand `${ENV}` in display-only brand metadata; single-source the version if set (#51)."""
    brand: dict[str, Any] = {
        k: (os.path.expandvars(v) if isinstance(v, str) else v) for k, v in d["brand"].items()
    }
    vcmd = brand.pop("version_cmd", None)
    if vcmd:
        brand["version"] = _tool_version(vcmd) or brand.get("version", "")
    d["brand"] = brand


def _expand_input_defaults(d: dict[str, Any]) -> None:
    """Expand `${ENV}` in each input's DEFAULT only; a submitted value is never expanded (#51)."""
    for inp in d.get("inputs", []):
        if isinstance(inp.get("default"), str):
            inp["default"] = os.path.expandvars(inp["default"])


def load_descriptors() -> dict[str, Any]:
    """Discover every <tools_dir>/<name>/<name>.yaml, ordered by `order` then id."""
    ds = []
    for y in sorted(_tools_dir().glob("*/*.yaml")):
        d = yaml.safe_load(y.read_text())
        try:
            _validate_descriptor(d, y)  # fail closed before the descriptor is used at all
        except _DescriptorError as e:
            # #174: isolate a bad descriptor. Skip it with a warning instead of raising, so one
            # malformed file does not down every other tab (and --check). Fail closed per-tool.
            warnings.warn(f"skipping invalid descriptor {y.name}: {e}", stacklevel=2)
            continue
        flag = d.get("feature_flag") if isinstance(d, dict) else None
        if flag and not feature_enabled(flag):
            continue  # #67: gated off for this deployment (e.g. mint_oscal in the OSS base edition)
        if isinstance(d.get("brand"), dict):
            _expand_brand(d)
        _expand_input_defaults(d)
        d["_dir"] = str(y.parent)
        ds.append(d)
    ds.sort(key=lambda d: (d.get("order", 99), d["id"]))
    return {d["id"]: d for d in ds}


def feature_enabled(flag: str) -> bool:
    """`feature_flag: X` renders only when True (#67): env `BREACHSAFE_UX_<X>`, default ON.

    Lets a deployment hide Pro features (e.g. mint_oscal/OSCAL) before they move to Pro (#25).
    """
    val = os.environ.get(f"BREACHSAFE_UX_{flag.upper()}", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def verify_path(value: str, argv_template: list[str]) -> tuple[bool, str]:
    """Run a tool's own version/verify command for a user path (the 'Verify' button).

    {value} is the path (e.g. ["{value}", "--version"]). Returns (ok, one-line summary), never
    raises; resolves via the augmented tool PATH like the engine (#116).
    """
    argv = [(value if a == "{value}" else a) for a in argv_template]
    if not argv or not argv[0].strip():
        return (False, "no path set")
    resolved = _resolve(argv[0]) or argv[0]
    p = _run([resolved, *argv[1:]], timeout=10, env=_run_env())
    if p is None:
        return (False, "cannot run")
    line = ((p.stdout or p.stderr).strip().splitlines() or [""])[0][:140]
    return (p.returncode == 0, line or f"exit {p.returncode}")


def run_action(action: dict[str, Any], params: dict[str, Any]) -> tuple[bool, str]:
    """Run a descriptor-declared action button (#5) and report (ok, output).

    Renders argv from the current inputs, runs it (no shell, stdin closed, timeout), and reports
    (ok, output) per `ok_if` (default exit 0). output is the tool's own stdout+stderr (#97).
    Generic replacement for the hardcoded openssl preflight (#21). Never raises.
    """
    try:
        argv = _render(action["argv"], params.copy())
    except _DescriptorError as e:
        return (False, str(e))
    if not argv or not argv[0].strip():
        return (False, "no command")
    # #116: augmented tool PATH so a bare argv[0] resolves via the per-tool bin shims.
    p = _run(argv, input_="", timeout=action.get("timeout_s", 10), env=_run_env())
    if p is None:
        return (False, "could not run")
    combined = p.stdout + p.stderr
    ok = _match(action.get("ok_if") or {"exit": 0}, combined, p.returncode)
    output = combined.strip()[:4000]
    return (ok, output or f"exit {p.returncode}")


def _render(argv: list[str], mapping: dict[str, Any]) -> list[str]:
    """Substitute `{name}` tokens into each argv element (never a shell); unresolved fails CLOSED."""
    unresolved: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        whole = m.group(0)
        if whole == "{{":
            return "{"
        if whole == "}}":
            return "}"
        name = m.group(1)
        if name in mapping:
            return str(mapping[name])
        unresolved.add(name)
        return whole

    out = [_SUBST.sub(repl, a) for a in argv]
    if unresolved:
        raise _DescriptorError("unresolved token(s) in argv: " + ", ".join(sorted(unresolved)))
    return out


_COND_KEYS = {"stdout_contains", "stdout_contains_any", "stdout_not_contains", "exit"}


def _match(cond: dict[str, Any], text: str, returncode: int) -> bool:
    """Evaluate a badge/action condition, failing CLOSED (#182); all present sub-conditions AND."""
    if not cond or (set(cond) - _COND_KEYS):
        return False
    checks = (
        "stdout_contains" not in cond or cond["stdout_contains"] in text,
        "stdout_contains_any" not in cond or any(s in text for s in cond["stdout_contains_any"]),
        "stdout_not_contains" not in cond or cond["stdout_not_contains"] not in text,
        "exit" not in cond or returncode == cond["exit"],
    )
    return all(checks)


def _input_argv(spec: dict[str, Any], params: dict[str, Any]) -> tuple[list[str], list[str]]:
    """One input's (options, positionals) contribution to the argv.

    At most one of positional (value), flag (token if truthy), or arg (['--x', value] when set).
    Values are single argv elements.
    """
    v = params.get(spec["name"])
    if spec.get("positional"):
        return ([], [str(v)] if v not in (None, "") else [])
    if "flag" in spec:
        return ([spec["flag"]] if v else [], [])
    if "arg" in spec:
        # Drop only the empty sentinels by identity, not `v not in (None, "", False)`: that
        # membership test treats a numeric 0 as absent (0 == False in Python), so `--maxfail 0`
        # or `--retries 0` were silently omitted (#171). A real 0/0.0 must reach the argv.
        drop = v is None or v == "" or v is False
        return ([spec["arg"], str(v)] if not drop else [], [])
    return ([], [])


def _build_argv(desc: dict[str, Any], params: dict[str, Any], mapping: dict[str, Any]) -> list[str]:
    """Static `run.argv`, or build from `run.base` + each input's argv mapping."""
    run = desc["run"]
    if "argv" in run:
        return _render(run["argv"], mapping)
    base = list(run.get("base", []))
    options: list[str] = []
    positionals: list[str] = []
    if run.get("positional_from"):  # compose one positional, e.g. "{host}:{port}"
        positionals.append(run["positional_from"])  # template; resolved by _render below
    for spec in desc.get("inputs", []):
        opts, poss = _input_argv(spec, params)
        options += opts
        positionals += poss
    argv = base + options
    # wizard #9 (argument injection): options, then a literal "--", then positionals, so a
    # leading-dash value can't be parsed as a flag. A tool lacking "--" opts out via
    # run.no_end_of_options (documented weaker posture).
    if positionals and not run.get("no_end_of_options"):
        argv.append("--")
    argv += positionals
    return _render(argv, mapping)


def _run_workdir(desc: dict[str, Any]) -> Path:
    """Unique per-invocation workdir under RUN_ROOT (GHSA-6ffp-258g-fvp5).

    A fresh uuid4 dir each run so no stale artifact is reused and no two runs share a dir;
    RUN_ROOT pruned to N (#121).
    """
    workdir = RUN_ROOT / f"{desc['id']}-{uuid.uuid4().hex[:12]}"
    workdir.mkdir(parents=True, exist_ok=True)
    _prune_run_root()  # #121: bound RUN_ROOT growth (keep the most-recent runs, incl. this one)
    return workdir


def _launch(
    argv: list[str], run: dict[str, Any], workdir: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str] | dict[str, Any]:
    """Run the tool argv (no shell); return its CompletedProcess or an error-result dict (#183)."""
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=run.get("timeout_s", 120),
            env=env,
            cwd=str(workdir),
        )
    except FileNotFoundError:
        return {
            "error": f"tool not found: {argv[0]}",
            "badge": ("unavailable", f"'{argv[0]}' is not installed or not on PATH"),
        }
    except subprocess.TimeoutExpired:
        return {"error": "tool timed out", "badge": ("unavailable", "tool timed out")}
    except (OSError, ValueError) as e:  # NUL byte, E2BIG, bad fd, permission — launch itself failed
        return {
            "error": f"could not launch tool: {e}",
            "badge": ("unavailable", "tool could not be launched"),
        }


def _nonzero_exit_result(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """Build the wizard #10 badge for a nonzero exit from the tool's last diagnostic line."""
    _err = proc.stderr.strip()
    _reason = _err.splitlines()[-1][:160] if _err else f"scan failed (exit {proc.returncode})"
    return {"error": (_err[:2000] or f"exit {proc.returncode}"), "badge": ("unavailable", _reason)}


def _postprocess(
    desc: dict[str, Any],
    workdir: Path,
    artifact: Path,
    proc: subprocess.CompletedProcess[str],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Persist stdout, enforce the false-green guards (#10/#15), then badge via the validator."""
    run = desc["run"]
    # #50/#44: always capture stdout to the workdir so a validator can inspect it (artifact:optional).
    (workdir / "stdout.txt").write_text(proc.stdout or "")
    if run.get("artifact_from") == "stdout":
        artifact.write_text(proc.stdout)
    # wizard #10 (false-green): a nonzero exit is never VALID even if a schema-shaped artifact was
    # written (the validator checks SHAPE, not success); a tool opts in via trust_artifact_on_nonzero.
    if proc.returncode != 0 and not run.get("trust_artifact_on_nonzero"):
        return _nonzero_exit_result(proc)
    # wizard #15 (false-green): exit 0 with an empty/missing artifact must not badge VALID.
    if not artifact.exists() or artifact.stat().st_size == 0:
        return {
            "error": "tool produced no output",
            "badge": ("unavailable", "scan produced no output"),
        }
    try:
        art_json = json.loads(artifact.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        # wizard #11: a non-JSON/unreadable artifact is "no structured highlights"; badge still
        # comes from the external validator below, not this parse.
        art_json = None
    return {
        "artifact": art_json,
        "artifact_path": str(artifact),
        "badge": _validate(desc, workdir, artifact, params),
        "highlights": _highlights(desc, art_json),
        "log": proc.stderr,  # #190: tool diagnostic log (stderr) for the Raw log accordion
    }


def run_descriptor(desc: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    """Run one descriptor end to end and return the UI-facing result dict (wizard #12).

    Builds a no-shell argv, runs the tool then its validator, derives the badge (a (state, detail)
    tuple; state in valid / invalid / unavailable / none). A successful run also carries `artifact`,
    `artifact_path`, and `highlights`. Any error returns `error` + `unavailable`, never raising.
    """
    workdir = _run_workdir(desc)
    artifact = workdir / desc["run"].get("artifact_name", "artifact.json")
    env = _run_env()  # #116: augmented tool PATH (per-tool bin shims -> ambient PATH)
    mapping = params | {
        "share": str(workdir),
        "workdir": str(workdir),
        "artifact": str(artifact),
        "python": sys.executable,
    }
    try:
        argv = _build_argv(desc, params, mapping)
    except _DescriptorError as e:
        # wizard #8: a malformed descriptor is an 'unavailable' badge, never a silent bad scan.
        return {"error": str(e), "badge": ("unavailable", f"descriptor error: {e}")}
    if _tool_source(desc["run"])[0] == "image":
        # Docker backend (W-3/W-4): tool is the image ENTRYPOINT, so drop argv[0] for `docker run`.
        # --pull=always keeps it current; missing docker -> FileNotFoundError -> unavailable.
        argv = ["docker", "run", "--rm", "--pull=always", desc["run"]["image"], *argv[1:]]
    proc = _launch(argv, desc["run"], workdir, env)
    if isinstance(proc, dict):
        return proc  # launch failed — error-result badge, never a traceback (#183)
    return _postprocess(desc, workdir, artifact, proc, params)


def _select_validator(v: dict[str, Any], params: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve validate.by (#43) to the validator case for the current inputs; unmatched -> None."""
    if "by" not in v:
        return v
    key = "|".join(str(params.get(k, "")) for k in v["by"])
    cases = v.get("cases", {})
    return cases[key] if key in cases else v.get("default")


def _validate_mapping(workdir: Path, artifact: Path) -> dict[str, str]:
    """Token namespace for a validator's argv: workdir/artifact paths + {python} + {stdout_file}."""
    return {
        "share": str(workdir),
        "workdir": str(workdir),
        "artifact": str(artifact),
        "artifact_name": artifact.name,
        "stdout_file": str(workdir / "stdout.txt"),
        "python": sys.executable,
    }


def _fail_detail(rule: dict[str, Any], text: str) -> str:
    """Extract the validator's own diagnostic lines for the badge detail via `fail_detail_grep`."""
    g = rule.get("fail_detail_grep")
    if not g:
        return ""
    return "\n".join(ln.strip() for ln in text.splitlines() if g in ln)[:1500]


def _pass_if_valid(rule: dict[str, Any], text: str, rc: int) -> bool:
    """Decide whether a `pass_if` match badges VALID (GHSA-6ffp-258g-fvp5).

    A `pass_if` match badges VALID only when the validator also exited 0 (unless pass_if pins
    `exit`, an opt-out) — else output merely containing "valid" false-greens.
    """
    pass_if = rule.get("pass_if")
    if not pass_if or not _match(pass_if, text, rc):
        return False
    return "exit" in pass_if or rc == 0


def _apply_badge_rule(rule: dict[str, Any], text: str, rc: int) -> tuple[str, str]:
    """Run the badge state machine (fail CLOSED, #182).

    infra -> unavailable; blessed -> valid; else the rule's `otherwise` (default invalid).
    """
    if "unavailable_if" in rule and _match(rule["unavailable_if"], text, rc):
        return ("unavailable", "validator could not run (infrastructure)")
    if _pass_if_valid(rule, text, rc):
        return ("valid", "validator accepted the artifact")
    detail = _fail_detail(rule, text)
    if "fail_if" in rule and _match(rule["fail_if"], text, rc):
        return ("invalid", detail or "validator rejected the artifact")
    return (rule.get("otherwise", "invalid"), detail or "validator ran; artifact not accepted")


def _validate(
    desc: dict[str, Any], workdir: Path, artifact: Path, params: dict[str, Any] | None = None
) -> tuple[str, str]:
    v = desc.get("validate")
    if not v:
        return ("none", "no external validator declared")
    v = _select_validator(v, params or {})
    if not v:
        # #43 fail-closed: a variant with no validator (unmatched selector or explicit null) is a
        # "none" badge, never a green (e.g. qureddy format=json/rich has no schema validator).
        return ("none", "no validator for this output")
    try:
        argv = _render(v["argv"], _validate_mapping(workdir, artifact))
    except _DescriptorError as e:
        # #104: _validate runs outside run_descriptor's try, so an unresolved validate.argv token
        # would raise to the UI; badge unavailable instead ("never raises to the UI" contract).
        return ("unavailable", f"validator descriptor error: {e}")
    if not _resolve(argv[0]):  # #116: resolve via the augmented tool PATH, like the tool itself
        return ("unavailable", f"validator '{argv[0]}' not installed")
    try:
        out = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=v.get("timeout_s", 180),
            env=_run_env(),  # #116: run the validator against the same augmented tool PATH
        )
    except Exception as e:  # any validator launch failure is an 'unavailable' badge, never a raise
        return ("unavailable", f"validator error: {type(e).__name__}")
    return _apply_badge_rule(v["badge_rule"], out.stdout + out.stderr, out.returncode)


# _find_prop / _highlights / _posture live in _render.py (size ceiling); _highlights is imported
# above and re-exported so `facade._highlights` stays importable (app + tests).
