#!/usr/bin/env bash
# Deterministic generic-code-hygiene scan (Modes 2 and 5).
#
# Runs the four checks in references/generic-code-hygiene.md in one pass instead
# of re-typing each grep by hand every audit: panics/aborts, subprocess calls
# outside a designated shim, stray logging in library code, and dead code /
# floating TODOs. Read-only -- never modifies the target tree.
#
# Usage:
#   scripts/hygiene_scan.sh <path-to-src-dir> [shim-file-substring]
#
# The optional second argument excludes hits inside the repo's own designated
# subprocess/shell-out shim file (e.g. "openssl_probe.py") from the subprocess
# section, since that file is expected to contain those calls.
#
# Portability notes from actually testing this on real machines, not just
# assuming POSIX/bash behavior:
#   - File discovery uses `find`, not `grep -r`. Verified against a real
#     permission-restricted subdirectory: some recursive-grep implementations
#     abort the ENTIRE search on the first unreadable subdirectory rather
#     than skipping it and continuing -- silently under-reporting findings
#     on any real target tree with so much as one restricted subdir (a
#     `.git` internal, a vendor dir). `find` reports and continues instead.
#   - No `mapfile`/`readarray`/bash arrays: macOS ships bash 3.2 by default
#     (last GPLv2 release; mapfile needs bash 4+), so this uses a portable
#     `find -print0 | while read -r -d ''` loop instead, which works on 3.2.

set -uo pipefail  # not -e: grep's "no match" exit code (1) is expected, not fatal

TARGET="${1:-}"
SHIM="${2:-}"

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "Usage: $0 <path-to-src-dir> [shim-file-substring]" >&2
  exit 1
fi

FIND_ERRS="$(mktemp)"
trap 'rm -f "$FIND_ERRS"' EXIT

section() {
  echo
  echo "== $1 =="
}

# scan_ext <extension> <pattern> -- greps every file with the given extension
# under $TARGET, one file at a time (never a recursive grep). find's stderr
# (permission-denied etc.) is captured to $FIND_ERRS and reported once at the
# end rather than interleaved into results.
scan_ext() {
  local ext="$1" pattern="$2"
  find "$TARGET" -type f -name "*.$ext" -print0 2>>"$FIND_ERRS" |
    while IFS= read -r -d '' f; do
      grep -nE "$pattern" "$f" 2>/dev/null | sed "s|^|$f:|"
    done
}

count_and_print() {
  local label="$1"
  local n=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    echo "  $line"
    n=$((n + 1))
  done
  echo "  ($label: $n hits)"
}

section "1. Panics / unrecoverable aborts"
{
  scan_ext rs 'unwrap\(\)|\.expect\(|panic!'
  scan_ext py 'assert ' | grep -v '/tests/'
} | count_and_print "panics/asserts"

section "2. Subprocess / shell-out calls"
{
  scan_ext rs 'Command::new|std::process'
  scan_ext py 'subprocess\.'
} | { if [ -n "$SHIM" ]; then grep -v "$SHIM"; else cat; fi } | count_and_print "subprocess calls"
if [ -z "$SHIM" ]; then
  echo "  (no shim file given -- review each hit manually; most repos confine"
  echo "   subprocess calls to exactly one designated module)"
fi

section "3. Stray logging in library code"
{
  scan_ext rs 'println!|eprintln!|print!|dbg!'
  # Bare builtin `print(` only -- excludes `x.print(`/`console.print(` etc.,
  # a real false-positive class found testing this against a repo whose
  # designated output module legitimately calls a Rich console's .print().
  scan_ext py '(^|[^.[:alnum:]_])print\('
} | count_and_print "stray print/log calls"

section "4. Dead code / commented-out code / floating TODOs"
{
  # Plain `//` comments only (excludes `///` doc comments and `//!` module
  # docs) that look like a commented-out statement: a call ending in `;`.
  # Tested against a real codebase -- the naive '//.*word(' pattern matches
  # nearly every /// doc comment with an example or function reference and
  # is useless; this version requires the statement-shaped `;` ending.
  scan_ext rs '^[[:space:]]*//[^/!].*[a-zA-Z_][a-zA-Z0-9_]*\([^)]*\)[[:space:]]*;[[:space:]]*$'
  { scan_ext rs 'TODO|FIXME'; scan_ext py 'TODO|FIXME'; } | grep -v '#[0-9]\|issue'
} | count_and_print "dead code / floating TODOs"

if [ -s "$FIND_ERRS" ]; then
  echo
  echo "== find warnings (directories skipped, not a scan failure) =="
  sort -u "$FIND_ERRS" | sed 's/^/  /'
fi

echo
echo "Each hit above is a CANDIDATE -- read the surrounding code and decide real"
echo "violation vs. false positive before treating it as a finding. See"
echo "references/generic-code-hygiene.md for what counts as a real violation in"
echo "each category, and the top-level SKILL.md for whether this run is Mode 2"
echo "(report only) or Mode 5 (fix your own uncommitted work)."
