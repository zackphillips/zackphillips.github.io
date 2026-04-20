"""Backfill per-day GPX track files from all telemetry position snapshots.

Reads every timestamped JSON snapshot in data/telemetry/, filters out positions
inside the South Beach Harbor privacy zone, and produces:

  data/telemetry/tracks/YYYY-MM-DD.gpx   — one GPX per sailing day (UTC date)
  data/telemetry/tracks_index.json        — index of all sailing days with metadata

Existing GPX files are never overwritten so the script is safe to re-run;
it only fills in missing days and appends new metadata entries.

Run from the repo root:
    uv run python -m scripts.backfill_tracks
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .utils import get_project_root, load_vessel_info

TELEMETRY_DIR = Path("data/telemetry")
TRACKS_DIR = TELEMETRY_DIR / "tracks"
TRACKS_INDEX_FILE = TELEMETRY_DIR / "tracks_index.json"

HARBOR_LAT = 37.7802069
HARBOR_LON = -122.3858040
HARBOR_RADIUS_M = 200.0

_NS_GPX = "http://www.topografix.com/GPX/1/1"
_NS_GPXTPX = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"
ET.register_namespace("", _NS_GPX)
ET.register_namespace("gpxtpx", _NS_GPXTPX)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


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


def _parse_snapshot(path: Path) -> dict[str, Any] | None:
    """Extract (timestamp, lat, lon, speed_ms, course_rad) from a SignalK snapshot file."""
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None

    updates = data.get("updates", [])
    if not updates:
        return None
    update = updates[0]
    ts = update.get("timestamp")
    if not ts:
        return None

    lat = lon = speed = course = None
    for v in update.get("values", []):
        p = v.get("path", "")
        val = v.get("value")
        if p == "navigation.position" and isinstance(val, dict):
            lat = val.get("latitude")
            lon = val.get("longitude")
        elif p == "navigation.speedOverGround" and isinstance(val, (int, float)):
            speed = float(val)
        elif p == "navigation.courseOverGroundTrue" and isinstance(val, (int, float)):
            course = float(val)

    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None

    return {"timestamp": ts, "latitude": float(lat), "longitude": float(lon),
            "speed_ms": speed, "course_rad": course}


def _build_day_gpx(points: list[dict[str, Any]], date_str: str, vessel_name: str) -> str:
    g = ET.Element(f"{{{_NS_GPX}}}gpx", {"version": "1.1", "creator": vessel_name})
    meta = ET.SubElement(g, f"{{{_NS_GPX}}}metadata")
    ET.SubElement(meta, f"{{{_NS_GPX}}}name").text = f"{vessel_name} \u2014 {date_str}"
    ET.SubElement(meta, f"{{{_NS_GPX}}}time").text = _fmt_gpx_time(points[0]["timestamp"])
    trk = ET.SubElement(g, f"{{{_NS_GPX}}}trk")
    ET.SubElement(trk, f"{{{_NS_GPX}}}name").text = f"{vessel_name} \u2014 {date_str}"
    seg = ET.SubElement(trk, f"{{{_NS_GPX}}}trkseg")
    for p in points:
        trkpt = ET.SubElement(seg, f"{{{_NS_GPX}}}trkpt", {
            "lat": f"{p['latitude']:.6f}",
            "lon": f"{p['longitude']:.6f}",
        })
        ET.SubElement(trkpt, f"{{{_NS_GPX}}}time").text = _fmt_gpx_time(p["timestamp"])
        speed, course = p.get("speed_ms"), p.get("course_rad")
        if speed is not None or course is not None:
            ext = ET.SubElement(trkpt, f"{{{_NS_GPX}}}extensions")
            tpe = ET.SubElement(ext, f"{{{_NS_GPXTPX}}}TrackPointExtension")
            if speed is not None:
                ET.SubElement(tpe, f"{{{_NS_GPXTPX}}}speed").text = f"{speed:.3f}"
            if course is not None:
                ET.SubElement(tpe, f"{{{_NS_GPXTPX}}}course").text = f"{math.degrees(course) % 360:.1f}"
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
            total_nm += _haversine_m(
                prev["latitude"], prev["longitude"], p["latitude"], p["longitude"]
            ) / 1852.0
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


def _load_tracks_index(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        tracks = data.get("tracks", data) if isinstance(data, dict) else data
        return {t["date"]: t for t in tracks if isinstance(t, dict) and "date" in t}
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> int:
    root = get_project_root()
    telemetry_dir = root / TELEMETRY_DIR
    tracks_dir = root / TRACKS_DIR
    tracks_index_path = root / TRACKS_INDEX_FILE

    try:
        vessel_info = load_vessel_info("data/vessel/info.yaml")
        vessel_name = vessel_info.get("name", "Vessel")
    except Exception:
        vessel_name = "Vessel"

    # Collect all timestamped snapshot files (skip index/latest files)
    skip = {"signalk_latest.json", "positions_index.json", "snapshots_index.json",
            "tracks_index.json"}
    files = sorted(
        f for f in telemetry_dir.glob("*.json")
        if f.name not in skip and not f.name.startswith("tracks")
    )
    print(f"Found {len(files)} snapshot files")

    # Parse and group by UTC date
    by_day: dict[str, list[dict[str, Any]]] = {}
    skipped = 0
    for path in files:
        pt = _parse_snapshot(path)
        if pt is None:
            skipped += 1
            continue
        if _haversine_m(pt["latitude"], pt["longitude"], HARBOR_LAT, HARBOR_LON) <= HARBOR_RADIUS_M:
            continue
        date_str = pt["timestamp"][:10]
        by_day.setdefault(date_str, []).append(pt)

    print(f"Parsed {len(files) - skipped} points across {len(by_day)} sailing days "
          f"({skipped} files skipped)")

    # Load existing index so we don't duplicate entries
    existing = _load_tracks_index(tracks_index_path)
    tracks_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for date_str, points in sorted(by_day.items()):
        gpx_path = tracks_dir / f"{date_str}.gpx"
        if gpx_path.exists():
            existing.setdefault(date_str, _make_track_meta(date_str, points))
            continue
        gpx_xml = _build_day_gpx(points, date_str, vessel_name)
        gpx_path.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{gpx_xml}\n',
                             encoding="utf-8")
        existing[date_str] = _make_track_meta(date_str, points)
        print(f"  Wrote {gpx_path.name}  ({len(points)} pts)")
        written += 1

    tracks_index_path.write_text(
        json.dumps({"tracks": sorted(existing.values(), key=lambda t: t["date"])}, indent=2),
        encoding="utf-8",
    )
    print(f"Done. {written} GPX files written, {len(existing)} total sailing days indexed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
