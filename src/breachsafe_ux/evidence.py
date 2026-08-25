"""Evidence export orchestration delegated to the Go evidence composer."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from breachsafe_ux.resolve import _resolve, _run_env


def _evidence_workspace(
    chain: dict[str, Any], artifact_path: str
) -> tuple[Path, dict[str, Path], Path, dict[str, Path]]:
    workdir = Path(artifact_path).resolve().parent
    root = workdir.resolve()

    def inside_workspace(name: str) -> Path:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"descriptor path escapes run directory: {name}")
        return path

    paths = {role: inside_workspace(name) for role, name in chain["artifact_files"].items()}
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing scan artifacts: {', '.join(missing)}")
    request_path = inside_workspace(chain.get("request_file", "request.json"))
    output_paths = {role: inside_workspace(name) for role, name in chain["output_files"].items()}
    return workdir, paths, request_path, output_paths


def _write_report_request(
    chain: dict[str, Any], workdir: Path, paths: dict[str, Path], request_path: Path
) -> datetime:
    request = json.loads(json.dumps(chain["request_template"]))
    request["identity"]["report_id"] = f"ux-{workdir.name}"
    generated_at = datetime.now(UTC)
    request["identity"]["generated_at"] = generated_at.isoformat().replace("+00:00", "Z")
    for role, spec in chain["request_artifacts"].items():
        request[spec["request_key"]]["expected_sha256"] = hashlib.sha256(
            paths[role].read_bytes()
        ).hexdigest()
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    return generated_at


def _name_report_outputs(
    paths: dict[str, Path], output_paths: dict[str, Path], generated_at: datetime
) -> dict[str, Path]:
    if "archive" not in output_paths:
        return output_paths
    scan_doc = json.loads(paths["scan"].read_text())
    host = str(scan_doc.get("target", {}).get("host", "scan"))
    safe_host = re.sub(r"[^A-Za-z0-9.-]+", "-", host).strip(".-") or "scan"
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    root = output_paths["archive"].resolve().parent
    scan_root = paths["scan"].resolve().parent
    if root != scan_root:
        raise ValueError("evidence outputs must remain inside the scan workspace")
    output_paths["archive"] = root / f"{safe_host}.breachsafe.{stamp}.zip"
    if "pdf" in output_paths:
        output_paths["pdf"] = root / f"{safe_host}.breachsafe.{stamp}.pdf"
    return output_paths


def _report_argv(
    chain: dict[str, Any],
    paths: dict[str, Path],
    request_path: Path,
    output_paths: dict[str, Path],
) -> list[str]:
    mapping = {
        "profile": chain["profile"],
        "stream": chain.get("stream", ""),
        "request": str(request_path),
    }
    mapping.update({role: str(path) for role, path in paths.items()})
    mapping.update({role: str(path) for role, path in output_paths.items()})
    argv = [token.format_map(mapping) for token in chain["argv"]]
    argv[0] = _resolve(argv[0]) or argv[0]
    return argv


def _execute_report_argv(argv: list[str], workdir: Path, timeout_s: int) -> tuple[list[str], str]:
    proc = subprocess.run(
        argv, cwd=str(workdir), capture_output=True, text=True, timeout=timeout_s, env=_run_env()
    )
    log = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        safe_log = log.replace(str(workdir), "<run>")
        raise subprocess.SubprocessError(safe_log.strip()[-2000:] or f"exit {proc.returncode}")
    return argv, log


def run_evidence_report(
    chain: dict[str, Any], artifact_path: str | None
) -> tuple[bool, dict[str, Any]]:
    """Invoke evidence-go; it owns PDF rendering, log creation, and ZIP packaging."""
    if not artifact_path:
        return False, {"error": "Run the scan first; no scan artifact is available."}
    try:
        workdir, paths, request_path, output_paths = _evidence_workspace(chain, artifact_path)
        generated_at = _write_report_request(chain, workdir, paths, request_path)
        output_paths = _name_report_outputs(paths, output_paths, generated_at)
        argv, log = _execute_report_argv(
            _report_argv(chain, paths, request_path, output_paths),
            workdir,
            chain.get("timeout_s", 300),
        )
        missing = [str(path) for path in output_paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Evidence CLI did not create: {', '.join(missing)}")
        return True, {
            "status": "exported",
            **{role: str(path) for role, path in output_paths.items()},
            "request": str(request_path),
            "command": " ".join(argv),
            "workdir": str(workdir),
            "log": log.strip()[-4000:],
        }
    except FileNotFoundError as exc:
        return False, {"error": str(exc)}
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        return False, {"error": f"report export failed: {exc}"}
