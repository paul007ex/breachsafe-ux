# Comprehensive anti-pattern catalog

Sourced from established software-engineering literature (Fowler's *Refactoring* code
smells, SOLID, OWASP Top 10 / CWE Top 25 security categories, well-known concurrency/
testing/API-design anti-patterns, and common per-language/platform idioms) — **not**
this codebase family's own incident history. That's a deliberately different source
than `recurring-bug-categories.md`, which only admits an entry once it's actually
recurred here; this file is breadth-first coverage of what's broadly known to be wrong,
so a reviewer has the full net even for a pattern nobody's hit yet in this family.
Don't merge the two files — one is "what's bitten us," the other is "what's known to
bite."

**How to use this file**: it's a checklist, not prose to read start to finish. Numbers
are global and sequential (item 1 through the total) so a finding can be cited by
number ("flags #34, #112") and the catalog's size stays honestly countable rather than
an open-ended vibe. The **Domain** column lets you skip whole categories fast — a
crypto/RFC-conformance change doesn't need the UX/TypeScript categories walked, and a
pure UX bug fix doesn't need the crypto-adjacent security items (#65, #66) or the Rust
section. Not every item applies to every language/repo — skip what doesn't apply
rather than forcing a finding. New items only get added here if they're a genuinely
established, named pattern from real literature (cite the source in the entry) — this
file grows by curation, not by padding.

## Contents (20 categories, 173 items)

| # | Category | Domain | Items |
|---|---|---|---|
| 1 | Classic code smells (Fowler) | general | #1–18 |
| 2 | SOLID violations | general | #19–23 |
| 3 | Error-handling anti-patterns | general | #24–29 |
| 4 | Concurrency anti-patterns | general, cloud | #30–35 |
| 5 | API/interface design anti-patterns | general, ux | #36–42 |
| 6 | Security bugs (OWASP Top 10 / CWE Top 25-informed) | security, crypto | #43–67 |
| 7 | Testing anti-patterns | general | #68–76 |
| 8 | Dependency/supply-chain anti-patterns | cicd, cloud | #77–82 |
| 9 | Observability/logging anti-patterns | general, cloud | #83–87 |
| 10 | Language-specific: Python | python | #88–95 |
| 11 | Language-specific: Rust | rust, crypto | #96–101 |
| 12 | Language-specific: TypeScript/JavaScript | ts/js, ux | #102–108 |
| 13 | Language-specific: SQL/Django ORM | database | #109–114 |
| 14 | Language/platform-specific: Windows | windows | #115–123 |
| 15 | GitHub Actions / CI-CD anti-patterns | cicd, cloud | #124–133 |
| 16 | OSS Python packaging/release anti-patterns | python, cicd | #134–143 |
| 17 | Cross-harvested "must/must-not" checklist (this library's own hard rules) | general | #144–154 |
| 18 | Architecture-level anti-patterns | architecture, cloud | #155–162 |
| 19 | Documentation/commenting anti-patterns | general | #163–168 |
| 20 | Naming-convention anti-patterns (this platform's own) | general | #169–173 |

## 1. Classic code smells (Fowler)

1. **Duplicated code** — same logic in ≥2 places; a fix in one silently doesn't apply to the other.
2. **Long method** — a function that needs scrolling to read; usually doing more than one job. Falsifiable guideline, not a hard law: **~30 logical lines** as a target ceiling before splitting (this platform's own `check_size_policy.py` default is 50 for the function ceiling — 30 is a stricter target worth aiming for, 50 is the enforced hard gate).
3. **Large class / God object** — one class/module that knows or does too much; every change touches it. Falsifiable guideline: **~400 logical lines per file** as the enforced ceiling (`breachsafe-common/quality-gates/check_size_policy.py`'s actual default), ~200 for a single class.
4. **Long parameter list** — 5+ positional params; a sign the params want to be a struct/object.
5. **Divergent change** — one class changed for many unrelated reasons (low cohesion).
6. **Shotgun surgery** — one conceptual change requires editing many unrelated files (high coupling).
7. **Feature envy** — a method that uses another object's data more than its own; logic lives in the wrong place.
8. **Data clumps** — the same group of fields/params always travels together; should be its own type.
9. **Primitive obsession** — a raw string/int standing in for a real domain concept (an email as a bare `str`, a currency amount as a bare `float`).
10. **Switch/if-chain on type** — repeated type-dispatch logic that polymorphism should replace.
11. **Speculative generality** — abstraction/hook built for a future need that isn't real yet ("we might need this later").
12. **Temporary field** — a field only meaningful in some code paths, `None`/unset otherwise.
13. **Message chains** — `a.b().c().d()` — reaching through several objects to get one value; fragile to any intermediate's change.
14. **Middle man** — a class that does nothing but delegate to another; the indirection earns nothing.
15. **Inappropriate intimacy** — two classes reaching into each other's internals/private state.
16. **Data class** — a class with only getters/setters and no behavior; logic that should live with the data lives elsewhere instead.
17. **Refused bequest** — a subclass that overrides most of its parent's behavior to do nothing/throw — wrong inheritance relationship.
18. **Comments compensating for unclear code** — a comment explaining *what* convoluted code does, instead of the code being rewritten to not need it (comments should explain *why*, not translate *what*).

## 2. SOLID violations

19. **Single Responsibility** — a class/module changes for more than one reason.
20. **Open/Closed** — adding a new case requires editing existing, already-tested code instead of extending it.
21. **Liskov Substitution** — a subclass that breaks a caller's assumptions about the base type (throws where the base wouldn't, narrows an accepted input range).
22. **Interface Segregation** — a fat interface forcing implementers to stub out methods they don't need.
23. **Dependency Inversion** — high-level logic directly constructing/depending on a concrete low-level implementation instead of an abstraction/seam.

## 3. Error-handling anti-patterns

24. **Swallowed exceptions** — `except: pass` / `catch {}` with no log, no re-raise, no comment explaining why it's safe to ignore.
25. **Catching too broadly** — `except Exception` / `catch (Exception e)` where a specific type would do, masking bugs unrelated to the one being handled.
26. **Exceptions for control flow** — using a raised exception as the normal-path mechanism for a common, expected condition (e.g. "not found" as an exception instead of a typed result/None).
27. **Ignored return codes** — a function/subprocess call whose failure signal (exit code, error return) is never checked.
28. **Error message without context** — `raise ValueError("invalid")` with no field name, no offending value, no remediation hint.
29. **Resource leak on the error path** — a file/socket/lock acquired before a possible early return/exception, never released on that path (missing `finally`/context manager).

## 4. Concurrency anti-patterns

30. **Race condition on shared mutable state** — two threads/tasks read-modify-write the same value without a lock/atomic.
31. **Deadlock via inconsistent lock ordering** — two code paths acquire the same two locks in opposite order.
32. **Busy-wait instead of a real wait primitive** — a `while not done: sleep(0.01)` loop instead of an event/condition variable.
33. **Double-checked locking without a memory barrier** — a check-lock-check pattern that's only safe with proper memory-ordering guarantees the code doesn't actually provide.
34. **Unbounded concurrency** — spawning a thread/task per item with no pool/semaphore, exhausting resources under load.
35. **Shared mutable default state across "instances"** — module-level or class-level mutable state that different callers unintentionally share (see also #90, mutable default arguments).

## 5. API/interface design anti-patterns

36. **Boolean parameter trap** — `create(user, True, False)` where the call site can't tell what the booleans mean without checking the signature.
37. **Stringly-typed API** — using bare strings for what should be an enum/typed value (`status: str` accepting arbitrary values instead of a closed set).
38. **Leaky abstraction** — a wrapper/adapter that still requires callers to know the underlying implementation's details to use it correctly.
39. **Anemic domain model** — data objects with no behavior, all logic lives in separate "service" functions that manipulate them from outside.
40. **God function/constructor** — one function/constructor that does setup, validation, side effects, and the actual work all at once.
41. **Silent breaking change** — changing a public function's behavior/return shape without a version bump or deprecation path.
42. **Inconsistent naming across a module** — `get_x`/`fetch_y`/`retrieve_z` all doing the same kind of thing with no naming convention.

## 6. Security bugs (OWASP Top 10 / CWE Top 25-informed)

43. **SQL injection** — building a query via string concatenation with untrusted input instead of parameterized queries (CWE-89).
44. **Command injection** — untrusted input reaching a shell/`subprocess` call with `shell=True` or unescaped interpolation (CWE-78).
45. **Cross-site scripting (XSS)** — reflected, stored, or DOM-based — untrusted input rendered into HTML/JS context without escaping (CWE-79).
46. **Cross-site request forgery (CSRF)** — a state-changing endpoint with no anti-CSRF token/state validation, relying only on ambient cookies (CWE-352).
47. **Server-side request forgery (SSRF)** — fetching a URL derived from user input without validating/allowlisting the target, including internal/metadata-endpoint addresses (CWE-918).
48. **SSRF via redirect-following** — the initial URL is validated but redirects are followed unchecked into an internal address.
49. **XML external entity (XXE) injection** — parsing untrusted XML with external entity resolution enabled (CWE-611).
50. **Insecure deserialization** — deserializing untrusted data with a format/library that can execute code (`pickle.loads` on untrusted input, unsafe YAML loaders) (CWE-502).
51. **Broken access control / IDOR** — an endpoint that checks authentication but not whether *this* user may act on *this* resource (CWE-639).
52. **Privilege escalation via unchecked role/permission changes** — a user able to elevate their own role through an unprotected update endpoint.
53. **Security misconfiguration** — default credentials, verbose stack traces in production, unnecessary features/ports left enabled (CWE-16).
54. **Sensitive data exposure at rest or in transit** — no encryption where it's expected, or a weak/legacy cipher still in use (CWE-311/CWE-319).
55. **Weak password hashing** — MD5/SHA1/unsalted hashes for credential storage instead of bcrypt/scrypt/argon2 (CWE-916).
56. **Using components with known vulnerabilities** — a pinned dependency with a published CVE and no upgrade/mitigation plan (cross-ref §8, dependency anti-patterns).
57. **Insufficient logging and monitoring of security-relevant events** — auth failures, permission denials, and admin actions not logged anywhere (cross-ref §9).
58. **Path traversal** — a user-controlled file path used without normalization/allowlisting, allowing `../../etc/passwd`-style escape (CWE-22).
59. **Open redirect** — redirecting to a user-supplied URL without validating it's same-origin/allowlisted (CWE-601).
60. **Clickjacking** — missing `X-Frame-Options`/`frame-ancestors` CSP on a page that shouldn't be frameable (CWE-1021).
61. **Regular-expression denial of service (ReDoS)** — a regex with catastrophic backtracking applied to untrusted input (CWE-1333).
62. **Mass assignment** — binding all request fields directly onto a model with no explicit allowlist, letting an attacker set fields like `is_admin` (CWE-915).
63. **Integer overflow/underflow** — arithmetic on attacker-influenced values without bounds checking, most relevant at Rust/C/FFI boundaries (CWE-190/191).
64. **Buffer overflow** — writing past an allocated buffer in native code or across an FFI boundary — classic memory-safety bug (CWE-120/787).
65. **Timing side-channel in security-sensitive comparisons** — using `==` instead of a constant-time compare for secrets/HMACs/passwords (CWE-208).
66. **Weak randomness for security purposes** — using `random`/`Math.random()` instead of a CSPRNG for tokens, keys, or nonces (CWE-338).
67. **JWT/token validation bugs** — accepting `alg: none`, skipping signature verification, or not checking expiration/audience claims.

## 7. Testing anti-patterns

68. **Assertion roulette** — a test with many assertions and no message, so a failure doesn't say which one broke.
69. **Mystery guest** — a test that depends on external state (a file, a database row) not set up within the test itself, so it's unclear why it passes or fails.
70. **Test interdependence** — tests that only pass in a specific order or share mutable state between them.
71. **Testing implementation, not behavior** — asserting on private internals/mock call counts instead of observable outputs, so refactoring breaks tests without behavior changing.
72. **Excessive setup / fragile fixtures** — a test needing so much setup that nobody can tell what's actually being tested.
73. **Slow tests in the fast-feedback loop** — a unit test that hits the network/sleeps/spins up a container, slowing everyone's inner loop.
74. **Non-deterministic tests ("flaky")** — a test that fails intermittently for reasons unrelated to the code under test (timing, ordering, uninitialized state).
75. **Happy-path-only coverage** — tests exist but never exercise the error/edge/adversarial path that's actually risky.
76. **Quality theater** — skipped/xfail tests, lowered coverage thresholds, retry-count bumps masking a real deterministic failure (cross-ref `recurring-bug-categories.md`, `breachsafe-cicd-hygiene`).

## 8. Dependency/supply-chain anti-patterns

77. **Unpinned dependencies** — `>=` ranges in a production manifest with no lockfile, letting a transitive update change behavior silently.
78. **Vendoring without provenance** — copying a dependency's source in-tree with no record of which version/commit/license it came from.
79. **Phantom dependency** — code that imports a package only present transitively, not declared directly — breaks the moment the real direct dependency drops it.
80. **Dependency confusion risk** — an internal package name that could collide with a public registry name, without a scoped namespace.
81. **License incompatibility** — pulling in a copyleft dependency into code with an incompatible license, unnoticed.
82. **Abandoned/unmaintained dependency** — a load-bearing package with no commits/releases in years and no fork/vendor plan if it breaks.

## 9. Observability/logging anti-patterns

83. **Print-debugging left in production code** — `print()`/`console.log` instead of the real logger, or debug-level logging left at info/warn.
84. **Silent failure** — a caught error that neither logs nor surfaces anywhere; the system just does nothing and looks fine.
85. **Logging without structure** — free-text log lines that can't be queried/alerted on, where structured fields (request id, tenant id, error code) would let them be.
86. **No correlation id across a request's lifecycle** — impossible to trace one user's request across services/async boundaries in logs.
87. **Alerting on symptoms, not causes** — a monitor that fires on a downstream symptom with no link back to the actual failing component.

## 10. Language-specific: Python

88. **Mutable default arguments** — `def f(x=[])`: the list is created once at function-definition time and shared across every call that doesn't pass its own.
89. **Bare `except:`** — catches `SystemExit`/`KeyboardInterrupt` too, not just application errors.
90. **Module-level mutable global state** — a dict/list at module scope that multiple importers mutate, with import order determining behavior.
91. **String concatenation in a loop** — `s += x` in a loop is O(n²); use `"".join(...)`.
92. **Shadowing a builtin** — naming a variable `list`, `id`, `type`, etc., silently breaking later use of the real builtin in that scope.
93. **`is` vs `==` for value comparison** — `is` compares identity; using it for value equality on ints/strings relies on CPython interning accidents.
94. **Circular imports papered over with local imports** — importing inside a function to dodge a circular-import error, instead of fixing the actual module boundary.
95. **Not using context managers for resources** — manual `open()`/`close()` instead of `with`, leaking file handles on the exception path.

## 11. Language-specific: Rust

96. **Unnecessary `.clone()`** — cloning to dodge the borrow checker instead of restructuring ownership; a performance and clarity smell.
97. **`.unwrap()`/`.expect()` on a `Result`/`Option` from fallible I/O or user input** — panics instead of propagating a typed error.
98. **Overuse of `unsafe`** — an `unsafe` block wider than the minimum needed, or used to avoid understanding a lifetime/borrow issue rather than for a genuine FFI/perf need.
99. **`Rc<RefCell<>>` as a default pattern** — reaching for shared mutable state instead of restructuring ownership; each occurrence should be a deliberate, justified choice, not a habit.
100. **Ignoring a `Result` without `?` or explicit handling** — a fallible call whose error is silently dropped (no `let _ =` justification comment).
101. **Stringly-typed errors** — `Err("something went wrong".to_string())` instead of a typed error enum implementing `std::error::Error`.

## 12. Language-specific: TypeScript/JavaScript

102. **`any` typing** — defeats the type system at exactly the boundary where it matters most (external data, API responses).
103. **Non-null assertion (`!`) as a habit** — silencing a real possible-null case instead of handling it.
104. **Callback hell / unhandled promise rejections** — deeply nested callbacks, or an async call with no `.catch`/try-catch, letting a rejection vanish.
105. **Prototype pollution risk** — merging untrusted objects into another object without guarding `__proto__`/`constructor`/`prototype` keys (CWE-1321).
106. **Mutating props/state directly** (React) — bypassing the framework's update mechanism, causing stale renders or silent bugs.
107. **`useEffect` with a missing/incorrect dependency array** — stale closures capturing old values, or effects re-running more/less than intended.
108. **Barrel-file re-export cycles** — `index.ts` files that re-export each other, creating import cycles that are hard to trace.
108.1. **Design-token bypass — hardcoded status/brand color literals** — arbitrary Tailwind hex (`bg-[#FB718F]`, `text-[#DB2B49]`) or inline `style={{color:'#...'}}` for pass/fail/severity instead of a semantic token (`destructive`/`success`, `--status-fail`/`--status-pass`). Tell-tale that it's a real defect not a nit: the *same* semantic renders as *different* hex across views (two "fail" reds), so dark-mode/rebrand can't propagate and severity coloring is inconsistent. Grep gate: `-\[#[0-9a-f]` in components should be zero outside brand-logo SVGs. (BreachSAFE #227)
108.2. **Brand/config constant defined but consumed 0×** — a token module (`config/brand.ts`) exports the value while the raw literal is hardcoded across the tree; the abstraction exists but nothing routes through it, so the next change is again a find-replace. (BreachSAFE #226)

## 13. Language-specific: SQL/Django ORM

109. **N+1 query** — looping over a queryset and hitting the database again per row instead of `select_related`/`prefetch_related`.
110. **Missing index on a frequently-filtered/joined column** — a query that will silently degrade as the table grows.
111. **Raw SQL string interpolation** — building a query with f-strings/`%` instead of parameterized queries — the classic injection vector (see also #43).
112. **Fat model with business logic that belongs in a service layer**, or the inverse — logic duplicated across views instead of living once on the model/manager.
113. **Migrations that aren't reversible** — a migration with no safe rollback path, discovered only when a rollback is actually needed.
114. **Transaction scope too wide or too narrow** — either holding a lock/transaction open across slow I/O (blocking other writers) or not wrapping related writes atomically (partial-write risk on failure).
114.1. **Sibling-inconsistent scoping in a read endpoint** — one facet of a response ignores the scope/filters the other facets apply. A dropdown-metadata view scopes `services`/`regions`/`types` to the latest scan (or the request's `filter[...]`) but computes `groups` from an unscoped tenant-wide `Model.objects.filter(tenant_id=...)`, so it returns filter values that yield zero results and does a full-table scan on a hot autocomplete path. Grep for metadata/aggregation views where one `values_list`/aggregate is bounded and its neighbour isn't. (BreachSAFE #228)

## 14. Language/platform-specific: Windows

Real, not theoretical — cross-platform code that only ever ran/tested on Linux/macOS
routinely breaks on Windows for reasons that "shouldn't matter" but do: filesystem
semantics, shell semantics, and console behavior all differ in ways POSIX-only
experience doesn't anticipate.

115. **Hardcoded forward-slash path separators** — string-built paths (`dir + "/" + name`) instead of `pathlib`/`os.path.join`; breaks or silently produces a wrong path on Windows.
116. **Case-sensitive path assumptions** — Windows filesystems are (usually) case-insensitive while Linux/most macOS setups are case-sensitive; a casing bug can silently "work" on a dev machine and break for every Windows user, or the reverse for a Linux deploy target.
117. **Line-ending assumptions (LF vs CRLF)** — string parsing/comparison assuming `\n` only; a file checked out with CRLF line endings (a common Windows git default) breaks exact-match parsing or shifts byte offsets used elsewhere.
118. **POSIX-only shell syntax executed via subprocess** — code assuming `/bin/sh` semantics (globbing, `&&`, quoting rules) when the shell actually invoked on Windows is `cmd.exe` or PowerShell, which parse differently.
119. **PowerShell injection** — building a PowerShell command string via untrusted-input concatenation; PowerShell's quoting/escaping rules differ from POSIX shells, so a POSIX-safe escaping routine doesn't protect a PowerShell invocation.
120. **Reserved filename collisions** — Windows reserves `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9` as device names; a user-supplied filename matching one (even with an extension, e.g. `con.txt`) fails or behaves unexpectedly.
121. **`MAX_PATH` (260-character) path-length limit** — a deeply nested path or long filename that works on Linux/macOS silently fails to open/create on Windows unless long-path support is explicitly enabled.
122. **File-locking differences** — Windows locks an open file against deletion/rename by default; code assuming POSIX's "you can unlink/rename a file while another process holds it open" fails on Windows with a sharing-violation error.
123. **Console/terminal encoding assumptions** — assuming UTF-8 stdout by default; a Windows console using a legacy codepage mangles non-ASCII output unless encoding is set explicitly.

## 15. GitHub Actions / CI-CD anti-patterns

Cross-reference `breachsafe-cicd-hygiene` for #127, #128, #132, #133 in depth (missing
concurrency guards, duplicate CI across repos, cron/canary misclassified as disposable
cost, skip-masking) — summarized here, not fully repeated.

124. **`pull_request_target` checking out the PR's head ref** — runs with the base repo's secrets/write permissions against untrusted fork code; the single most dangerous GitHub Actions misconfiguration.
125. **Third-party actions pinned to a mutable tag (`@v3`, `@main`) instead of a commit SHA** — a tag can be moved by the action's maintainer (or an attacker who compromises their account) without your workflow changing at all.
126. **Script injection via untrusted context values** — `run: echo "${{ github.event.issue.title }}"` interpolates attacker-controlled text directly into a shell command; use an intermediate env var instead of inline `${{ }}` in a `run:` step.
127. **Overly broad `GITHUB_TOKEN` permissions** — default/unscoped `permissions: write-all` when the workflow only needs `contents: read`.
128. **Self-hosted runners accepting jobs from public-fork PRs** — a fork PR's workflow run executes on infrastructure with network/credential access it shouldn't have.
129. **Secrets echoed into logs** — even accidentally, via a `set -x`/debug-mode step or a tool that prints its full config including a secret env var.
130. **No provenance/SBOM on a released artifact** — a published binary/image/package with no record of what commit, dependency versions, or build environment produced it (see `breachsafe-release`'s Sigstore/SLSA coverage).
131. **Cache poisoning risk** — a workflow cache keyed on attacker-influenced input (a PR branch name, a user-supplied tag) that a later, more-privileged run then trusts.
132. **Workflow dispatch with unvalidated free-text inputs** — a `workflow_dispatch` input used directly in a shell command or as a file path without validation.
133. **No `timeout-minutes` on a job** — a hung step (network wait, deadlock) runs until the platform's own multi-hour ceiling, burning CI minutes silently.

## 16. OSS Python packaging/release anti-patterns

134. **`setup.py`-only packaging** in a new project instead of `pyproject.toml` (PEP 517/518/621) — loses standardized metadata, reproducible builds, and tool interoperability.
135. **No `py.typed` marker** on a package that ships type hints — without it, type checkers treat the package as untyped for downstream consumers even if every function is annotated.
136. **Long-lived PyPI API tokens in CI secrets** instead of Trusted Publishing (OIDC) — a leaked long-lived token is a standing compromise; OIDC-based publishing has no persistent secret to leak.
137. **Unpinned build backend/dependency ranges in a *published* package** — `>=` with no upper bound on a core dependency, breaking downstream installs when that dependency ships a breaking major version.
138. **No SPDX license identifiers** on source files in a project that claims a specific license — ambiguous provenance for anyone auditing supply-chain license compliance.
139. **`__version__` defined in more than one place** (package `__init__.py`, `pyproject.toml`, a docs config) — they drift, and a release ships with mismatched version strings.
140. **No `CHANGELOG.md`** (or one that isn't kept current) — consumers have no way to know what changed between versions without diffing releases themselves.
141. **Wildcard imports in library code** (`from module import *`) — pollutes the importer's namespace and hides what a module actually exports; acceptable in a throwaway script, not in a published library.
142. **Publishing a wheel built on a dirty/uncommitted working tree** — the artifact doesn't correspond to any real, inspectable commit.
143. **No `reuse lint`/license-header enforcement in CI** — license-header drift goes unnoticed until an external audit or a legal review catches it.

## 17. Cross-harvested "must/must-not" checklist (this library's own hard rules)

Every skill in this library states its own authorization gate and hard rules in its own
words — this collects them into one checklist so a reviewer can spot-check compliance
without re-reading every SKILL.md. These are this library's *own* non-negotiables, not
general industry patterns like the sections above.

144. **Never commits, pushes, branches, merges, or opens/comments on a PR without explicit in-conversation authorization for that specific action** — stated independently in `breachsafe-implement`, `breachsafe-red-team`, `breachsafe-release`, `breachsafe-review-gate`, and others. "The repo's own workflow docs describe this as the normal flow" is not standing authorization.
145. **Never adds test-only behavior to production code just to make documentation/checks pass** (`breachsafe-docs`) — the code should be correct on its own merits; docs describe real behavior, not the other way around.
146. **Never weakens a test to make it pass** — lowering an assertion, loosening a tolerance, or removing a check, to get a red test green, without fixing the actual defect the test caught.
147. **Never fakes production wiring in a fixture without a paired real-path test** — a mock/stub that diverges from real behavior, with nothing verifying the real path still works.
148. **A public/loaded contract must not silently change behavior** — a schema, CLI flag, or API response shape changes without a version bump, deprecation notice, or migration path.
149. **RLS must never be bypassed via raw SQL/`connection.cursor()`** without setting the tenant context first (`breachsafe-prowler-developer`/`breachsafe-prowler-ux`) — the single most consequential rule in any RLS-protected repo; a raw-SQL escape hatch that skips `SET api.tenant_id` is a cross-tenant data leak, not a shortcut.
150. **`ANTIPATTERN FLAGGED` must never be silently treated as `ANTIPATTERN APPROVED`** without evidence a human actually signed off (the governance fix in `breachsafe-implement`) — a flagged deviation is a request, not a decision, until someone with the authority to decide actually responds to it.
151. **Never disables TLS/certificate verification**, even "temporarily," without an explicit, reviewed exception.
152. **Never logs a secret, token, or credential**, even at debug level, even in a code path that's "unlikely to run in production."
153. **A destructive git operation (`reset --hard`, `push --force`, `clean -f`) is never run without an explicit request for that specific operation** — confirmed once doesn't imply standing permission for the next one.
154. **Skills stay in their lane** — an audit-only skill (`breachsafe-security-audit`, `breachsafe-conformance`, `breachsafe-release`) never fixes the code it's reviewing; it reports findings and waits for authorization to act. Crossing this line is itself a checklist item to watch for during self-review, not just a rule to follow.

## 18. Architecture-level anti-patterns

Macro/system-level, not single-file — cross-reference `breachsafe-architecture-review`
for the full design-review discipline; this is the checklist-item summary, not a
replacement for that skill's depth.

155. **Distributed monolith** — services split across process/network boundaries that still deploy in lockstep and share a database, paying microservices' latency/complexity cost with none of the independent-deployability benefit.
156. **Big ball of mud** — no discernible architecture at all; every component can reach every other, so no boundary is safe to change alone.
157. **Shared database across services** — two independently-deployed services both writing to the same tables, coupling their schemas even though their code is "separate."
158. **Synchronous call chains with no circuit breaker/timeout** — service A calls B calls C synchronously; a slow/down C cascades into A being down too, with no isolation.
159. **Missing backpressure/bulkheads** — one overloaded downstream dependency can exhaust the caller's own thread/connection pool, taking down unrelated functionality in the same process.
160. **No API versioning strategy** — a breaking change to a public API/contract has no migration path (no version header, no parallel old/new route, no deprecation window).
161. **God gateway/orchestrator** — a single service that talks to every other service and encodes cross-cutting business logic, becoming a de facto second monolith at the integration layer.
162. **Tight coupling to a specific cloud vendor's proprietary primitive** with no abstraction seam, when the architecture claims portability — the abstraction is aspirational, not real, until something has actually been swapped once.

## 19. Documentation/commenting anti-patterns

Distinct from #18 above (comments as a code-quality crutch) — this section is about the
documentation *practice* itself, not one file's comment style. Cross-reference
`python-style-conventions.md` for the enforced PEP 257 + Google Style Guide rules this
summarizes.

163. **Missing docstring on a public/nontrivial function or module** — no summary of what it does, no args/returns/raises documented where non-obvious.
164. **Ticket-number comments instead of rationale** (`# #NN: fix this`) — the *why* a decision was made is lost the moment the ticket tracker is gone/renumbered/inaccessible; write the reason inline, reference the ticket as a pointer, not a substitute.
165. **Documentation that describes intent instead of actual behavior** — a docstring/README paragraph written when the feature was planned, never updated when the implementation diverged from the plan.
166. **No architecture-decision record for a load-bearing choice** — a consequential design decision (data store choice, protocol choice, a security tradeoff) made with no ADR, so the reasoning is lost the moment the person who made it leaves the conversation.
167. **Stale badges/links in a README** — a build/coverage/version badge pointing at a CI job or URL that no longer exists or reports something untrue.
168. **Over-commented obvious code** — a comment restating exactly what the next line already says (`# increment i` above `i += 1`) — noise that trains readers to skip comments, including the ones that matter.

## 20. Naming-convention anti-patterns (this platform's own)

Where a name is genuinely platform-identifying (a repo, a published package, a shared
skill, a public API/CLI name) — not everywhere, not internal variables/functions —
prefer `breachsafe-<common-or-standard-term>` so there's no collision with an
unrelated OSS project of the same generic name and attribution back to this platform
stays unambiguous at a glance (`breachsafe-implement`, `breachsafe-common`,
`breachsafe-crypto-rs` follow this; internal function/variable names inside those
repos correctly do not).

169. **A repo/package name that's a bare generic term** — e.g. naming a crate/package just `scanner` or `crypto` with no platform prefix, collidable with any number of unrelated same-named projects on crates.io/PyPI/npm and untraceable back to this platform from the name alone.
170. **Inconsistent prefixing across sibling repos** — some platform repos carry the `breachsafe-` prefix, others don't, with no documented rule for which gets one — makes it impossible to tell from a repo list which ones belong to this platform.
171. **Over-prefixing internal identifiers** — applying the `breachsafe-` (or platform-name) prefix to internal variables, private functions, or local file names where it adds no disambiguation value and only adds noise (the convention is for platform-identifying, externally-visible names, not everything).
172. **A skill/package name that collides with an existing well-known tool of the same generic name** — publishing something called `implement` or `review` with no namespace, where a search/install collides with an unrelated, more established project.
173. **Renaming a platform-identifying artifact without updating all cross-references** — a repo/package renamed to add or fix its prefix, but old skill files, manifests, or docs still reference the pre-rename name — the exact class of drift this whole library's mechanical verification scripts exist to catch.

## Using this checklist, end to end

Run it in this order for the best signal-to-noise: (1) skim the Contents table's
**Domain** column, decide which categories plausibly apply to the diff/repo in front
of you (a UX bug doesn't need §6's crypto-adjacent items or §11's Rust section walked;
a crypto/RFC-conformance change doesn't need §12's TypeScript/React items) — not all 20
will apply to any one change; (2) walk only those categories, item by item, citing a
number for anything that hits; (3) for any hit, anchor it to a real file:line, not a
vague "watch out for this" — an unanchored hit isn't a finding yet; (4) if nothing in a
category applies, say so and move on rather than forcing a match. This file is a net to
check against, not a mandatory minimum word count — a clean review that correctly finds
zero hits in 16 of 20 categories is a good review, not an incomplete one.
