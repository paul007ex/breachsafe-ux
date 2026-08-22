"""Schema tests for the descriptor contract (#48).

These prove the JSON Schema (`descriptor.schema.json`) accepts every real descriptor and
rejects the corruption classes that used to fail deep in a run (or silently). They also prove
`load_descriptors()` fails CLOSED — a bad descriptor raises at load, it is never silently
dropped or rendered.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from breachsafe_ux.facade import (
    _DescriptorError,
    _validate_descriptor,
    _validator,
    load_descriptors,
)
from breachsafe_ux.resolve import ROOT

REPO_DESCRIPTORS = sorted((ROOT / "tools").glob("*/*.yaml"))


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def test_schema_itself_is_wellformed():
    from jsonschema import Draft202012Validator

    schema = json.loads((ROOT / "src" / "breachsafe_ux" / "descriptor.schema.json").read_text())
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("path", REPO_DESCRIPTORS, ids=lambda p: p.name)
def test_real_descriptors_are_valid(path):
    """Every shipped descriptor must validate clean (also the CI gate over tools/*/*.yaml)."""
    assert REPO_DESCRIPTORS, "no descriptors found under tools/"
    errs = list(_validator().iter_errors(_load(path)))
    assert not errs, f"{path.name}: " + "; ".join(
        f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs
    )


def _q() -> dict:
    return _load(ROOT / "tools" / "qureddy" / "qureddy.yaml")


@pytest.mark.parametrize(
    "mutate, where",
    [
        (lambda d: d["inputs"][2].__setitem__("postional", True), "inputs/2"),  # typo'd key
        (lambda d: d["inputs"][2].__setitem__("flag", "--x"), "inputs/2"),  # arg AND flag
        (lambda d: d.pop("id"), "<root>"),  # missing required
        (
            lambda d: d["validate"]["cases"]["cbom"]["badge_rule"].__setitem__("pass_if", {}),
            "validate/cases/cbom",
        ),  # oneOf collapses the deep path to the case
        (lambda d: d["run"].__setitem__("artifact_from", "stderr"), "run/artifact_from"),
        (lambda d: d["inputs"].append({"name": "z", "type": "enum"}), None),  # enum w/o choices
        (lambda d: d["run"].__setitem__("timeout_s", 0), "run/timeout_s"),  # timeout must be >=1
        (lambda d: d.__setitem__("id", "Bad Id"), "id"),  # id not a slug
    ],
)
def test_corruptions_are_rejected(mutate, where):
    d = _q()
    mutate(d)
    errs = list(_validator().iter_errors(d))
    assert errs, "expected the schema to reject this corruption"
    if where is not None:
        paths = {"/".join(map(str, e.path)) or "<root>" for e in errs}
        assert where in paths, f"expected an error at {where}, got {paths}"


def test_input_with_no_argv_mapping_is_allowed():
    """host/port are token-only inputs (none of arg/flag/positional) used via positional_from."""
    d = _q()
    host = next(i for i in d["inputs"] if i["name"] == "host")
    assert not ({"arg", "flag", "positional"} & set(host))  # really has none
    assert not list(_validator().iter_errors(d))


def test_load_descriptors_fails_closed_on_bad_descriptor(tmp_path, monkeypatch):
    tool = tmp_path / "broken"
    tool.mkdir()
    (tool / "broken.yaml").write_text(
        yaml.safe_dump(
            {"id": "broken", "run": {"base": ["x"]}, "inputs": [{"name": "a", "type": "nope"}]}
        )
    )
    monkeypatch.setenv("BREACHSAFE_UX_TOOLS_DIR", str(tmp_path))
    with pytest.raises(_DescriptorError) as ei:
        load_descriptors()
    assert "broken.yaml" in str(ei.value)


def test_validate_descriptor_names_file_and_path():
    with pytest.raises(_DescriptorError) as ei:
        _validate_descriptor({"run": {"base": ["x"]}}, Path("t/foo.yaml"))  # missing id
    msg = str(ei.value)
    assert "foo.yaml" in msg and "id" in msg
