import argparse
import json
import math
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests

from .utils import get_project_root, load_vessel_info

DEFAULT_OUTPUT_FILE = "./data/telemetry/signalk_latest.json"
STALE_MAX_AGE_MINUTES = 60
STALE_FILTER_KEYS = ("environment", "navigation", "entertainment")
POSITION_RETENTION_HOURS = (24 * 24)  # 24 days
POSITION_INDEX_FILE = "./data/telemetry/positions_index.json"
# All snapshot files (timestamp + filename only, no position — safe to publish).
# Used by the frontend sparkline feature to load historical telemetry for all paths.
SNAPSHOT_INDEX_FILE = "./data/telemetry/snapshots_index.json"

# Top-level SignalK keys to include in compressed position archives.
# Excludes static design data, raw sensor hardware keys, and AIS bounding boxes.
SNAPSHOT_PATH_WHITELIST: frozenset[str] = frozenset({
    "navigation", "environment", "electrical", "tanks", "propulsion", "internet"
})

# Privacy exclusion zones: (lat, lon, radius_metres).
# Positions inside these circles are redacted from all stored/published data.
# All other telemetry for those samples is retained as normal.
PRIVACY_EXCLUSION_ZONES: list[tuple[float, float, float]] = [
    (37.7802069, -122.3858040, 200.0),  # South Beach Harbor, San Francisco
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _is_position_private(lat: float, lon: float) -> bool:
    """Return True if the position falls inside any privacy exclusion zone."""
    return any(
        _haversine_m(lat, lon, zone_lat, zone_lon) <= radius
        for zone_lat, zone_lon, radius in PRIVACY_EXCLUSION_ZONES
    )


def load_vessel_data() -> dict:
    """Load vessel configuration from YAML or JSON file."""
    try:
        # Try to load config (will try YAML first, then JSON)
        vessel_data = load_vessel_info("data/vessel/info.yaml")
        if vessel_data:

            # Construct SignalK URL from vessel data
            signalk = vessel_data.get("signalk", {})
            if signalk.get("host") and signalk.get("port"):
                protocol = signalk.get("protocol", "http")
                host = signalk["host"]
                port = signalk["port"]
                return {
                    "signalk_url": f"{protocol}://{host}:{port}/signalk/v1/api/vessels/self",
                    "vessel_data": vessel_data,
                }
    except Exception as e:
        print(f"Warning: Could not load vessel data: {e}")

    # Fallback to default
    return {
        "signalk_url": "http://localhost:3000/signalk/v1/api/vessels/self",
        "vessel_data": {},
    }


def parse_args() -> SimpleNamespace:
    # Load vessel data first to get default SignalK URL
    vessel_config = load_vessel_data()

    parser = argparse.ArgumentParser(description="Fetch SignalK data and commit to git")
    parser.add_argument("--branch", default=os.getenv("GIT_BRANCH", "main"))
    parser.add_argument("--remote", default=os.getenv("GIT_REMOTE", "origin"))
    parser.add_argument(
        "--signalk-url",
        dest="signalk_url",
        default=os.getenv("SIGNALK_URL", vessel_config["signalk_url"]),
        help="SignalK API URL (defaults to vessel config or http://localhost:3000/signalk/v1/api/vessels/self)",
    )
    parser.add_argument(
        "--output", dest="output", default=os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)
    )
    parser.add_argument(
        "--interval",
        dest="interval",
        type=int,
        default=int(os.getenv("INTERVAL", "0")),
        help="Update interval in seconds (0 for one-shot)",
    )
    parser.add_argument(
        "--use-https",
        dest="use_https",
        action="store_true",
        default=os.getenv("USE_HTTPS", "false").lower() == "true",
        help="Use HTTPS instead of HTTP for SignalK connection",
    )
    parser.add_argument(
        "--no-reset",
        dest="no_reset",
        action="store_true",
        default=os.getenv("NO_RESET", "false").lower() == "true",
    )
    parser.add_argument(
        "--no-push",
        dest="no_push",
        action="store_true",
        default=os.getenv("NO_PUSH", "false").lower() == "true",
    )
    parser.add_argument(
        "--amend",
        dest="amend",
        action="store_true",
        default=os.getenv("GIT_AMEND", "true").lower() == "true",
    )
    parser.add_argument(
        "--force-push",
        dest="force_push",
        action="store_true",
        default=os.getenv("GIT_FORCE_PUSH", "true").lower() == "true",
    )
    return parser.parse_args()


def fetch_blob(signalk_url: str) -> dict:
    response = requests.get(signalk_url)
    response.raise_for_status()
    return response.json()


def filter_stale_data(
    blob: dict[str, Any],
    *,
    max_age_minutes: int = STALE_MAX_AGE_MINUTES,
    target_keys: tuple[str, ...] = STALE_FILTER_KEYS,
    reference_time: datetime | None = None,
) -> dict[str, Any]:
    """
    Remove stale measurements from selected top-level sections so the UI shows them as unavailable.
    """

    if not isinstance(blob, dict) or max_age_minutes <= 0:
        return blob

    cutoff = (reference_time or datetime.now(UTC)) - timedelta(minutes=max_age_minutes)

    def parse_timestamp(ts: Any) -> datetime | None:
        if not isinstance(ts, str):
            return None
        normalized = ts.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def prune(node: Any) -> Any:
        if isinstance(node, dict):
            timestamp = node.get("timestamp")
            ts = parse_timestamp(timestamp)
            if ts is not None and ts < cutoff:
                node = {k: v for k, v in node.items() if k not in {"value", "timestamp"}}

            cleaned: dict[str, Any] = {}
            for key, value in node.items():
                pruned_value = prune(value)
                if pruned_value is not None:
                    cleaned[key] = pruned_value

            if not cleaned:
                return None
            return cleaned

        if isinstance(node, list):
            cleaned_list = []
            for item in node:
                pruned_item = prune(item)
                if pruned_item is not None:
                    cleaned_list.append(pruned_item)
            return cleaned_list or None

        return node

    for key in target_keys:
        if key in blob:
            pruned = prune(blob[key])
            if pruned is None:
                blob.pop(key)
            else:
                blob[key] = pruned
    return blob


def git_reset(remote: str, branch: str) -> None:
    subprocess.run(["git", "fetch", "--all"], check=True)
    subprocess.run(["git", "reset", "--hard", f"{remote}/{branch}"], check=True)


def git_commit_and_push(
    file_path: Path, amend: bool, no_push: bool, force_push: bool
) -> None:
    subprocess.run(["git", "add", "data/telemetry"], check=True)
    commit_cmd = ["git", "commit", "-m", f"Auto update {datetime.now().isoformat()}"]
    if amend:
        commit_cmd.insert(2, "--amend")
    # allow empty to avoid failures when content is unchanged
    commit_cmd.insert(2, "--allow-empty")
    subprocess.run(commit_cmd, check=True)
    if not no_push:
        push_cmd = ["git", "push"]
        if force_push:
            push_cmd.append("--force")
        subprocess.run(push_cmd, check=True)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_position_filename(timestamp: datetime) -> str:
    return f"{timestamp.strftime('%Y-%m-%dT%H-%M-%S.%f')}Z.json"


def _parse_position_filename(name: str) -> datetime | None:
    if not name.endswith("Z.json"):
        return None
    stem = name[:-5]
    try:
        return datetime.strptime(stem, "%Y-%m-%dT%H-%M-%S.%f")
    except ValueError:
        return None


def _load_position_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("positions"), list):
        return [item for item in payload["positions"] if isinstance(item, dict)]
    return []


def _write_position_index(path: Path, entries: list[dict[str, Any]]) -> None:
    payload = {"positions": entries}
    path.write_text(json.dumps(payload, indent=2))


def _collect_signalk_values(
    node: Any,
    path: str,
    *,
    values: list[dict[str, Any]],
    whitelist: frozenset[str] | None = None,
) -> None:
    """Collect SignalK paths and values as a list of {path, value} dicts.

    At the top level (path="") the optional *whitelist* restricts which
    top-level keys are traversed.  Object-valued nodes whose every leaf is
    numeric (e.g. navigation.position) are emitted as a single object entry
    rather than being flattened into individual scalar entries.
    """
    if not isinstance(node, dict):
        return

    # Top-level: optionally restrict to whitelisted keys only.
    if not path:
        keys = (k for k in node if not whitelist or k in whitelist)
        for key in keys:
            child = node[key]
            if isinstance(child, dict):
                _collect_signalk_values(child, key, values=values)
        return

    value = node.get("value")
    if isinstance(value, (int, float)):
        values.append({"path": path, "value": float(value)})
    elif isinstance(value, dict):
        # If every leaf is numeric, emit as a compact object (e.g. position).
        numeric_leaves = {k: v for k, v in value.items() if isinstance(v, (int, float))}
        if numeric_leaves and len(numeric_leaves) == len(value):
            values.append({"path": path, "value": numeric_leaves})
        else:
            for k, v in value.items():
                if isinstance(v, (int, float)):
                    values.append({"path": f"{path}.{k}", "value": float(v)})

    for key, child in node.items():
        if key in {"value", "meta", "values", "pgn", "$source", "source"}:
            continue
        if isinstance(child, dict):
            _collect_signalk_values(child, f"{path}.{key}", values=values)


def _collect_numeric_values(
    node: Any,
    path: str,
    *,
    values: dict[str, float],
) -> None:
    if not isinstance(node, dict):
        return

    value = node.get("value")
    if isinstance(value, (int, float)):
        if path:
            values[path] = float(value)
    elif isinstance(value, dict):
        for key, subvalue in value.items():
            if isinstance(subvalue, (int, float)):
                subpath = f"{path}.{key}" if path else key
                values[subpath] = float(subvalue)

    for key, child in node.items():
        if key in {"value", "meta", "values", "pgn", "$source", "source"}:
            continue
        if isinstance(child, dict):
            child_path = f"{path}.{key}" if path else key
            _collect_numeric_values(child, child_path, values=values)


def _update_snapshot_index(output_dir: Path, filename: str, timestamp: datetime) -> None:
    """Add a new entry to snapshots_index.json and prune expired entries.

    The snapshot index contains {timestamp, file} pairs for every saved
    telemetry snapshot — including privacy-redacted ones — so the frontend
    sparkline feature can load historical data for all SignalK paths.
    """
    index_path = output_dir / Path(SNAPSHOT_INDEX_FILE).name
    try:
        existing = json.loads(index_path.read_text()) if index_path.exists() else []
        if not isinstance(existing, list):
            existing = []
    except json.JSONDecodeError:
        existing = []

    cutoff = datetime.now(UTC) - timedelta(hours=POSITION_RETENTION_HOURS)
    existing = [
        e for e in existing
        if isinstance(e, dict) and (_parse_timestamp(e.get("timestamp")) or datetime.min.replace(tzinfo=UTC)) >= cutoff
    ]
    existing.append({"timestamp": timestamp.isoformat(), "file": filename})
    existing.sort(key=lambda e: e.get("timestamp") or "")
    index_path.write_text(json.dumps(existing, indent=2))


def _prune_old_position_files(output_dir: Path) -> None:
    """Delete timestamped position snapshot files older than the retention window."""
    cutoff = datetime.now(UTC) - timedelta(hours=POSITION_RETENTION_HOURS)
    for file_path in output_dir.iterdir():
        if not file_path.is_file():
            continue
        ts = _parse_position_filename(file_path.name)
        if ts is None:
            continue
        if ts.replace(tzinfo=UTC) < cutoff:
            file_path.unlink(missing_ok=True)


def update_position_cache(blob: dict[str, Any], output_path: Path) -> None:
    navigation = blob.get("navigation", {}) if isinstance(blob, dict) else {}
    position = navigation.get("position") if isinstance(navigation, dict) else None
    if not isinstance(position, dict):
        return
    value = position.get("value")
    if not isinstance(value, dict):
        return
    lat = value.get("latitude")
    lon = value.get("longitude")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return

    timestamp = _parse_timestamp(position.get("timestamp")) or datetime.now(UTC)
    speed_over_ground = None
    course_over_ground_true = None
    if isinstance(navigation, dict):
        speed = navigation.get("speedOverGround")
        if isinstance(speed, dict):
            speed_value = speed.get("value")
            if isinstance(speed_value, (int, float)):
                speed_over_ground = speed_value
        heading = navigation.get("headingTrue")
        if isinstance(heading, dict):
            heading_value = heading.get("value")
            if isinstance(heading_value, (int, float)):
                course_over_ground_true = heading_value
    # Check privacy: redact position if inside an exclusion zone.
    position_private = _is_position_private(lat, lon)
    if position_private:
        print(f"Privacy: position redacted — within exclusion zone ({lat:.6f}, {lon:.6f})")

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _format_position_filename(timestamp)
    position_file = output_dir / filename

    # --- Snapshot file: full SignalK delta format, whitelisted paths only ---
    signalk_values: list[dict[str, Any]] = []
    _collect_signalk_values(blob, "", values=signalk_values, whitelist=SNAPSHOT_PATH_WHITELIST)
    # Always strip any auto-collected navigation.position (may be redacted).
    signalk_values = [v for v in signalk_values if v["path"] != "navigation.position"]
    if not position_private:
        # Prepend position only when it is safe to store.
        pos_entry = {"path": "navigation.position", "value": {"latitude": lat, "longitude": lon}}
        signalk_values.insert(0, pos_entry)

    snapshot_payload = {
        "context": "vessels.self",
        "updates": [{
            "timestamp": timestamp.isoformat(),
            "values": signalk_values,
        }],
    }
    position_file.write_text(json.dumps(snapshot_payload, indent=2))

    # Always update the all-snapshots index (no position data — privacy safe).
    _update_snapshot_index(output_dir, filename, timestamp)

    # --- Index entry: only written when position is not private ---
    if position_private:
        # Update the index (pruning old entries) without adding a new one.
        index_path = output_dir / Path(POSITION_INDEX_FILE).name
        entries = _load_position_index(index_path)
        cutoff = datetime.now(UTC) - timedelta(hours=POSITION_RETENTION_HOURS)
        entries = [e for e in entries if (_parse_timestamp(e.get("timestamp")) or datetime.min.replace(tzinfo=UTC)) >= cutoff]
        _write_position_index(index_path, entries)
        _prune_old_position_files(output_dir)
        return

    index_values: list[dict[str, Any]] = [
        {"path": "navigation.position", "value": {"latitude": lat, "longitude": lon}},
    ]
    if speed_over_ground is not None:
        index_values.append({"path": "navigation.speedOverGround", "value": speed_over_ground})
    if course_over_ground_true is not None:
        index_values.append({"path": "navigation.courseOverGroundTrue", "value": course_over_ground_true})

    index_entry: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "file": filename,
        "values": index_values,
    }

    index_path = output_dir / Path(POSITION_INDEX_FILE).name
    entries = _load_position_index(index_path)
    cutoff = datetime.now(UTC) - timedelta(hours=POSITION_RETENTION_HOURS)

    def keep_entry(entry: dict[str, Any]) -> bool:
        entry_ts = _parse_timestamp(entry.get("timestamp"))
        return entry_ts is not None and entry_ts >= cutoff

    entries = [entry for entry in entries if keep_entry(entry)]
    entries.append(index_entry)
    entries.sort(key=lambda item: item.get("timestamp") or "")
    _write_position_index(index_path, entries)

    _prune_old_position_files(output_dir)


def run_update(
    branch: str,
    remote: str,
    signalk_url: str,
    output_path: str,
    use_https: bool,
    no_reset: bool,
    amend: bool,
    no_push: bool,
    force_push: bool,
) -> Path:
    # Modify SignalK URL if use_https is specified
    if use_https and signalk_url.startswith("http://"):
        signalk_url = signalk_url.replace("http://", "https://", 1)

    # Resolve output path against project root if not absolute
    output_file = Path(output_path)
    if not output_file.is_absolute():
        output_file = get_project_root() / output_file
    output_file = output_file.resolve()

    # Ensure destination directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if not no_reset:
        git_reset(remote=remote, branch=branch)
    blob = fetch_blob(signalk_url=signalk_url)

    # Redact navigation.position from the live blob if inside a privacy zone,
    # so the position is never committed to the public repository.
    nav = blob.get("navigation") if isinstance(blob, dict) else None
    if isinstance(nav, dict):
        pos = nav.get("position")
        if isinstance(pos, dict):
            pos_val = pos.get("value", {})
            lat = pos_val.get("latitude")
            lon = pos_val.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                if _is_position_private(lat, lon):
                    print(f"Privacy: position redacted from {output_file.name} — within exclusion zone")
                    nav.pop("position", None)

    output_file.write_text(json.dumps(blob, indent=2))
    print(f"Wrote SignalK blob to {output_file}")
    update_position_cache(blob, output_file)
    git_commit_and_push(
        file_path=output_file, amend=amend, no_push=no_push, force_push=force_push
    )
    return output_file


def main() -> int:
    try:
        args = parse_args()
        while True:
            run_update(
                branch=args.branch,
                remote=args.remote,
                signalk_url=args.signalk_url,
                output_path=args.output,
                use_https=args.use_https,
                no_reset=args.no_reset,
                amend=args.amend,
                no_push=args.no_push,
                force_push=args.force_push,
            )
            if args.interval == 0:
                break
            time.sleep(args.interval)
        return 0
    except Exception as exc:  # noqa: BLE001 - top-level safety
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
