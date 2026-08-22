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

import yaml
from jsonschema import Draft202012Validator

from breachsafe_ux._render import _highlights  # used by run_descriptor; _posture lives in _render

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent  # repo root (…/breachsafe-ux)
TOOLS = ROOT / "tools"
RUN_ROOT = Path(
    os.environ.get("BREACHSAFE_UX_RUN_ROOT", str(Path.home() / "mint-proof" / "wizard-runs"))
)
# Substitution grammar (#50): `{{`/`}}` are literal braces; `{name}` is a token.
_SUBST = re.compile(r"\{\{|\}\}|\{([a-zA-Z0-9_]+)\}")
_VER_RE = re.compile(r"\d+\.\d+(?:\.\d+)?(?:[-.\w]+)?")  # first version-looking token (#51)


class _DescriptorError(Exception):
    """A descriptor is malformed (e.g. an unresolved {token} in run argv). Surfaced as an
    'unavailable' badge rather than shipped as literal text to the tool (wizard #8).
    """


def _tools_dir() -> Path:
    """The descriptor root. A host package (e.g. qureddy) points here via BREACHSAFE_UX_TOOLS_DIR
    so the wizard renders that package's own tools instead of the bundled examples (W-1/W-2).
    Read at call time — never bound at import — so setting the env before launch is enough.
    """
    d = os.environ.get("BREACHSAFE_UX_TOOLS_DIR")
    return Path(d) if d else TOOLS


_SCHEMA_PATH = PKG / "descriptor.schema.json"


@functools.lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """The compiled descriptor JSON Schema, loaded once. See descriptor.schema.json (#48)."""
    return Draft202012Validator(json.loads(_SCHEMA_PATH.read_text()))


SUPPORTED_SCHEMA_VERSION = 1


def _check_schema_version(doc: dict, path: Path) -> None:
    """Version handshake (#49). A descriptor may declare `schema_version`; absent means 1
    (back-compat, warned once per file). A version newer than this build understands fails
    CLOSED with a clear 'needs a newer breachsafe-ux' message, rather than a confusing
    structural error from a schema that predates those fields.
    """
    ver = doc.get("schema_version") if isinstance(doc, dict) else None
    if ver is None:
        warnings.warn(
            f"{path.name}: no schema_version; assuming {SUPPORTED_SCHEMA_VERSION}", stacklevel=2
        )
        return
    if isinstance(ver, int) and ver > SUPPORTED_SCHEMA_VERSION:
        raise _DescriptorError(
            f"{path.name}: schema_version {ver} needs a newer breachsafe-ux "
            f"(this build supports up to {SUPPORTED_SCHEMA_VERSION})"
        )


def _validate_descriptor(doc: dict, path: Path) -> None:
    """Fail closed (#48): a descriptor that does not match descriptor.schema.json must not
    render. Raise naming the file and the JSON path of the first problem, so a typo is a clear
    load-time error, not a silent drop or a mid-run surprise.
    """
    _check_schema_version(doc, path)  # #49: version first, so a too-new descriptor says so
    errs = sorted(_validator().iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        loc = "/".join(map(str, errs[0].path)) or "<root>"
        raise _DescriptorError(f"{path.name}: invalid descriptor at '{loc}': {errs[0].message}")


def load_descriptors() -> dict:
    """Discover every <tools_dir>/<name>/<name>.yaml, ordered by `order` then id."""
    ds = []
    for y in sorted(_tools_dir().glob("*/*.yaml")):
        d = yaml.safe_load(y.read_text())
        _validate_descriptor(d, y)  # fail closed before the descriptor is used at all
        flag = d.get("feature_flag") if isinstance(d, dict) else None
        if flag and not feature_enabled(flag):
            continue  # #67: gated off for this deployment (e.g. mint_oscal in the OSS base edition)
        if isinstance(d.get("brand"), dict):
            # Display-only metadata may reference env vars, e.g. version: "${QUREDDY_VERSION}",
            # so a host can single-source the version instead of duplicating it here. Scoped to
            # brand only: run/validate argv never expand env, to avoid env injection into a command.
            d["brand"] = {
                k: (os.path.expandvars(v) if isinstance(v, str) else v)
                for k, v in d["brand"].items()
            }
            # Single-source the shown version from the installed tool (#51): if brand.version_cmd
            # is set, run it and use the parsed version; fall back to the literal `version`.
            vcmd = d["brand"].pop("version_cmd", None)
            if vcmd:
                d["brand"]["version"] = _tool_version(vcmd) or d["brand"].get("version", "")
        for inp in d.get("inputs", []):
            # Pre-populate a field from the environment, e.g. default: "${QUREDDY_BIN}", so a host
            # can show a resolved path the user then edits. Expands the DEFAULT value only, before
            # the widget renders; the value a user submits is passed as a single argv element.
            if isinstance(inp.get("default"), str):
                inp["default"] = os.path.expandvars(inp["default"])
        d["_dir"] = str(y.parent)
        ds.append(d)
    ds.sort(key=lambda d: (d.get("order", 99), d["id"]))
    return {d["id"]: d for d in ds}


def feature_enabled(flag: str) -> bool:
    """A descriptor or chain marked `feature_flag: X` renders only when this returns True (#67).

    Gated by env `BREACHSAFE_UX_<X>` (default ON). Lets a deployment hide Pro features — e.g.
    `mint_oscal` / OSCAL — so the OSS base experience can be previewed (BREACHSAFE_UX_MINT_OSCAL=
    false) before the code is physically decoupled to the Pro consumer (#25).
    """
    val = os.environ.get(f"BREACHSAFE_UX_{flag.upper()}", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def _bin_path() -> str:
    return os.pathsep.join(str(p) for p in _tools_dir().glob("*/bin"))


def _tool_version(argv: list[str]) -> str | None:
    """Display-only (#51): run a tool's own version command and return the first version-looking
    token, so a descriptor's shown version can be single-sourced from the installed tool instead
    of a drifting literal. Resolves argv[0] against the tool bin shims. Never raises.
    """
    path = f"{_bin_path()}{os.pathsep}{os.environ.get('PATH', '')}"
    exe = shutil.which(argv[0], path=path) or argv[0]
    try:
        p = subprocess.run([exe, *argv[1:]], input="", capture_output=True, text=True, timeout=5)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    m = _VER_RE.search((p.stdout or "") + (p.stderr or ""))
    return m.group(0) if m else None


def tool_available(desc: dict) -> bool:
    """Best-effort: can this descriptor's tool actually run here? Used to render an accurate
    chain-button state (W-5) rather than a dead button that always reports UNAVAILABLE.
    """
    run = desc.get("run", {})
    if run.get("image"):
        return shutil.which("docker") is not None
    base = run.get("base") or run.get("argv") or []
    cmd = base[0] if base else None
    if not cmd:
        return True
    path = f"{_bin_path()}{os.pathsep}{os.environ.get('PATH', '')}"
    return shutil.which(cmd, path=path) is not None


def verify_path(value: str, argv_template: list[str]) -> tuple[bool, str]:
    """Run a tool's own version/verify command for a user-supplied path (the 'Verify' button).

    argv_template uses {value} for the path, e.g. ["{value}", "--version"]. Returns
    (ok, one-line summary). Never raises; a bad path reports (False, reason).
    """
    argv = [(value if a == "{value}" else a) for a in argv_template]
    if not argv or not argv[0].strip():
        return (False, "no path set")
    resolved = shutil.which(argv[0]) or argv[0]
    try:
        p = subprocess.run([resolved, *argv[1:]], capture_output=True, text=True, timeout=10)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return (False, f"cannot run: {type(e).__name__}")
    line = ((p.stdout or p.stderr).strip().splitlines() or [""])[0][:140]
    return (p.returncode == 0, line or f"exit {p.returncode}")


def run_action(action: dict, params: dict) -> tuple[bool, str]:
    """Run a descriptor-declared action button (#5): render its argv from the current input
    values, run it (no shell, stdin closed so a tool that reads stdin can't hang, timeout), and
    report (ok, one-line summary) per the action's `ok_if` condition (default: exit 0).

    This is the generic replacement for what used to be the hardcoded openssl `test_connection`
    preflight: a 'Test connection' button is now just an action whose argv is `openssl s_client`
    declared in the descriptor (ADR-0002 §2a / #21). Never raises.
    """
    try:
        argv = _render(action["argv"], dict(params))
    except _DescriptorError as e:
        return (False, str(e))
    if not argv or not argv[0].strip():
        return (False, "no command")
    try:
        p = subprocess.run(
            argv, input="", capture_output=True, text=True, timeout=action.get("timeout_s", 10)
        )
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        return (False, f"could not run: {type(e).__name__}")
    ok = _match(action.get("ok_if") or {"exit": 0}, p.stdout + p.stderr, p.returncode)
    line = ((p.stdout or p.stderr).strip().splitlines() or [""])[0][:140]
    return (ok, line or f"exit {p.returncode}")


def _render(argv: list[str], mapping: dict) -> list[str]:
    """Substitute `{name}` tokens into each argv element (never a shell). `{{` and `}}` are
    literal braces. An unresolved `{name}` is a descriptor bug and fails CLOSED with
    _DescriptorError (wizard #8), so a mistyped token never ships as literal text and scans
    garbage.

    Token namespace (#50): engine-provided are `{share}` `{workdir}` `{artifact}`
    `{artifact_name}` `{python}` and, in validate.argv only, `{stdout_file}`; every other
    `{name}` is an input's value.
    """
    unresolved: set[str] = set()

    def repl(m: re.Match) -> str:
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


def _match(cond: dict, text: str, returncode: int) -> bool:
    """Evaluate a badge/action condition. Fail CLOSED (#182): an empty or all-unrecognized
    condition never passes — a descriptor typo (e.g. stdout_has for stdout_contains) is a bug,
    not a green. All present sub-conditions must hold (AND). Shared by _validate and run_action.
    """
    if not cond or (set(cond) - _COND_KEYS):
        return False
    ok = True
    if "stdout_contains" in cond:
        ok = ok and cond["stdout_contains"] in text
    if "stdout_contains_any" in cond:
        ok = ok and any(s in text for s in cond["stdout_contains_any"])
    if "stdout_not_contains" in cond:
        ok = ok and cond["stdout_not_contains"] not in text
    if "exit" in cond:
        ok = ok and returncode == cond["exit"]
    return ok


def _build_argv(desc: dict, params: dict, mapping: dict) -> list[str]:
    """Static `run.argv`, or build from `run.base` + each input's argv mapping.

    An input maps to argv by at most one of: positional (value), flag (token if truthy),
    arg (['--x', value] when set). Values are single argv elements — never a shell string.
    """
    run = desc["run"]
    if "argv" in run:
        return _render(run["argv"], mapping)
    base = list(run.get("base", []))
    options: list[str] = []
    positionals: list[str] = []
    if run.get("positional_from"):  # compose one positional, e.g. "{host}:{port}"
        positionals.append(run["positional_from"])  # template; resolved by _render below
    for spec in desc.get("inputs", []):
        v = params.get(spec["name"])
        if spec.get("positional"):
            if v not in (None, ""):
                positionals.append(str(v))
        elif "flag" in spec:
            if v:
                options.append(spec["flag"])
        elif "arg" in spec:
            if v not in (None, "", False):
                options += [spec["arg"], str(v)]
    argv = base + options
    # wizard #9 (argument injection): emit all options first, then a literal "--", then the
    # positionals, so everything after "--" is data. A leading-dash field value (e.g.
    # host="--openssl=/tmp/x") can no longer be parsed as a flag by the target tool. A tool whose
    # parser does not support "--" opts out with run.no_end_of_options (documented weaker posture).
    if positionals and not run.get("no_end_of_options"):
        argv.append("--")
    argv += positionals
    return _render(argv, mapping)


def run_descriptor(desc: dict, params: dict) -> dict:
    """Run one descriptor end to end and return the UI-facing result dict (wizard #12).

    Builds a no-shell argv from the descriptor + params, runs the tool, then its external
    validator, and derives the badge. Returns a dict whose `badge` is a (state, detail)
    tuple with state in valid / invalid / unavailable / none; a successful run also carries
    `artifact` (parsed JSON or None), `artifact_path`, and `highlights`. A launch, timeout,
    nonzero-exit, or descriptor error returns `error` + an `unavailable` badge and never raises
    to the UI.
    """
    key = uuid.uuid5(
        uuid.NAMESPACE_URL, desc["id"] + json.dumps(params, sort_keys=True, default=str)
    ).hex[:12]
    workdir = RUN_ROOT / f"{desc['id']}-{key}"
    workdir.mkdir(parents=True, exist_ok=True)
    artifact = workdir / desc["run"].get("artifact_name", "artifact.json")

    env = dict(os.environ)
    env["PATH"] = f"{_bin_path()}{os.pathsep}{env.get('PATH', '')}"
    mapping = dict(params) | {
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
    if desc["run"].get("image"):
        # Docker backend (W-3/W-4): the tool binary is the image ENTRYPOINT, so drop argv[0]
        # (the tool name in run.base) and hand the rest to `docker run`. Pin images by @sha256;
        # a stdout-artifact tool needs no mount (docker captures stdout). Missing docker ->
        # FileNotFoundError below -> unavailable, never a false verdict.
        argv = ["docker", "run", "--rm", desc["run"]["image"], *argv[1:]]

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=desc["run"].get("timeout_s", 120),
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
    except (OSError, ValueError) as e:
        # NUL byte in a param, E2BIG, bad fd, permission — the launch itself failed.
        # A badge, never a traceback to the UI (#183). FileNotFoundError is caught above.
        return {
            "error": f"could not launch tool: {e}",
            "badge": ("unavailable", "tool could not be launched"),
        }

    # First-class {stdout_file} (#50): always capture stdout to the workdir, regardless of exit
    # code, so a validator can inspect it (needed by artifact:optional, #44).
    (workdir / "stdout.txt").write_text(proc.stdout or "")
    if desc["run"].get("artifact_from") == "stdout":
        artifact.write_text(proc.stdout)
    # wizard #10 (false-green): a nonzero exit must never badge VALID, even when the tool still
    # wrote a schema-shaped artifact. The validator checks artifact SHAPE (e.g. CycloneDX
    # conformance), not whether the scan actually succeeded, so a partial/failed run that emits a
    # well-formed CBOM would otherwise pass. Any nonzero exit is a non-valid state; a tool
    # whose contract legitimately exits nonzero with a trustworthy artifact opts in explicitly.
    if proc.returncode != 0 and not desc["run"].get("trust_artifact_on_nonzero"):
        _err = proc.stderr.strip()
        # Surface the tool's own last diagnostic line (e.g. "OpenSSL 3.5 LTS not found") so the
        # badge says what actually failed, not a generic "tool run failed".
        _reason = _err.splitlines()[-1][:160] if _err else f"scan failed (exit {proc.returncode})"
        return {
            "error": (_err[:2000] or f"exit {proc.returncode}"),
            "badge": ("unavailable", _reason),
        }

    # wizard #15 (false-green): exit 0 with an empty/missing artifact must not badge VALID.
    # The validator checks SHAPE; a zero-byte or absent artifact means the tool produced nothing.
    if not artifact.exists() or artifact.stat().st_size == 0:
        return {
            "error": "tool produced no output",
            "badge": ("unavailable", "scan produced no output"),
        }

    try:
        art_json = json.loads(artifact.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        # wizard #11: narrowed from bare Exception. A non-JSON or unreadable artifact is a
        # legitimate "no structured highlights" case; the badge still comes from the external
        # validator below, not this parse. A wider catch would mask real bugs.
        art_json = None
    return {
        "artifact": art_json,
        "artifact_path": str(artifact),
        "badge": _validate(desc, workdir, artifact, params),
        "highlights": _highlights(desc, art_json),
    }


def _select_validator(v: dict, params: dict) -> dict | None:
    """Resolve validate.by (#43): choose the case whose key matches the current input values
    (joined with '|' for multi-key). Fail CLOSED — an unmatched selector with no default, or an
    explicit null case, yields None ('no validator'), never a green. A singular validate (no
    'by') passes through unchanged (back-compat).
    """
    if "by" not in v:
        return v
    key = "|".join(str(params.get(k, "")) for k in v["by"])
    cases = v.get("cases", {})
    return cases[key] if key in cases else v.get("default")


def _validate(
    desc: dict, workdir: Path, artifact: Path, params: dict | None = None
) -> tuple[str, str]:
    v = desc.get("validate")
    if not v:
        return ("none", "no external validator declared")
    v = _select_validator(v, params or {})
    if not v:
        # #43 fail-closed: a variant with no validator (unmatched selector or explicit null) is
        # a "none" badge, never a green. e.g. qureddy format=json/rich has no schema validator.
        return ("none", "no validator for this output")
    mapping = {
        "share": str(workdir),
        "workdir": str(workdir),
        "artifact": str(artifact),
        "artifact_name": artifact.name,
        "stdout_file": str(workdir / "stdout.txt"),
        "python": sys.executable,
    }
    argv = _render(v["argv"], mapping)
    if not shutil.which(argv[0]):
        return ("unavailable", f"validator '{argv[0]}' not installed")
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=v.get("timeout_s", 180))
    except Exception as e:
        return ("unavailable", f"validator error: {type(e).__name__}")
    text = out.stdout + out.stderr
    rule = v["badge_rule"]
    rc = out.returncode

    # state machine: infra failure → unavailable; ran + blessed → valid; ran + not blessed → invalid
    if "unavailable_if" in rule and _match(rule["unavailable_if"], text, rc):
        return ("unavailable", "validator could not run (infrastructure)")
    if "pass_if" in rule and _match(rule["pass_if"], text, rc):
        return ("valid", "validator accepted the artifact")
    g = rule.get("fail_detail_grep")
    detail = "\n".join(ln.strip() for ln in text.splitlines() if g and g in ln)[:1500] if g else ""
    if "fail_if" in rule and _match(rule["fail_if"], text, rc):
        return ("invalid", detail or "validator rejected the artifact")
    return (rule.get("otherwise", "invalid"), detail or "validator ran; artifact not accepted")


# _find_prop / _highlights / _posture live in _render.py (kept the engine under the size ceiling).
# Re-exported here so `facade._highlights` / `facade._posture` remain importable (app + tests).
