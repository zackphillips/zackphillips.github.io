# AGENTS.md — Working on S.V. Mermug Vessel Tracker

A guide for AI agents (and humans) contributing to this repo.

---

## Architecture

```
SignalK (onboard) → scripts/update_signalk_data.py (Raspberry Pi)
                  → git commit + push → GitHub Pages → mermug.com
```

- **No backend server.** The site is 100% static HTML/CSS/JS served by GitHub Pages.
- The Raspberry Pi runs two systemd services that commit new data every ~2.5 minutes.
- The browser fetches committed JSON files directly from the repo.
- The Pi auto-pushes; code changes go through normal PRs from a laptop/agent.

---

## Repo layout

```
index.html               # Single-page app entry point
sw.js                    # Service worker (offline support)
assets/
  constants.js           # All magic numbers / thresholds — edit here, not in app.js
  utils.js               # Shared helpers (UMD module — sets window.vesselUtils)
  app.js                 # Main frontend logic — reads window.VESSEL_CONSTANTS
  styles.css
data/
  vessel/
    info.yaml            # Vessel config (name, MMSI, SignalK host, privacy zones)
    logo.png
    polars.csv           # ORC polar data — download from jieter.github.io/orc-data
  telemetry/             # AUTO-GENERATED — do not hand-edit
    signalk_latest.json  # Most recent SignalK snapshot (Pi-managed)
    positions_index.json # Rolling 24-hour position history for map track
    instrument_log.json  # Rolling 120-entry sparkline data (~5 hours)
    tracks/              # Per-day GPX files (backfill_tracks.py)
    tracks_index.json    # Metadata index for GPX tracks
scripts/
  update_signalk_data.py # Pi daemon: fetch SignalK → commit telemetry
  update_polar_data.py   # Pi daemon: accumulate polar performance samples
  backfill_tracks.py     # One-shot: generate GPX files from snapshot history
  telemetry_to_jibset.py # Export telemetry to JibSet format
  utils.py               # Shared Python helpers (load_vessel_info, etc.)
  vessel_config_wizard.py # Interactive setup wizard
services/                # systemd service templates
tests/                   # Python (pytest) + JavaScript (vitest) tests
```

---

## Development commands

```bash
make server    # Local dev server at http://localhost:8000
make test      # Run Python + JavaScript tests
make test-py   # Python only (pytest)
make test-js   # JavaScript only (vitest) — requires npm
make lint      # ruff check --fix
make sync-dev  # uv sync --extra dev (refresh Python dev dependencies)
```

Always run `make test` before committing code changes. Pre-commit hooks run ruff
automatically if installed (`make pre-commit-install`).

---

## Frontend: critical loading order

`index.html` loads scripts in this exact order:

```html
<script src="assets/utils.js"></script>
<script src="assets/constants.js"></script>
<script src="assets/app.js?v=N"></script>
```

### The `var` rule in `constants.js`

`constants.js` **must** use `var`, not `const`:

```javascript
// CORRECT
var VESSEL_CONSTANTS = Object.freeze({ ... });

// WRONG — const at top level of a classic browser script does NOT become
// window.VESSEL_CONSTANTS, so app.js guard throws and the whole page breaks.
const VESSEL_CONSTANTS = Object.freeze({ ... });
```

`app.js` starts with:

```javascript
if (!window.VESSEL_CONSTANTS) throw new Error('constants.js must load before app.js');
const C = window.VESSEL_CONSTANTS;
```

`utils.js` is safe because it uses an explicit UMD pattern (`root.vesselUtils = factory()`).

### Adding or changing thresholds

Put numeric thresholds in `assets/constants.js`. Reference them in `app.js` as `C.SOME_KEY`.
Never hardcode magic numbers directly in `app.js`.

### Bumping the app.js cache-bust version

When deploying a breaking JS change, increment `?v=N` on the `app.js` script tag in
`index.html`. The service worker uses `mermug-shell-v1` — bump `SHELL_CACHE` in `sw.js`
only when you want to force all clients to re-fetch every shell asset.

---

## Vessel configuration (`data/vessel/info.yaml`)

This file drives both the frontend and the Pi backend:

```yaml
name: "S.V.Mermug"
mmsi: "338543654"
theme: "mermug"   # light | dark | mermug | deep-sea | …
signalk:
  host: "192.168.8.50"
  port: "3000"

privacy_zones:
  - name: "South Beach Harbor, San Francisco"
    lat: 37.7802069
    lon: -122.3858040
    radius_m: 200
```

- **Privacy zones** are read by both `update_signalk_data.py` (Python) and `app.js`
  (JavaScript) to redact positions near home marina. Add more zones freely; both sides
  use the same list from this single file.
- The Pi reads this file on every run, so changes take effect within one update cycle
  without restarting any service.

---

## Backend scripts (run on the Raspberry Pi)

### `scripts/update_signalk_data.py`

The main Pi daemon. Every ~150 seconds it:

1. Fetches the full SignalK vessel tree via HTTP.
2. Drops any positions inside privacy zones.
3. Writes `data/telemetry/signalk_latest.json` (latest state).
4. Appends one entry to `data/telemetry/instrument_log.json` (rolling 120-entry
   sparkline log — keeps ~5 hours at the default cadence).
5. Updates `data/telemetry/positions_index.json` with the new position; purges entries
   older than `POSITION_RETENTION_HOURS = 24`.
6. Commits and pushes all changed files.

Key constants (top of file):

| Constant | Default | Purpose |
|---|---|---| 
| `POSITION_RETENTION_HOURS` | 24 | How long raw positions are kept |
| `INSTRUMENT_LOG_ENTRIES` | 120 | Max sparkline entries (~5 hours) |
| `INSTRUMENT_LOG_FILE` | `data/telemetry/instrument_log.json` | Sparkline data |

### `scripts/update_polar_data.py`

Accumulates polar performance samples by comparing actual SOG/TWA against ORC polars.
Runs as a separate service every ~15 seconds. Writes to `data/vessel/polars_*.json`.

### `scripts/backfill_tracks.py`

One-shot script. Run it after a passage to generate per-day GPX files from any
existing snapshot history:

```bash
uv run python -m scripts.backfill_tracks
```

Reads privacy zones from `info.yaml`. Safe to re-run — never overwrites existing GPX.

---

## Data files — what to touch and what not to

| File | Who writes it | Can you edit? |
|---|---|---|
| `data/vessel/info.yaml` | Human / wizard | Yes — this is config |
| `data/vessel/polars.csv` | Human (download) | Yes |
| `data/telemetry/signalk_latest.json` | Pi daemon | No — overwritten each cycle |
| `data/telemetry/positions_index.json` | Pi daemon | No |
| `data/telemetry/instrument_log.json` | Pi daemon | No |
| `data/telemetry/tracks/*.gpx` | `backfill_tracks.py` | No (generated) |
| `data/telemetry/tracks_index.json` | `backfill_tracks.py` | No (generated) |

The Pi is always running and will overwrite any manual edits to telemetry files on its
next push.

---

## Deploying code changes

1. Develop on a feature branch; the Pi pushes to `main` continuously.
2. Open a PR; merge via GitHub (the Pi's next push will land on top cleanly).
3. If you need to force-push `main` (rare — only after history rewrites):
   ```bash
   TOKEN=$(cat ~/.claude/remote/.session_ingress_token)
   git -c "http.extraHeader=Authorization: Bearer $TOKEN" push origin main --force
   ```
   Then pull on any other machines (`git pull --rebase origin main`).
   The Pi will self-recover — it rebases before pushing.

---

## Known gotchas

- **`const` vs `var` at global scope in classic browser scripts**: `const` does not
  create a `window.*` property. Use `var` for any global the app accesses via
  `window.SomeName`. This caught us once and blanked the entire site.

- **`git filter-repo` removes remotes**: After running `git filter-repo`, re-add with
  `git remote add origin <url>`.

- **Pi is always pushing**: if your `git push` is rejected with "fetch first", run
  `git pull --rebase origin main` then push again.

- **Service worker caching during development**: use the browser's "Bypass for network"
  devtools option or bump `SHELL_CACHE` version to see frontend changes immediately.

- **`instrument_log.json` vs snapshot files**: The frontend sparklines read
  `instrument_log.json` (one fetch). Old code fetched ~60 individual snapshot files in
  parallel. Do not re-introduce per-snapshot fetches — they balloon repo size.

- **`INSTRUMENT_LOG_ENTRIES` must match**: the value in `constants.js` and in
  `update_signalk_data.py` must be the same number, since the Python side controls how
  many entries are retained and the JS side controls how many it reads.

---

## External APIs used by the frontend

| API | Used for | Key |
|---|---|---|
| NOAA Tides & Currents | Tide chart | None (public) |
| Open-Meteo | Weather + swell forecast | None (public) |
| OpenStreetMap Nominatim | Reverse geocoding (location name) | None (public) |

All API calls are made client-side; no proxy needed.
