import math
from unittest.mock import patch

import scripts.update_polar_data as upd


# --- _fold_twa ---

def test_fold_twa_starboard():
    assert upd._fold_twa(90.0) == 90.0

def test_fold_twa_port():
    assert upd._fold_twa(270.0) == 90.0

def test_fold_twa_head_to_wind():
    assert upd._fold_twa(0.0) == 0.0

def test_fold_twa_dead_downwind():
    assert upd._fold_twa(180.0) == 180.0

def test_fold_twa_negative():
    assert upd._fold_twa(-45.0) == 45.0


# --- _twa_bin ---

def test_twa_bin_starboard():
    assert upd._twa_bin(45.0) == 45

def test_twa_bin_folds_port_tack():
    # 270° = 90° on the port side
    assert upd._twa_bin(270.0) == 90

def test_twa_bin_folds_near_180():
    assert upd._twa_bin(200.0) == 160  # 360 - 200 = 160

def test_twa_bin_snaps_to_grid_down():
    assert upd._twa_bin(92.0) == 90

def test_twa_bin_snaps_to_grid_up():
    assert upd._twa_bin(93.0) == 95

def test_twa_bin_clamps_to_180():
    assert upd._twa_bin(180.0) == 180

def test_twa_bin_zero():
    assert upd._twa_bin(0.0) == 0

def test_twa_bin_negative_folds():
    # Negative angles should fold the same as their positive mirror
    assert upd._twa_bin(-45.0) == upd._twa_bin(45.0)


# --- _tws_bin ---

def test_tws_bin_snaps_to_even():
    assert upd._tws_bin(9.0) == 8  # rounds to nearest 2

def test_tws_bin_snaps_up():
    assert upd._tws_bin(11.0) == 12  # rounds to nearest 2 (11 rounds to 12 for nearest even)

def test_tws_bin_clamps_low():
    assert upd._tws_bin(0.5) == 2

def test_tws_bin_clamps_high():
    assert upd._tws_bin(50.0) == 30

def test_tws_bin_exact():
    assert upd._tws_bin(10.0) == 10


# --- update_accumulator ---

def test_update_accumulator_records_new_bin():
    acc = {"bins": {}, "observations": 0}
    improved = upd.update_accumulator(acc, 90.0, 10.0, 5.5)
    assert improved
    assert acc["bins"]["90_10"] == 5.5
    assert acc["observations"] == 1

def test_update_accumulator_keeps_max():
    acc = {"bins": {}, "observations": 0}
    upd.update_accumulator(acc, 90.0, 10.0, 5.5)
    improved = upd.update_accumulator(acc, 90.0, 10.0, 4.0)  # slower
    assert not improved
    assert acc["bins"]["90_10"] == 5.5

def test_update_accumulator_replaces_with_new_max():
    acc = {"bins": {}, "observations": 0}
    upd.update_accumulator(acc, 90.0, 10.0, 5.5)
    improved = upd.update_accumulator(acc, 90.0, 10.0, 7.0)  # faster
    assert improved
    assert acc["bins"]["90_10"] == 7.0

def test_update_accumulator_filters_low_tws():
    acc = {"bins": {}, "observations": 0}
    improved = upd.update_accumulator(acc, 90.0, 1.0, 3.0)  # TWS below MIN_TWS_KTS
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_filters_low_stw():
    acc = {"bins": {}, "observations": 0}
    improved = upd.update_accumulator(acc, 90.0, 10.0, 0.2)  # STW below MIN_STW_KTS
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_filters_hull_speed():
    acc = {"bins": {}, "observations": 0}
    improved = upd.update_accumulator(acc, 90.0, 20.0, 10.0)  # STW above MAX_STW_KTS
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_filters_speed_wind_ratio():
    acc = {"bins": {}, "observations": 0}
    # 6 kts boat speed in 2 kts of wind — obviously motoring
    improved = upd.update_accumulator(acc, 90.0, 2.0, 6.0)
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_filters_small_twa():
    acc = {"bins": {}, "observations": 0}
    # 20° TWA — no displacement sailboat points this high
    improved = upd.update_accumulator(acc, 20.0, 10.0, 5.0)
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_filters_small_twa_port_side():
    acc = {"bins": {}, "observations": 0}
    # 340° = 20° folded — same filter should apply
    improved = upd.update_accumulator(acc, 340.0, 10.0, 5.0)
    assert not improved
    assert acc["bins"] == {}

def test_update_accumulator_accepts_at_min_twa_boundary():
    acc = {"bins": {}, "observations": 0}
    # Exactly at MIN_TWA_DEG should be accepted
    improved = upd.update_accumulator(acc, upd.MIN_TWA_DEG, 10.0, 5.0)
    assert improved

def test_update_accumulator_increments_observations_even_without_improvement():
    acc = {"bins": {}, "observations": 0}
    upd.update_accumulator(acc, 90.0, 10.0, 5.5)
    upd.update_accumulator(acc, 90.0, 10.0, 4.0)  # no improvement
    assert acc["observations"] == 2

def test_update_accumulator_folds_twa():
    acc = {"bins": {}, "observations": 0}
    # 270° should land in the same bin as 90°
    upd.update_accumulator(acc, 90.0, 10.0, 5.0)
    upd.update_accumulator(acc, 270.0, 10.0, 6.0)  # port tack, faster
    assert acc["bins"]["90_10"] == 6.0

def test_update_accumulator_sets_last_updated():
    acc = {"bins": {}, "observations": 0}
    upd.update_accumulator(acc, 90.0, 10.0, 5.5)
    assert acc["last_updated"] is not None


# --- load_accumulator / save_accumulator ---

def test_accumulator_roundtrip(tmp_path):
    path = tmp_path / "acc.json"
    acc = {"bins": {"90_10": 7.2}, "observations": 42, "last_updated": "2026-01-01"}
    upd.save_accumulator(acc, path)
    loaded = upd.load_accumulator(path)
    assert loaded["bins"]["90_10"] == 7.2
    assert loaded["observations"] == 42

def test_load_accumulator_returns_empty_when_missing(tmp_path):
    acc = upd.load_accumulator(tmp_path / "nonexistent.json")
    assert acc["bins"] == {}
    assert acc["observations"] == 0

def test_load_accumulator_handles_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.json"
    path.write_text("not json{{{")
    acc = upd.load_accumulator(path)
    assert acc["bins"] == {}


# --- write_polar_csv ---

def test_write_polar_csv_header(tmp_path):
    acc = {"bins": {}, "observations": 0}
    csv = tmp_path / "polars_calculated.csv"
    upd.write_polar_csv(acc, csv)
    first_line = csv.read_text().split("\n")[0]
    assert first_line == "twa/tws;4;6;8;10;12;14;16;20;24"

def test_write_polar_csv_row_count(tmp_path):
    acc = {"bins": {}, "observations": 0}
    csv = tmp_path / "polars_calculated.csv"
    upd.write_polar_csv(acc, csv)
    data_lines = [l for l in csv.read_text().strip().split("\n") if l]
    # 1 header + 9 TWA rows
    assert len(data_lines) == 10

def test_write_polar_csv_twa_rows(tmp_path):
    acc = {"bins": {}, "observations": 0}
    csv = tmp_path / "polars_calculated.csv"
    upd.write_polar_csv(acc, csv)
    lines = csv.read_text().strip().split("\n")
    twas = [int(l.split(";")[0]) for l in lines[1:] if l]
    assert twas == upd.OUTPUT_TWA

def test_write_polar_csv_reflects_bin_data(tmp_path):
    acc = {"bins": {"90_10": 7.5}, "observations": 1}
    csv = tmp_path / "polars_calculated.csv"
    upd.write_polar_csv(acc, csv)
    # The 90° row should have a non-zero value near the 10-knot column
    lines = csv.read_text().strip().split("\n")
    row_90 = next(l for l in lines if l.startswith("90;"))
    speeds = [float(v) for v in row_90.split(";")[1:]]
    assert any(s > 0 for s in speeds)

def test_write_polar_csv_all_zeros_when_no_data(tmp_path):
    acc = {"bins": {}, "observations": 0}
    csv = tmp_path / "polars_calculated.csv"
    upd.write_polar_csv(acc, csv)
    lines = csv.read_text().strip().split("\n")
    for line in lines[1:]:
        speeds = [float(v) for v in line.split(";")[1:]]
        assert all(s == 0.0 for s in speeds)


# --- fetch_polar_sample ---

def _make_signalk_blob(tws_ms=5.14, twa_rad=math.radians(90), stw_ms=3.09):
    return {
        "navigation": {"speedThroughWater": {"value": stw_ms}},
        "environment": {
            "wind": {
                "speedTrue": {"value": tws_ms},
                "angleTrueWater": {"value": twa_rad},
            }
        },
    }


def _fake_requests(blob):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return blob

    class FakeRequests:
        @staticmethod
        def get(url, timeout=5): return FakeResp()

    return FakeRequests


def test_fetch_polar_sample_returns_tuple():
    with patch("scripts.update_polar_data.requests", _fake_requests(_make_signalk_blob())):
        result = upd.fetch_polar_sample("http://fake")
    assert result is not None
    twa_deg, tws_kts, stw_kts = result
    assert abs(twa_deg - 90.0) < 1.0
    assert abs(tws_kts - 5.14 * 1.94384) < 0.1
    assert abs(stw_kts - 3.09 * 1.94384) < 0.1

def test_fetch_polar_sample_returns_none_on_missing_wind():
    blob = {"navigation": {"speedThroughWater": {"value": 3.0}}}  # no wind
    with patch("scripts.update_polar_data.requests", _fake_requests(blob)):
        assert upd.fetch_polar_sample("http://fake") is None

def test_fetch_polar_sample_returns_none_on_missing_speed():
    blob = {
        "environment": {
            "wind": {
                "speedTrue": {"value": 5.0},
                "angleTrueWater": {"value": 1.57},
            }
        }
    }
    with patch("scripts.update_polar_data.requests", _fake_requests(blob)):
        assert upd.fetch_polar_sample("http://fake") is None

def test_fetch_polar_sample_falls_back_to_sog():
    blob = {
        "navigation": {"speedOverGround": {"value": 3.0}},  # STW absent, SOG present
        "environment": {
            "wind": {
                "speedTrue": {"value": 5.0},
                "angleTrueWater": {"value": 1.57},
            }
        },
    }
    with patch("scripts.update_polar_data.requests", _fake_requests(blob)):
        result = upd.fetch_polar_sample("http://fake")
    assert result is not None

def test_fetch_polar_sample_returns_none_on_network_error():
    class BrokenRequests:
        @staticmethod
        def get(url, timeout=5):
            raise ConnectionError("no route to host")

    with patch("scripts.update_polar_data.requests", BrokenRequests):
        assert upd.fetch_polar_sample("http://fake") is None
