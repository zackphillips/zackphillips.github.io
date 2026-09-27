@AGENTS.md

# Session scope — read before editing anything

Most sessions in this repo are **content sessions**: editing vessel config in
`data/vessel/`. Treat that as the default scope. Do not touch the static site
or the Pi backend unless the user says the session is for site or plugin
development.

| Path | Default scope | Notes |
|---|---|---|
| `data/vessel/info.yaml`, `polars.csv`, `logo.png` | **Editable** | Vessel config |
| `data/telemetry/**` | Never edit | Pi-managed, overwritten every cycle |
| `index.html`, `assets/`, `sw.js`, `manifest.json` | **Off limits by default** | Static site — written by the [signalk-github-pages](https://github.com/zackphillips/signalk-github-pages) plugin, see `.tracker-manifest.json` |
| `scripts/`, `services/`, `Makefile`, `tests/`, `pyproject.toml` | **Off limits by default** | Pi backend + tooling — same reason |

If a config change seems to need a frontend change, stop and say so rather
than editing `assets/` to make it work. The frontend is owned by the SignalK
plugin; edits made here diverge from that code and are overwritten on its
next upgrade.

Everything else — build commands, gotchas, data-file rules — is in
`AGENTS.md` above.
