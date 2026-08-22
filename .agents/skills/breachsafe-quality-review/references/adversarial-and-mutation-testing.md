# Test-suite integrity — does "green" mean "tested"? (Mode 6)

A green suite is not evidence the code is tested — only that the tests written happen to
pass. This mode asks the harder question: **would the tests fail if the code were wrong?**
Use it when a suite looks reassuring but the product still ships bugs.

Real precedent (endpoint collector): **33 green unit tests**, yet 4 build-breaking image
bugs and a latent SSRF shipped anyway. Root cause was measurable — only **6 of 33 tests**
exercised the host-validation guard, so a mutant `def valid_host(h): return True` survives
~32 of them. Green told us nothing about the guard.

The four techniques below, cheapest-first. You do not need all four every time — reach for
the one that matches the risk (mutation for "do tests catch bugs", property for parsers/
validators, container-structure for any image, adversarial corpus for any input guard).

## Contents
- 1. The 30-second mutation smell (no tooling)
- 2. Mutation testing — the discriminator (`mutmut` / `cosmic-ray`)
- 3. Property-based testing (`hypothesis`) — auto-finds adversarial inputs
- 4. Container-structure testing — closes the build→run gap
- 5. Adversarial input corpus (reusable across unit + property tests)
- Report shape

## 1. The 30-second mutation smell (no tooling)

Before installing anything: pick the function that matters (a validator, a gate, a parser)
and count how many tests actually exercise it.
```bash
grep -cE '<func_name>|<its behaviour keywords>' path/to/tests/*.py
```
If a security-critical guard is touched by 1–2 tests, a "return the safe-looking constant"
mutant survives the rest. That surviving mutant is usually a real finding waiting to be
written (it was, verbatim, the SSRF). Name the mutant you think survives, then prove it.

## 2. Mutation testing — the discriminator (`mutmut` / `cosmic-ray`)

Mutation testing edits the product code (flip `>=`→`>`, `and`→`or`, `True`→`False`, delete
a line) and re-runs the suite. A **surviving mutant** = a change that broke nothing =
untested logic.
```bash
uv run mutmut run --paths-to-mutate path/to/core.py     # then: mutmut results
```
- Report the **mutation score** (killed / total), not just pass/fail. Gate the *pure core*
  first (deterministic, no IO) — start ~70%, ratchet up; don't demand it on IO/orchestration
  glue where mutants are noisy.
- Each survivor is a candidate finding: read it, decide if it's a real gap or an equivalent
  mutant (semantically identical — not a bug). **Don't file equivalent mutants** — that's
  the false-positive brake (`review-false-positives.md`) applied to mutation output.
- This is the metric that answers "the scorecard is all 9s but bugs still ship": a high
  mutation score is earned discrimination; a green suite is not.

## 3. Property-based testing (`hypothesis`) — auto-finds adversarial inputs

Hand-picked fixtures test the inputs you thought of. Properties test the ones you didn't,
and **shrink** failures to a minimal repro. Highest value on **parsers, validators, and
version/format gates**.
```python
from hypothesis import given, strategies as st

@given(st.ip_addresses())                 # would have surfaced the internal-IP SSRF
def test_valid_host_rejects_internal(ip):
    assert host_guard.valid_host(str(ip)) is (not ip.is_private and not ip.is_loopback ...)

@given(st.text())                          # would have surfaced the trailing-\n bypass
def test_valid_host_no_control_chars(s):
    if valid_host(s): assert "\n" not in s and "\x00" not in s
```
Pattern per target: a **round-trip** property (`split(join(x)) == x`), an **invariant**
property (validated output always satisfies the contract), and a **never** property (a
guard never accepts a class it's meant to block). Pin a `@seed` for the CI regression once a
property has found a bug, and keep the shrunk example as an explicit unit test too.

## 4. Container-structure testing — closes the build→run gap

Unit tests never build or run the image, so Dockerfile/packaging bugs are invisible to them
(precedent: all 4 #95 image bugs — wheel-glob `COPY` failure, `ModuleNotFoundError` from
non-standalone imports, silently-unwritten evidence file, root-vs-non-root perms). For any
Dockerized deliverable, assert the *built artifact*:
```yaml
# container-structure-test.yaml (GoogleContainerTools) — or goss/dgoss
commandTests:
  - {name: openssl-is-pqc, command: openssl, args: [version], expectedOutput: ['OpenSSL 3\.5\.7']}
  - {name: mlkem-available, command: openssl, args: [list, -kem-algorithms], expectedOutput: ['ML-KEM-768']}
  - {name: tool-on-path, command: qureddy, args: [--version], exitCode: 0}
metadataTest: {user: "1000"}          # process is non-root
fileExistenceTests: [{name: evidence, path: /opt/.../versions.txt, shouldExist: true}]
```
Plus: **`hadolint`** on the Dockerfile (catches the `|| true`-masked failure and perm
smells), **`trivy image`** for CVEs (a source-built dependency means *you* own its CVE
tracking — gate it), **`dive`** for layer bloat. Wire these into the same CI that gates the
image, and **actually run the build once by hand** and quote the failing step — a build that
"should work" is not a tested build.

## 5. Adversarial input corpus (reusable across unit + property tests)

For any input guard / validator, run the standing corpus and confirm each is handled the way
the guard *claims*:
- **SSRF / internal targets:** `169.254.169.254` (cloud metadata), `127.0.0.1`, `::1`,
  `10.0.0.1`/`192.168.1.1` (RFC1918), `fe80::…` (link-local), `0.0.0.0`, `localhost`,
  `*.internal`. A scanner/fetcher that accepts these is an SSRF pivot the moment the target
  becomes user-controlled.
- **Injection shapes:** leading `-`/`--`, shell metacharacters, spaces (arg-injection).
- **Encoding traps:** trailing `\n` (Python `$` matches before a terminal newline — anchor
  with `\Z` or `re.fullmatch`), embedded `\n`/`\r` (CRLF/log-injection), `\x00`, unicode
  digits (`²³` pass `.isdigit()` but not `.isdecimal()`), IDN/punycode, mixed-case.
- **Resource / ReDoS:** time the validator on `"a"*100000` and nested-quantifier bait; a
  regex with unbounded nested `(...)*` over `.{n,}` is the shape to suspect. **Verify with a
  timer before claiming ReDoS** — bounded `{0,61}` quantifiers are usually safe (proven safe
  on the collector at <0.3 ms; don't file what you haven't timed).

## Report shape

- Lead with the **mutation score** (or the "N of M tests touch this guard" smell) — that is
  the discrimination signal, and the answer to "why is everything graded 9?"
- For each surviving mutant / property failure / container-test failure: the **minimal
  repro** (shrunk input or failing image step), the **real** vs **claimed** behaviour, and
  whether it's a `[bug]` or an equivalent-mutant/`[won't-fix]`.
- Everything here must be **run, not reasoned** — quote the real command output. A named
  mutant you didn't execute, or an image bug you didn't reproduce by building, is a guess.
