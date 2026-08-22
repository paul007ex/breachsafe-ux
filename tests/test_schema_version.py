"""schema_version handshake (#49).

A descriptor may declare `schema_version`. Absent means 1 (back-compat, warned). A version
newer than this build understands fails CLOSED, so an old engine refuses a new descriptor with
a clear message instead of a confusing structural error.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from breachsafe_ux.facade import (
    ROOT,
    SUPPORTED_SCHEMA_VERSION,
    _DescriptorError,
    _validate_descriptor,
)


def _ok() -> dict:
    return {"schema_version": SUPPORTED_SCHEMA_VERSION, "id": "t", "run": {"base": ["x"]}}


def test_current_version_loads():
    _validate_descriptor(_ok(), Path("t.yaml"))  # no raise, no warning


def test_absent_version_warns_but_loads():
    d = _ok()
    del d["schema_version"]
    with pytest.warns(UserWarning, match="no schema_version"):
        _validate_descriptor(d, Path("t.yaml"))


def test_too_new_fails_closed():
    d = _ok()
    d["schema_version"] = SUPPORTED_SCHEMA_VERSION + 1
    with pytest.raises(_DescriptorError, match="newer breachsafe-ux"):
        _validate_descriptor(d, Path("t.yaml"))


def test_shipped_descriptors_declare_version():
    for p in sorted((ROOT / "tools").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text())
        assert d.get("schema_version") == SUPPORTED_SCHEMA_VERSION, (
            f"{p.name} missing schema_version"
        )
