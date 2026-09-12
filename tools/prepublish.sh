#!/usr/bin/env bash
# prepublish.sh - one pass/fail verdict before an irreversible publish.
#
# Flipping this repository public cannot be undone, and a term that reaches a
# public repo reaches its history with it. This runs every check that has a
# view on "is it safe to publish", in sequence, and fails if any of them do.
#
# Deliberately not a normalised finding model across four heterogeneous tools.
# Each tool prints its own output in its own shape; this decides the verdict.
# The requirement is one answer before an irreversible action, and sequencing
# satisfies it. A unified schema would be an evening spent buying nothing.
#
# Configuration, via environment so no local path is baked into a published file:
#   DISCLOSURE_BLOCKLIST  path to toast-blocklist.md
#   VOICE_SCRIPTS         directory holding pii_scan.py, check_ai_isms.py,
#                         check_em_dash.sh
#
# Usage:  tools/prepublish.sh [path]        (defaults to the repo root)
# Exit:   0 every check passed
#         1 at least one check failed - do not publish
#         2 could not run: a required tool or the blocklist is missing
#
# A missing tool is exit 2, never a silent pass. A gate that passes because it
# could not find its rules produces false confidence at exactly the moment
# false confidence is most expensive.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$REPO_ROOT}"

failures=()
ran=0

hr() { printf '\n%s\n' "------------------------------------------------------------"; }

require() {
  # require <description> <path>
  if [ ! -e "$2" ]; then
    echo "error: $1 not found: $2" >&2
    echo "       set \$DISCLOSURE_BLOCKLIST and \$VOICE_SCRIPTS, or install the tools." >&2
    exit 2
  fi
}

# --- configuration -----------------------------------------------------------

: "${DISCLOSURE_BLOCKLIST:=}"
: "${VOICE_SCRIPTS:=}"

if [ -z "$DISCLOSURE_BLOCKLIST" ]; then
  echo "error: \$DISCLOSURE_BLOCKLIST is not set (path to toast-blocklist.md)" >&2
  exit 2
fi
if [ -z "$VOICE_SCRIPTS" ]; then
  echo "error: \$VOICE_SCRIPTS is not set (directory holding the voice/PII scripts)" >&2
  exit 2
fi

require "blocklist" "$DISCLOSURE_BLOCKLIST"
require "pii_scan.py" "$VOICE_SCRIPTS/pii_scan.py"
require "check_ai_isms.py" "$VOICE_SCRIPTS/check_ai_isms.py"
require "check_em_dash.sh" "$VOICE_SCRIPTS/check_em_dash.sh"

# Explicit top-level paths rather than "." - check_em_dash.sh greps recursively
# and would otherwise walk .git, which is both slow and meaningless.
#
# Built with a read loop rather than mapfile: macOS ships bash 3.2, where
# mapfile does not exist. This script has to run on the machine it is written
# on, at 16:15, without anyone installing anything.
SCAN_PATHS=()
while IFS= read -r entry; do
  SCAN_PATHS[${#SCAN_PATHS[@]}]="$entry"
done < <(
  find "$TARGET" -mindepth 1 -maxdepth 1 \
    ! -name '.git' ! -name 'node_modules' ! -name '__pycache__' ! -name '.venv' \
    ! -name '.pytest_cache' \
    -print
)

# --- 1. disclosure: internal terms -------------------------------------------

# A check that could not run (exit 2) is kept apart from a check that ran and
# found something (exit 1). Folding the two together meant "we could not look"
# and "we looked and it was dirty" produced the same message, and a check that
# scanned nothing still counted towards "4/4 checks clean".
cannot_run=()

hr; echo "1/4 disclosure gate (internal terms)"
python3 "$REPO_ROOT/tools/disclosure_gate.py" "$TARGET" \
  --mode public --blocklist "$DISCLOSURE_BLOCKLIST"
rc=$?
if [ "$rc" -eq 2 ]; then cannot_run[${#cannot_run[@]}]="disclosure gate"
elif [ "$rc" -ne 0 ]; then failures[${#failures[@]}]="disclosure gate"; fi
ran=$((ran + 1))

# --- 2. PII -------------------------------------------------------------------

hr; echo "2/4 PII scan"
python3 "$VOICE_SCRIPTS/pii_scan.py" "$TARGET"
rc=$?
if [ "$rc" -eq 2 ]; then cannot_run[${#cannot_run[@]}]="PII scan"
elif [ "$rc" -ne 0 ]; then failures[${#failures[@]}]="PII scan"; fi
ran=$((ran + 1))

# --- 3. em dashes -------------------------------------------------------------

hr; echo "3/4 em dash check"
if [ ${#SCAN_PATHS[@]} -gt 0 ]; then
  bash "$VOICE_SCRIPTS/check_em_dash.sh" "${SCAN_PATHS[@]}"
  rc=$?
  if [ "$rc" -eq 2 ]; then cannot_run[${#cannot_run[@]}]="em dash check"
  elif [ "$rc" -ne 0 ]; then failures[${#failures[@]}]="em dash check"; fi
else
  # Nothing to scan is not a pass. It is the check failing to happen.
  echo "nothing to scan - target has no top-level entries"
  cannot_run[${#cannot_run[@]}]="em dash check (nothing to scan)"
fi
ran=$((ran + 1))

# --- 4. voice: AI-isms in prose ----------------------------------------------
# check_ai_isms.py takes one file at a time, and only prose is worth checking -
# the README and description are what a judge reads.

hr; echo "4/4 AI-ism check (markdown only)"
ai_ism_failed=0
ai_ism_docs=0
while IFS= read -r doc; do
  echo "  $doc"
  ai_ism_docs=$((ai_ism_docs + 1))
  python3 "$VOICE_SCRIPTS/check_ai_isms.py" "$doc" || ai_ism_failed=1
done < <(find "$TARGET" -name '*.md' \
  -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.pytest_cache/*' -print)
if [ "$ai_ism_docs" -eq 0 ]; then
  echo "  no markdown found"
  cannot_run[${#cannot_run[@]}]="AI-ism check (no markdown found)"
elif [ "$ai_ism_failed" -ne 0 ]; then
  failures[${#failures[@]}]="AI-ism check"
fi
ran=$((ran + 1))

# --- verdict ------------------------------------------------------------------

hr
if [ ${#cannot_run[@]} -ne 0 ]; then
  echo "CANNOT RUN - ${#cannot_run[@]} of $ran checks did not execute:"
  for c in "${cannot_run[@]}"; do echo "  - $c"; done
  if [ ${#failures[@]} -ne 0 ]; then
    echo "and ${#failures[@]} that did run reported findings:"
    for f in "${failures[@]}"; do echo "  - $f"; done
  fi
  echo ""
  echo "This is not a pass. A check that did not execute has told you nothing."
  exit 2
fi

if [ ${#failures[@]} -eq 0 ]; then
  echo "PASS - $ran/$ran checks ran and are clean. Safe to publish."
  exit 0
fi

echo "FAIL - ${#failures[@]} of $ran checks failed:"
for f in "${failures[@]}"; do echo "  - $f"; done
echo ""
echo "Do not publish until these are resolved."
exit 1
