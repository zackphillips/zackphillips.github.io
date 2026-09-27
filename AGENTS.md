# AGENTS.md — S.V. Mermug site repository

A guide for AI agents (and humans) working in this repo.

## What this repo is

The published output of the [signalk-github-pages](https://github.com/zackphillips/signalk-github-pages)
Signal K plugin, served by GitHub Pages at mermug.com. The plugin, running on
the boat's Raspberry Pi, commits telemetry straight to `main` through the
GitHub API (`Telemetry <timestamp>Z (<nav state>)` commits) and rewrites the
frontend on install and upgrade. There is no build step and no code to run here.

## What you may edit

`.tracker-manifest.json` lists every path the plugin owns. Do not edit those
paths: the next publish or upgrade overwrites them, and a fix made here is lost.
Frontend changes, telemetry format changes and config changes (privacy zones,
custom links, timezone, logo, polar) belong in the plugin repo or its config page.

| Path | Owner |
|---|---|
| `index.html`, `sw.js`, `manifest.json`, `.nojekyll`, `assets/**` | Plugin |
| `data/telemetry/**`, `data/vessel/site.json`, `data/tide_stations.json` | Plugin |
| `data/vessel/polars.csv`, `logo.png`, `icon.png` | Plugin |
| `assets/custom.css` | You — loaded last by the page, never written by the plugin |
| `README.md`, `LICENSE`, `AGENTS.md`, `CLAUDE.md`, `.gitignore` | You |

If a request needs a change to a plugin-owned path, stop and say so rather than
editing it here.

## Working with `main`

The plugin commits to `main` every 2 minutes underway and hourly when
stationary. Make changes on a branch and merge through a PR. The plugin builds
each commit against the live `HEAD`, so a merged PR and a telemetry commit
interleave cleanly. Never force-push `main`: it would drop telemetry committed
in the meantime.
