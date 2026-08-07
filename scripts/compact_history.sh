#!/usr/bin/env bash
#
# compact_history.sh — ONE-TIME, DESTRUCTIVE git history rewrite.
#
# scripts/prune_telemetry.py deletes snapshot deltas from the *working tree*,
# but every one of those ~32k files is still recorded across thousands of past
# commits, which is what keeps .git at ~1.1 GB. This script purges the raw
# timestamped snapshot files (data/telemetry/*Z.json) from ALL history using
# git filter-repo, so the space is actually reclaimed.
#
# This rewrites every commit hash. It is NOT something to run regularly — it is
# a one-time cleanup. After it runs you MUST force-push and every other clone
# (the Pi especially) must re-sync, or the next auto-push will restore the old
# history.
#
# What is purged:   data/telemetry/<timestamp>Z.json   (raw snapshot deltas)
# What is kept:     GPX tracks, tracks_index.json, positions_index.json,
#                   instrument_log.json, signalk_latest.json, snapshots_index.json,
#                   and all code/config.
#
# Usage:
#   scripts/compact_history.sh            # dry-run: analyze + show projected size
#   scripts/compact_history.sh --run      # actually rewrite history
#
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

RUN=0
[[ "${1:-}" == "--run" ]] && RUN=1

echo "Repo: $REPO_ROOT"
echo "Current .git size: $(du -sh .git | cut -f1)"

# --- Ensure git-filter-repo is available -----------------------------------
if ! git filter-repo --version >/dev/null 2>&1; then
  echo "→ git-filter-repo not found; installing via uv tool..."
  if command -v uv >/dev/null 2>&1; then
    uv tool install git-filter-repo
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo "error: need 'uv' (or pip) to install git-filter-repo." >&2
    echo "       Try: pip install git-filter-repo" >&2
    exit 1
  fi
fi

# Match ONLY raw snapshot deltas: data/telemetry/<ISO-timestamp>Z.json
# (index/latest/GPX files never match this pattern, so they survive.)
SNAPSHOT_REGEX='^data/telemetry/[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Z\.json$'

# Count matching blobs across all history for a before/after sense of scale.
match_count=$(git log --all --pretty=format: --name-only --diff-filter=A \
  | grep -E '^data/telemetry/[0-9]{4}-[0-9]{2}-[0-9]{2}T.*Z\.json$' \
  | sort -u | wc -l | tr -d ' ')
echo "→ ~$match_count distinct snapshot delta paths recorded in history"

if [[ "$RUN" -eq 0 ]]; then
  cat <<EOF

DRY RUN — nothing changed.

To actually reclaim the space, run:

    scripts/compact_history.sh --run

Before you do:
  • Make sure the Pi's telemetry service is STOPPED (so it isn't mid-push).
  • This rewrites all commit hashes and cannot be undone without a backup.

A safety backup of .git will be written to ../<repo>.git.backup before rewriting.
EOF
  exit 0
fi

# --- Guardrails ------------------------------------------------------------
if [[ -n "$(git status --porcelain)" ]]; then
  echo "error: working tree is dirty. Commit or stash first." >&2
  exit 1
fi

BACKUP="${REPO_ROOT}.git.backup"
echo "→ Backing up .git to $BACKUP"
rm -rf "$BACKUP"
cp -a .git "$BACKUP"

# Remember the origin URL — filter-repo strips remotes by design (AGENTS.md gotcha).
ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"

echo "→ Rewriting history (purging snapshot deltas)..."
git filter-repo --force --invert-paths --path-regex "$SNAPSHOT_REGEX"

# Re-add origin (filter-repo removed it) and run gc to reclaim space.
if [[ -n "$ORIGIN_URL" ]]; then
  git remote add origin "$ORIGIN_URL" 2>/dev/null || git remote set-url origin "$ORIGIN_URL"
  echo "→ Restored origin: $ORIGIN_URL"
fi

echo "→ Expiring reflog and repacking..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo
echo "Done. New .git size: $(du -sh .git | cut -f1)"
echo "Backup of the old .git is at: $BACKUP"
cat <<EOF

NEXT STEPS (required — the rewrite is local only until you push):

  1. Force-push the rewritten history:
       TOKEN=\$(cat ~/.claude/remote/.session_ingress_token)
       git -c "http.extraHeader=Authorization: Bearer \$TOKEN" push origin main --force

  2. On the Pi and any other clone, re-sync to the new history:
       git fetch origin && git reset --hard origin/main

  3. Restart the Pi telemetry service.

  4. Once you've confirmed everything works, delete the backup:
       rm -rf "$BACKUP"
EOF
