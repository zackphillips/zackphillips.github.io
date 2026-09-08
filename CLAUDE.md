@AGENTS.md

# Session scope — read before editing anything

Most sessions in this repo are **content sessions**: editing the ship's docs
in `docs/*.md`, or vessel config in `data/vessel/`. Treat that as the default
scope. Do not touch the static site or the Pi backend unless the user says
the session is for site or plugin development.

| Path | Default scope | Notes |
|---|---|---|
| `docs/*.md` | **Editable** | Ship's docs — the usual work here |
| `data/vessel/info.yaml`, `polars.csv`, `logo.png` | **Editable** | Vessel config |
| `docs/index.json` | Never hand-edit | Generated — `make docs-index` |
| `data/telemetry/**` | Never edit | Pi-managed, overwritten every cycle |
| `index.html`, `docs.html`, `assets/`, `sw.js`, `manifest.json` | **Off limits by default** | Static site — slated to move into the SignalK plugin, see `docs/signalk-plugin.md` |
| `scripts/`, `services/`, `Makefile`, `tests/`, `pyproject.toml`, `.github/` | **Off limits by default** | Pi backend + tooling — same reason |

If a docs change seems to need a frontend change (a new category, a new
doc-tag style, a rendering bug), stop and say so rather than editing
`assets/` to make it work. The frontend and backend are being replaced by a
published SignalK plugin; edits made here will diverge from that code and
be lost when it lands.

Everything else — build commands, gotchas, data-file rules — is in
`AGENTS.md` above.
