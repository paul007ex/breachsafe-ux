# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Opt-in Docker end-to-end test for the scan -> PDF -> ZIP evidence workflow."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

DOCKER = shutil.which("docker")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("BREACHSAFE_E2E") != "1",
        reason="set BREACHSAFE_E2E=1 to run the real Docker evidence workflow",
    ),
    pytest.mark.skipif(
        DOCKER is None,
        reason="Docker is required for the evidence workflow",
    ),
]

CONTAINER = os.environ.get("BREACHSAFE_E2E_CONTAINER", "breachsafe-ux-pdf-only")


def _docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [DOCKER or "docker", "exec", CONTAINER, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=240,
    )


def test_real_scan_to_pdf_to_zip_workflow() -> None:
    """Run the actual container tools and assert every evidence artifact is packaged."""
    probe = subprocess.run(
        [DOCKER or "docker", "inspect", CONTAINER], capture_output=True, text=True, check=False
    )
    if probe.returncode != 0:
        pytest.skip(f"Docker container {CONTAINER!r} is not running")

    run_dir = "/tmp/breachsafe-e2e"
    setup = _docker("sh", "-c", f"rm -rf {run_dir} && mkdir -p {run_dir}")
    assert setup.returncode == 0, setup.stderr
    scan = _docker(
        "sh",
        "-c",
        f"qureddy scan tls example.com:443 --output-dir {run_dir} --quiet 2>{run_dir}/raw.log",
    )
    assert scan.returncode == 0, scan.stderr

    export = _docker(
        "python3",
        "-c",
        "from breachsafe_ux.facade import load_descriptors, run_evidence_report; "
        "d=load_descriptors()['qureddy']; "
        "c=next(x for x in d['chains'] if x.get('kind') == 'pdf_export'); "
        f"ok,out=run_evidence_report(c, '{run_dir}/scan.cdx.json'); "
        "print(out); raise SystemExit(0 if ok else 1)",
    )
    assert export.returncode == 0, export.stderr + export.stdout
    listing = _docker("sh", "-c", f"find {run_dir} -maxdepth 1 -type f -printf '%f\\n'")
    assert listing.returncode == 0, listing.stderr
    names = set(listing.stdout.splitlines())
    pdfs = sorted(name for name in names if name.endswith(".pdf"))
    archives = sorted(name for name in names if name.endswith(".zip"))
    assert len(pdfs) == 1 and ".breachsafe." in pdfs[0]
    assert len(archives) == 1 and ".breachsafe." in archives[0]
    assert "raw.log" in names
    assert "pdf-render.log" in names

    archive_path = f"{run_dir}/{archives[0]}"
    check = _docker(
        "python3",
        "-c",
        "import zipfile; "
        f"z=zipfile.ZipFile('{archive_path}'); "
        "n=set(z.namelist()); "
        "required={'request.json','scan.cdx.json','scan.json','raw.log'}; "
        "assert required <= n, sorted(n); "
        "assert 'report.pdf' in n; assert 'report.result.json' in n; "
        "assert 'raw.log' in n",
    )
    assert check.returncode == 0, check.stderr + check.stdout
