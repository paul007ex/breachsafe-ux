# Python conventions — locked-model, quality-gated CLI discipline

Grounded in `qureddy` (QuReddy) and the adjacent `quorum` (Qurum) tooling. Re-verify specifics
(exact section numbers, exact gate thresholds) against the target repo's own coding-standards
doc — treat what's below as the shape of the discipline, not a substitute for reading that doc.

## Contents
- The bar: 10/10, first time — write like the best modern Python
- No placeholder scaffolding
- Locked model discipline
- Subprocess-boundary discipline
- Structured logging and output-stream discipline
- Errors — a typed hierarchy, never bare raises
- Self-describing code — every file carries its own map, invariants & hard-won lessons
- Observability is REQUIRED — lean is good, silent is not (standard now, OTel-ready)
- Boundary models & derived accessors (learned from Prowler `finding.py`)
- Docstrings, comments & readability (PEP 257 + Google Python Style Guide)
- Quality gates (verify-only — this skill runs them locally, it doesn't own the sign-off)
- Escape hatches — use them explicitly, don't bury them
- Refuse security shortcuts

## The bar: 10/10, first time — write like the best modern Python

Every file you write should read like it belongs in the reference codebases the Python
community treats as gold standard for **fully-typed, clean-architecture** code:
**FastAPI**, **Pydantic (v2)**, **httpx**, **Starlette**, **Poetry**. Study their shape;
match it. When extending a fork (e.g. BreachSAFE-Enterprise over Prowler), the target is
**"someone took over the upstream and made it better"** — at least as good on every axis,
strictly better where you can be.

A file is 10/10 when *all* of these hold (not "ruff is green"):
- **Fully typed** — no bare `dict`/`list`, no implicit `Optional` (`x: str = None`), no
  legacy `typing.List`/`Dict`. Passes `mypy --strict`. Structured data is a `TypedDict`/
  Pydantic model / `@dataclass`, not `dict[str, Any]`.
- **Clean architecture** — one concern per module; a package (`pkg/{parsing,detectors,
  adapters,pipeline,exceptions}.py`), not a 400-line do-everything file. Depend on
  `Protocol`/ABC seams, not concrete singletons. (Clean-Architecture Python: type-driven,
  SOLID, protocols.)
- **Documented** — module + every public/nontrivial function has a PEP 257 docstring
  (imperative summary; Args/Returns/Raises where non-obvious). Comments say *why*, never
  `# #NN:` ticket refs (see the docstring section below).
- **Observable** — a real `logging` logger (never `print`), logging at boundaries. See
  "Structured logging" below.
- **Typed errors** — a small exception hierarchy, not bare `RuntimeError`/`ValueError`.
  See "Errors" below.
- **No footguns** — no mutable default args, no `sys.stdout` default params, no
  module-level mutable lookup tables (see the discipline sections below).
- **Verified** — tests + the full gate set (`mypy --strict`, `bandit`, coverage floor,
  SPDX) actually run, not assumed.

Concrete calibration from this repo family: the endpoint collector *beat* Prowler's own
provider on mutable-default args (0 vs 3), implicit-Optional (0 vs 15), legacy typing, and
dead-code/TODOs (0 vs 14) — but *lost* to it on package structure, docstrings, and having
a logger + exception hierarchy. 10/10 = win **all** of those at once.

## No placeholder scaffolding

Every file created must be exercised by the running command, by a test, or by tooling those
require. Do not create empty modules, unused abstractions, speculative plugin systems, fake
registries, TODO-only files, placeholder tests, or unused extension points. If a file you're
about to create can't participate in the working command path or the test suite, don't create
it — explain why in your response instead.

This is the single most common way agent-written Python in this codebase family goes wrong:
building the "obviously needed later" abstraction before there's a second real call site for
it. Add the second helper when you have the second use case, not the first.

## Locked model discipline

When a feature area has a locked Pydantic model spec (in a milestone-implement skill file, an
ADR, or a schema doc), treat it as locked:

- You may add fields only if the spec explicitly authorizes it for this task.
- Never remove a field or change its type without an explicit, discussed schema decision —
  frozen models with `extra="forbid"` mean consumers depending on the current shape will
  break silently otherwise.
- Fixed vocabularies are `Enum`, not raw strings — this catches typos at construction time
  instead of at "why isn't my rule firing" time.
- Immutable collections are `tuple[...]`, not `list[...]`.
- Datetimes are timezone-aware UTC.
- A model that's built once at the end of an operation (e.g. scan metadata capturing
  start/end time) should be constructed once, fully formed — don't build it early and mutate
  it, and don't mutate any nested model after the top-level result object is built.

If a locked spec deliberately includes fields not yet used by the current milestone (schema
stability ahead of a later milestone that will use them), that's a plausible, documented
exception — flag it as `ANTIPATTERN FLAGGED: speculative generality, because <reason tied to
the actual spec> — needs your sign-off` in your final response rather than silently complying,
silently refusing, or deciding for yourself that it's fine.

## Subprocess-boundary discipline

When the tool's real behavior comes from an external process (OpenSSL, or any other
subprocess-driven dependency), confine every call to that process to exactly one dedicated
module — not scattered across the codebase. Within that module:

- Arguments as a list, never a shell string; `shell=False` always.
- Explicit timeout on every call — no unbounded subprocess calls.
- `capture_output=True`, `check=False`, and explicit, manual return-code handling — don't let
  a non-zero exit raise an uncaught exception where the caller needs a structured failure
  category instead.
- Path/binary resolution follows an explicit, documented precedence (e.g. an explicit CLI
  flag, then an environment variable, then a bare name on `PATH`) — don't hardcode a path.

## Structured logging and output-stream discipline

- Logs are structured key/value calls (e.g. `structlog`-style), not f-string messages.
- Logs go to stderr. Program/scan output goes to stdout. If the tool emits machine-readable
  output (JSON), stdout must stay parseable — nothing else writes there.
- Serialize output via the model's own serialization (`model.model_dump(mode="json")` for
  Pydantic), never a hand-built dict that can drift from the model's actual shape.
- **Never write `def render(..., stream: IO[str] = sys.stdout) -> None:`.** A default parameter
  value is evaluated once, at function-definition time — it captures whatever `sys.stdout` is
  at import time, not whatever it is when the function is later called. Anything that later
  reassigns `sys.stdout` (`contextlib.redirect_stdout`, most test-capture fixtures, console
  wrappers) is silently ignored by a caller relying on the default. This exact shape shipped
  independently in three separate output adapters in the same codebase
  (`render_json`/`render_rich`/`render_cbom`) before being caught — it's the same root cause as
  the `stale-stream-capture` bug class (a module snapshotting `sys.stdout` at import time), just
  via a default argument instead of a module-level assignment. Use `stream: IO[str] | None = None`
  and resolve `sys.stdout` inside the function body instead.
- **A module-level `dict`/`list` literal used as a lookup table is a mutable, process-wide
  singleton.** Anything that mutates it (a test that patches one entry instead of using
  `unittest.mock.patch.dict`, a bug anywhere in the process) corrupts it for every other caller
  for the rest of the process's lifetime, silently. Wrap style/lookup tables in
  `types.MappingProxyType(...)` (or build them as a `tuple` of pairs) so mutation raises
  `TypeError` immediately at the mutation site instead of corrupting shared state invisibly.

## Errors — a typed hierarchy, never bare raises

Bare `raise RuntimeError(...)` / `raise ValueError(...)` at module boundaries is a smell:
callers can only catch it by string-matching. Define a small, typed hierarchy so callers
catch by type and each error carries remediation (Prowler does this per provider —
`GithubBaseException(ProwlerException)` with coded errors + `message`/`remediation`; match
that bar):

```python
# pkg/exceptions.py
class EndpointError(Exception):
    """Base for all collector errors."""

class CatalogError(EndpointError):        # replaces raw RuntimeError on catalog load
    """The check catalog is missing/unreadable/malformed."""

class InvalidScanTargetError(EndpointError, ValueError):  # replaces the host ValueError
    """The scan target isn't a plain hostname/IP (injection-shaped)."""
```

- Raise the typed error; include a one-line *remediation* in the message where the user
  can act on it. One base class per package so callers can `except EndpointError`.
- **Failures-as-values stays for expected/recoverable outcomes** — a tool that times out or
  is absent returns a `(state, note)` result (or a Result type), it does **not** raise.
  Reserve exceptions for programmer/config errors (bad catalog, invalid target). Don't
  raise across a fan-out boundary where one unit's failure must not sink the batch — return
  a status and let the orchestrator record it.

## Self-describing code — every file carries its own map, invariants & hard-won lessons

Rich comments are required, but **structured, not scattered** (do not reintroduce line-level
`# #NN:` ticket-refs — those are git-blame noise; strip them). Three granularities, three
homes; don't smear one across the others. Model repos: `qureddy`, `breachsafe-pki-rs`.

1. **File-header docstring = the file's architecture.** Every module opens with: its single
   job (the "this is the only place that does X" constraint it enforces — e.g.
   `qureddy/scanners/tls/openssl_probe.py`: "the only place that calls openssl via
   subprocess"), its place in the package (what it depends on / what depends on it — the
   dependency direction), and a one-line map of its sections. **Read and understand this
   before changing the file.**
2. **Per-file INVARIANTS + flagged-antipattern block (greppable, auditable).** Right after
   the docstring, list the invariants every change must be audited against, plus any
   deviation a human already signed off on (only after that sign-off — don't pre-write this
   block on spec, and don't let its presence become a template for granting yourself new ones):
   ```python
   # INVARIANTS (audit every change against these):
   #   - map_findings stays pure — no tool I/O in this module.
   #   - tool failures are (state, note) values, never raised across the fan-out.
   # ANTIPATTERN APPROVED (see #67): module-level CATALOG load at import, because <reason>.
   ```
   `ANTIPATTERN FLAGGED: <name>, because <reason>` (before human review) /
   `ANTIPATTERN APPROVED (see <link>): <name>, because <reason>` (after it) and
   `ASSUMPTION: <x> because <y>` are greppable markers — a reviewer can audit a diff against
   the file's own stated contract, and can tell at a glance whether a deviation was actually
   signed off or just self-declared.
3. **Hard-won-lessons / evolution comments where the bug lived — the WHY, not the ticket #.**
   ```python
   # WHY: a missing qureddy binary must degrade to not_installed, not failed — operators
   # triage a config gap differently from a crash. The first cut shipped the opposite and
   # masked real breakage. (history: CHANGELOG; tracking: the linked issue.)
   ```

**Chronological bug-fix history lives in `CHANGELOG.md`, not the source** — Keep-a-Changelog +
SemVer, every entry backlinking **both the issue and the PR** (`Closes #55 · PR #57`) and its
governing ADR, with a `### Security` section. This is where you *see the patterns* over time.
**Decisions live in an ADR ledger** (`docs/adr/` with a status legend — 🟢 built / 🔵 accepted /
🟡 proposed / ⚫ superseded; superseded ADRs are **kept and marked, never deleted**, and each
names the code symbol it governs). The discipline (the "three places" rule from pki-rs): every
enforced invariant is referenced in **comment (the why) + issue (tracking) + CHANGELOG (history)**
— land on any one, reach the others.

**Every function gets a docstring** (PEP 257) — no exceptions for nontrivial ones; file header
+ per-function docstrings together mean a reader never reverse-engineers intent.

**Calibrate (the brake):** rich headers + invariant blocks on modules that *carry* invariants
(core logic, adapters, subprocess/security paths). A one-line docstring is enough on a
genuinely trivial helper — don't cargo-cult a 30-line header onto a 10-line file, and the
auditor must not flag its absence there.

## Observability is REQUIRED — lean is good, silent is not (standard now, OTel-ready)

"Lean" never means "silent." Any module that shells out, degrades, or crosses a boundary
**must** be observable, in this tiered order:
1. **Structured logging (mandatory, now)** — a real logger (`logging.getLogger(__name__)`;
   the framework's logger in the adapter), never `print`. Log at boundaries with **stable
   key/value fields** — `event="scan.tool_finished", tool=…, state=…, host=…, duration_ms=…`
   (not f-string prose). Stable keys are the whole point: they map 1:1 to metric labels and
   OTel span attributes later, so you instrument once.
2. **Metrics (now, cheap)** — emit counts/durations for the things you'd page on: per-tool
   state counts, scan duration, findings count, degrade rate. Reuse the app's existing metric
   sink; a counter + a histogram is enough to start.
3. **Error telemetry (now)** — capture failures to the app's existing Sentry (`capture_message`/
   `capture_exception`) on `failed`/`not_installed` states + hard-raise paths, tagged with the
   same stable keys.
4. **OpenTelemetry (the forward path, NOT a prerequisite)** — do **not** pull OTel in on day
   one. Instead design steps 1–3 so OTel drops in without refactor: one logical operation =
   one span (a fan-out = one span per unit), log fields = span attributes, metrics =
   OTel instruments. When you adopt OTel, it wraps the existing seam; nothing rewrites.

The failure to avoid: shipping a "clean, lean" scanner that logs 0×, has no metrics, and
reports nothing to telemetry — a degraded scan then leaves no operator trace. Prowler logs
32× in one provider; match and exceed that, don't undercut it in the name of leanness.

## Boundary models & derived accessors (learned from Prowler `finding.py`)

- **A model at a validation boundary (an output/finding/config that crosses a trust or
  serialization edge) should be a `pydantic.BaseModel` with validators**, not a bare
  `@dataclass` — so every construction site pays validation and a bad field fails at
  construction, not three layers downstream. Plain `@dataclass`/`NamedTuple` is fine for
  internal, already-trusted value objects.
- **Expose derived/computed fields as typed `@property` accessors** (`def severity(self) ->
  str: ...`), not by re-reading a nested dict at every call site. One documented accessor >
  N scattered `obj["a"]["b"]` lookups.

## Docstrings, comments & readability (PEP 257 + Google Python Style Guide)

Write these *as you go*, not as a later cleanup. `ruff check` passing does **not** mean
this-clean — ruff catches none of the below. Sources:
https://peps.python.org/pep-0257/ and https://google.github.io/styleguide/pyguide.html.

- **Docstring every module, every public function/class/method, and every *nontrivial*
  private function** — a detector, a parser, a tool adapter, anything whose job you can't
  read off its name + signature. Truly trivial one-liners are exempt. PEP 257 shape:
  triple-quoted, one-line summary in the **imperative mood** ("Return the parsed X", not
  "Returns…" / "True only for…"); document effects, return semantics, and raised
  exceptions — don't restate the signature. If a function's contract is a shaped tuple
  (e.g. a tool adapter returning `(result, (state, note))`), the docstring must say so.
- **Don't invert the commenting.** The classic failure (found in the endpoint collector:
  11 nontrivial functions with no docstring while trivial lines carried comments) is
  commenting the obvious and staying silent on the subtle. Comment the *tricky* part — a
  regex, a non-obvious ordering, a defensive fallback — with the **why**; assume the
  reader knows Python (Google: "never describe the code itself").
- **A `# #123:` ticket reference is not a comment** — that's changelog, it belongs in the
  commit message / `git blame`, not the source. Write the *reason* ("nmap is optional;
  absent ≠ failure"), never the bare issue number.
- **Every broad `except Exception:` carries a one-line reason** for the broad catch, or it
  reads as silently swallowing bugs.
- **Precise types, not bare containers** — `dict[str, X]` not `dict`; a `TypedDict` for
  structured tool output, not `dict[str, Any]`. This is what `mypy --strict` (below)
  enforces; a bare-container `[type-arg]` error is a real violation, not noise.
- **Length**: split a function over ~40 lines; split a *module that does many jobs*
  (parse + model + detect + adapt + orchestrate in one file) into a package
  (`pkg/{parsing,detectors,adapters,pipeline}.py`) — short functions in a 400-line
  do-everything module is still "too long."

The auditor (`breachsafe-quality-review`) enforces exactly these via that skill's own
Python style-conventions reference — writing to them here means nothing to fix at
review.

## Quality gates (verify-only — this skill runs them locally, it doesn't own the sign-off)

The repo's coding-standards doc has an authoritative Tier-1 gate list and exact thresholds
(coverage percentage, severity thresholds for security scanners) — read it and use its exact
numbers, not the illustrative ones below. The typical shape of a Tier-1 gate set in this
codebase family:

```
ruff check .                          # lint
ruff format --check .                 # format, verify-only — never rewrite without being asked
mypy <package> --strict               # types
pytest --cov=<package> --cov-fail-under=<N>   # tests + coverage floor
bandit -r <package>                   # Python security footguns
pip-audit                             # known-vulnerable dependencies
deptry .                              # unused/undeclared dependencies
reuse lint                            # SPDX header compliance
gitleaks detect --no-git --source .   # secret scan (or trufflehog if unavailable)
```

Run these as part of the normal implementation loop — you should not hand back code you
haven't run these against locally. But note the distinction: running them here is part of
making the code correct before you say "done," not the same thing as a formal PR-readiness
audit. If the user is asking "is this ready to merge" as a distinct question, that's the
reviewing skill's job (`breachsafe-quality-review`), not this one's.

- Do not claim a gate passed without having run it. If a tool is unavailable, say so plainly
  (`NOT RUN: <reason>`) rather than skipping silently or asserting success.
- A coverage-threshold miss is a real signal — add tests, don't lower the threshold to make
  the number pass.
- `ruff format --check .` (not bare `ruff format .`) unless the task is explicitly a
  formatting-only change the user asked for — mechanical formatting and behavior changes stay
  in separate commits per most of these repos' own coding rules.

## Escape hatches — use them explicitly, don't bury them

- `ASSUMPTION: I am assuming X because the spec is silent on it. If wrong, change to Y.` —
  when a spec gap forces a judgment call. Don't invent file paths, function names, or library
  APIs to fill the gap silently — hallucinated imports/APIs are the single biggest source of
  bugs in agent-written code.
- `ANTIPATTERN FLAGGED: <name>, because <reason>` — for a plausible, documented deviation from
  the repo's own anti-pattern rules (e.g. the speculative-generality case above). This is a
  request, not a decision: state it prominently in the final response (not buried in a code
  comment) and treat the deviation as unresolved until a human confirms it. Keep these rare —
  reaching for this marker routinely instead of finding a compliant approach is itself the
  antipattern. Only write `ANTIPATTERN APPROVED` in code, and only after that sign-off actually
  happened (e.g. linking the issue/comment where a human said yes).

## Refuse security shortcuts

Refuse — and propose the secure alternative instead of silently complying — for any request
that requires: disabled TLS/certificate verification, `shell=True` with any
externally-influenced input, removed subprocess/network timeouts, logging of secrets,
`eval`/`exec`/`pickle.loads` on untrusted input, or swallowing a security-relevant error. This
applies even when the request is framed as temporary ("just for now," "to make CI green").
