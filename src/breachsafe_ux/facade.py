"""Engine: config-driven, honest single-tool runner.

A tool is a YAML descriptor under tools/<name>/<name>.yaml. The engine renders it, builds a
typed argv (no shell), runs the tool, runs its external validator, and derives an HONEST
3-state badge (valid / invalid / validator-unavailable). Zero tool-specific logic lives here.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, uuid
from pathlib import Path
import yaml

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent.parent                    # repo root (…/breachsafe-ux)
TOOLS = ROOT / "tools"
RUN_ROOT = Path(os.environ.get("BREACHSAFE_UX_RUN_ROOT", os.path.expanduser("~/mint-proof/wizard-runs")))
_TOK = re.compile(r"\{([a-zA-Z0-9_]+)\}")


class _DescriptorError(Exception):
    """A descriptor is malformed (e.g. an unresolved {token} in run argv). Surfaced as an honest
    'unavailable' badge rather than shipped as literal text to the tool (wizard #8)."""


def _reject_residual(out: list[str]) -> list[str]:
    """wizard #8 (fail-open): a mistyped {token} in run.base/positional_from/argv would otherwise
    ship as literal text (e.g. "example.com:{prt}") and silently scan garbage. A residual token in
    the RUN argv is a descriptor bug; raise instead of running."""
    residual = sorted({tok for a in out for tok in _TOK.findall(a)})
    if residual:
        raise _DescriptorError("unresolved token(s) in run argv: " + ", ".join(residual))
    return out


def _tools_dir() -> Path:
    """The descriptor root. A host package (e.g. qureddy) points here via BREACHSAFE_UX_TOOLS_DIR
    so the wizard renders that package's own tools instead of the bundled examples (W-1/W-2).
    Read at call time — never bound at import — so setting the env before launch is enough."""
    d = os.environ.get("BREACHSAFE_UX_TOOLS_DIR")
    return Path(d) if d else TOOLS


def load_descriptors() -> dict:
    """Discover every <tools_dir>/<name>/<name>.yaml, ordered by `order` then id."""
    ds = []
    for y in sorted(_tools_dir().glob("*/*.yaml")):
        d = yaml.safe_load(y.read_text())
        if isinstance(d.get("brand"), dict):
            # Display-only metadata may reference env vars, e.g. version: "${QUREDDY_VERSION}",
            # so a host can single-source the version instead of duplicating it here. Scoped to
            # brand only: run/validate argv never expand env, to avoid env injection into a command.
            d["brand"] = {k: (os.path.expandvars(v) if isinstance(v, str) else v)
                          for k, v in d["brand"].items()}
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


def _bin_path() -> str:
    return os.pathsep.join(str(p) for p in _tools_dir().glob("*/bin"))


def tool_available(desc: dict) -> bool:
    """Best-effort: can this descriptor's tool actually run here? Used to render an honest
    chain-button state (W-5) rather than a dead button that always reports UNAVAILABLE."""
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


def test_connection(host: str, port, openssl: str = "openssl", timeout: float = 8.0) -> tuple[bool, str]:
    """Preflight: does the endpoint complete a TLS handshake, using the same OpenSSL the scan
    uses? `openssl s_client` with EOF on stdin. Never raises."""
    # DEFERRED wizard #6: this hardcodes OpenSSL/TLS ("s_client -connect") inside the otherwise
    # tool-agnostic engine, contradicting the module contract at the top of this file. The fix
    # (drive preflight from a descriptor "preflight.argv" template through _subst, as run/validate
    # already are) is designed in ADR wizard #5 and gated on the SSH descriptor being the second
    # real consumer. Until then this stays TLS-specific by deliberate, tracked exception.
    if not str(host).strip():
        return (False, "no host")
    ossl = shutil.which(openssl.strip()) or openssl.strip() or "openssl"
    try:
        p = subprocess.run([ossl, "s_client", "-connect", f"{str(host).strip()}:{int(port)}"],
                           input="", capture_output=True, text=True, timeout=timeout)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return (False, f"could not run: {type(e).__name__}")
    ok = p.returncode == 0
    return (ok, f"{host}:{port} TLS {'ok' if ok else 'failed'}")


def _subst(argv: list[str], mapping: dict) -> list[str]:
    return [_TOK.sub(lambda m: str(mapping.get(m.group(1), m.group(0))), a) for a in argv]


def _build_argv(desc: dict, params: dict, mapping: dict) -> list[str]:
    """Static `run.argv`, or build from `run.base` + each input's argv mapping.

    An input maps to argv by exactly one of: positional (value), flag (token if truthy),
    arg (['--x', value] when set). Values are single argv elements — never a shell string.
    """
    run = desc["run"]
    if "argv" in run:
        return _reject_residual(_subst(run["argv"], mapping))
    argv = list(run.get("base", []))
    # DEFERRED wizard #9 (argument injection): shell=False stops SHELL injection but not ARGUMENT
    # injection -- a leading-dash field value (e.g. host="--openssl=/tmp/x") lands in option
    # position and the target tool may parse it as a flag. The fix (emit all options first, then a
    # literal "--", then positionals) needs an argv-order change across descriptors and is tracked
    # separately; qureddy is confirmed to honor "--". Not exploitable on the default loopback bind.
    if run.get("positional_from"):                      # compose one positional, e.g. "{host}:{port}"
        argv.append(_subst([run["positional_from"]], mapping)[0])
    for spec in desc.get("inputs", []):
        v = params.get(spec["name"])
        if spec.get("positional"):
            if v not in (None, ""):
                argv.append(str(v))
        elif "flag" in spec:
            if v:
                argv.append(spec["flag"])
        elif "arg" in spec:
            if v not in (None, "", False):
                argv += [spec["arg"], str(v)]
    return _reject_residual(_subst(argv, mapping))


def run_descriptor(desc: dict, params: dict) -> dict:
    """Run one descriptor end to end and return the UI-facing result dict (wizard #12).

    Builds a no-shell argv from the descriptor + params, runs the tool, then its external
    validator, and derives the honest badge. Returns a dict whose `badge` is a (state, detail)
    tuple with state in valid / invalid / unavailable / none; a successful run also carries
    `artifact` (parsed JSON or None), `artifact_path`, and `highlights`. A launch, timeout,
    nonzero-exit, or descriptor error returns `error` + an `unavailable` badge and never raises
    to the UI.
    """
    key = uuid.uuid5(uuid.NAMESPACE_URL, desc["id"] + json.dumps(params, sort_keys=True, default=str)).hex[:12]
    workdir = RUN_ROOT / f"{desc['id']}-{key}"
    workdir.mkdir(parents=True, exist_ok=True)
    artifact = workdir / desc["run"].get("artifact_name", "artifact.json")

    env = dict(os.environ)
    env["PATH"] = f"{_bin_path()}{os.pathsep}{env.get('PATH','')}"
    mapping = dict(params) | {"share": str(workdir), "workdir": str(workdir),
                              "artifact": str(artifact), "python": sys.executable}
    try:
        argv = _build_argv(desc, params, mapping)
    except _DescriptorError as e:
        # wizard #8: a malformed descriptor is an honest 'unavailable', never a silent bad scan.
        return {"error": str(e), "badge": ("unavailable", f"descriptor error: {e}")}
    if desc["run"].get("image"):
        # Docker backend (W-3/W-4): the tool binary is the image ENTRYPOINT, so drop argv[0]
        # (the tool name in run.base) and hand the rest to `docker run`. Pin images by @sha256;
        # a stdout-artifact tool needs no mount (docker captures stdout). Missing docker ->
        # FileNotFoundError below -> honest unavailable, never a false verdict.
        argv = ["docker", "run", "--rm", desc["run"]["image"], *argv[1:]]

    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=desc["run"].get("timeout_s", 120), env=env, cwd=str(workdir))
    except FileNotFoundError:
        return {"error": f"tool not found: {argv[0]}",
                "badge": ("unavailable", f"'{argv[0]}' is not installed or not on PATH")}
    except subprocess.TimeoutExpired:
        return {"error": "tool timed out", "badge": ("unavailable", "tool timed out")}
    except (OSError, ValueError) as e:
        # NUL byte in a param, E2BIG, bad fd, permission — the launch itself failed.
        # Honest badge, never a traceback to the UI (#183). FileNotFoundError is caught above.
        return {"error": f"could not launch tool: {e}", "badge": ("unavailable", "tool could not be launched")}

    if desc["run"].get("artifact_from") == "stdout":
        artifact.write_text(proc.stdout)
    # wizard #10 (false-green): a nonzero exit must never badge VALID, even when the tool still
    # wrote a schema-shaped artifact. The validator checks artifact SHAPE (e.g. CycloneDX
    # conformance), not whether the scan actually succeeded, so a partial/failed run that emits a
    # well-formed CBOM would otherwise pass. Any nonzero exit is an honest non-valid state; a tool
    # whose contract legitimately exits nonzero with a trustworthy artifact opts in explicitly.
    if proc.returncode != 0 and not desc["run"].get("trust_artifact_on_nonzero"):
        _err = proc.stderr.strip()
        # Surface the tool's own last diagnostic line (e.g. "OpenSSL 3.5 LTS not found") so the
        # badge says what actually failed, not a generic "tool run failed".
        _reason = _err.splitlines()[-1][:160] if _err else f"scan failed (exit {proc.returncode})"
        return {"error": (_err[:2000] or f"exit {proc.returncode}"),
                "badge": ("unavailable", _reason)}

    try:
        art_json = json.loads(artifact.read_text())
    except (json.JSONDecodeError, OSError, ValueError):
        # wizard #11: narrowed from bare Exception. A non-JSON or unreadable artifact is a
        # legitimate "no structured highlights" case; the badge still comes from the external
        # validator below, not this parse. A wider catch would mask real bugs.
        art_json = None
    return {"artifact": art_json, "artifact_path": str(artifact),
            "badge": _validate(desc, workdir, artifact),
            "highlights": _highlights(desc, art_json)}


def _validate(desc: dict, workdir: Path, artifact: Path) -> tuple[str, str]:
    v = desc.get("validate")
    if not v:
        return ("none", "no external validator declared")
    mapping = {"share": str(workdir), "workdir": str(workdir),
               "artifact": str(artifact), "artifact_name": artifact.name, "python": sys.executable}
    argv = _subst(v["argv"], mapping)
    if not shutil.which(argv[0]):
        return ("unavailable", f"validator '{argv[0]}' not installed")
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=v.get("timeout_s", 180))
    except Exception as e:
        return ("unavailable", f"validator error: {type(e).__name__}")
    text = out.stdout + out.stderr
    rule = v["badge_rule"]

    _COND_KEYS = {"stdout_contains", "stdout_contains_any", "stdout_not_contains", "exit"}

    def match(cond: dict) -> bool:
        # Fail CLOSED (#182): an empty or all-unrecognized condition must never vacuously
        # pass. A descriptor typo (e.g. stdout_has for stdout_contains) is a bug, not a
        # green — a false 'valid' in the one honesty-critical path is the worst outcome.
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
            ok = ok and out.returncode == cond["exit"]
        return ok

    # honesty: infra failure → unavailable; ran + blessed → valid; ran + not blessed → invalid
    if "unavailable_if" in rule and match(rule["unavailable_if"]):
        return ("unavailable", "validator could not run (infrastructure)")
    if "pass_if" in rule and match(rule["pass_if"]):
        return ("valid", "validator accepted the artifact")
    g = rule.get("fail_detail_grep")
    detail = "\n".join(l.strip() for l in text.splitlines() if g and g in l)[:1500] if g else ""
    if "fail_if" in rule and match(rule["fail_if"]):
        return ("invalid", detail or "validator rejected the artifact")
    return (rule.get("otherwise", "invalid"), detail or "validator ran; artifact not accepted")


def _find_prop(obj, name):
    if isinstance(obj, dict):
        if obj.get("name") == name and "value" in obj:
            return obj["value"]
        for v in obj.values():
            r = _find_prop(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for it in obj:
            r = _find_prop(it, name)
            if r is not None:
                return r
    return None


def _highlights(desc: dict, art) -> list[dict]:
    out = []
    if art is None:
        return out
    for h in desc.get("render", {}).get("highlights", []):
        val = _find_prop(art, h["find_prop"]) if "find_prop" in h else None
        if val is not None:
            out.append({"label": h["label"], "value": val})
    return out
