# Recurring bug categories (Modes 2, 5)

A trap list of bug *shapes* that recur across languages and repos, each grounded in a
real, named precedent rather than presented as a generic warning. Generalized from
QuReddy's `python-oss-crypto-reviewer` skill, which built this list from its own issue
tracker (issue numbers cited below are QuReddy's; the category is the reusable part, not
the specific issue). Add a category here only once it's actually recurred — a single
occurrence is a bug, not yet a pattern worth a permanent entry.

When reviewing a diff, scan for these shapes. If one turns up and it isn't what the
change is fixing, flag it separately — it's an independent bug, not part of this review.

- **Stream/output contamination masked by test-runner behavior.** A log handler that
  binds to a language-level stdio object (`sys.stderr`, a captured writer) gets silently
  redirected by a test runner that mixes/captures streams — tests pass, real users piping
  output see contamination. Fix generally binds to the OS-level file descriptor at
  startup, not the language-level object. **Caveat, also learned the hard way (QuReddy
  #194):** an fd-level fix only covers *in-process* stream mixing (test runners,
  `redirect_stderr`) — it does not cover a genuine shell-level `2>&1`, because the shell
  already merges the underlying descriptors via `dup2()` before the process starts; by
  the time your code runs there is no separate "original stream" left to snapshot.
  Verify any such fix against a **real** shell redirect or `subprocess.run(...,
  stderr=subprocess.STDOUT)`, not only in-process test-runner capture — the two are
  structurally different bugs that look identical from inside the test suite.
- **A size/retention cap applied to the same buffer the parser reads from.** "I added a
  cap on stored payload size" silently becomes "the parser now sees truncated input" if
  the cap is applied before parsing rather than only at the storage boundary. Fix:
  separate the storage cap from the parser's input.
- **Concatenating two output streams without a separator.** `stdout + stderr` glued with
  no `\n` produces a synthetic seam line that can satisfy a `MULTILINE` regex by
  accident. Fix: join with an explicit separator.
- **Subprocess exit code ignored after capturing output.** `subprocess.run(...,
  check=False)` followed by returning captured output without checking `returncode`
  silently treats a failed command's output as if it succeeded.
- **An empty/ambiguous signal mapped to a specific category instead of "unknown."** A
  classifier that sees empty output on a nonzero exit and picks a specific failure
  category is usually wrong — empty means *unknown*, not "the specific thing I expected."
  Fix: a distinct unknown/unclassified category rather than a plausible-looking guess.
- **A top-level catch-all making two different failure classes indistinguishable.**
  `except Exception: sys.exit(SAME_CODE_AS_TARGET_FAILURE)` makes "our own code crashed"
  indistinguishable from "the thing we were checking is actually broken." Fix: a distinct
  internal-error exit code/status separate from the domain failure code.
- **Brittle parser regex tied to today's exact output shape.** Over-tight anchors
  (`\s*$`, narrow character classes) silently drop fields the moment an upstream tool
  adds trailing annotations or changes formatting slightly. Fix: anchor on word
  boundaries, accept broader character classes, and add a fixture for the new shape when
  found.
- **A retry/rerun mechanism configured to swallow deterministic failures, not just
  flakes.** `pytest-rerunfailures` (or any retry-on-fail harness) reporting "N passed"
  while several tests only passed on a later attempt masks hard failures as flakiness.
  Verify by running the suspect test 3x back-to-back with no rerun markers — three real
  passes, not "passed eventually."
- **A dependency's own vendored/forked exception class silently stops matching
  `isinstance`.** A dependency can start raising its own internal fork of another
  library's exception (same name, same shape, different class object) after a routine
  version bump under an open-ended version range. `isinstance(exc, OtherLib.SomeError)`
  stops matching silently; nothing crashes, execution just falls into the wrong
  `except`/`catch` arm. Fix: match by class name across the exception's MRO/hierarchy
  instead of `isinstance` against one specific package's class when a dependency has
  known vendoring risk, and pin version ranges accordingly.
- **Cross-repo coupling to another repo's private/internal API, undocumented as a
  contract.** A producer repo reverse-engineers a consumer repo's private,
  underscore-prefixed function to match its exact expected shape. Works today; nothing in
  either repo's CI catches drift if the consumer refactors that private function, because
  there's no shared schema or cross-repo integration test. When a fix depends on another
  BQP repo's internal behavior, flag the missing contract test as part of the review —
  don't just credit the fix for matching today's shape.
- **Mutable default arguments/fields shared across instances.** `default=[]` (or
  equivalent shared-mutable-default in any language with the same footgun) silently
  shares state across instances; the fix is a factory/lazy-default, not a literal.
- **A library API silently dropping or renaming an option across a version bump.** Code
  written against an older version's API surface (e.g. a keyword argument that existed,
  then didn't) fails with an empty/wrong result rather than an exception — the failure
  mode is silent, not loud, which is what makes it worth a named category rather than
  "read the changelog and move on."

Add new entries here only once a category has actually recurred at least once beyond its
original occurrence — that's what distinguishes a real pattern worth a permanent check
from a one-off bug that already got fixed.
