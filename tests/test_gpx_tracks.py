"""Tests for per-day GPX track generation and backfill script."""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.update_signalk_data as usd
import scripts.backfill_tracks as bt

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

HARBOR_LAT = 37.7802069
HARBOR_LON = -122.3858040

# A position clearly outside the harbor (~6 km NW, near the Golden Gate)
OUTSIDE_LAT = 37.8229
OUTSIDE_LON = -122.4373

# A position inside the harbor exclusion zone
INSIDE_LAT = HARBOR_LAT
INSIDE_LON = HARBOR_LON

NS = {"gpx": "http://www.topografix.com/GPX/1/1",
      "gpxtpx": "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"}


def _make_index_entry(
    ts: str,
    lat: float = OUTSIDE_LAT,
    lon: float = OUTSIDE_LON,
    speed: float | None = 2.5,
    course: float | None = 1.57,
) -> dict:
    values = [{"path": "navigation.position", "value": {"latitude": lat, "longitude": lon}}]
    if speed is not None:
        values.append({"path": "navigation.speedOverGround", "value": speed})
    if course is not None:
        values.append({"path": "navigation.courseOverGroundTrue", "value": course})
    return {"timestamp": ts, "file": f"{ts[:10]}T00-00-00.000000Z.json", "values": values}


def _make_snapshot_file(tmp_path: Path, ts: str, lat: float, lon: float,
                         speed: float | None = None, course: float | None = None) -> Path:
    """Write a fake SignalK snapshot file in the expected format."""
    values = [{"path": "navigation.position", "value": {"latitude": lat, "longitude": lon}}]
    if speed is not None:
        values.append({"path": "navigation.speedOverGround", "value": speed})
    if course is not None:
        values.append({"path": "navigation.courseOverGroundTrue", "value": course})
    payload = {"context": "vessels.self", "updates": [{"timestamp": ts, "values": values}]}
    # Filename must match the timestamp pattern
    fname = ts.replace(":", "-").replace("+00:00", "Z").replace(".", ".") + ".json"
    # Simplify: use a known-good filename format
    fname = f"{ts[:10]}T{ts[11:19].replace(':', '-')}.000000Z.json"
    path = tmp_path / fname
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# _fmt_gpx_time
# ---------------------------------------------------------------------------

def test_fmt_gpx_time_utc_offset():
    result = usd._fmt_gpx_time("2026-04-11T15:00:15+00:00")
    assert result == "2026-04-11T15:00:15Z"


def test_fmt_gpx_time_strips_microseconds():
    result = usd._fmt_gpx_time("2026-04-11T15:00:15.864000+00:00")
    assert result == "2026-04-11T15:00:15Z"


def test_fmt_gpx_time_no_tz_treated_as_utc():
    result = usd._fmt_gpx_time("2026-04-11T15:00:15")
    assert result == "2026-04-11T15:00:15Z"


def test_fmt_gpx_time_passthrough_on_bad_value():
    bad = "not-a-timestamp"
    assert usd._fmt_gpx_time(bad) == bad


# ---------------------------------------------------------------------------
# _extract_pos_from_values
# ---------------------------------------------------------------------------

def test_extract_pos_full():
    values = [
        {"path": "navigation.position", "value": {"latitude": 37.82, "longitude": -122.44}},
        {"path": "navigation.speedOverGround", "value": 2.5},
        {"path": "navigation.courseOverGroundTrue", "value": 1.57},
    ]
    lat, lon, speed, course = usd._extract_pos_from_values(values)
    assert lat == pytest.approx(37.82)
    assert lon == pytest.approx(-122.44)
    assert speed == pytest.approx(2.5)
    assert course == pytest.approx(1.57)


def test_extract_pos_missing_speed_course():
    values = [
        {"path": "navigation.position", "value": {"latitude": 37.82, "longitude": -122.44}},
    ]
    lat, lon, speed, course = usd._extract_pos_from_values(values)
    assert lat == pytest.approx(37.82)
    assert lon == pytest.approx(-122.44)
    assert speed is None
    assert course is None


def test_extract_pos_no_position():
    values = [{"path": "navigation.speedOverGround", "value": 3.0}]
    lat, lon, speed, course = usd._extract_pos_from_values(values)
    assert lat is None
    assert lon is None
    assert speed == pytest.approx(3.0)


def test_extract_pos_empty():
    lat, lon, speed, course = usd._extract_pos_from_values([])
    assert all(v is None for v in (lat, lon, speed, course))


# ---------------------------------------------------------------------------
# _build_day_gpx
# ---------------------------------------------------------------------------

def _sample_points(n: int = 3) -> list[dict]:
    return [
        {
            "timestamp": f"2026-04-11T1{i}:00:00+00:00",
            "latitude": 37.82 + i * 0.01,
            "longitude": -122.44 + i * 0.01,
            "speed_ms": 2.5 + i * 0.1,
            "course_rad": 1.57 + i * 0.05,
        }
        for i in range(n)
    ]


def test_build_day_gpx_is_valid_xml():
    xml_str = usd._build_day_gpx(_sample_points(), "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    assert root is not None


def test_build_day_gpx_correct_point_count():
    pts = _sample_points(5)
    xml_str = usd._build_day_gpx(pts, "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    trkpts = root.findall(".//gpx:trkpt", NS)
    assert len(trkpts) == 5


def test_build_day_gpx_lat_lon_correct():
    pts = [{"timestamp": "2026-04-11T15:00:00+00:00",
            "latitude": 37.822875, "longitude": -122.437270,
            "speed_ms": 2.5, "course_rad": 1.57}]
    xml_str = usd._build_day_gpx(pts, "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    trkpt = root.find(".//gpx:trkpt", NS)
    assert float(trkpt.attrib["lat"]) == pytest.approx(37.822875, abs=1e-5)
    assert float(trkpt.attrib["lon"]) == pytest.approx(-122.437270, abs=1e-5)


def test_build_day_gpx_speed_extension():
    pts = [{"timestamp": "2026-04-11T15:00:00+00:00",
            "latitude": 37.82, "longitude": -122.44,
            "speed_ms": 4.0, "course_rad": 0.0}]
    xml_str = usd._build_day_gpx(pts, "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    speed_el = root.find(".//gpxtpx:speed", NS)
    assert speed_el is not None
    assert float(speed_el.text) == pytest.approx(4.0, abs=0.01)


def test_build_day_gpx_course_extension_in_degrees():
    pts = [{"timestamp": "2026-04-11T15:00:00+00:00",
            "latitude": 37.82, "longitude": -122.44,
            "speed_ms": 2.0, "course_rad": math.pi}]  # π rad = 180°
    xml_str = usd._build_day_gpx(pts, "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    course_el = root.find(".//gpxtpx:course", NS)
    assert course_el is not None
    assert float(course_el.text) == pytest.approx(180.0, abs=0.2)


def test_build_day_gpx_no_extension_when_no_speed_course():
    pts = [{"timestamp": "2026-04-11T15:00:00+00:00",
            "latitude": 37.82, "longitude": -122.44,
            "speed_ms": None, "course_rad": None}]
    xml_str = usd._build_day_gpx(pts, "2026-04-11", "S.V. Test")
    root = ET.fromstring(xml_str)
    assert root.find(".//gpx:extensions", NS) is None


def test_build_day_gpx_track_name_contains_date():
    xml_str = usd._build_day_gpx(_sample_points(), "2026-04-11", "S.V. Mermug")
    root = ET.fromstring(xml_str)
    name_el = root.find(".//gpx:trk/gpx:name", NS)
    assert name_el is not None
    assert "2026-04-11" in name_el.text
    assert "Mermug" in name_el.text


# ---------------------------------------------------------------------------
# _make_track_meta
# ---------------------------------------------------------------------------

def test_make_track_meta_basic_fields():
    pts = [
        {"timestamp": "2026-04-11T15:00:00+00:00", "latitude": 37.82, "longitude": -122.44,
         "speed_ms": 3.0, "course_rad": 1.0},
        {"timestamp": "2026-04-11T16:00:00+00:00", "latitude": 37.83, "longitude": -122.43,
         "speed_ms": 5.0, "course_rad": 1.1},
    ]
    meta = usd._make_track_meta("2026-04-11", pts)
    assert meta["date"] == "2026-04-11"
    assert meta["file"] == "tracks/2026-04-11.gpx"
    assert meta["points"] == 2
    assert meta["start"] == "2026-04-11T15:00:00Z"
    assert meta["end"] == "2026-04-11T16:00:00Z"


def test_make_track_meta_duration():
    pts = [
        {"timestamp": "2026-04-11T12:00:00+00:00", "latitude": 37.82, "longitude": -122.44,
         "speed_ms": 3.0, "course_rad": 0.0},
        {"timestamp": "2026-04-11T14:30:00+00:00", "latitude": 37.83, "longitude": -122.43,
         "speed_ms": 4.0, "course_rad": 0.0},
    ]
    meta = usd._make_track_meta("2026-04-11", pts)
    assert meta["duration_hours"] == pytest.approx(2.5, abs=0.01)


def test_make_track_meta_max_speed_kts():
    pts = [
        {"timestamp": "2026-04-11T12:00:00+00:00", "latitude": 37.82, "longitude": -122.44,
         "speed_ms": 5.144, "course_rad": 0.0},   # ≈ 10 kts
        {"timestamp": "2026-04-11T12:05:00+00:00", "latitude": 37.83, "longitude": -122.43,
         "speed_ms": 2.572, "course_rad": 0.0},   # ≈ 5 kts
    ]
    meta = usd._make_track_meta("2026-04-11", pts)
    assert meta["max_speed_kts"] == pytest.approx(10.0, abs=0.1)


def test_make_track_meta_distance_positive():
    pts = [
        {"timestamp": "2026-04-11T12:00:00+00:00", "latitude": 37.80, "longitude": -122.44,
         "speed_ms": 3.0, "course_rad": 0.0},
        {"timestamp": "2026-04-11T12:10:00+00:00", "latitude": 37.85, "longitude": -122.44,
         "speed_ms": 3.0, "course_rad": 0.0},
    ]
    meta = usd._make_track_meta("2026-04-11", pts)
    assert meta["distance_nm"] > 0


# ---------------------------------------------------------------------------
# _load_tracks_index / _write_tracks_index round-trip
# ---------------------------------------------------------------------------

def test_tracks_index_round_trip(tmp_path):
    entries = [
        {"date": "2026-04-11", "file": "tracks/2026-04-11.gpx", "points": 181},
        {"date": "2026-03-21", "file": "tracks/2026-03-21.gpx", "points": 403},
    ]
    path = tmp_path / "tracks_index.json"
    usd._write_tracks_index(path, entries)
    loaded = usd._load_tracks_index(path)
    assert len(loaded) == 2
    assert loaded[0]["date"] == "2026-04-11"


def test_load_tracks_index_missing_file(tmp_path):
    result = usd._load_tracks_index(tmp_path / "nonexistent.json")
    assert result == []


def test_load_tracks_index_malformed_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json }", encoding="utf-8")
    result = usd._load_tracks_index(path)
    assert result == []


# ---------------------------------------------------------------------------
# _update_track_files (integration)
# ---------------------------------------------------------------------------

def _make_outside_entries(date_prefix: str, count: int = 3) -> list[dict]:
    return [
        _make_index_entry(
            f"{date_prefix}T1{i}:00:00+00:00",
            lat=OUTSIDE_LAT,
            lon=OUTSIDE_LON,
        )
        for i in range(count)
    ]


def test_update_track_files_creates_gpx(tmp_path):
    entries = _make_outside_entries("2026-04-11")
    tracks_dir = tmp_path / "tracks"
    index_path = tmp_path / "tracks_index.json"

    with patch("scripts.update_signalk_data.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        mock_dt.fromisoformat = datetime.fromisoformat
        usd._update_track_files(entries, tracks_dir, index_path, "S.V. Test")

    assert (tracks_dir / "2026-04-11.gpx").exists()
    assert index_path.exists()


def test_update_track_files_skips_harbor_positions(tmp_path):
    harbor_entry = _make_index_entry("2026-04-11T12:00:00+00:00",
                                      lat=INSIDE_LAT, lon=INSIDE_LON)
    tracks_dir = tmp_path / "tracks"
    index_path = tmp_path / "tracks_index.json"

    with patch("scripts.update_signalk_data.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        mock_dt.fromisoformat = datetime.fromisoformat
        usd._update_track_files([harbor_entry], tracks_dir, index_path, "S.V. Test")

    # No GPX should be created — all positions were inside the harbor
    assert not (tracks_dir / "2026-04-11.gpx").exists()
    assert not index_path.exists()


def test_update_track_files_does_not_overwrite_past_day(tmp_path):
    entries = _make_outside_entries("2026-03-21")
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    index_path = tmp_path / "tracks_index.json"

    # Pre-create the GPX with sentinel content
    sentinel = "SENTINEL_CONTENT"
    (tracks_dir / "2026-03-21.gpx").write_text(sentinel)

    with patch("scripts.update_signalk_data.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        mock_dt.fromisoformat = datetime.fromisoformat
        usd._update_track_files(entries, tracks_dir, index_path, "S.V. Test")

    assert (tracks_dir / "2026-03-21.gpx").read_text() == sentinel


def test_update_track_files_overwrites_today(tmp_path):
    entries = _make_outside_entries("2026-04-20")
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir()
    index_path = tmp_path / "tracks_index.json"

    # Pre-create stale content for today
    (tracks_dir / "2026-04-20.gpx").write_text("OLD_CONTENT")

    with patch("scripts.update_signalk_data.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        mock_dt.fromisoformat = datetime.fromisoformat
        usd._update_track_files(entries, tracks_dir, index_path, "S.V. Test")

    content = (tracks_dir / "2026-04-20.gpx").read_text()
    assert content != "OLD_CONTENT"
    assert "<?xml" in content


def test_update_track_files_index_has_correct_metadata(tmp_path):
    entries = _make_outside_entries("2026-04-11", count=5)
    tracks_dir = tmp_path / "tracks"
    index_path = tmp_path / "tracks_index.json"

    with patch("scripts.update_signalk_data.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 20, 12, 0, tzinfo=UTC)
        mock_dt.fromisoformat = datetime.fromisoformat
        usd._update_track_files(entries, tracks_dir, index_path, "S.V. Test")

    data = json.loads(index_path.read_text())
    assert "tracks" in data
    track = data["tracks"][0]
    assert track["date"] == "2026-04-11"
    assert track["points"] == 5
    assert track["file"] == "tracks/2026-04-11.gpx"


# ---------------------------------------------------------------------------
# backfill_tracks._parse_snapshot
# ---------------------------------------------------------------------------

def test_parse_snapshot_valid_file(tmp_path):
    path = _make_snapshot_file(tmp_path, "2026-04-11T15:00:00+00:00",
                                lat=OUTSIDE_LAT, lon=OUTSIDE_LON, speed=3.0, course=1.57)
    result = bt._parse_snapshot(path)
    assert result is not None
    assert result["latitude"] == pytest.approx(OUTSIDE_LAT, abs=1e-4)
    assert result["longitude"] == pytest.approx(OUTSIDE_LON, abs=1e-4)
    assert result["speed_ms"] == pytest.approx(3.0, abs=0.01)
    assert result["course_rad"] == pytest.approx(1.57, abs=0.01)
    assert result["timestamp"] == "2026-04-11T15:00:00+00:00"


def test_parse_snapshot_minimal_no_speed_course(tmp_path):
    path = _make_snapshot_file(tmp_path, "2026-04-11T15:00:00+00:00",
                                lat=OUTSIDE_LAT, lon=OUTSIDE_LON)
    result = bt._parse_snapshot(path)
    assert result is not None
    assert result["speed_ms"] is None
    assert result["course_rad"] is None


def test_parse_snapshot_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not json }", encoding="utf-8")
    assert bt._parse_snapshot(path) is None


def test_parse_snapshot_missing_position(tmp_path):
    payload = {"context": "vessels.self",
               "updates": [{"timestamp": "2026-04-11T15:00:00+00:00", "values": []}]}
    path = tmp_path / "2026-04-11T15-00-00.000000Z.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert bt._parse_snapshot(path) is None


# ---------------------------------------------------------------------------
# backfill_tracks.main (end-to-end)
# ---------------------------------------------------------------------------

def test_backfill_main_creates_gpx_and_index(tmp_path):
    # Build a fake telemetry directory with a couple of outside-harbor snapshots
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _make_snapshot_file(tel_dir, "2026-03-21T14:00:00+00:00", OUTSIDE_LAT, OUTSIDE_LON, 5.0, 1.0)
    _make_snapshot_file(tel_dir, "2026-03-21T16:00:00+00:00", OUTSIDE_LAT + 0.01, OUTSIDE_LON, 4.0, 1.1)
    # Add a harbor position that should be filtered
    _make_snapshot_file(tel_dir, "2026-03-22T10:00:00+00:00", INSIDE_LAT, INSIDE_LON, 0.1, 0.0)

    tracks_dir = tel_dir / "tracks"

    with (
        patch("scripts.backfill_tracks.TELEMETRY_DIR", tel_dir),
        patch("scripts.backfill_tracks.TRACKS_DIR", tracks_dir),
        patch("scripts.backfill_tracks.TRACKS_INDEX_FILE", tel_dir / "tracks_index.json"),
        patch("scripts.backfill_tracks.load_vessel_info", return_value={"name": "S.V. Test"}),
    ):
        # Patch get_project_root so the script uses our tmp directory
        with patch("scripts.backfill_tracks.get_project_root", return_value=tmp_path):
            result = bt.main()

    assert result == 0
    assert (tracks_dir / "2026-03-21.gpx").exists()
    # Harbor-only day should not produce a GPX
    assert not (tracks_dir / "2026-03-22.gpx").exists()

    index = json.loads((tel_dir / "tracks_index.json").read_text())
    dates = [t["date"] for t in index["tracks"]]
    assert "2026-03-21" in dates
    assert "2026-03-22" not in dates


def test_backfill_main_does_not_overwrite_existing_gpx(tmp_path):
    tel_dir = tmp_path / "telemetry"
    tel_dir.mkdir()
    _make_snapshot_file(tel_dir, "2026-03-21T14:00:00+00:00", OUTSIDE_LAT, OUTSIDE_LON)

    tracks_dir = tel_dir / "tracks"
    tracks_dir.mkdir()
    sentinel = "SENTINEL"
    (tracks_dir / "2026-03-21.gpx").write_text(sentinel)

    with (
        patch("scripts.backfill_tracks.TELEMETRY_DIR", tel_dir),
        patch("scripts.backfill_tracks.TRACKS_DIR", tracks_dir),
        patch("scripts.backfill_tracks.TRACKS_INDEX_FILE", tel_dir / "tracks_index.json"),
        patch("scripts.backfill_tracks.load_vessel_info", return_value={"name": "S.V. Test"}),
        patch("scripts.backfill_tracks.get_project_root", return_value=tmp_path),
    ):
        bt.main()

    assert (tracks_dir / "2026-03-21.gpx").read_text() == sentinel
