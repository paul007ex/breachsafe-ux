# What NOT to flag — the false-positive brake (Modes 2, 5)

Every other reference here lists things to *flag*. This one is the brake: without it a
review becomes noise, and noise gets the real findings ignored. Read this before writing up
any finding. Harvested from `python-oss-crypto-reviewer`'s false-positive guardrails.

## Contents
- The one decision heuristic
- Do NOT flag (these are usually correct)
- Verify before you assert (the anti-embarrassment rule)
- Separate "wrong" from "preference" in the writeup

## The one decision heuristic

> **"Would I write this differently, AND would the difference change observable behavior or
> catch a real failure? If there's no behavior/safety change, it's a style preference — drop
> it or mark it explicitly as `[style, your call]`, don't file it as a finding."**

A real finding names a concrete failure (input → wrong output/crash) or a violated,
*enforced* rule. "I'd have done it another way" is not a finding.

## Do NOT flag (these are usually correct)

- **`x == null` / `x is None`-style null-ish checks** that are intentional — verify the
  actual lint config before calling it a violation. (`== null` in JS matches null+undefined
  on purpose; many `eqeqeq` configs allow it via `"smart"`/`allowNull`.) **Run the linter;
  don't assume from the rule name.**
- **Tool errors that are invocation/environment artifacts, not code defects** — e.g. mypy
  `Source file found twice under different module names`, a tool "error" that's really a
  path/packaging/CI-invocation issue. Isolate (run the tool the canonical way) before
  reporting; a harness artifact is `NOT A CODE DEFECT`.
- **Missing docstrings on genuinely trivial private helpers** (`_run`, a one-line getter).
- **Comments deleted during a fix**, unless the comment encoded a non-obvious *why*.
- **Formatting / import-order nits** — those are a separate mechanical commit, not a review
  finding (note once, don't itemize).
- **`from __future__ import annotations` already present**; `assert isinstance(...)`
  type-narrowing that can't fail in prod; an imperfect-but-clear test name.
- **Failures-as-values `(state, note)`** for expected/recoverable outcomes — that's a
  deliberate honest-degrade pattern, not "missing exception handling."
- **Tuples used instead of lists** in non-frozen contexts; a 2-line clarifying refactor on
  the already-changed line.

## Verify before you assert (the anti-embarrassment rule)

Before filing ANY tool-based finding: run the tool the project's own way (its `lint`/gate
script, the documented invocation) and quote the real exit code + output. An agent (or you)
claiming "lint is red" / "mypy fails" without having run it the canonical way is how false
HIGHs get filed. If you can't run it, say `UNVERIFIED — needs a real run`, don't assert.

## Separate "wrong" from "preference" in the writeup

When you do flag something, label its class: **`[bug]`** (behavior/safety), **`[refactor]`**
(structure, non-blocking follow-up), **`[style, your call]`** (preference — reviewer may
decline). Quote the specific line, name the enforced rule/section it violates, and propose a
concrete fix. Don't bundle style preferences into a bug's severity.
