"""Accumulate polar performance data from SignalK and write polars_calculated.csv.

Runs continuously at a configurable interval (default 10s). For each sample:
  - Reads TWS, TWA, and STW/SOG from the SignalK API
  - Folds TWA to 0-180° (port/starboard symmetry)
  - Updates a max-speed-per-bin accumulator (constant size, never grows)
  - Writes polars_calculated.csv in the same semicolon-delimited format as polars.csv

The accumulator is persisted to polars_accumulated.json (gitignored) so it
survives service restarts. The CSV is a derived view — it never grows beyond
its fixed grid dimensions.
"""

import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import requests

from .utils import get_project_root, load_vessel_info

ACCUMULATOR_FILE = "data/vessel/polars_accumulated.json"
POLAR_CSV_FILE = "data/vessel/polars_calculated.csv"

# Output grid — same TWS columns as polars.csv for drop-in frontend compatibility.
OUTPUT_TWS: list[int] = [4, 6, 8, 10, 12, 14, 16, 20, 24]
OUTPUT_TWA: list[int] = [0, 52, 60, 75, 90, 110, 120, 135, 150]

# Accumulator bin resolution
TWA_BIN_SIZE = 5  # degrees
TWS_BIN_SIZE = 2  # knots

# Quality-filter thresholds
MIN_TWS_KTS = 2.0
MIN_STW_KTS = 0.5
MAX_STW_KTS = 9.5        # generous hull-speed ceiling for a 42ft displacement boat
MAX_SPEED_WIND_RATIO = 1.5  # STW can't exceed 1.5× TWS (catches motoring in light air)
MIN_TWA_DEG = 30         # no displacement sailboat points within 30° of true wind


def _twa_bin(twa_deg: float) -> int:
    """Fold TWA to 0–180° then snap to the nearest TWA_BIN_SIZE grid point."""
    twa = abs(twa_deg) % 360
    if twa > 180:
        twa = 360 - twa
    return max(0, min(180, round(twa / TWA_BIN_SIZE) * TWA_BIN_SIZE))


def _tws_bin(tws_kts: float) -> int:
    """Snap TWS to the nearest TWS_BIN_SIZE grid point, clamped to [2, 30]."""
    return max(2, min(30, round(tws_kts / TWS_BIN_SIZE) * TWS_BIN_SIZE))


def load_accumulator(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"bins": {}, "observations": 0, "last_updated": None}


def save_accumulator(acc: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(acc, indent=2))


def _fold_twa(twa_deg: float) -> float:
    """Fold an arbitrary TWA to the 0–180° range."""
    twa = abs(twa_deg) % 360
    return 360 - twa if twa > 180 else twa


def update_accumulator(acc: dict, twa_deg: float, tws_kts: float, stw_kts: float) -> bool:
    """Update the max-speed bin; return True if any bin was improved."""
    if tws_kts < MIN_TWS_KTS or stw_kts < MIN_STW_KTS:
        return False
    if stw_kts > MAX_STW_KTS:
        return False
    if stw_kts > tws_kts * MAX_SPEED_WIND_RATIO:
        return False
    if _fold_twa(twa_deg) < MIN_TWA_DEG:
        return False
    key = f"{_twa_bin(twa_deg)}_{_tws_bin(tws_kts)}"
    improved = key not in acc["bins"] or stw_kts > acc["bins"][key]
    if improved:
        acc["bins"][key] = round(stw_kts, 3)
    acc["observations"] = acc.get("observations", 0) + 1
    acc["last_updated"] = datetime.now(UTC).isoformat()
    return improved


def _best_speed(acc: dict, twa_target: float, tws_target: float) -> float:
    """Return the best observed speed near (twa_target, tws_target)."""
    best = 0.0
    twa_center = round(twa_target / TWA_BIN_SIZE) * TWA_BIN_SIZE
    tws_center = round(tws_target / TWS_BIN_SIZE) * TWS_BIN_SIZE
    for dtwa in range(-TWA_BIN_SIZE * 2, TWA_BIN_SIZE * 2 + 1, TWA_BIN_SIZE):
        tw = max(0, min(180, twa_center + dtwa))
        for dtws in range(-TWS_BIN_SIZE * 2, TWS_BIN_SIZE * 2 + 1, TWS_BIN_SIZE):
            ts = max(2, min(30, tws_center + dtws))
            val = acc["bins"].get(f"{tw}_{ts}", 0.0)
            if val > best:
                best = val
    return best


def write_polar_csv(acc: dict, path: Path) -> None:
    """Write polars_calculated.csv as a drop-in replacement for polars.csv."""
    lines = ["twa/tws;" + ";".join(str(t) for t in OUTPUT_TWS)]
    for twa in OUTPUT_TWA:
        row = [
            f"{_best_speed(acc, float(twa), float(tws)):.2f}"
            for tws in OUTPUT_TWS
        ]
        lines.append(f"{twa};" + ";".join(row))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _get_value(node: dict, *path: str) -> float | None:
    """Traverse a nested SignalK dict and return the leaf .value, or None."""
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, dict):
        v = node.get("value")
    else:
        v = node
    return float(v) if isinstance(v, (int, float)) else None


def fetch_polar_sample(signalk_url: str) -> tuple[float, float, float] | None:
    """Return (twa_deg, tws_kts, stw_kts) from SignalK, or None if unavailable."""
    try:
        resp = requests.get(signalk_url, timeout=5)
        resp.raise_for_status()
        blob = resp.json()
    except Exception as exc:
        print(f"SignalK fetch error: {exc}")
        return None

    nav = blob.get("navigation", {})
    wind = blob.get("environment", {}).get("wind", {})

    tws_ms = _get_value(wind, "speedTrue") or _get_value(wind, "speedApparent")
    if tws_ms is None:
        return None

    twa_rad = (
        _get_value(wind, "angleTrueWater")
        or _get_value(wind, "angleTrueGround")
        or _get_value(wind, "angleApparent")
    )
    if twa_rad is None:
        return None

    stw_ms = _get_value(nav, "speedThroughWater") or _get_value(nav, "speedOverGround")
    if stw_ms is None:
        return None

    return math.degrees(twa_rad), tws_ms * 1.94384, stw_ms * 1.94384


def _load_signalk_url() -> str:
    try:
        vessel = load_vessel_info("data/vessel/info.yaml")
        sk = vessel.get("signalk", {})
        if sk.get("host") and sk.get("port"):
            return f"{sk.get('protocol', 'http')}://{sk['host']}:{sk['port']}/signalk/v1/api/vessels/self"
    except Exception:
        pass
    return "http://localhost:3000/signalk/v1/api/vessels/self"


def parse_args() -> SimpleNamespace:
    parser = argparse.ArgumentParser(
        description="Accumulate polar performance data from SignalK"
    )
    parser.add_argument("--signalk-url", dest="signalk_url", default=_load_signalk_url())
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Sampling interval in seconds (0 = one-shot)",
    )
    parser.add_argument("--accumulator", default=ACCUMULATOR_FILE)
    parser.add_argument("--output", default=POLAR_CSV_FILE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = get_project_root()
    acc_path = (
        Path(args.accumulator)
        if Path(args.accumulator).is_absolute()
        else (root / args.accumulator).resolve()
    )
    csv_path = (
        Path(args.output)
        if Path(args.output).is_absolute()
        else (root / args.output).resolve()
    )

    acc = load_accumulator(acc_path)
    print(
        f"Loaded accumulator: {acc.get('observations', 0)} observations, "
        f"{len(acc.get('bins', {}))} bins populated"
    )

    while True:
        sample = fetch_polar_sample(args.signalk_url)
        if sample is not None:
            twa_deg, tws_kts, stw_kts = sample
            improved = update_accumulator(acc, twa_deg, tws_kts, stw_kts)
            if improved:
                save_accumulator(acc, acc_path)
                write_polar_csv(acc, csv_path)
                print(
                    f"New max: TWA={_twa_bin(twa_deg)}° TWS={_tws_bin(tws_kts)}kts "
                    f"→ {stw_kts:.2f}kts | {acc['observations']} total observations"
                )
            else:
                print(
                    f"Sample: TWA={twa_deg:.1f}° TWS={tws_kts:.1f}kts "
                    f"STW={stw_kts:.2f}kts (no improvement)"
                )

        if args.interval == 0:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
