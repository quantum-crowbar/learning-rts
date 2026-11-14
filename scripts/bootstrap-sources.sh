#!/usr/bin/env bash
# Clone source repos into code/ at pinned revisions and apply local patches.
# Idempotent: safe to re-run. Never touches code/learning-rts history.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=../sources/pins.env
source sources/pins.env
mkdir -p code

# --- OLD: deep-rts (pinned upstream + patches) -------------------------------
DR=code/deep-rts
if [ ! -d "$DR/.git" ]; then
  git clone --quiet "$DEEP_RTS_URL" "$DR"
fi
git -C "$DR" fetch --quiet origin
git -C "$DR" checkout --quiet "$DEEP_RTS_SHA"

for p in patches/deep-rts/*.patch; do
  [ -e "$p" ] || continue
  abs="$ROOT/$p"
  if git -C "$DR" apply --check "$abs" 2>/dev/null; then
    git -C "$DR" apply "$abs"
    echo "applied  $p"
  elif git -C "$DR" apply --check --reverse "$abs" 2>/dev/null; then
    echo "already  $p"
  else
    echo "ERROR: $p neither applies nor is already applied (is $DR modified?)" >&2
    exit 1
  fi
done

# --- NEW: learning-rts (own repo; remote not configured yet) ------------------
NR=code/learning-rts
if [ ! -d "$NR/.git" ]; then
  echo "NOTE: $NR missing. If it has a remote, clone it there; otherwise create it with 'git init $NR'." >&2
fi

echo "deep-rts @ $(git -C "$DR" rev-parse --short HEAD) (+patches)"
