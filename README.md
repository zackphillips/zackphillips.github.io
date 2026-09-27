# S.V. Mermug — Voyage Tracker

![Vessel Logo](data/vessel/logo.png)

A public voyage tracker for **S.V. Mermug**, a 42.7-foot sailboat based in San Francisco Bay. Visit [mermug.com](https://mermug.com) to see where the boat is, where it's been, and what the weather looks like along the way.

This is **not** an onboard instrument dashboard — for that, the boat runs [KIP](https://github.com/mxtommy/Kip) connected to a local [SignalK](https://signalk.org/) server. This site is for the people who aren't on the boat: friends, family, and anyone following along from shore.

---

## How it works

The [signalk-github-pages](https://github.com/zackphillips/signalk-github-pages) plugin runs inside the Signal K server aboard and commits telemetry to this repository: every 2 minutes underway, hourly while moored or anchored. GitHub Pages serves the static site, and the browser reads the committed JSON directly. There is no server to maintain.

```
Signal K + signalk-github-pages (onboard) → GitHub API commit → GitHub Pages → mermug.com
```

Configuration (privacy zones, custom links, timezone, logo) lives in the plugin's config page on the boat, not in this repository.

---

## What's in this repository

The plugin writes `.tracker-manifest.json` listing every path it manages. Those paths are overwritten on its next publish or upgrade, so change them in the plugin, not here:

- `index.html`, `sw.js`, `manifest.json`, `.nojekyll`, `assets/**`
- `data/telemetry/**`, `data/vessel/site.json`, `data/tide_stations.json`
- `data/vessel/polars.csv`, `logo.png`, `icon.png`

Everything else is hand-maintained: this README, `LICENSE`, `AGENTS.md`/`CLAUDE.md`, and `assets/custom.css` if one is added (the page loads it last and the plugin never writes it).

---

## Site features

- **Current position** with human-readable location name (via OpenStreetMap)
- **Voyage track** — breadcrumb trail of recent positions on an interactive map, plus per-day GPX
- **Navigation snapshot** — heading, speed, wind, water temperature
- **Tide predictions** — NOAA data for the nearest station to the vessel
- **Weather forecasts** — wind and swell forecasts at the vessel's current position
- **Electrical status** — battery state of charge and power draw
- **Sailing performance** — actual vs. theoretical polar performance
- **Privacy** — positions inside configured zones (the home marina) are never published

---

## Vessel

**S.V. Mermug** — Hull #BEY57004E494
- Length: 42.7 ft | Beam: 13.9 ft | Draft: 6.2 ft
- MMSI: 338543654 | USCG: 1024168

---

## License

Open source. See [LICENSE](LICENSE).
