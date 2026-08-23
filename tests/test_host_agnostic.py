# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""The generic host must not hardcode tool-specific identifiers (agnosticism gate).

EnXemble is a config-driven, tool-agnostic host: a tool is a YAML descriptor under tools/,
and the host renders whatever a descriptor declares. This gate fails if a host module
contains a tool identifier (a descriptor `id`, an artifact filename, or a known tool/format
token) as a STRING LITERAL in code. Comments and docstrings are ignored, so explanatory
"e.g. qureddy" comments are allowed; only tool-specific behavior in code is a regression.

Driven by the descriptors themselves, so it needs no manual list upkeep.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest
import yaml

from breachsafe_ux.resolve import ROOT

if TYPE_CHECKING:
    from pathlib import Path

# The generic host. Every module here must work for any tool descriptor, with no tool logic.
HOST_MODULES = ["facade", "resolve", "_render", "render", "_argv", "app", "brand"]

# Tool/format tokens that must never drive host code. Descriptor ids + artifact filenames are
# added dynamically below, so a new tool is covered automatically.
EXTRA_TOKENS = {"qureddy", "cyclonedx", "mint-oscal", "cbom"}


def _tool_tokens() -> set[str]:
    tokens = set(EXTRA_TOKENS)
    for descriptor in (ROOT / "tools").glob("*/*.yaml"):
        doc = yaml.safe_load(descriptor.read_text()) or {}
        if doc.get("id"):
            tokens.add(str(doc["id"]))
        for art in doc.get("run", {}).get("artifacts", []):
            if art.get("file"):
                tokens.add(str(art["file"]))
    return {t.lower() for t in tokens if t}


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    """id()s of the Constant nodes that are module/class/function docstrings (to exclude them)."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                ids.add(id(first.value))
    return ids


def _code_string_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    skip = _docstring_node_ids(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip
    ]


@pytest.mark.parametrize("module", HOST_MODULES)
def test_host_module_has_no_hardcoded_tool_identifiers(module: str):
    path = ROOT / "src" / "breachsafe_ux" / f"{module}.py"
    tokens = _tool_tokens()
    leaks = sorted(
        {
            f"{tok!r} in {lit!r}"
            for lit in _code_string_literals(path)
            for tok in tokens
            if tok in lit.lower()
        }
    )
    assert not leaks, (
        f"{module}.py hardcodes tool-specific string literal(s) in code: {leaks}. "
        "The host must stay tool-agnostic; move tool-specific values into the descriptor YAML."
    )


def test_agnostic_gate_actually_has_tokens_to_check():
    # Guard the guard: if descriptor discovery breaks, the parametrized test would pass vacuously.
    assert "qureddy" in _tool_tokens()
