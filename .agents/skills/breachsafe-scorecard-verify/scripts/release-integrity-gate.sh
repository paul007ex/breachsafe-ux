#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# release-integrity-gate.sh <owner/repo> [tag]
#
# The signing STEP existing in release.yml does NOT mean it RAN for this
# release. A workflow can carry cosign/attest-build-provenance and still ship an
# unsigned release because the workflow never executed for that tag (a manually
# cut release, a cancelled run, a tag pushed before the signing job was added).
# Scorecard's Signed-Releases then dings you and it looks like a config bug when
# the config is fine -- the RUN is missing.
#
# This gate FAILS (exit 1) if EITHER:
#   (a) the release has no signature/attestation -- checked two ways:
#       release assets for .sig/.sigstore/.intoto, AND `gh attestation verify`
#       against GitHub's attestation store (attest-build-provenance leaves NO
#       release asset, only a store entry, so the asset check alone is blind); OR
#   (b) the signing workflow did not SUCCESSFULLY run for this tag
#       (gh run list correlated to the tag).
#
# Read-only except a temp download of the release artifact (cleaned up).
# Deps: gh (authenticated), jq. `gh attestation verify` used if present.
# bash 3.2 safe. Drop the CI snippet in the SKILL into your own release.yml to
# enforce this BEFORE publish instead of catching it later via Scorecard.
#
# Usage:
#   release-integrity-gate.sh breachsafe/qureddy            # latest release
#   release-integrity-gate.sh breachsafe/qureddy v0.2.16
# Env:
#   WORKFLOW  signing workflow filename (default release.yml)

set -u

WORKFLOW="${WORKFLOW:-release.yml}"
die() { echo "error: $*" >&2; exit 2; }

REPO="${1:-}"
[ -n "$REPO" ] || die "usage: release-integrity-gate.sh <owner/repo> [tag]"
case "$REPO" in */*) : ;; *) die "expected <owner/repo>";; esac
TAG="${2:-}"

for t in gh jq; do command -v "$t" >/dev/null 2>&1 || die "missing tool: $t"; done

if [ -z "$TAG" ]; then
  TAG="$(gh release list -R "$REPO" -L 1 --json tagName -q '.[0].tagName' 2>/dev/null)"
  [ -n "$TAG" ] || die "no releases found in $REPO"
fi

echo "=================================================================="
echo " Release integrity gate: ${REPO} @ ${TAG}"
echo "=================================================================="

FAIL=0

# --- (a) signature / attestation -------------------------------------------
ASSETS="$(gh release view "$TAG" -R "$REPO" --json assets -q '.assets[].name' 2>/dev/null)"
[ -n "$ASSETS" ] || echo "  note: release has no assets at all"
SIG_ASSET="$(printf '%s\n' "$ASSETS" | grep -iE '\.(sig|asc|sigstore|intoto|pem)([.]jsonl?)?$|attestation|\.intoto\.' )"

ATTEST="unknown"
if command -v gh >/dev/null 2>&1 && gh attestation --help >/dev/null 2>&1; then
  TMP="$(mktemp -d)"
  # prefer a wheel, then sdist, then any single asset
  PRIMARY="$(printf '%s\n' "$ASSETS" | grep -iE '\.whl$' | head -1)"
  [ -n "$PRIMARY" ] || PRIMARY="$(printf '%s\n' "$ASSETS" | grep -iE '\.tar\.gz$' | head -1)"
  [ -n "$PRIMARY" ] || PRIMARY="$(printf '%s\n' "$ASSETS" | head -1)"
  if [ -n "$PRIMARY" ]; then
    if gh release download "$TAG" -R "$REPO" -p "$PRIMARY" -D "$TMP" >/dev/null 2>&1; then
      if gh attestation verify "$TMP/$PRIMARY" --repo "$REPO" >/dev/null 2>&1; then
        ATTEST="pass"
      else
        ATTEST="fail"
      fi
    fi
  fi
  rm -rf "$TMP"
fi

if [ -n "$SIG_ASSET" ]; then
  echo "  [PASS] signature assets present: $(printf '%s' "$SIG_ASSET" | tr '\n' ',' | sed 's/,$//')"
elif [ "$ATTEST" = "pass" ]; then
  echo "  [PASS] provenance attestation verifies via gh attestation (no asset, store-only)"
elif [ "$ATTEST" = "fail" ]; then
  echo "  [FAIL] no signature asset AND gh attestation verify found none for $TAG"
  FAIL=1
else
  echo "  [FAIL] no signature/attestation asset; could not confirm attestation store"
  echo "         (assets: $(printf '%s' "$ASSETS" | tr '\n' ',' | sed 's/,$//'))"
  FAIL=1
fi

# --- (b) did the signing workflow actually run for this tag? ----------------
RUNS="$(gh run list -R "$REPO" --workflow="$WORKFLOW" -L 40 \
        --json headBranch,displayTitle,conclusion,event,createdAt 2>/dev/null)"
if [ -z "$RUNS" ] || [ "$RUNS" = "[]" ]; then
  echo "  [FAIL] no runs of $WORKFLOW found (workflow missing or never executed)"
  FAIL=1
else
  MATCH="$(printf '%s' "$RUNS" | jq -r --arg t "$TAG" '
    .[] | select(.headBranch==$t or (.displayTitle|contains($t)))
        | "\(.conclusion)\t\(.createdAt)\t\(.displayTitle)"' | head -1)"
  if [ -z "$MATCH" ]; then
    echo "  [FAIL] $WORKFLOW never ran for $TAG -- signing steps existed but did"
    echo "         not execute for this release (this is why it is unsigned)."
    LAST="$(printf '%s' "$RUNS" | jq -r '.[0] | "\(.headBranch) (\(.conclusion), \(.createdAt))"')"
    echo "         most recent $WORKFLOW run: $LAST"
    FAIL=1
  else
    CONC="$(printf '%s' "$MATCH" | cut -f1)"
    if [ "$CONC" = "success" ]; then
      echo "  [PASS] $WORKFLOW ran successfully for $TAG"
    else
      echo "  [FAIL] $WORKFLOW ran for $TAG but conclusion=$CONC (not success)"
      FAIL=1
    fi
  fi
fi

echo "------------------------------------------------------------------"
if [ "$FAIL" -eq 0 ]; then
  echo "VERDICT: PASS -- ${TAG} is signed and its signing workflow ran."
  exit 0
else
  echo "VERDICT: FAIL -- ${TAG} is NOT provably signed. Do not treat as released."
  echo "  Fix forward: re-run $WORKFLOW for $TAG (gh workflow run $WORKFLOW -R $REPO"
  echo "  --ref $TAG) or cut a new patch release, then re-run this gate. If this is"
  echo "  a real regression, file it with a 'verified-regression' label and a"
  echo "  machine-checkable close-criterion: 'this gate exits 0 for <tag>'."
  exit 1
fi
