import argparse
import json
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
POSITION_RETENTION_HOURS = 24
POSITION_INDEX_FILE = "./data/telemetry/positions_index.json"
SERIES_FILE = "./data/telemetry/signalk_series.ndjson"


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
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _format_position_filename(timestamp)
    position_file = output_dir / filename
    position_payload = {"timestamp": timestamp.isoformat(), "latitude": lat, "longitude": lon}
    if speed_over_ground is not None:
        position_payload["speedOverGround"] = speed_over_ground
    if course_over_ground_true is not None:
        position_payload["courseOverGroundTrue"] = course_over_ground_true
    position_file.write_text(json.dumps(position_payload, indent=2))

    index_path = output_dir / Path(POSITION_INDEX_FILE).name
    entries = _load_position_index(index_path)
    cutoff = datetime.now(UTC) - timedelta(hours=POSITION_RETENTION_HOURS)

    def keep_entry(entry: dict[str, Any]) -> bool:
        entry_ts = _parse_timestamp(entry.get("timestamp"))
        return entry_ts is not None and entry_ts >= cutoff

    entries = [entry for entry in entries if keep_entry(entry)]
    entries.append(position_payload)
    entries.sort(key=lambda item: item.get("timestamp") or "")
    _write_position_index(index_path, entries)

    for file_path in output_dir.iterdir():
        if not file_path.is_file():
            continue
        ts = _parse_position_filename(file_path.name)
        if ts is None:
            continue
        if ts.replace(tzinfo=UTC) < cutoff:
            file_path.unlink(missing_ok=True)


def _collect_series_entries(
    node: Any,
    path: str,
    *,
    fallback_timestamp: str,
    entries: list[dict[str, Any]],
) -> None:
    if not isinstance(node, dict):
        return

    node_timestamp = node.get("timestamp") if isinstance(node.get("timestamp"), str) else None
    timestamp = node_timestamp or fallback_timestamp
    value = node.get("value")
    if isinstance(value, (int, float)):
        entries.append({"path": path, "timestamp": timestamp, "value": value})
    elif isinstance(value, dict):
        for key, subvalue in value.items():
            if isinstance(subvalue, (int, float)):
                subpath = f"{path}.{key}" if path else key
                entries.append({"path": subpath, "timestamp": timestamp, "value": subvalue})

    for key, child in node.items():
        if key in {"value", "meta", "values", "pgn", "$source", "source"}:
            continue
        if isinstance(child, dict):
            child_path = f"{path}.{key}" if path else key
            _collect_series_entries(
                child, child_path, fallback_timestamp=fallback_timestamp, entries=entries
            )


def update_series_cache(blob: dict[str, Any], output_path: Path) -> None:
    if not isinstance(blob, dict):
        return
    timestamp = None
    if isinstance(blob.get("timestamp"), str):
        timestamp = blob["timestamp"]
    if not timestamp:
        timestamp = datetime.now(UTC).isoformat()

    entries: list[dict[str, Any]] = []
    _collect_series_entries(blob, "", fallback_timestamp=timestamp, entries=entries)
    if not entries:
        return

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    series_path = output_dir / Path(SERIES_FILE).name
    with series_path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


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
    output_file.write_text(json.dumps(blob, indent=2))
    print(f"Wrote SignalK blob to {output_file}")
    update_position_cache(blob, output_file)
    update_series_cache(blob, output_file)
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
