#!/usr/bin/env python3
"""Convert telemetry JSON points to Jibset-compatible GPX/CSV/TXT."""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional
import xml.etree.ElementTree as ET


FILENAME_TS_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}-\d{2}-\d{2})(?P<micro>\.\d+)?Z\.json$"
)


@dataclass
class TrackPoint:
    timestamp: datetime
    latitude: float
    longitude: float
    source: Path


def parse_time_adjust(value: str) -> timedelta:
    match = re.fullmatch(r"([+-])?(\d{2}):(\d{2}):(\d{2})", value.strip())
    if not match:
        raise ValueError("time adjustment must be like +HH:MM:SS or -HH:MM:SS")
    sign_str, hh, mm, ss = match.groups()
    sign = -1 if sign_str == "-" else 1
    return sign * timedelta(hours=int(hh), minutes=int(mm), seconds=int(ss))


def parse_filename_timestamp(path: Path) -> Optional[datetime]:
    match = FILENAME_TS_RE.match(path.name)
    if not match:
        return None
    date_part = match.group("date")
    time_part = match.group("time").replace("-", ":")
    micro_part = match.group("micro") or ""
    fmt = "%Y-%m-%dT%H:%M:%S"
    ts_str = f"{date_part}T{time_part}{micro_part}Z"
    try:
        dt = datetime.strptime(ts_str, fmt + ".%fZ" if micro_part else fmt + "Z")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def parse_iso_timestamp(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_point(path: Path) -> Optional[TrackPoint]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        return None

    ts = None
    if "timestamp" in data:
        ts = parse_iso_timestamp(str(data["timestamp"]))

    if ts is None:
        ts = parse_filename_timestamp(path)

    if ts is None:
        return None

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return None

    return TrackPoint(timestamp=ts, latitude=lat_f, longitude=lon_f, source=path)


def iter_telemetry_files(input_dir: Path) -> Iterable[Path]:
    for path in sorted(input_dir.glob("*.json")):
        if path.name in {"signalk_latest.json", "positions_index.json"}:
            continue
        yield path


def collect_points(files: Iterable[Path]) -> List[TrackPoint]:
    points: List[TrackPoint] = []
    for path in files:
        point = load_point(path)
        if point:
            points.append(point)
    points.sort(key=lambda p: p.timestamp)
    return points


def split_into_sequences(points: List[TrackPoint], max_gap: timedelta) -> List[List[TrackPoint]]:
    if not points:
        return []
    sequences = [[points[0]]]
    for point in points[1:]:
        if point.timestamp - sequences[-1][-1].timestamp > max_gap:
            sequences.append([point])
        else:
            sequences[-1].append(point)
    return sequences


def clamp_points(points: List[TrackPoint], start: Optional[datetime], end: Optional[datetime]) -> List[TrackPoint]:
    if start:
        points = [p for p in points if p.timestamp >= start]
    if end:
        points = [p for p in points if p.timestamp <= end]
    return points


def format_timestamp(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_csv(points: List[TrackPoint], output: Path, delimiter: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(["time", "latitude", "longitude"])
        for point in points:
            writer.writerow([
                format_timestamp(point.timestamp),
                f"{point.latitude:.6f}",
                f"{point.longitude:.6f}",
            ])


def write_gpx(points: List[TrackPoint], output: Path, name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    gpx = ET.Element(
        "gpx",
        {
            "version": "1.1",
            "creator": "telemetry_to_jibset",
            "xmlns": "http://www.topografix.com/GPX/1/1",
        },
    )
    trk = ET.SubElement(gpx, "trk")
    ET.SubElement(trk, "name").text = name
    seg = ET.SubElement(trk, "trkseg")
    for point in points:
        trkpt = ET.SubElement(
            seg,
            "trkpt",
            {"lat": f"{point.latitude:.6f}", "lon": f"{point.longitude:.6f}"},
        )
        ET.SubElement(trkpt, "time").text = format_timestamp(point.timestamp)

    tree = ET.ElementTree(gpx)
    tree.write(output, encoding="utf-8", xml_declaration=True)


def parse_datetime_arg(value: str) -> datetime:
    dt = parse_iso_timestamp(value)
    if dt is None:
        raise argparse.ArgumentTypeError("datetime must be ISO-8601 (e.g. 2026-02-01T00:00:00Z)")
    return dt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert telemetry JSON points to Jibset-compatible GPX/CSV/TXT",
    )
    parser.add_argument(
        "--input-dir",
        default="data/telemetry",
        help="Directory containing telemetry JSON files",
    )
    parser.add_argument(
        "--format",
        choices=["gpx", "csv", "txt"],
        default="gpx",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: jibset_track.<ext> in current dir)",
    )
    parser.add_argument(
        "--max-gap-seconds",
        type=int,
        default=600,
        help="Gap threshold to split sequences (default: 600 seconds)",
    )
    parser.add_argument(
        "--use-all",
        action="store_true",
        help="Use all points instead of just the most recent sequence",
    )
    parser.add_argument(
        "--start",
        type=parse_datetime_arg,
        help="Start time (ISO-8601) to trim points",
    )
    parser.add_argument(
        "--end",
        type=parse_datetime_arg,
        help="End time (ISO-8601) to trim points",
    )
    parser.add_argument(
        "--time-adjust",
        help="Adjust timestamps by +HH:MM:SS or -HH:MM:SS",
    )
    parser.add_argument(
        "--name",
        default="Jibset Track",
        help="Track name for GPX output",
    )

    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    files = list(iter_telemetry_files(input_dir))
    points = collect_points(files)
    if not points:
        raise SystemExit("No telemetry points found.")

    if args.time_adjust:
        adjust = parse_time_adjust(args.time_adjust)
        for point in points:
            point.timestamp = point.timestamp + adjust

    if not args.use_all:
        sequences = split_into_sequences(points, timedelta(seconds=args.max_gap_seconds))
        points = sequences[-1] if sequences else []

    points = clamp_points(points, args.start, args.end)
    if not points:
        raise SystemExit("No points left after filtering.")

    output = Path(args.output) if args.output else Path(f"jibset_track.{args.format}")

    if args.format == "gpx":
        write_gpx(points, output, args.name)
    elif args.format == "csv":
        write_csv(points, output, ",")
    else:
        write_csv(points, output, "	")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
