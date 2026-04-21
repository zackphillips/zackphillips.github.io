# S.V. Mermug — Voyage Tracker

![Vessel Logo](data/vessel/logo.png)

A public voyage tracker for **S.V. Mermug**, a 42.7-foot sailboat based in San Francisco Bay. Visit [mermug.com](https://mermug.com) to see where the boat is, where it's been, and what the weather looks like along the way.

This is **not** an onboard instrument dashboard — for that, the boat runs [KIP](https://github.com/mxtommy/Kip) connected to a local [SignalK](https://signalk.org/) server. This site is for the people who aren't on the boat: friends, family, and anyone following along from shore.

---

## How it works

A Raspberry Pi aboard the boat runs a Python script that periodically pulls data from the onboard SignalK server and commits it to this repository. GitHub Pages serves the static site. The browser reads those committed JSON files — no live server, no WebSocket, no backend to maintain.

```
SignalK (onboard) → Python script (Raspberry Pi) → Git push → GitHub Pages → mermug.com
```

Data freshness depends on the Pi's update interval and internet connectivity from the boat (marina WiFi or cellular). Typical latency is a few minutes.

---

## Site features

- **Current position** with human-readable location name (via OpenStreetMap)
- **Voyage track** — breadcrumb trail of recent positions on an interactive map
- **Navigation snapshot** — heading, speed, wind, water temperature
- **Tide predictions** — NOAA data for the nearest station to the vessel
- **Weather forecasts** — wind and swell forecasts at the vessel's current position
- **Electrical status** — battery state of charge and power draw
- **Sailing performance** — actual vs. theoretical polar performance
- **Dark/light mode** with persistent preference

---

## Vessel

**S.V. Mermug** — Hull #BEY57004E494
- Length: 42.7 ft | Beam: 13.9 ft | Draft: 6.2 ft
- MMSI: 338543654 | USCG: 1024168

---

## Backend setup (Raspberry Pi)

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- SignalK server running on the local vessel network
- Git configured with push access to this repository

### Install

```bash
git clone <repository-url>
cd zackphillips.github.io
make pre-commit-install
```

### Configure vessel

```bash
make config
```

This runs an interactive wizard that writes `data/vessel/info.yaml` with your vessel name, MMSI, and SignalK host/port.

### Run as a system service

```bash
make install              # Install and start all services
make status               # Check service statuses
make show-logs-website    # Stream website service logs
make show-logs-polars     # Stream polar accumulation service logs
make uninstall            # Remove all services
```

---

## Development

```bash
make server    # Local dev server at http://localhost:8000
make test      # Run Python + JavaScript tests
make lint      # Run ruff linter and auto-fix
```

### Tech stack

- **Frontend**: Vanilla JS, HTML/CSS — [Leaflet](https://leafletjs.com/) for maps, [Chart.js](https://www.chartjs.org/) for polar charts
- **Backend**: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), [`ruff`](https://docs.astral.sh/ruff/)
- **Data**: Static JSON committed to git, served via GitHub Pages
- **External APIs**: NOAA Tides, Open-Meteo, OpenStreetMap Nominatim

### Data files

| File | Description |
|------|-------------|
| `data/vessel/info.yaml` | Vessel configuration (name, MMSI, SignalK host/port) |
| `data/vessel/polars.csv` | ORC polar performance data — download from [jieter.github.io/orc-data](https://jieter.github.io/orc-data/site/) |
| `data/telemetry/signalk_latest.json` | Latest snapshot from SignalK |
| `data/telemetry/positions_index.json` | Position history for track rendering |
| `data/telemetry/snapshots_index.json` | Index of all timestamped snapshots |

### Privacy

Positions within configured exclusion zones (e.g. home marina) are automatically redacted from committed data.

---

## License

Open source. See [LICENSE](LICENSE).
