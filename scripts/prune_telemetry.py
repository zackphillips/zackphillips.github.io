"""Prune redundant telemetry snapshot deltas from the working tree.

The Pi daemon writes one timestamped snapshot file per update cycle
(``data/telemetry/2026-...Z.json``). These raw "delta" files are only ever
used as *source material* for the per-day GPX tracks — the frontend never
fetches them directly (see ``SNAPSHOT_INDEX_URL`` in constants.js, marked
"legacy"). Once each sailing day has a GPX track, the raw snapshots are dead
weight: tens of thousands of files, hundreds of MB, committed forever.

This script makes cleanup safe and repeatable:

  1. Run backfill_tracks so every sailing day has a GPX file
     (backfill never overwrites existing tracks — safe to re-run).
  2. Delete timestamped snapshot files older than ``--keep-hours``
     (default 0 = delete all; the Pi regenerates the rolling live files).
  3. Prune stale entries from the legacy snapshots_index.json.
  4. Optionally stage/commit the deletions.

Protected files are NEVER touched: signalk_latest.json, positions_index.json,
instrument_log.json, snapshots_index.json, tracks_index.json, tracks/*.gpx,
and everything under data/vessel/.

Usage:
    uv run python -m scripts.prune_telemetry            # backfill + delete all, stage
    uv run python -m scripts.prune_telemetry --dry-run  # show what would happen
    uv run python -m scripts.prune_telemetry --keep-hours 24 --commit
    uv run python -m scripts.prune_telemetry --no-backfill
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .backfill_tracks import main as backfill_main
from .utils import get_project_root

TELEMETRY_DIR = Path("data/telemetry")
SNAPSHOT_INDEX_FILE = TELEMETRY_DIR / "snapshots_index.json"

# Files in data/telemetry/ that are managed state, not raw snapshot deltas.
PROTECTED_NAMES = frozenset({
    "signalk_latest.json",
    "positions_index.json",
    "instrument_log.json",
    "snapshots_index.json",
    "tracks_index.json",
})


def _parse_snapshot_filename(name: str) -> datetime | None:
    """Return the UTC timestamp encoded in a snapshot filename, or None.

    Snapshot files look like ``2026-04-22T00-16-53.109000Z.json``. Anything
    that doesn't match this exact shape (index files, GPX, etc.) returns None
    and is therefore left untouched.
    """
    if not name.endswith("Z.json"):
        return None
    if name in PROTECTED_NAMES:
        return None
    stem = name[:-6]  # strip "Z.json"
    try:
        return datetime.strptime(stem, "%Y-%m-%dT%H-%M-%S.%f").replace(tzinfo=UTC)
    except ValueError:
        return None


def _find_snapshots(telemetry_dir: Path, cutoff: datetime) -> list[Path]:
    """All timestamped snapshot files strictly older than *cutoff*."""
    victims = []
    for path in telemetry_dir.iterdir():
        if not path.is_file():
            continue
        ts = _parse_snapshot_filename(path.name)
        if ts is not None and ts < cutoff:
            victims.append(path)
    return sorted(victims)


def _prune_snapshot_index(index_path: Path, dry_run: bool) -> int:
    """Drop entries from snapshots_index.json whose files no longer exist."""
    if not index_path.exists():
        return 0
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0

    entries = payload.get("snapshots", payload) if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        return 0

    telemetry_dir = index_path.parent
    kept = [
        e for e in entries
        if isinstance(e, dict) and (telemetry_dir / str(e.get("file", ""))).exists()
    ]
    removed = len(entries) - len(kept)
    if removed and not dry_run:
        if isinstance(payload, dict) and "snapshots" in payload:
            payload["snapshots"] = kept
            index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            index_path.write_text(json.dumps(kept, indent=2), encoding="utf-8")
    return removed


def _git(args: list[str], root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-hours", type=float, default=0.0,
        help="Keep snapshots newer than this many hours (default 0 = delete all).",
    )
    parser.add_argument(
        "--no-backfill", action="store_true",
        help="Skip the GPX backfill step (only do this if tracks are already current).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be deleted without changing anything.",
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="git commit the deletions (does not push; the Pi/you pushes).",
    )
    args = parser.parse_args(argv)

    root = get_project_root()
    telemetry_dir = root / TELEMETRY_DIR
    if not telemetry_dir.is_dir():
        print(f"error: {telemetry_dir} not found", file=sys.stderr)
        return 1

    # 1. Backfill GPX first so no sailing day's track is lost when we delete
    #    its source snapshots. Backfill never overwrites existing GPX.
    if not args.no_backfill and not args.dry_run:
        print("→ Backfilling GPX tracks from snapshots...")
        rc = backfill_main()
        if rc != 0:
            print("error: backfill failed; aborting before any deletion",
                  file=sys.stderr)
            return rc
    elif args.dry_run and not args.no_backfill:
        print("(dry-run) would backfill GPX tracks before deleting snapshots")

    # 2. Delete old snapshot deltas.
    cutoff = datetime.now(UTC) - timedelta(hours=args.keep_hours)
    victims = _find_snapshots(telemetry_dir, cutoff)
    total_bytes = sum(p.stat().st_size for p in victims)

    label = "would delete" if args.dry_run else "deleting"
    print(f"→ {label} {len(victims)} snapshot files "
          f"({total_bytes / 1e6:.1f} MB), keeping last {args.keep_hours:g}h")

    if not args.dry_run:
        for path in victims:
            path.unlink(missing_ok=True)
        stale = _prune_snapshot_index(root / SNAPSHOT_INDEX_FILE, args.dry_run)
        if stale:
            print(f"→ pruned {stale} stale entries from snapshots_index.json")
    else:
        stale = _prune_snapshot_index(root / SNAPSHOT_INDEX_FILE, dry_run=True)
        if stale:
            print(f"(dry-run) would prune {stale} stale snapshots_index.json entries")

    if not victims:
        print("Nothing to prune. Working tree already clean.")
        return 0

    if args.dry_run:
        print("\nDry run complete — no files changed.")
        return 0

    # 3. Stage the deletions so the Pi's next `git add data/telemetry` commit
    #    (or an explicit --commit here) records them.
    _git(["add", "data/telemetry"], root)

    if args.commit:
        msg = f"Prune {len(victims)} telemetry snapshots ({total_bytes / 1e6:.1f} MB)"
        try:
            _git(["commit", "-m", msg], root)
            print(f"→ committed: {msg}")
            print("  (not pushed — the Pi will carry it up, or push manually)")
        except subprocess.CalledProcessError as exc:
            print(f"warning: commit failed: {exc.stderr.strip()}", file=sys.stderr)
    else:
        print("→ deletions staged (not committed). Re-run with --commit to commit,")
        print("  or let the Pi's next telemetry commit pick them up.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
