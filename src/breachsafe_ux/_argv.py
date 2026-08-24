# SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io>
# SPDX-License-Identifier: Apache-2.0
"""Argv construction for the tool-facade engine (#186).

Turns a descriptor's `run` block plus the current input values into a no-shell argv:
`{name}` token substitution (`_render`), one input's contribution (`_input_argv`), and the
whole `run.base` + options + `--` + positionals assembly (`_build_argv`). Kept out of
facade.py so the engine module stays under the size ceiling; imports only the stdlib, so
facade can re-export these with no import cycle.
"""

from __future__ import annotations

import re
from typing import Any

_SUBST = re.compile(r"\{\{|\}\}|\{([a-zA-Z0-9_]+)\}")


class _DescriptorError(Exception):
    """A descriptor is malformed (e.g. an unresolved {token} in run argv).

    Surfaced as an 'unavailable' badge rather than shipped as literal text to the tool (wizard #8).
    """


def _render(argv: list[str], mapping: dict[str, Any]) -> list[str]:
    """Substitute `{name}` tokens into each argv element (never a shell); unresolved fails CLOSED."""
    unresolved: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        whole = m.group(0)
        if whole == "{{":
            return "{"
        if whole == "}}":
            return "}"
        name = m.group(1)
        if name in mapping:
            return str(mapping[name])
        unresolved.add(name)
        return whole

    out = [_SUBST.sub(repl, a) for a in argv]
    if unresolved:
        raise _DescriptorError("unresolved token(s) in argv: " + ", ".join(sorted(unresolved)))
    return out


def _repeat_flag_argv(flag: str, level: Any) -> list[str]:
    """A verbosity-style count input's options (#3): `flag` emitted `level` times.

    A short flag ("-v") collapses to one getopt-style token ("-vvv"); a long flag ("--verbose")
    repeats as separate tokens. Level 0/None/"" emits nothing. int() guards a stray string level;
    a real 0 (quiet) is honored, not treated as absent.
    """
    try:
        n = int(level) if level not in (None, "", False) else 0
    except TypeError, ValueError:
        n = 0
    if n <= 0:
        return []
    if flag.startswith("-") and not flag.startswith("--"):
        return ["-" + flag[1:] * n]  # -v -> -vvv
    return [flag] * n


def _arg_argv(arg: str, v: Any) -> list[str]:
    """A `--x value` option's tokens, or [] when the value is an empty sentinel.

    Drop only the empty sentinels by identity, not `v not in (None, "", False)`: that membership
    test treats a numeric 0 as absent (0 == False in Python), so `--maxfail 0` or `--retries 0`
    were silently omitted (#171). A real 0/0.0 must reach the argv.
    """
    if v is None or v == "" or v is False:
        return []
    return [arg, str(v)]


def _input_argv(spec: dict[str, Any], params: dict[str, Any]) -> tuple[list[str], list[str]]:
    """One input's (options, positionals) contribution to the argv.

    At most one of positional (value), flag (token if truthy), arg (['--x', value] when set),
    or repeat_flag (a count -> the short flag repeated N times). Values are single argv elements.
    """
    v = params.get(spec["name"])
    if spec.get("positional"):
        return ([], [str(v)] if v not in (None, "") else [])
    if "repeat_flag" in spec:
        return (_repeat_flag_argv(spec["repeat_flag"], v), [])
    if "flag" in spec:
        return ([spec["flag"]] if v else [], [])
    if "arg" in spec:
        return (_arg_argv(spec["arg"], v), [])
    return ([], [])


def _build_argv(desc: dict[str, Any], params: dict[str, Any], mapping: dict[str, Any]) -> list[str]:
    """Static `run.argv`, or build from `run.base` + each input's argv mapping.

    Only descriptor-authored templates (`run.argv`, `run.base`, `positional_from`) carry
    `{tokens}` and are rendered against the mapping. User input VALUES are inserted literally and
    are NEVER passed back through `_render`: a value that happens to contain a `{word}` (a regex
    like `{2,3}`, a JSON snippet, a Jinja fragment) must reach the tool as typed, not be
    substituted from — or fail the whole run closed against — the engine's token namespace
    (workdir/artifact/python/input names).
    """
    run = desc["run"]
    if "argv" in run:
        return _render(run["argv"], mapping)
    base = _render(list(run.get("base", [])), mapping)  # descriptor template
    options: list[str] = []
    positionals: list[str] = []
    if run.get("positional_from"):  # a template composed from inputs, e.g. "{host}:{port}"
        positionals.append(_render([run["positional_from"]], mapping)[0])  # rendered once, here
    for spec in desc.get("inputs", []):
        opts, poss = _input_argv(spec, params)  # literal user values; not re-rendered
        options += opts
        positionals += poss
    argv = base + options
    # #199: an output-dir tool writes correlated artifacts (e.g. qureddy's scan.cdx.json +
    # scan.json) into one run directory. The flag is an OPTION, so it goes before the "--".
    if run.get("output_dir_flag"):
        argv += [run["output_dir_flag"], mapping["workdir"]]
    # wizard #9 (argument injection): options, then a literal "--", then positionals, so a
    # leading-dash value can't be parsed as a flag. A tool lacking "--" opts out via
    # run.no_end_of_options (documented weaker posture).
    if positionals and not run.get("no_end_of_options"):
        argv.append("--")
    return argv + positionals
