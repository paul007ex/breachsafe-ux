"""Artifact-derived strings are HTML-escaped before they reach the rendered markup (#121).

A CBOM/scan artifact is untrusted input; a highlight value, badge detail, or posture text taken
from it must not be able to inject markup (e.g. a ``<script>``) into the badge/banner the UI
renders. render.py escapes those values with html.escape; the static markup it builds is left as-is.
"""

from __future__ import annotations

from breachsafe_ux.render import _badge, _posture_md

_XSS = "<script>alert(1)</script>"


def test_badge_escapes_highlight_value():
    out = _badge("valid", "ok", hi=[{"label": "algorithm", "value": _XSS}])
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_badge_escapes_highlight_label():
    out = _badge("valid", "ok", hi=[{"label": _XSS, "value": "x"}])
    assert "<script>" not in out


def test_badge_escapes_detail():
    out = _badge("invalid", _XSS)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_posture_md_escapes_text():
    out = _posture_md({"text": _XSS, "level": "high"})
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_badge_preserves_static_markup():
    """Guard the guard: escaping the untrusted values must not mangle the static badge markup."""
    out = _badge("valid", "all good", hi=[{"label": "cipher", "value": "AES-256"}])
    assert "<span" in out  # the state header span we build is untouched
    assert "`AES-256`" in out  # a benign value renders normally inside its code span
