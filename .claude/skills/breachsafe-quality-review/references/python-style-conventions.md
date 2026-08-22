# Python style & documentation conventions (Modes 1, 2, 5)

Our house Python convention = **PEP 8** (layout) + **PEP 257** (docstrings) + the
**Google Python Style Guide** (comments/typing/function length), with the BQP-specific
tightenings below. This exists because `generic-code-hygiene.md` deliberately punts on
docstrings ("check the repo convention") — *this file is that convention* for Python
(QuReddy, Qurum, the BreachSAFE-Enterprise collector, any future Python tooling).

Sources (verify against them, don't paraphrase from memory):
- Google Python Style Guide — https://google.github.io/styleguide/pyguide.html
- PEP 257 (docstrings) — https://peps.python.org/pep-0257/
- PEP 8 (style) — https://peps.python.org/pep-0008/

Real precedent: the BreachSAFE-Enterprise endpoint collector passed `ruff check` + tests
but failed this checklist — 11 nontrivial functions with no docstring, `#NN:` ticket refs
used as inline comments, bare `dict` (20 `mypy --strict` errors). Lint-clean ≠ this-clean.

## Contents
- 1. Docstrings — PEP 257 + Google
- 2. Comments explain WHY, never WHAT — Google
- 3. Type annotations — Google + `mypy --strict`
- 4. Function & module length — Google
- 5. Layout — PEP 8 / Google (mostly `ruff` catches these)
- 6. Observability & typed errors
- 7b. Boundary models & accessors (Prowler `finding.py` sets the bar)
- 8. Self-describing files & tracking (rich, structured — not scattered)
- Baseline — the 10/10 bar
- 7. Concrete Python traps (grep for these)
- Report shape

## 1. Docstrings — PEP 257 + Google

**Required on:** every module; every public function/class/method; every *nontrivial or
non-obvious* private function (Google: "mandatory when nontrivial or has non-obvious
logic"). Truly trivial one-line helpers (`_run`, a pure getter) are exempt — but a
function whose job you can't infer from its name/signature is **not** trivial.

The common failure is **inverted commenting**: trivial lines carry comments while the
detectors / parsers / `run()` contracts that actually need explaining have none. Flag
that inversion explicitly.

Machine-check missing docstrings (use this, don't eyeball):
```bash
python3 - <<'PY' path/to/module.py
import ast,sys
tree=ast.parse(open(sys.argv[1]).read())
TRIVIAL={"_run","_cfg"}  # adjust per module
for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and ast.get_docstring(n) is None and n.name not in TRIVIAL:
        print(f"  line {n.lineno:>3}  {n.name}()  -- NO docstring")
PY
```

**Format (PEP 257):** triple double quotes; one-line summary in the **imperative mood**
("Return the parsed result", *not* "Returns…" / "True only for…"); for multi-line, a
summary line, blank line, then detail. Don't restate the signature — document *effects,
return semantics, side effects, raised exceptions*. Google's Args/Returns/Raises sections
are the target shape for anything with non-obvious parameters (e.g. a tool adapter whose
contract is `-> (result, (state, note))` must say so).

## 2. Comments explain WHY, never WHAT — Google

- "Never describe the code itself; assume the reader knows Python." Delete comments that
  restate the line.
- **Ticket references are not comments.** `# #55: presence-check like nmap/testssl` is
  changelog — it belongs in the commit/`git blame`, not the source. Keep the *why*
  ("nmap is optional; absent ≠ failure"), drop the `#NN:`.
  ```bash
  grep -nE '#\s*#[0-9]+' path/**/*.py   # ticket-ref-as-comment smell
  ```
- Comment the *tricky* parts (a regex, a non-obvious ordering, a defensive fallback) with
  the reasoning. A broad `except Exception:` MUST carry a one-line reason for the broad
  catch (otherwise it reads as swallowing bugs):
  ```bash
  grep -nA1 'except Exception' path/**/*.py   # each hit needs a why-comment on the same/next line
  ```

## 3. Type annotations — Google + `mypy --strict`

- Annotate all public APIs; prefer **precise** types over bare containers. `dict` →
  `dict[str, X]`, `list` → `list[X]`, `subprocess.CompletedProcess` →
  `CompletedProcess[str]`. Structured tool output → a `TypedDict`, not `dict[str, Any]`.
- `X | None`, never implicit `= None` optionals. Don't annotate `self`/`cls` or
  `__init__`'s return.
- The gate is `mypy --strict` (see `python-quality-gates.md` step 3); a bare-container
  `[type-arg]` error is a real violation, not noise.

## 4. Function & module length — Google

- No hard per-function limit, but **> ~40 lines → consider splitting**.
- A module that does many jobs (parse + model + detect + adapt + orchestrate in one file)
  is the real "it's too long" smell even when each function is short — recommend a
  package split (`pkg/{parsing,detectors,adapters,pipeline}.py`) rather than trimming
  lines. Length-of-file and length-of-function are different findings; name which.

## 5. Layout — PEP 8 / Google (mostly `ruff` catches these)

`ruff check` + `ruff format --check` cover import ordering (`__future__`→stdlib→
third-party→local), 2-blank-lines between top-level defs, spacing. Run **`ruff format
--check`** in review (verify-only) — `ruff check` passing does **not** mean formatted.

## 6. Observability & typed errors

```bash
grep -rn 'logger\.\|getLogger\|logging\.' pkg/ | grep -v tests/   # expect > 0 in anything that shells out / can degrade
grep -rn 'raise RuntimeError\|raise ValueError\|raise Exception' pkg/ | grep -v tests/  # bare raises → should be a typed hierarchy
ls pkg/exceptions.py 2>/dev/null || echo "no exceptions module"
```
- **Logging**: code that shells out or degrades and logs **0×** is a finding (a scanner
  with no operator trace). Core = stdlib `logging.getLogger(__name__)`; the framework
  adapter uses the framework logger (e.g. `prowler.lib.logger`). Never `print` in library
  code.
- **Errors**: bare `RuntimeError`/`ValueError` at boundaries → recommend a typed hierarchy
  (`PkgError` base + specific subclasses, remediation in the message), so callers catch by
  type. But **don't** flag failures-as-values `(state, note)` for recoverable/expected tool
  outcomes — that's correct; only the hard-raise config/target paths need typed errors.
- **Observability tier (lean ≠ silent)**: logging is the floor, not the ceiling. Also expect
  **metrics** (per-unit state counts, duration, findings/degrade counts) and **error
  telemetry** (Sentry `capture_*` on failed states). Log events must use **stable k/v fields**
  (`event=…, tool=…, state=…, duration_ms=…`), not f-string prose — because those keys become
  metric labels and OTel attributes. **OTel itself is a forward path, not a day-1 requirement**
  — flag "no OTel" only as a `[refactor]` follow-up, but flag "no logging/metrics at all on a
  degrading scanner" as a real gap.

## 7b. Boundary models & accessors (Prowler `finding.py` sets the bar)
- A model that crosses a **validation/serialization/trust boundary** (output, finding, config
  from untrusted input) should be a **`pydantic.BaseModel` with validators**, not a bare
  `@dataclass` — so validation is paid at every construction site. Internal already-trusted
  value objects may stay `@dataclass`/`NamedTuple`; don't over-flag those.
- Prefer typed **`@property` accessors** for derived fields over repeated nested-dict access
  at call sites.

## 8. Self-describing files & tracking (rich, structured — not scattered)

For modules that carry invariants (core/adapters/security paths — calibrate; don't demand this
on trivial helpers):
```bash
grep -rn 'INVARIANTS\|ANTIPATTERN FLAGGED\|ANTIPATTERN APPROVED\|ASSUMPTION:' pkg/  # per-file contract present?
grep -rn '# #[0-9]' pkg/                                        # scattered ticket-refs → still a smell
ls CHANGELOG.md docs/adr/ 2>/dev/null                           # history + decisions have homes?
```
- **File header** states the module's single job + dependency direction; **per-file INVARIANTS
  + `ANTIPATTERN FLAGGED:`/`ANTIPATTERN APPROVED (see <link>):` block** so a diff can be
  audited against the file's own contract — and so a reviewer can tell at a glance whether a
  deviation was actually signed off (`APPROVED`, with a link) or just self-declared
  (`FLAGGED`, still open).
- **WHY-comments** encode the failure mode a fix prevents — not the ticket number.
- History → `CHANGELOG.md` (Keep-a-Changelog, entries backlink **issue + PR** + ADR); decisions →
  ADR ledger with a status legend, superseded kept-not-deleted. The "three places" rule: every
  invariant referenced in comment + issue + CHANGELOG.
- Architecture **Mermaid diagram** in `docs/explanation/`, each followed by a "reading the graph"
  prose block stating the invariant it encodes. `[refactor]`-severity if missing, not a blocker.

## Baseline — the 10/10 bar

The target is code that reads like the community's gold-standard fully-typed codebases
(**FastAPI, Pydantic v2, httpx, Starlette, Poetry**) and, for a fork, is "the upstream
taken over and made better" — at least as good on every axis. A module is 10/10 only when
it passes §1–6 **and** the `python-quality-gates.md` gate set (mypy --strict, bandit,
coverage floor, SPDX) — not merely `ruff check`. Precedent: the endpoint collector beat
Prowler's provider on mutable-defaults/implicit-Optional/legacy-typing/dead-code but lost
on structure + docstrings + logger/exceptions — 10/10 = win all of them at once.

## 7. Concrete Python traps (grep for these)

Real bugs that pass lint. Harvested from `python-oss-crypto-reviewer`.
- **Mutable default arg / `Field(default=[])`** — shares one object across instances → use
  `field(default_factory=list)` / `Field(default_factory=list)`. `grep -nE '=\s*(\[\]|\{\})' ` in signatures/Field.
- **Ignored subprocess returncode** — `subprocess.run(..., check=False)` then returning
  `stdout` without checking `.returncode`; a nonzero exit silently returns whatever emitted.
- **`sys.stdout`/`sys.stderr` bound at call/def time** — captured by in-process test runners;
  bind to the kernel fd (`os.dup(2)`) or resolve inside the function, not a default param.
- **`urlparse` silently drops `user:pass@` userinfo** — handle it explicitly.
- **Vendored-exception drift** — `isinstance(exc, click.UsageError)` stops matching when a dep
  vendors its own fork; match by class name across the MRO, and pin deps with vendoring risk
  (open-ended `>=` lets the fork in).
- **Validation in the caller, not the model** — a check added in a CLI handler/request wrapper
  that should be a Pydantic `field_validator` leaves every *other* construction site
  unguarded. Test: "if a different caller builds this model directly, do they pay the same
  validation?"
- **General-security greps** — `verify=False`, `ssl.CERT_NONE`, `random` for security (→
  `secrets`).

## Report shape

Group findings as: **docstrings missing** (list `file:line func()`), **comment smells**
(`#NN:` refs, restated-code, uncommented broad-except), **imprecise types** (mypy count),
**length/structure** (module doing N jobs → split). Cite the rule + source per group.
Every item here is mechanical / zero-logic-change — say so, so it can land as one
style commit separate from behavior.
