# Generic anti-pattern self-check (Mode 5)

**This is the one mode in this skill that fixes instead of only reporting.** Every other
mode in this skill is audit-only by default. This one is different because the posture
is different: you're checking your **own in-progress, uncommitted** work before you
commit it, not auditing someone else's already-merged code. That's a meaningfully
different situation — there's no independent author to hand findings back to, and
catching your own mistake before it's committed is strictly better than filing it as a
finding against yourself. Fix what you find here, immediately, before committing.

This mode still never pushes, opens a PR, or takes any remote/shared-state action on its
own initiative — "fix your own working tree" stops at the boundary of your local
checkout. Publishing the result still needs the same authorization as anything else in
this skill.

This is the generic, cross-language, non-crypto-specific version of a pre-commit
self-check. Crypto-primitive-specific anti-patterns (unsafe FFI boundaries, nonce reuse,
KDF label correctness, hedged-signature assumptions, memory zeroization of secret
material, timing side channels) are `breachsafe-security-audit`'s checklist, not this
one — if your change touches cryptographic code, run that skill too before committing.

## Contents
- How to use this
- 1. Panics, subprocess discipline, logging discipline, dead code/TODOs
- 2. Orphan source files
- 3. Unchecked narrowing casts / truncation
- 4. Reimplementing something a dependency already provides
- 5. Test regression check
- 6. Test integrity — false greens
- Report format

## How to use this

Run every check below against your own diff (uncommitted or staged, not yet pushed). For
each hit, read the surrounding code and decide: real violation, or false positive? Fix
real violations before committing — don't rationalize past a finding just because it's
inconvenient right now. If you find a violation that's pre-existing (not introduced by
your change), it's fine to leave it and note it separately rather than silently fixing
unrelated code in the same commit — but say so.

## 1. Panics, subprocess discipline, logging discipline, dead code/TODOs

Shared with Mode 2 (PR audit) — see this skill's generic-code-hygiene checks and grep
commands, listed in SKILL.md's References section (four categories: panics/aborts,
subprocess-outside-shim, stray logging, dead code/floating TODOs). This mode's posture:
**fix what you find**,
immediately, before committing — the opposite of Mode 2's report-only posture, same
underlying checklist (see the authorization-gate section at the top of this file for why
the posture differs).

## 2. Orphan source files

```bash
# Rust: every .rs file under src/ should be reachable from a mod declaration
ls src/**/*.rs
grep -rn '^mod \|^pub mod ' src/lib.rs src/main.rs 2>/dev/null
```

A file that exists on disk but isn't wired into the module tree / package `__init__`
compiles or imports as if it doesn't exist — silently dead code that nobody notices is
dead.

## 3. Unchecked narrowing casts / truncation

```bash
grep -n ' as u8\b\| as u16\b\| as i32\b' src/**/*.rs
```

Every narrowing cast needs either a preceding bounds check or an explicit comment
explaining why truncation can't happen here. An unguarded cast is a silent-corruption
bug waiting for an input that's larger than whoever wrote it assumed.

## 4. Reimplementing something a dependency already provides

Read every function you added or modified. For each one, ask: is this logic that the
crate/library you're already depending on (OpenSSL, the standard library, a vetted
third-party package) already implements safely? Reimplementing algorithmic logic that a
trusted dependency already exposes is both wasted effort and a fresh surface for bugs the
dependency's maintainers already fixed once. This is a general "don't reinvent the wheel"
check — for anything cryptographic specifically, the bar is much stricter and belongs to
`breachsafe-security-audit`.

## 5. Test regression check

```bash
cargo test --lib --tests --quiet 2>&1 | tail -3
# or
pytest --collect-only -q | tail -3 && pytest -q
```

Pass count must be at or above the baseline you captured before starting your change. Any
drop is a regression your change introduced — resolve it before committing, don't commit
first and file a follow-up.

## 6. Test integrity — false greens

A rising pass count is necessary but **not sufficient**: green tests that don't exercise
the real path are worse than no tests, because they actively assert that a broken thing
works. Check every test you added or touched:

- **Fixture that fakes a production precondition.** If a fixture/monkeypatch sets up a
  state that production establishes for itself (a registration, an env var, a patched
  global, a stubbed client), there must be a **paired test that runs the real path without
  that fixture**. Otherwise the suite is green precisely because it skipped the step that
  fails in prod. This is the exact shape that shipped a P0: a fixture registered a
  tool-wrapper that production never registered, so every test passed and every live scan
  crashed. The fix is not "add more mocks" — it's one no-mock test of the real wiring
  (in-process or subprocess) plus deleting the masking fixture.
  ```bash
  grep -rn 'monkeypatch\|mock\|patch(' tests/ | grep -iE 'regist|env|global|wrapper|client'  # each: is there a no-fixture real-path counterpart?
  ```
- **Test weakened to pass.** Never loosen an assertion, add a `skip`/`xfail`, or widen an
  expected value to make a failing test go green — that deletes the signal. If the test's
  premise is genuinely wrong, fix the premise and say why; if the code is wrong, fix the
  code.
- **Definition of done = the live path runs clean, not "pytest is green."** For anything
  that shells out, wires into a framework, or touches a real service, the change isn't done
  until you've run the real thing once and seen it succeed. Green units are a gate, not the
  finish line.
- **Failure returning an empty-but-valid value.** A tool timeout/parse-error that returns
  `{}` / `[]` / `None` which downstream reads as "nothing wrong = safe" is a silent false
  negative. Failures must be a distinct state (a status field, a typed error), never
  collapsed into the same value as a clean result.

## Report format

```
ANTI-PATTERN SELF-CHECK RESULTS
================================
1. Panics/subprocess/logging/dead-code (generic-code-hygiene.md) : PASS / FAIL (fixed / list remaining)
2. Orphan source files                                            : PASS / FAIL
3. Unchecked narrowing casts                                       : PASS / FAIL
4. Reimplemented dependency logic                                  : PASS / FAIL
5. Test regression                                                  : N passed, M failed (baseline: X)
6. Test integrity (false greens)                                    : PASS / FAIL (masking fixture / weakened test / failure-as-empty)

VERDICT: CLEAN / N VIOLATIONS FIXED BEFORE COMMIT
```
