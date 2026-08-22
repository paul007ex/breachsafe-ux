#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# scorecard-verify.sh <owner/repo>
#
# Trust-but-verify wrapper around OpenSSF Scorecard. It NEVER trusts the
# aggregate score or the securityscorecards.dev viewer on its own:
#
#   1. Fetches the official API and prints score + scan date + staleness, and
#      whether the scorecard.yml workflow is disabled (which freezes the score
#      and makes `gh workflow run scorecard.yml` return HTTP 422).
#   2. For every check scoring < 10, runs a deterministic `gh` probe against the
#      repo and classifies the gap REAL-GAP / FALSE-POSITIVE / FIXED-BUT-LAGGING
#      / STRUCTURAL / NEEDS-JUDGMENT, with the evidence it used.
#
# A local `scorecard` run under-scores Signed-Releases / CI-Tests / SAST vs the
# GitHub-hosted scan (a PAT can't see everything the hosted scanner can), so this
# reconciles against the OFFICIAL API, not a local run. Local numbers are a floor.
#
# Read-only. Dependencies: gh (authenticated), curl, jq, python3. bash 3.2 safe
# (macOS default) -- no mapfile, no associative arrays, no ${var,,}.
#
# Usage:
#   scripts/scorecard-verify.sh breachsafe/qureddy
# Env:
#   STALE_DAYS  staleness threshold in days (default 14)
#   PR_SAMPLE   how many merged PRs to sample for CI-Tests (default 15)

set -u

STALE_DAYS="${STALE_DAYS:-14}"
PR_SAMPLE="${PR_SAMPLE:-15}"

die() { echo "error: $*" >&2; exit 2; }

REPO="${1:-}"
[ -n "$REPO" ] || die "usage: scorecard-verify.sh <owner/repo>"
case "$REPO" in */*) : ;; *) die "expected <owner/repo>, got '$REPO'";; esac
OWNER="${REPO%%/*}"
NAME="${REPO#*/}"

for t in gh curl jq python3; do
  command -v "$t" >/dev/null 2>&1 || die "missing required tool: $t"
done

API="https://api.securityscorecards.dev/projects/github.com/${OWNER}/${NAME}"
JSON="$(curl -s -w '\n%{http_code}' "$API")"
CODE="$(printf '%s' "$JSON" | tail -n1)"
JSON="$(printf '%s' "$JSON" | sed '$d')"

echo "=================================================================="
echo " OpenSSF Scorecard verification: ${REPO}"
echo "=================================================================="
echo

if [ "$CODE" != "200" ]; then
  echo "OFFICIAL API: no published result (HTTP $CODE)."
  echo "  The repo has never completed a hosted Scorecard run, or the project"
  echo "  is not indexed. Trigger one: gh workflow run scorecard.yml -R $REPO"
  echo "  (or run \`scorecard --repo=github.com/$REPO\` locally -- FLOOR only)."
  echo
  AGGREGATE="(none)"
else
  AGGREGATE="$(printf '%s' "$JSON" | jq -r '.score')"
  SDATE="$(printf '%s' "$JSON" | jq -r '.date')"
  COMMIT="$(printf '%s' "$JSON" | jq -r '.repo.commit')"
  AGE="$(python3 - "$SDATE" <<'PY'
import sys, datetime
try:
    d = datetime.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
    now = datetime.datetime.now(datetime.timezone.utc)
    print((now - d).days)
except Exception:
    print(-1)
PY
)"
  echo "OFFICIAL API (${API#https://}):"
  echo "  aggregate score : ${AGGREGATE}/10"
  echo "  scan date       : ${SDATE}  (${AGE} days ago)"
  echo "  scanned commit  : ${COMMIT}"
  if [ "$AGE" -ge "$STALE_DAYS" ] 2>/dev/null; then
    echo "  >> STALE: older than ${STALE_DAYS}d. Do NOT quote this number as current."
    echo "     Trigger a fresh run: gh workflow run scorecard.yml -R $REPO"
  elif [ "$AGE" -lt 0 ] 2>/dev/null; then
    echo "  >> could not parse scan date; treat as stale."
  else
    echo "  >> fresh (<= ${STALE_DAYS}d)."
  fi
fi
echo

# --- Is the scorecard.yml workflow itself disabled/frozen? ------------------
WF="$(gh api "repos/${REPO}/actions/workflows/scorecard.yml" 2>/dev/null)"
if [ -n "$WF" ]; then
  STATE="$(printf '%s' "$WF" | jq -r '.state // "unknown"')"
  echo "scorecard.yml workflow state: ${STATE}"
  case "$STATE" in
    active) : ;;
    *) echo "  >> WORKFLOW NOT ACTIVE. The published score is FROZEN at the last"
       echo "     run and will not refresh. \`gh workflow run scorecard.yml\` will"
       echo "     fail: 'HTTP 422: Cannot trigger on a disabled workflow'."
       echo "     Re-enable it (gh workflow enable scorecard.yml -R $REPO) or run"
       echo "     scorecard locally, and SAY which produced your numbers." ;;
  esac
else
  echo "scorecard.yml workflow: not found in ${REPO} (.github/workflows/)."
  echo "  The published score, if any, came from the deps.dev weekly scan, not a"
  echo "  repo-owned workflow -- you cannot trigger a refresh via gh workflow run."
fi
echo

[ "$CODE" = "200" ] || { echo "No per-check data to verify without an API result. Stopping."; exit 0; }

# --- Per-check deterministic verification -----------------------------------
echo "PER-CHECK VERIFICATION (only checks scoring < 10):"
echo "------------------------------------------------------------------"
printf '%-22s %-6s %-18s %s\n' "CHECK" "SCORE" "CLASS" "EVIDENCE"
printf '%-22s %-6s %-18s %s\n' "-----" "-----" "-----" "--------"

repo_file() {  # $1 = path in repo -> decoded content on stdout (empty if absent)
  gh api "repos/${REPO}/contents/$1" -q '.content' 2>/dev/null | base64 -d 2>/dev/null
}

probe_signed_releases() {
  local tag assets sigs
  tag="$(gh release list -R "$REPO" -L 1 --json tagName -q '.[0].tagName' 2>/dev/null)"
  if [ -z "$tag" ]; then CLASS="NEEDS-JUDGMENT"; EVID="no GitHub releases found"; return; fi
  assets="$(gh release view "$tag" -R "$REPO" --json assets -q '.assets[].name' 2>/dev/null)"
  sigs="$(printf '%s\n' "$assets" | grep -iE '\.(sig|asc|sigstore|intoto|pem|crt|cert)([.]jsonl?)?$|attestation|\.intoto\.' )"
  if [ -n "$sigs" ]; then
    CLASS="FIXED-BUT-LAGGING"
    EVID="$tag has signature/attestation assets ($(printf '%s' "$sigs" | tr '\n' ',' )); score lags until next scan"
  else
    CLASS="REAL-GAP"
    EVID="$tag ships only [$(printf '%s' "$assets" | tr '\n' ',' | sed 's/,$//')] -- no .sig/.sigstore/.intoto/attestation"
  fi
}

probe_ci_tests() {
  local rows nocheck
  rows="$(gh pr list -R "$REPO" --state merged -L "$PR_SAMPLE" \
          --json number,statusCheckRollup 2>/dev/null)"
  if [ -z "$rows" ]; then CLASS="NEEDS-JUDGMENT"; EVID="could not list merged PRs"; return; fi
  nocheck="$(printf '%s' "$rows" | jq -r '.[] | select((.statusCheckRollup|length)==0) | .number' | tr '\n' ',' | sed 's/,$//')"
  if [ -n "$nocheck" ]; then
    CLASS="REAL-GAP"
    EVID="merged PRs with zero status checks: #${nocheck} (of last ${PR_SAMPLE})"
  else
    CLASS="FIXED-BUT-LAGGING"
    EVID="all sampled merged PRs carry checks; score lags older commits"
  fi
}

probe_pinned() {
  local details dref line dockerfile flagged
  details="$(printf '%s' "$JSON" | jq -r '.checks[]|select(.name=="Pinned-Dependencies")|.details[]?' 2>/dev/null)"
  # find a flagged pip/pipCommand line referencing a local wheel we build ourselves
  dref="$(printf '%s' "$details" | grep -iE 'pipCommand not pinned|pip .*not pinned' | grep -oE '[A-Za-z0-9_./-]+:[0-9]+' | head -1)"
  if [ -n "$dref" ]; then
    dockerfile="${dref%%:*}"; line="${dref##*:}"
    flagged="$(repo_file "$dockerfile" | awk -v n="$line" 'NR==n{print; exit}')"
    case "$flagged" in
      *pip*install*.whl*|*pip*install*/tmp/*|*pip*install*"${NAME}"*)
        CLASS="FALSE-POSITIVE"
        EVID="$dref installs our OWN build wheel ('$(printf '%s' "$flagged" | sed 's/^ *//;s/ *$//')') -- a local artifact CANNOT be hash-pinned" ;;
      "")
        CLASS="NEEDS-JUDGMENT"
        EVID="flagged $dref but couldn't read the line; inspect by hand" ;;
      *)
        CLASS="REAL-GAP"
        EVID="unpinned dep at $dref: '$(printf '%s' "$flagged" | sed 's/^ *//;s/ *$//')' -- pin by hash/digest" ;;
    esac
  else
    CLASS="NEEDS-JUDGMENT"
    EVID="unpinned dep reported but not a pip/Dockerfile line; check GHA action SHAs / go/npm lockfiles"
  fi
}

probe_sast() {
  local ql on
  ql="$(repo_file '.github/workflows/codeql.yml')"
  [ -n "$ql" ] || ql="$(repo_file '.github/workflows/codeql-analysis.yml')"
  if [ -z "$ql" ]; then CLASS="NEEDS-JUDGMENT"; EVID="no codeql.yml found; check for other SAST (semgrep/bandit) triggers"; return; fi
  on="$(printf '%s' "$ql" | awk '/^on:/{f=1;next} /^[a-zA-Z]/{f=0} f' )"
  if printf '%s' "$on" | grep -qE '^[[:space:]]*push:'; then
    CLASS="FIXED-BUT-LAGGING"
    EVID="codeql.yml has a push: trigger -> scans every commit; 'not run on all commits' only reflects pre-fix history and recovers"
  else
    CLASS="REAL-GAP"
    EVID="codeql.yml triggers on [$(printf '%s' "$on" | grep -oE '^[[:space:]]*(pull_request|schedule|workflow_dispatch):' | tr -d ' :' | tr '\n' ',')] but NOT push: direct-to-main commits go unscanned"
  fi
}

reason_of() {  # $1 = check name -> API reason text
  printf '%s' "$JSON" | jq -r --arg n "$1" '.checks[]|select(.name==$n)|.reason'
}

emit() { printf '%-22s %-6s %-18s %s\n' "$1" "$2" "$3" "$4"; }

# iterate checks with score < 10, in a stable order
CHECKS="$(printf '%s' "$JSON" | jq -r '.checks[] | select(.score < 10 and .score != null) | "\(.name)\t\(.score)"')"
if [ -z "$CHECKS" ]; then
  echo "(every check is 10/10 -- nothing to verify)"
else
  printf '%s\n' "$CHECKS" | while IFS="$(printf '\t')" read -r cname cscore; do
    CLASS="NEEDS-JUDGMENT"; EVID="$(reason_of "$cname")"
    case "$cname" in
      Signed-Releases)      probe_signed_releases ;;
      CI-Tests)             probe_ci_tests ;;
      Pinned-Dependencies)  probe_pinned ;;
      SAST)                 probe_sast ;;
      Code-Review)          CLASS="REAL-GAP";   EVID="needs branch rule requiring approving review -- ${EVID}" ;;
      Branch-Protection)    CLASS="REAL-GAP";   EVID="needs branch protection rule -- ${EVID}" ;;
      Contributors)         CLASS="STRUCTURAL"; EVID="needs 2+ orgs via contributor profile Company field -- note, don't chase" ;;
      CII-Best-Practices)   CLASS="STRUCTURAL"; EVID="self-cert badge -- use breachsafe-openssf-badge skill, not this one (${EVID})" ;;
      Fuzzing)              CLASS="NEEDS-JUDGMENT"; EVID="no fuzzing detected -- decide if in-scope (${EVID})" ;;
      License|Security-Policy) CLASS="NEEDS-JUDGMENT"; EVID="${EVID}" ;;
    esac
    emit "$cname" "$cscore" "$CLASS" "$EVID"
  done
fi

echo "------------------------------------------------------------------"
echo "Legend:"
echo "  REAL-GAP          fix the repo; if a genuine regression, label the"
echo "                    issue 'verified-regression' with machine-checkable"
echo "                    close-criteria (not manual judgment)."
echo "  FALSE-POSITIVE    Scorecard heuristic limitation; document, do not 'fix'."
echo "  FIXED-BUT-LAGGING already remediated; score recovers on next scan."
echo "  STRUCTURAL        property of the project/org, not a code defect."
echo "  NEEDS-JUDGMENT    probe inconclusive; verify by hand, record evidence."
echo
echo "Reconcile: a LOCAL \`scorecard\` run under-scores Signed-Releases, CI-Tests"
echo "and SAST vs this hosted API. Treat local numbers as a floor, this as truth."
