<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.ai> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# Descriptor substitution tokens (#50)

`run.argv`, `run.positional_from`, and `validate.argv` are argv templates. Before the tool or
validator runs, the engine substitutes `{name}` tokens into each argv element. Substitution is
never through a shell, so a value is always a single argv element.

## Namespace

| Token | Where | Meaning |
|---|---|---|
| `{<input name>}` | run, validate | the value the user entered for that input |
| `{share}` | run, validate | the per-run working directory |
| `{workdir}` | run, validate | alias of `{share}` |
| `{artifact}` | run, validate | full path to the run's artifact file |
| `{artifact_name}` | validate | the artifact's file name (no directory) |
| `{stdout_file}` | validate only | file holding the tool's captured stdout (always written) |
| `{python}` | run, validate | the interpreter running breachsafe-ux (`sys.executable`) |

`{stdout_file}` is validate-only: at run-build time the tool has not produced stdout yet.

## Literal braces

`{{` renders as a literal `{` and `}}` as a literal `}`. Use these to pass a real brace to a
tool, e.g. `--filter={{ .Name }}` becomes `--filter={ .Name }`.

## Fail-closed

An unresolved `{name}` (a token that is neither an input nor an engine token) is a descriptor
bug. The engine raises rather than shipping the literal text, so a typo like `{prt}` can never
silently scan garbage. Escaped braces (`{{`, `}}`) are never treated as unresolved tokens.
