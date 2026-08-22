#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Run a pinned, checksum-verified full-history secret scan.

The Gitleaks binary is downloaded from its official GitHub release, its SHA-256
digest is verified against ``scripts/release-tools.json`` before it is ever
executed, and the archive is re-extracted on every run so a stale or tampered
extraction is never trusted. The scan covers the complete Git history (``HEAD``).
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
TOOLS_MANIFEST = ROOT / "scripts" / "release-tools.json"
DOWNLOAD_TIMEOUT = 120
SCAN_TIMEOUT = 300
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


def main() -> int:
    """Scan the complete current Git history with the pinned Gitleaks binary."""
    cache = ROOT / ".cache" / "release-tools"
    cache.mkdir(parents=True, exist_ok=True)
    gitleaks = download_tool("gitleaks", cache)
    completed = subprocess.run(
        [str(gitleaks), "git", "--no-banner", "--log-opts=HEAD", str(ROOT)],
        cwd=ROOT,
        check=False,
        timeout=SCAN_TIMEOUT,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
