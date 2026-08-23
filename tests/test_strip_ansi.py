# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""ANSI escape stripping for display (#4).

A tool's captured stdout/stderr can carry ANSI escape sequences (e.g. `rich` colour); shown
verbatim in the web view they render as escape-code garbage. render._strip_ansi removes them
from the human-readable text before display, while leaving ordinary content untouched.
"""

from __future__ import annotations

from breachsafe_ux.render import _strip_ansi


def test_strip_ansi_removes_sgr_colour():
    assert _strip_ansi("\x1b[31mRED\x1b[0m") == "RED"


def test_strip_ansi_leaves_plain_string_unchanged():
    assert _strip_ansi("just plain text 123") == "just plain text 123"


def test_strip_ansi_preserves_embedded_newlines():
    assert _strip_ansi("\x1b[32mline one\x1b[0m\nline two\n") == "line one\nline two\n"
