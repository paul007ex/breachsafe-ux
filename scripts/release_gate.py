#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Run the fail-closed, authoritative breachsafe-ux release gate.

This is the single local command that reproduces every blocking CI check for a
release candidate: lint, type-check, tests, the file-size policy, the
single-source version check, license (reuse) compliance, a build, and a
full-history secret scan. Every static tool runs under a checksum-pinned ``uv``
with ``uv run --locked`` so the versions match the committed lockfile exactly.

The gate is fail-closed: the first failing check stops the run with a nonzero
exit and a stable, greppable summary line.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOOLS_MANIFEST = ROOT / "scripts" / "release-tools.json"
DOWNLOAD_TIMEOUT = 120
COMMAND_TIMEOUT = 600
REPOSITORIES = {"uv": "astral-sh/uv", "gitleaks": "gitleaks/gitleaks"}


def sha256(path: Path) -> str:
    """Return a file's lowercase SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def platform_key() -> str:
    """Return the release-manifest key for this platform."""
    systems = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}
    machines = {"x86_64": "x64", "AMD64": "x64", "arm64": "arm64", "aarch64": "arm64"}
    try:
        return f"{systems[platform.system()]}-{machines[platform.machine()]}"
    except KeyError as exc:
        raise RuntimeError(f"unsupported platform: {platform.platform()}") from exc


def _download_https(url: str, destination: Path) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise RuntimeError(f"tool URL is not approved: {url}")
    with urllib.request.urlopen(  # noqa: S310  # nosec B310 - restricted HTTPS host.
        url, timeout=DOWNLOAD_TIMEOUT
    ) as response:
        destination.write_bytes(response.read())


def _extract_archive(name: str, archive: Path, destination: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            if any(
                Path(member).is_absolute() or ".." in Path(member).parts
                for member in bundle.namelist()
            ):
                raise RuntimeError(f"{name} archive contains an unsafe path")
            bundle.extractall(destination)
    else:
        with tarfile.open(archive) as bundle:
            bundle.extractall(destination, filter="data")


def download_tool(name: str, directory: Path) -> Path:
    """Download, checksum, freshly extract, and return a pinned tool."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(TOOLS_MANIFEST.read_text(encoding="utf-8"))[name]
    key = platform_key()
    asset = manifest["assets"].get(key)
    if asset is None:
        raise RuntimeError(f"{name} does not support platform {key}")
    filename, expected = asset
    tag = manifest["version"] if name == "uv" else f"v{manifest['version']}"
    archive = directory / filename
    if not archive.exists():
        url = f"https://github.com/{REPOSITORIES[name]}/releases/download/{tag}/{filename}"
        _download_https(url, archive)
    actual = sha256(archive)
    if actual != expected:
        raise RuntimeError(f"{name} checksum mismatch: expected {expected}, got {actual}")
    fresh = directory / f".{name}-fresh"
    if fresh.exists():
        shutil.rmtree(fresh)
    fresh.mkdir()
    _extract_archive(name, archive, fresh)
    executable = f"{name}.exe" if platform.system() == "Windows" else name
    matches = list(fresh.rglob(executable))
    if len(matches) != 1:
        shutil.rmtree(fresh)
        raise RuntimeError(f"{name} archive did not contain exactly one executable")
    matches[0].chmod(0o755)
    relative = matches[0].relative_to(fresh)
    unpacked = directory / name
    if unpacked.exists():
        shutil.rmtree(unpacked)
    fresh.replace(unpacked)
    return unpacked / relative


def _run(name: str, command: list[str]) -> None:
    print(f"::group::{name}", flush=True)
    completed = subprocess.run(  # noqa: S603 - fixed repository gate definitions.
        command, cwd=ROOT, check=False, timeout=COMMAND_TIMEOUT
    )
    print("::endgroup::", flush=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{name} failed (exit {completed.returncode})")


def _gates(uv: Path) -> None:
    run = [str(uv), "run", "--locked", "--python", "3.12"]
    _run("sync", [str(uv), "sync", "--locked", "--python", "3.12"])
    _run("ruff", [*run, "ruff", "check", "src", "tests"])
    _run("mypy", [*run, "mypy", "src"])
    _run("tests", [*run, "pytest", "tests/", "-q"])
    _run("file-size", [*run, "python", "scripts/check_size_policy.py"])
    _run("version", [*run, "python", "scripts/bump_version.py", "--check"])
    _run("reuse", [*run, "reuse", "lint"])
    _run("build", [*run, "python", "-m", "build"])
    _run("secrets", [sys.executable, "scripts/run_secret_scan.py"])


def main() -> int:
    """Run every blocking local release check, fail-closed on the first breach."""
    if sys.version_info[:2] != (3, 12):
        print("release gate requires Python 3.12", file=sys.stderr)
        return 2
    cache = ROOT / ".cache" / "release-tools"
    cache.mkdir(parents=True, exist_ok=True)
    try:
        uv = download_tool("uv", cache)
        _gates(uv)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"release gate FAIL: {exc}", file=sys.stderr)
        return 1
    print("release gate PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
