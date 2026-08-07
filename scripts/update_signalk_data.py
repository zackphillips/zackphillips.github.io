import argparse
import json
import math
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import requests

from .utils import atomic_write_text, get_project_root, load_vessel_info

DEFAULT_OUTPUT_FILE = "./data/telemetry/signalk_latest.json"
# (connect timeout, read timeout) in seconds for every SignalK HTTP call.
FETCH_TIMEOUT = (5, 30)
# Wall-clock cap on network git operations (push/fetch/rebase), in seconds.
GIT_NETWORK_TIMEOUT = 120
STALE_MAX_AGE_MINUTES = 60
STALE_FILTER_KEYS = ("environment", "navigation", "entertainment")
POSITION_RETENTION_HOURS = 24  # how long positions stay in positions_index.json
POSITION_INDEX_FILE = "./data/telemetry/positions_index.json"
INSTRUMENT_LOG_FILE = "./data/telemetry/instrument_log.json"
INSTRUMENT_LOG_ENTRIES = 120  # ~5 hours at the default 2.5-min update cadence
TRACKS_DIR = "./data/telemetry/tracks"
TRACKS_INDEX_FILE = "./data/telemetry/tracks_index.json"

_NS_GPX = "http://www.topografix.com/GPX/1/1"
_NS_GPXTPX = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
ET.register_namespace("", _NS_GPX)
ET.register_namespace("gpxtpx", _NS_GPXTPX)
# Fallback privacy zone used when none are defined in info.yaml.
_FALLBACK_PRIVACY_ZONES: list[tuple[float, float, float]] = [
    (37.7802069, -122.3858040, 200.0),  # South Beach Harbor, San Francisco
]

# Active exclusion zones — populated from info.yaml by load_vessel_data().
# Each entry is (lat, lon, radius_metres).
PRIVACY_EXCLUSION_ZONES: list[tuple[float, float, float]] = list(
    _FALLBACK_PRIVACY_ZONES
)


def _load_privacy_zones(
    vessel_data: dict[str, Any],
) -> list[tuple[float, float, float]]:
    """Parse privacy_zones from vessel config; fall back to built-in default."""
    raw = vessel_data.get("privacy_zones", [])
    if not isinstance(raw, list) or not raw:
        return list(_FALLBACK_PRIVACY_ZONES)
    zones = []
    for z in raw:
        if not isinstance(z, dict):
            continue
        try:
            zones.append((float(z["lat"]), float(z["lon"]), float(z["radius_m"])))
        except (KeyError, TypeError, ValueError):
            continue
    return zones or list(_FALLBACK_PRIVACY_ZONES)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def _get_privacy_zone_center(lat: float, lon: float) -> tuple[float, float] | None:
    """Return the center of the first exclusion zone containing (lat, lon), or None."""
    for zone_lat, zone_lon, radius in PRIVACY_EXCLUSION_ZONES:
        if _haversine_m(lat, lon, zone_lat, zone_lon) <= radius:
            return zone_lat, zone_lon
    return None


def _is_position_private(lat: float, lon: float) -> bool:
    """Return True if the position falls inside any privacy exclusion zone."""
    return _get_privacy_zone_center(lat, lon) is not None


def load_vessel_data() -> dict:
    """Load vessel configuration from YAML or JSON file."""
    global PRIVACY_EXCLUSION_ZONES
    try:
        # Try to load config (will try YAML first, then JSON)
        vessel_data = load_vessel_info("data/vessel/info.yaml")
        if vessel_data:
            PRIVACY_EXCLUSION_ZONES = _load_privacy_zones(vessel_data)

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
        "--no-push",
        dest="no_push",
        action="store_true",
        default=os.getenv("NO_PUSH", "false").lower() == "true",
    )
    return parser.parse_args()


def fetch_blob(signalk_url: str) -> dict:
    # Timeouts are mandatory: without them a SignalK server that accepts the
    # connection but never answers (wedged process, half-open link over marina
    # wifi) blocks this call forever. The daemon then hangs without exiting, so
    # systemd's Restart=always never fires and the site silently freezes.
    response = requests.get(signalk_url, timeout=FETCH_TIMEOUT)
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
                node = {
                    k: v for k, v in node.items() if k not in {"value", "timestamp"}
                }

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


def _rebase_in_progress() -> bool:
    """True if a rebase is mid-flight (so `rebase --abort` is meaningful)."""
    git_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        or ".git"
    )
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def git_commit_and_push(no_push: bool, remote: str, branch: str) -> None:
    # Only stage the path if it exists. `git add` on a missing pathspec exits
    # non-zero, and with the retry handler now inside the daemon loop that
    # would turn one missing directory into an endless failing-cycle loop
    # rather than a single crash. The path is resolved against the working
    # directory because that is what git itself resolves it against
    # (systemd sets WorkingDirectory to the repo root).
    if Path("data/telemetry").exists():
        subprocess.run(["git", "add", "data/telemetry"], check=True)
    nothing_staged = (
        subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0
    )
    if nothing_staged:
        return
    subprocess.run(
        ["git", "commit", "-m", f"Auto update {datetime.now().isoformat()}"],
        check=True,
    )
    if no_push:
        return
    push_cmd = ["git", "push", remote, branch]
    try:
        # Network git operations need a timeout for the same reason the HTTP
        # fetch does: a stalled TCP connection makes them block indefinitely,
        # which hangs the daemon without ever exiting.
        subprocess.run(push_cmd, check=True, timeout=GIT_NETWORK_TIMEOUT)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # Push failed — fetch latest and rebase queued commits on top, then retry.
        # If that also fails (offline or genuine conflict), defer and continue;
        # the commits stay queued locally and go up on a later cycle.
        try:
            subprocess.run(
                ["git", "fetch", remote], check=True, timeout=GIT_NETWORK_TIMEOUT
            )
            subprocess.run(
                ["git", "rebase", "-X", "theirs", f"{remote}/{branch}"],
                check=True,
                timeout=GIT_NETWORK_TIMEOUT,
            )
            subprocess.run(push_cmd, check=True, timeout=GIT_NETWORK_TIMEOUT)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            # Only abort if a rebase is actually in progress — calling abort
            # unconditionally spews an error whenever it was the fetch that failed.
            if _rebase_in_progress():
                subprocess.run(["git", "rebase", "--abort"], check=False)
            print(f"Push deferred (offline or merge conflict): {e}")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _load_position_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("positions"), list):
        return [item for item in payload["positions"] if isinstance(item, dict)]
    return []


def _write_position_index(path: Path, entries: list[dict[str, Any]]) -> None:
    payload = {"positions": entries}
    atomic_write_text(path, json.dumps(payload, indent=2))


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


def _update_instrument_log(
    output_dir: Path, timestamp: datetime, blob: dict[str, Any]
) -> None:
    """Append a compact numeric reading to instrument_log.json and trim to the last N entries.

    The frontend reads this one file for every sparkline.
    Each entry is {timestamp, values: {signalk.path: float}} — only numeric leaf values.
    """
    log_path = output_dir / Path(INSTRUMENT_LOG_FILE).name
    try:
        existing: list[dict[str, Any]] = (
            json.loads(log_path.read_text(encoding="utf-8")).get("entries", [])
            if log_path.exists()
            else []
        )
        if not isinstance(existing, list):
            existing = []
    except (json.JSONDecodeError, OSError, AttributeError):
        existing = []

    numeric: dict[str, float] = {}
    _collect_numeric_values(blob, "", values=numeric)

    existing.append({"timestamp": timestamp.isoformat(), "values": numeric})
    trimmed = existing[-INSTRUMENT_LOG_ENTRIES:]
    atomic_write_text(log_path, json.dumps({"entries": trimmed}, separators=(",", ":")))


def _load_tracks_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        tracks = data.get("tracks", data) if isinstance(data, dict) else data
        return tracks if isinstance(tracks, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_tracks_index(path: Path, entries: list[dict[str, Any]]) -> None:
    atomic_write_text(path, json.dumps({"tracks": entries}, indent=2))


def _fmt_gpx_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ts


def _extract_pos_from_values(
    values: list[dict[str, Any]],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Return (lat, lon, speed_ms, course_rad) from a positions index values list."""
    lat = lon = speed = course = None
    for v in values:
        p = v.get("path", "")
        val = v.get("value")
        if p == "navigation.position" and isinstance(val, dict):
            lat = val.get("latitude")
            lon = val.get("longitude")
        elif p == "navigation.speedOverGround" and isinstance(val, (int, float)):
            speed = float(val)
        elif p == "navigation.courseOverGroundTrue" and isinstance(val, (int, float)):
            course = float(val)
    return lat, lon, speed, course


def _build_day_gpx(
    points: list[dict[str, Any]], date_str: str, vessel_name: str
) -> str:
    """Serialise one sailing day's points to a GPX XML string (no XML declaration)."""
    g = ET.Element(f"{{{_NS_GPX}}}gpx", {"version": "1.1", "creator": vessel_name})
    meta = ET.SubElement(g, f"{{{_NS_GPX}}}metadata")
    ET.SubElement(meta, f"{{{_NS_GPX}}}name").text = f"{vessel_name} \u2014 {date_str}"
    ET.SubElement(meta, f"{{{_NS_GPX}}}time").text = _fmt_gpx_time(
        points[0]["timestamp"]
    )
    trk = ET.SubElement(g, f"{{{_NS_GPX}}}trk")
    ET.SubElement(trk, f"{{{_NS_GPX}}}name").text = f"{vessel_name} \u2014 {date_str}"
    seg = ET.SubElement(trk, f"{{{_NS_GPX}}}trkseg")
    for p in points:
        trkpt = ET.SubElement(
            seg,
            f"{{{_NS_GPX}}}trkpt",
            {
                "lat": f"{p['latitude']:.6f}",
                "lon": f"{p['longitude']:.6f}",
            },
        )
        ET.SubElement(trkpt, f"{{{_NS_GPX}}}time").text = _fmt_gpx_time(p["timestamp"])
        speed = p.get("speed_ms")
        course = p.get("course_rad")
        if speed is not None or course is not None:
            ext = ET.SubElement(trkpt, f"{{{_NS_GPX}}}extensions")
            tpe = ET.SubElement(ext, f"{{{_NS_GPXTPX}}}TrackPointExtension")
            if speed is not None:
                ET.SubElement(tpe, f"{{{_NS_GPXTPX}}}speed").text = f"{speed:.3f}"
            if course is not None:
                ET.SubElement(
                    tpe, f"{{{_NS_GPXTPX}}}course"
                ).text = f"{math.degrees(course) % 360:.1f}"
    ET.indent(g, space="  ")
    return ET.tostring(g, encoding="unicode")


def _make_track_meta(date_str: str, points: list[dict[str, Any]]) -> dict[str, Any]:
    total_nm = 0.0
    max_spd_kts = 0.0
    for i, p in enumerate(points):
        spd = p.get("speed_ms")
        if spd is not None:
            max_spd_kts = max(max_spd_kts, spd * 1.94384)
        if i > 0:
            prev = points[i - 1]
            total_nm += (
                _haversine_m(
                    prev["latitude"], prev["longitude"], p["latitude"], p["longitude"]
                )
                / 1852.0
            )
    start_ts, end_ts = points[0]["timestamp"], points[-1]["timestamp"]
    try:
        start_dt = datetime.fromisoformat(start_ts).astimezone(UTC)
        end_dt = datetime.fromisoformat(end_ts).astimezone(UTC)
        duration_h = (end_dt - start_dt).total_seconds() / 3600
    except ValueError:
        duration_h = 0.0
    return {
        "date": date_str,
        "file": f"tracks/{date_str}.gpx",
        "start": _fmt_gpx_time(start_ts),
        "end": _fmt_gpx_time(end_ts),
        "duration_hours": round(duration_h, 2),
        "points": len(points),
        "max_speed_kts": round(max_spd_kts, 1),
        "distance_nm": round(total_nm, 2),
    }


def _update_track_files(
    all_entries: list[dict[str, Any]],
    tracks_dir: Path,
    tracks_index_path: Path,
    vessel_name: str,
) -> None:
    """Generate/update per-day GPX files from positions index entries.

    Past days are written once and never overwritten. Today's file is always
    refreshed so it accumulates points throughout the sailing day. Existing
    GPX files from earlier backfills are never deleted.
    """
    today_utc = datetime.now(UTC).strftime("%Y-%m-%d")

    by_day: dict[str, list[dict[str, Any]]] = {}
    for entry in all_entries:
        ts = entry.get("timestamp", "")
        lat, lon, speed, course = _extract_pos_from_values(entry.get("values", []))
        if lat is None or lon is None or not ts:
            continue
        # Must check EVERY zone, not just PRIVACY_EXCLUSION_ZONES[0]. Checking
        # only the first zone redacted the map track but wrote positions from
        # every other zone straight into the published GPX files.
        if _is_position_private(lat, lon):
            continue
        date_str = ts[:10]
        by_day.setdefault(date_str, []).append(
            {
                "timestamp": ts,
                "latitude": lat,
                "longitude": lon,
                "speed_ms": speed,
                "course_rad": course,
            }
        )

    if not by_day:
        return

    tracks_dir.mkdir(parents=True, exist_ok=True)
    existing = {t["date"]: t for t in _load_tracks_index(tracks_index_path)}

    for date_str, points in by_day.items():
        gpx_path = tracks_dir / f"{date_str}.gpx"
        if gpx_path.exists() and date_str != today_utc:
            existing.setdefault(date_str, _make_track_meta(date_str, points))
            continue
        gpx_xml = _build_day_gpx(points, date_str, vessel_name)
        atomic_write_text(
            gpx_path, f'<?xml version="1.0" encoding="UTF-8"?>\n{gpx_xml}\n'
        )
        existing[date_str] = _make_track_meta(date_str, points)

    _write_tracks_index(
        tracks_index_path, sorted(existing.values(), key=lambda t: t["date"])
    )


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
    # Check privacy: use zone center if inside an exclusion zone.
    zone_center = _get_privacy_zone_center(lat, lon)
    if zone_center is not None:
        print(
            f"Privacy: showing zone center ({zone_center[0]:.6f}, {zone_center[1]:.6f}) - vessel within exclusion zone"
        )

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Index entry: use zone center when inside a privacy zone ---
    display_lat, display_lon = zone_center if zone_center is not None else (lat, lon)
    index_values: list[dict[str, Any]] = [
        {
            "path": "navigation.position",
            "value": {"latitude": display_lat, "longitude": display_lon},
        },
    ]
    if zone_center is None:
        if speed_over_ground is not None:
            index_values.append(
                {"path": "navigation.speedOverGround", "value": speed_over_ground}
            )
        if course_over_ground_true is not None:
            index_values.append(
                {
                    "path": "navigation.courseOverGroundTrue",
                    "value": course_over_ground_true,
                }
            )

    index_entry: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
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

    try:
        vessel_name = load_vessel_data().get("vessel_data", {}).get("name", "Vessel")
    except Exception:
        vessel_name = "Vessel"
    _update_track_files(
        entries,
        output_dir / "tracks",
        output_dir / Path(TRACKS_INDEX_FILE).name,
        vessel_name,
    )

    _update_instrument_log(output_dir, timestamp, blob)


def run_update(
    branch: str,
    remote: str,
    signalk_url: str,
    output_path: str,
    use_https: bool,
    no_push: bool,
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
    blob = fetch_blob(signalk_url=signalk_url)

    # Replace position with zone center in the blob if inside a privacy zone.
    nav = blob.get("navigation") if isinstance(blob, dict) else None
    if isinstance(nav, dict):
        pos = nav.get("position")
        if isinstance(pos, dict):
            pos_val = pos.get("value", {})
            lat = pos_val.get("latitude")
            lon = pos_val.get("longitude")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                zone_center = _get_privacy_zone_center(lat, lon)
                if zone_center is not None:
                    print(
                        f"Privacy: replacing position with zone center in {output_file.name}"
                    )
                    pos_val["latitude"] = zone_center[0]
                    pos_val["longitude"] = zone_center[1]

    atomic_write_text(output_file, json.dumps(blob, indent=2))
    print(f"Wrote SignalK blob to {output_file}")
    update_position_cache(blob, output_file)
    git_commit_and_push(no_push=no_push, remote=remote, branch=branch)
    return output_file


def main() -> int:
    try:
        args = parse_args()
    except Exception as exc:  # noqa: BLE001 - startup failure is genuinely fatal
        print(f"Error: {exc}")
        return 1

    while True:
        # A failed cycle must not kill the daemon. Anything transient — SignalK
        # returning 502, a truncated JSON body, a held git lock — should skip
        # this round and retry on the next one. Exiting here would mean waiting
        # out systemd's RestartSec (300s) for every hiccup.
        try:
            run_update(
                branch=args.branch,
                remote=args.remote,
                signalk_url=args.signalk_url,
                output_path=args.output,
                use_https=args.use_https,
                no_push=args.no_push,
            )
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"Update cycle failed (will retry): {exc}")
            if args.interval == 0:
                return 1
        if args.interval == 0:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
