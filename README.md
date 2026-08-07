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
- **Ship's docs** — operating procedures, systems reference and checklists, at [mermug.com/docs.html](https://mermug.com/docs.html)
- **Dark/light mode** with persistent preference

---

## Ship's docs

Every Markdown file in [`docs/`](docs/) is published at
[mermug.com/docs.html](https://mermug.com/docs.html) — browsable, searchable, and
readable on a phone. Adding a document is just adding a `.md` file, including
straight from the GitHub web UI: a workflow rebuilds the index on push, so no
local checkout or build step is needed.

Front matter is optional. Without it the title comes from the first `# heading`,
the category from the subdirectory, and the summary from the first paragraph:

```markdown
---
title: Man Overboard
category: Emergency
order: 10
---

# Man Overboard

- [ ] Shout "man overboard", point, keep eyes on them
- [ ] Hit MOB on the chartplotter
```

Details worth knowing:

- `- [ ]` items become checkboxes you can actually tick; the state is saved in
  that browser, so a pre-departure checklist survives closing the tab.
- Documents are cached for offline reading — the whole set is pre-fetched on
  first visit, so the procedures stay available with no signal.
- Files starting with `_` are drafts and stay off the site. Start a new document
  by copying [`docs/_template.md`](docs/_template.md).
- Editing locally? `make docs-index` regenerates `docs/index.json` (a pre-commit
  hook does it for you).

---

## Vessel

**S.V. Mermug** — Hull #BEY57004E494
- Length: 42.7 ft | Beam: 13.9 ft | Draft: 6.2 ft
- MMSI: 338543654 | USCG: 1024168

---

## Backend setup (Raspberry Pi)

### Prerequisites

- Python 3.11+
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
- **Backend**: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), [`ruff`](https://docs.astral.sh/ruff/)
- **Data**: Static JSON committed to git, served via GitHub Pages
- **External APIs**: NOAA Tides, Open-Meteo, OpenStreetMap Nominatim

### Data files

| File | Description |
|------|-------------|
| `data/vessel/info.yaml` | Vessel configuration (name, MMSI, SignalK host/port) |
| `data/vessel/polars.csv` | ORC polar performance data — download from [jieter.github.io/orc-data](https://jieter.github.io/orc-data/site/) |
| `data/telemetry/signalk_latest.json` | Latest snapshot from SignalK |
| `data/telemetry/positions_index.json` | Rolling 24h position history for track rendering |
| `data/telemetry/tracks/*.gpx` | Per-day GPX tracks, generated from the position index |

### Privacy

Positions within configured exclusion zones (e.g. home marina) are automatically redacted from committed data.

---

## License

Open source. See [LICENSE](LICENSE).
