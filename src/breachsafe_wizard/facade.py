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
ROOT = PKG.parent.parent                    # repo root (…/breachsafe-wizard)
TOOLS = ROOT / "tools"
RUN_ROOT = Path(os.environ.get("WIZARD_RUN_ROOT", os.path.expanduser("~/mint-proof/wizard-runs")))
_TOK = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def load_descriptors() -> dict:
    """Discover every tools/<name>/<name>.yaml, ordered by `order` then id."""
    ds = []
    for y in sorted(TOOLS.glob("*/*.yaml")):
        d = yaml.safe_load(y.read_text())
        d["_dir"] = str(y.parent)
        ds.append(d)
    ds.sort(key=lambda d: (d.get("order", 99), d["id"]))
    return {d["id"]: d for d in ds}


def _bin_path() -> str:
    return os.pathsep.join(str(p) for p in TOOLS.glob("*/bin"))


def _subst(argv: list[str], mapping: dict) -> list[str]:
    return [_TOK.sub(lambda m: str(mapping.get(m.group(1), m.group(0))), a) for a in argv]


def _build_argv(desc: dict, params: dict, mapping: dict) -> list[str]:
    """Static `run.argv`, or build from `run.base` + each input's argv mapping.

    An input maps to argv by exactly one of: positional (value), flag (token if truthy),
    arg (['--x', value] when set). Values are single argv elements — never a shell string.
    """
    run = desc["run"]
    if "argv" in run:
        return _subst(run["argv"], mapping)
    argv = list(run.get("base", []))
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
    return _subst(argv, mapping)


def run_descriptor(desc: dict, params: dict) -> dict:
    key = uuid.uuid5(uuid.NAMESPACE_URL, desc["id"] + json.dumps(params, sort_keys=True, default=str)).hex[:12]
    workdir = RUN_ROOT / f"{desc['id']}-{key}"
    workdir.mkdir(parents=True, exist_ok=True)
    artifact = workdir / desc["run"].get("artifact_name", "artifact.json")

    env = dict(os.environ)
    env["PATH"] = f"{_bin_path()}{os.pathsep}{env.get('PATH','')}"
    mapping = dict(params) | {"share": str(workdir), "workdir": str(workdir),
                              "artifact": str(artifact), "python": sys.executable}
    argv = _build_argv(desc, params, mapping)

    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=desc["run"].get("timeout_s", 120), env=env, cwd=str(workdir))
    except FileNotFoundError:
        return {"error": f"tool not found: {argv[0]}", "badge": ("unavailable", "tool not installed")}
    except subprocess.TimeoutExpired:
        return {"error": "tool timed out", "badge": ("unavailable", "tool timed out")}

    if desc["run"].get("artifact_from") == "stdout":
        artifact.write_text(proc.stdout)
    if proc.returncode != 0 and (not artifact.exists() or artifact.stat().st_size == 0):
        return {"error": (proc.stderr.strip()[:2000] or f"exit {proc.returncode}"),
                "badge": ("unavailable", "tool run failed")}

    try:
        art_json = json.loads(artifact.read_text())
    except Exception:
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

    def match(cond: dict) -> bool:
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
