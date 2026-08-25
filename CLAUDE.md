<!-- SPDX-FileCopyrightText: 2026 BreachSAFE <https://www.breachsafe.io> -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
# CLAUDE.md — BreachSAFE EnXemble

This file guides Claude Code (and any AI agent) working in this repository. It follows the
BreachSAFE repo standard defined in `breachsafe-common/docs/specs/2026-08-22-breachsafe-repo-design.md`
(the `breachsafe/breachsafe-repo` copier template, now consolidated into
`breachsafe-common/scaffold`). Retroactive `copier update` adoption is recorded in
`.copier-answers.yml`; skill drift is tracked in `skills.manifest.yaml`.

## What this repo is

The BreachSAFE EnXemble UX host — a Gradio-based web/tool facade that renders BreachSAFE
tools (e.g. QuReddy) behind a branded, config-driven surface.

- Archetype: `python-cli`
- Distribution / repo name: `breachsafe-ux`
- Python import name: `breachsafe_ux`
- Python baseline: `3.14`

## Standing invariants (inherited — do not relitigate)

- **License — Apache-2.0 (deliberate OSS exception).** Every first-party file carries an
  `SPDX-License-Identifier` header set to `Apache-2.0`. `breachsafe-ux` is a **deliberate, reviewed
  Apache-2.0 open-source exception** (#19) to the platform's PolyForm-Noncommercial default,
  so it can be the **public shared dependency of the OSS QuReddy [ux]**. Keep `LICENSE`,
  `NOTICE`, and the `REUSE.toml` annotation Apache-consistent. **Escalate before relicensing** —
  the Apache grant is a logged decision, never reverse it silently. Third-party/vendored
  material keeps its original license — never relabel it (e.g. the bundled Lucide icons stay
  ISC; the installed canonical skills stay PolyForm-Noncommercial-1.0.0).
- **Python 3.14.** Use the project venv for every
  command, hook, script, and test; do not fall back to system Python. `requires-python =
  ">=3.14"`. This is the platform standard and there is no 3.12 fallback. Migration #100 is done.
- **Issue-driven, branch + PR only.** Open an issue first for non-trivial work; branch from
  `main`; never commit directly to `main`. One thing per PR.
- **Quality gates are not theater.** Never lower the coverage floor, skip a test, add a blanket
  `noqa`, or weaken a gate to make it pass. A red gate is a bug to fix, not a baseline to accept.
  (Coverage floor is 70 today, ratcheting toward 90 — tracked in #89.)

## Standing process rules (spec §4.1 — enforced by the change-governance gate, not left to hope)

1. **Pressure-test in an isolated `/tmp` workstream**, never the shared checkout. HEAD-race with
   background agents corrupts the working tree; prove a change in `/tmp` (a throwaway clone or
   `git worktree`) before touching the real repo.
2. **Any non-surgical change requires a decision record before code.** "Non-surgical" = diff
   > ~150 LOC or > ~8 files, OR labelled `major`, OR touching a designated core path. The record
   holds a scored **A/B/C options comparison**, a **steelman** of the rejected options, and
   **pressure-test evidence** (log/link from the `/tmp` run) — written before code, not after.
3. **Major decisions get the A/B/C rating up front.** Before any large rewrite or new dependency,
   score the alternatives and record the winner — do not start typing the rewrite first.

## Repo map (MVC + engine + theme)

The UX host is a small MVC around a rendering engine and a theme layer:

| Module | Role | Notes |
|---|---|---|
| `src/breachsafe_ux/resolve.py` + `_render.py` | **Model** | resolve tool descriptors / build the render model; pure, no Gradio |
| `src/breachsafe_ux/render.py` | **View** | turns the model into view structures; pure, no Gradio |
| `src/breachsafe_ux/app.py` | **Controller** | wires model→view into the running app |
| `src/breachsafe_ux/facade.py` | **Engine** | the generic tool-facade engine |
| `src/breachsafe_ux/brand.py` | **Theme** | branding / white-label theming |

**Only `app.py` and `brand.py` import `gradio`.** Keep the framework dependency at the
controller + theme edge; model/view/engine stay Gradio-free so they are testable in isolation.

## Build / test / gate commands

Run against the locked environment (CI uses the locked path, so mirror it locally):

```
uv run --locked ruff check src tests          # lint
uv run --locked ruff format --check .          # format check
uv run --locked mypy src                        # type check
uv run --locked pytest tests/ -q                # tests (coverage floor enforced here)
uv run --locked python scripts/release_gate.py  # pre-release pre-flight gate
uvx --from 'reuse[charset-normalizer]' reuse lint   # SPDX / license-header compliance
python3 scripts/check_size_policy.py            # repo size-policy gate
```

There is **no `justfile`** yet — the gate set is being reworked in #127; use the commands above.

## Skills (smart-Claude-on-day-one)

Canonical skills come from `breachsafe/breachsafe-common/skills` — edit them there and re-sync,
never edit installed copies. The installed set is documented in `skills.manifest.yaml` (for
drift/sync); copies live in both `.claude/skills/` (Claude) and `.agents/skills/` (Codex).
