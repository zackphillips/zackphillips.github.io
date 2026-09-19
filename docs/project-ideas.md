---
title: Project Ideas
category: Maintenance
order: 25
description: Speculative projects and system upgrades under consideration — not yet planned or committed, unlike Planned Projects.
---

# S.V. Mermug — Project Ideas

Unlike [Planned Projects](planned-projects.md) — known fixes pulled from
[Systems Overview](systems.md) that are just waiting to be done — this page
is for projects still at the idea stage: worth writing down, not yet
scoped, and with no commitment to build. Design write-ups live here even
when a one-line item for the same project already sits on Planned Projects;
once the work is actually underway, move the detail across.

---

## Digital 12V Signal Monitoring & Windlass Chain Counter in Signal K

**Status:** Idea / not yet started
**Scope:** Wire discrete 12V signals into the autoisolator and publish them
to Signal K, with the windlass gypsy sensor as the flagship sub-project
(rode counter).

### 1. Candidate 12V digital signals to monitor

Any simple on/off 12V signal can be sensed and published to Signal K.
Candidates, roughly in order of usefulness:

| Signal | Why track it |
|---|---|
| Bilge float switch | Baseline. Log pump cycles; frequency trend is an early leak indicator. |
| High-water bilge alarm | Separate channel from the float switch, so "normal pumping" vs. "problem" are distinguishable. |
| MOB button | Timestamped event, can trigger position capture. |
| Windlass gypsy sensor | Chain counter / rode deployed — see section 2. |
| Shore power presence | Log when actually plugged in; useful for charge-state correlation. |
| Engine ignition / alternator D+ | Lets Signal K know engine running state without an engine gateway. |
| Anchor light / nav lights | Confirm the anchor light is actually on overnight. |
| Hatch / companionway switch | Poor-man's security sensor. |
| Autopilot or alarm relay state | Know when the AP is engaged from the data side. |

The bilge float switch, high-water alarm, and [MOB button](systems.md#mob-man-overboard-button)
are all separately tracked already — see [Bilge](systems.md#bilge) and
[MOB Button](mob-procedure.md). This project would give them (and the rest
of the list) a common wiring and publishing path instead of one-off builds.

### 2. Windlass chain counter (Quick Eagle 1400W)

#### Key finding: the sensor is already installed

Quick states that all their windlasses ship with a laps sensor suitable
for use with their chain counters. The Eagle line specifically lists an
**integrated sensor and magnet for chain counter** in its product spec.

Physically this is a cylindrical magnet fixed to the gypsy and a magnetic
field sensor in the windlass base. One pulse per gypsy revolution.

**This means no modification to the windlass power circuitry is
required.** The sensor is a separate two-conductor low-voltage signal,
entirely independent of the high-current motor wiring feeding the
[windlass](systems.md#windlass).

#### Wiring note (from a Quick sensor replacement writeup)

The sensor leads are a two-conductor wire under the gypsy. On at least one
Quick install the color mapping was blue→black and brown→red, and the hole
was sealed with silicone with a cable tie to prevent chafe. **Verify
against the manual for our specific unit before trusting this.** Quick's
chain counter panels also have a Sensor Status test under the Utilities
menu, useful for verifying the sensor before wiring anything downstream.

#### EMI gotcha (important)

Do **not** route the sensor signal wire alongside the heavy windlass power
cable. It picks up electromagnetic interference badly and produces false
counts. Run it on a separate path and add hardware debouncing on the
counting end.

### 3. Signal K integration path

#### What the ecosystem actually expects

Signal K plugins are built around **accumulated rode length**, not
velocity. Notably, `signalk-anchoralarm-plugin` (sbender9, well
maintained, and [already running aboard](signalk.md#automation-state) for
our anchor alarm) reads a rode counter path — default
`navigation.anchor.rodeCounterLength` — and can:

- auto-set the anchor position when the rode counter passes a threshold
  (or when the anchor reaches the seabed, using depth + bow height)
- use the rode counter value as the alarm radius instead of GPS
- wait a configurable stabilization period after the rode stops changing
  before completing anchoring

So the integration pattern is:

```
gypsy magnet → magnetic sensor → pulse counter → length math → navigation.anchor.rodeCounterLength → anchor alarm plugin
```

The pulse-to-length conversion (chain per gypsy revolution) happens
before Signal K. Nothing downstream wants a raw velocity input.

#### Recommended implementation: ESP32_chain_counter

**Repo:** https://github.com/htool/ESP32_chain_counter

Reads the windlass gypsy pulse sensor, counts pulses, does the length
math, and publishes to Signal K over WiFi. Also emits the B&G chain
counter PGN over NMEA 2000.

This likely removes the need to route the chain signal through the
autoisolator at all — a cheap ESP32 taps the existing two sensor wires
directly.

#### Alternative: Quick's own CAN-bus panels

Quick's CHC-series chain counter panels (e.g. CHC1203, QNC CHC) display
chain out, chain speed, and supply voltage, and network multiple control
units over CAN bus. There is an open Signal K mailing list thread on
connecting a Quick CHC 1203 to Signal K over CAN, but no confirmed working
recipe found. Lower priority than the ESP32 route unless a helm display is
wanted anyway.

### 4. Open questions

- Confirm chain-per-gypsy-revolution figure for the Eagle 1400W.
- Decide: ESP32 direct-to-Signal-K, or route the pulse through the
  autoisolator alongside the other digital signals for consistency?
- Does the autoisolator do pulse counting and arithmetic onboard, or only
  publish raw state changes?
- Up/down direction sensing — a single pulse sensor can't tell deploy
  from retrieve. Options: infer from windlass up/down solenoid state
  (another 12V digital signal), or accept manual reset at zero.

### References

- [ESP32_chain_counter (htool)](https://github.com/htool/ESP32_chain_counter)
- [signalk-anchoralarm-plugin (sbender9)](https://github.com/sbender9/signalk-anchoralarm-plugin)
- [Quick Eagle E1 product page](https://www.quickitaly.com/en/products/windlasses-and-capstans/windlasses-horizontal-axe/eagle-e1/)
- [Quick QNC CHC chain counter manual](https://manuals.plus/quick/qnc-chc-chain-counter-manual)
- [Quick CHC1102M manual (PDF)](https://www.sailorsams.com/assets/images/imt/anchoring/pdf/CHC1102M_manual.pdf)
- [Quick chain sensor install writeup (fetchinketch)](https://fetchinketch.net/boat-projects/quick-chain-sensor-install/)
- [Quick chain counter sensor repair (Out Chasing Stars)](https://outchasingstars.com/repairing-our-quick-chain-counter-sensor/)
- [YBW thread: wiring an up/down counter to a Quick magnetic sensor](https://forums.ybw.com/threads/wiring-an-up-down-counter-to-magnetic-sensor-in-quick-windlass.488233/)
- [Signal K mailing list: Quick CHC 1203 over CAN](https://groups.google.com/g/signalk/c/4hsjdUDk_s0)

---

## SignalK Plugin Conversion

**Status:** Idea / designed, not started
**Scope:** Replace the Pi's Python publisher and this repo's static site with
a published SignalK plugin, configured from the SignalK admin UI.

The tracker today is a Python daemon on the Pi (`scripts/update_signalk_data.py`)
that polls SignalK over HTTP, writes telemetry JSON into a git checkout, and
pushes to this repo, which GitHub Pages serves as [mermug.com](https://mermug.com).
Config lives in `data/vessel/info.yaml` and is edited by hand or via a terminal
wizard. See [SignalK Configuration](signalk.md) for the server side and
[Systems §13](systems.md#13-vessel-data-automation) for the rest of the data stack.

This section is the design for replacing that daemon with a **SignalK server
plugin**, installable from the App Store and configured from the SignalK
admin UI, intended to be published for other boats to use.

<span class="doc-tag doc-tag--planned">Planned</span> Nothing in this section
is built yet. Tracked on [Planned Projects](planned-projects.md#vessel-data-automation).

### Goals

- Configure everything from the SignalK plugin config page — no YAML, no
  wizard, no SSH.
- Keep GitHub Pages as the host: the public site stays static, no server.
- Publishable: an adopter with an empty GitHub repo and a SignalK server can
  be live in one sitting.
- Docs stay exactly as they are — Markdown in `docs/`, edited from the
  GitHub web UI, owned by the human, never touched by the plugin.
- No git checkout on the Pi. Nothing to corrupt, nothing to rebase.

### Non-goals

- Serving the tracker from the boat. That's KIP's job; this site is for
  people ashore.
- Replacing the docs pipeline. Docs are deliberately out of scope
  (see [Docs](#docs) for the one generated file).

### Architecture

```
SignalK server ──(in-process)──▶ plugin ──(GitHub Git Data API)──▶ repo ──▶ Pages
       ▲                            │
  navigation.state              plugin data dir
  (signalk-autostate)           (rolling state, offline queue)
```

| Today | After |
|---|---|
| Python daemon under systemd | Node plugin inside the SignalK server process |
| Polls `/signalk/v1/api/vessels/self` over HTTP | Reads the self tree in-process |
| Cadence from distance-to-marina heuristic | Cadence from `navigation.state` (already provided by signalk-autostate): moored/anchored → hourly, sailing/motoring → 2 min |
| Git checkout on the Pi, `git push`, rebase on conflict | GitHub Git Data API: blobs → tree → commit → ref. No `git` binary, no checkout |
| Rolling state read back from the checkout | Rolling state in the plugin's data dir (`app.getDataDirPath()`); GitHub is publish-only, seeded from the repo on first run |
| `info.yaml` hand-edited on both sides | Plugin config is the source of truth; plugin writes `data/vessel/info.yaml` so the frontend is unchanged |
| Service health via signalk-services-to-signalk watching the systemd unit | `app.setPluginStatus` / `setPluginError` in the admin UI |
| Frontend source in this repo | Frontend shipped inside the plugin package and written into the repo on install and on version upgrade |

#### Repo layout after conversion

The plugin lives in **its own repo** and is published to npm (the App Store
only sees npm). This repo becomes an *instance*: docs, vessel data, and
generated output, with no source code in it.

The plugin writes an ownership manifest (`.tracker-manifest.json`) listing
every path it manages, and never writes outside that list. This is an
allowlist, not a blacklist — anything not named is the user's by default.

| Path | Owner |
|---|---|
| `index.html`, `docs.html`, `assets/`, `sw.js`, `manifest.json`, `.nojekyll` | Plugin (written on install and upgrade) |
| `data/telemetry/**` | Plugin (every cycle) |
| `data/vessel/info.yaml` | Plugin (when config changes) |
| `docs/index.json` | Plugin (when the docs tree changes) — see [Docs](#docs) |
| `docs/*.md` | **User** |
| `data/vessel/logo.png`, `data/vessel/polars.csv` | **User** |
| `assets/custom.css` | **User** — loaded last by `index.html`; the plugin never writes it |
| Everything else | **User** |

`scripts/`, `services/`, `Makefile`, `tests/`, `pyproject.toml`, `uv.lock`,
`.pre-commit-config.yaml` and `.github/workflows/docs-index.yml` are deleted
from this repo once the plugin is live; their replacements live in the plugin
repo.

#### Collisions

With the Git Data API there is no merge. Each publish builds a tree against
the current `HEAD` with only the plugin's paths layered on top, so a docs
edit and a telemetry commit interleave cleanly regardless of order. The only
race is the ref update landing after someone else's push, which is a
re-read-and-retry. The ownership manifest is about *policy* (never clobber a
user file), not merge safety.

### Plugin config (JSON Schema → admin UI)

| Field | Type | Default | Notes |
|---|---|---|---|
| `github.repo` | string | — | `owner/name` |
| `github.branch` | string | `main` | |
| `github.token` | string, `format: password` | — | Fine-grained PAT, Contents: read/write on this repo only. SignalK stores plugin config as plain JSON on disk — document that |
| `interval.underway` | number (s) | 120 | Used when `navigation.state` is sailing / motoring |
| `interval.stationary` | number (s) | 3600 | moored / anchored / unknown |
| `privacyZones[]` | `{name, lat, lon, radius_m}` | `[]` | Positions inside any zone are redacted before storage *and* publish. **Default empty**, not the South Beach fallback hardcoded in the daemon today |
| `timezone` | string | server TZ | Groups GPX tracks by local calendar day |
| `instrumentLog.paths[]` | string | sparkline set | Allowlist of SignalK paths captured per entry — see [Payload size](#payload-size) |
| `instrumentLog.entries` | number | 120 | Rolling length |
| `positionRetentionHours` | number | 24 | |
| `site.theme` | enum | `mermug` | The theme list in `constants.js` |
| `site.marinetrafficShipId`, `site.postgsailLogsUrl`, `site.uscgNumber`, `site.hullNumber` | string | — | Display-only fields the frontend shows |

Vessel name and MMSI come from the server (`app.getSelfPath('name')`,
`app.selfId`) and are **not** config.

**Passage banner**: stays hand-edited in `data/vessel/info.yaml` under the
`passage:` key, which the plugin preserves when it rewrites the file. Moving
it into plugin config would mean editing over the VPN instead of from any
phone with GitHub access, which is a step backwards for a friend ashore.

### Publish cycle

Every tick (interval per `navigation.state`):

1. Snapshot the self tree; drop paths whose timestamp is older than the
   stale threshold (today `STALE_MAX_AGE_MINUTES = 60` on environment /
   navigation / entertainment).
2. Redact positions inside any privacy zone.
3. Update rolling state in the data dir: positions index, instrument log,
   per-day GPX, tracks index. Same file formats as today so the frontend
   doesn't change; each published JSON gains a `schema_version` field so a
   plugin and a frontend of different versions can detect a mismatch.
4. Publish: create one blob per changed file, one tree with `base_tree =
   HEAD`, one commit, update the ref. On a non-fast-forward, re-read `HEAD`
   and retry once. On network failure, keep the state locally and try again
   next tick — same behaviour as today's deferred push, minus the local
   commits.
5. `setPluginStatus("Published 14:32, sailing, next in 2 min")`.

Every call has an `AbortController` timeout. Every tick is wrapped so an
exception skips one cycle rather than reaching the server's event loop —
the daemon's "keep the retry handler inside the loop" rule, in-process.
A plugin bug can now take down the nav data hub, which the separate Python
process could not do; that is the main cost of this design.

### Payload size

<span class="doc-tag doc-tag--issue">Unresolved</span> `instrument_log.json`
is ~1 MB and is committed every 2 min underway. `git push` sends a small
delta; the Git Data API uploads the full base64 blob and does not accept
compressed request bodies, so over the cellular hotspot this is a real
regression — roughly 1.3 MB per cycle. The fix is upstream of the transport:
each entry carries ~167 numeric paths and the sparklines read a dozen. The
`instrumentLog.paths` allowlist brings the file down by an order of
magnitude, at which point the API approach is fine. Do this **before** the
transport switch, in the Python daemon, so the size drop is measured on the
current pipeline. Fallback if it isn't enough: shell out to `git` from a
clone in the data dir and keep the rebase logic.

### Docs

Docs are out of scope for the plugin except for one generated file.
`docs/index.json` is the manifest `docs.html` reads because a static site
can't list a directory; today the `docs-index` GitHub Action rebuilds it on
push. Options:

- **Keep the Action.** One more file adopters must copy into their repo, and
  a Python script in every user's repo. Refreshes on push.
- **Plugin builds it.** The plugin already reads the docs tree through the
  API; it rebuilds `docs/index.json` when the tree SHA changes and commits
  it with the next publish. Refresh latency is the check interval, not the
  push — a conditional request (ETag) every few minutes is free against the
  rate limit, so this can be tight.

Leaning toward the plugin building it: fewer moving parts for adopters, and
the last Python leaves this repo. The Markdown reader (`docs.html`,
`docs.js`) ships with the frontend as plugin-owned code; the content never
does.

### Migration order

- [ ] Add the instrument-log path allowlist to the Python daemon and confirm
      the file size drop on the live pipeline (see [Payload size](#payload-size))
- [ ] Create the plugin repo: TypeScript, `signalk-node-server-plugin`
      keyword, vitest, a dev server that serves the frontend against sample
      telemetry
- [ ] Port the publisher: stale filter, privacy redaction, positions index,
      instrument log, GPX + tracks index. Port the pytest cases alongside
- [ ] Publish via the Git Data API, with the ownership manifest and the
      `schema_version` field
- [ ] Config schema + `info.yaml` writer, preserving `passage:`
- [ ] Move the frontend into the plugin package; add the `custom.css` hook
- [ ] `docs/index.json` builder (or decide to keep the Action)
- [ ] Run both publishers side by side against a scratch repo, diff the
      output for a full sailing day
- [ ] Cut over: install from the App Store on the Pi, disable
      `vesselwebsite.service`, remove it from
      signalk-services-to-signalk, delete the backend files from this repo
- [ ] Publish to npm from a tagged release; README with the Pages setup steps
      and the plaintext-token caveat

### Open questions

- Plugin name. `signalk-github-pages-tracker` is descriptive; check npm.
- Whether to also expose the publish state (last commit SHA, queue depth)
  as SignalK paths so it shows in KIP, replacing what
  signalk-services-to-signalk gives today.
- `@signalk/tracks-plugin` is already installed and exposes a track API;
  whether to build GPX from that instead of the plugin's own position log.

---

## Uplink Phone Telemetry in Signal K

**Status:** Idea / not yet started
**Scope:** Publish the cellular uplink phone's health (battery level and
temperature, charge state, cell signal, network type, uptime) into Signal K.
Write it through a UDP Signal K data connection fed by a root shell script
that Tasker triggers. As a side effect, finish documenting the Tasker
tethering config that is already an open item on
[Planned Projects](planned-projects.md#vessel-data-automation).

### 1. Why

The [Google Pixel 4a](systems.md#internet-connectivity-cellular-hotspot) is
the boat's only internet uplink. Pushover alerts, PostgSail, the Windy
station, the mermug.com telemetry push and AstroWarp remote access all
depend on it. Right now nothing tells us how healthy the phone is.

- **Battery heat.** The phone sits on a charger around the clock in a
  closed cabin. A lithium pouch held at 100% and warm is the classic
  swelling failure. Logging battery temperature is the cheapest early
  warning.
- **Signal quality.** RSRP and network type (LTE vs. NR) explain slow or
  dropped uplink at different berths and anchorages. Without them we're
  guessing whether a problem is the phone, the carrier or the router.
- **Uptime.** Unexpected reboots show up as uptime resets. A reboot
  silently breaks tethering if the Tasker charge-start trigger doesn't
  re-fire.

### 2. Current state (from these docs)

- SignalK runs at `192.168.8.50:3000`, no SSL, token security,
  `allow_readonly` on. See [SignalK Configuration](signalk.md#server).
- The phone is rooted, on Visible Plus, and runs Tasker. Tasker enables
  tethering on charge start, and a follow-on script grants the boat
  network access. The exact profile and script are **not documented**.
- The phone also loads KIP as a status page, so it can already reach the
  Pi over HTTP in at least one direction. The tether topology is not
  recorded (see Open Questions).

### 3. Design

#### 3.1 Network path (decide first)

Everything else depends on whether the phone can reach the Pi.

- **Phone is on the boat LAN side** (e.g. Pi USB-tethered directly, or
  the grant script bridges the phone onto `192.168.8.0/24`): send straight
  to `192.168.8.50`. Nothing else needed.
- **Phone is the router's WAN upstream** (hotspot or USB tether into the
  router WAN): the phone sits outside the router's NAT. Add a router port
  forward, WAN UDP 7777 to `192.168.8.50:7777`. The phone then targets
  the router's address on the tether subnet (`ip neigh` on the phone).

A reverse proxy is **not** part of this design. It would need the same
port forward and adds a service to maintain. Revisit only if we later want
TLS or a single authenticated HTTP endpoint for several devices.

Test: from a root shell on the phone, run `ping 192.168.8.50`.

#### 3.2 Signal K ingest: UDP data connection

In SignalK admin, go to **Server → Data Connections → Add**:

| Setting | Value |
|---|---|
| Data Type | Signal K |
| Signal K Source | UDP |
| Port | 7777 |
| ID | `pixel4a` (becomes the `$source` label) |

The server accepts delta JSON datagrams directly, so there are no plugins,
no Node-RED flow and no device token for ingest. UDP is unauthenticated,
which is acceptable because the port is only reachable from the vessel LAN
or the tether subnet. **Never forward it from the open internet.** A lost
packet costs one status sample, which doesn't matter at a 2-minute
cadence.

**Rejected alternative:** Node-RED `http in` → change node (JSONata) →
`signalk-send-pathvalue`, gated on a shared-secret header. It has
delivery confirmation and auth, but it's more parts to maintain. Switch to
it only if UDP loss or spoofing becomes a real problem.

#### 3.3 Data paths

Standard Signal K paths where the spec has them, so KIP unit conversion
works. Custom paths under `communication.cellular` otherwise.

| Path | Units | Source on phone | Spec |
|---|---|---|---|
| `electrical.batteries.phone.stateOfCharge` | ratio 0–1 | `dumpsys battery` level / 100 | Standard |
| `electrical.batteries.phone.temperature` | K | `dumpsys battery` temperature (tenths °C) | Standard |
| `electrical.batteries.phone.chargingMode` | string | `dumpsys battery` status | Standard |
| `communication.cellular.rsrp` | dBm | `dumpsys telephony.registry` | Custom |
| `communication.cellular.networkType` | string | `getprop gsm.network.type` | Custom |
| `communication.cellular.uptime` | s | `/proc/uptime` | Custom |

For Android `dumpsys battery` status, 2 = charging, 3 = discharging,
4 = not charging and 5 = full.

#### 3.4 Collection script

Keep Tasker as the trigger only. Root shell reads are more reliable than
Tasker's built-in variables. `%CELLSIG` is the legacy 0–8 scale and often
returns -1 on Android 10+.

Proposed location: `/data/local/tmp/sk_status.sh` on the phone, with a
copy committed to this repo so the config is documented.

```sh
#!/system/bin/sh
# Publish uplink phone health to SignalK over UDP.
HOST=192.168.8.50   # or router tether-side IP if forwarded (see 3.1)
PORT=7777

B=$(dumpsys battery)
LVL=$(echo "$B" | awk '/^  level:/{print $2/100}')
TK=$(echo "$B"  | awk '/^  temperature:/{print $2/10+273.15}')
ST=$(echo "$B"  | awk '/^  status:/{print $2}')
case "$ST" in
  2) MODE=charging ;; 3) MODE=discharging ;;
  4) MODE=not-charging ;; 5) MODE=full ;; *) MODE=unknown ;;
esac

RSRP=$(dumpsys telephony.registry | grep -o 'rsrp=-[0-9]*' | head -1 | cut -d= -f2)
NET=$(getprop gsm.network.type | cut -d, -f1)
UP=$(cut -d' ' -f1 /proc/uptime)

printf '{"updates":[{"values":[
{"path":"electrical.batteries.phone.stateOfCharge","value":%s},
{"path":"electrical.batteries.phone.temperature","value":%s},
{"path":"electrical.batteries.phone.chargingMode","value":"%s"},
{"path":"communication.cellular.rsrp","value":%s},
{"path":"communication.cellular.networkType","value":"%s"},
{"path":"communication.cellular.uptime","value":%s}
]}]}\n' "$LVL" "$TK" "$MODE" "${RSRP:-null}" "$NET" "$UP" \
  | toybox nc -u -w1 "$HOST" "$PORT"
```

Verify before trusting the script:

- [ ] `toybox nc --help` lists `-u` on the phone's toybox build
- [ ] `dumpsys battery` indentation matches the awk anchors
- [ ] `dumpsys telephony.registry` emits `rsrp=` on LTE (on NR it may
  only emit `ssRsrp=`, so extend the grep if RSRP comes back null on 5G)
- [ ] `getprop gsm.network.type` returns something useful and not
  `Unknown`

#### 3.5 Tasker profile

- **Trigger:** Time context repeating every 2 min, all day.
- **Task:** Run Shell, `sh /data/local/tmp/sk_status.sh`, **Use Root** on.
- Exempt Tasker from battery optimization. Doze shouldn't apply while the
  phone is charging, but the exemption covers unplugged periods, which are
  exactly when the data matters most.

#### 3.6 Staleness watchdog (Node-RED, no function nodes)

Signal K keeps the last value forever, so a dead phone looks healthy.
Subscribe to `communication.cellular.uptime` and feed a `trigger` node set
to "send nothing, then after 5 min send". The output sets
`notifications.communication.cellular.stale` to `alert` for display at the
nav station in KIP and Freeboard. Any new sample resets the trigger and
sends a `normal` state.

**Known limitation:** Pushover can't deliver this alert, because Pushover
goes out through the phone that just died. It is a local-only alarm. From
off the boat, AstroWarp dropping is the only remote signal.

#### 3.7 Battery protection

Logging temperature only helps if we act on it. Once the data is flowing:

- Cap charge around 80% using a root charge controller (e.g. the
  ACC module, if the phone is rooted via Magisk). Confirm the cap works by
  watching `stateOfCharge` plateau and `temperature` drop.
- Add a SignalK zone on `electrical.batteries.phone.temperature`: warn at
  104 °F (313 K), alarm at 113 °F (318 K).

### 4. Failure modes

| Failure | Effect | Mitigation |
|---|---|---|
| Phone can't route to Pi | No data, silently | Test in 3.1 first; port forward if phone is WAN-side |
| Phone reboots, Tasker trigger doesn't re-fire | No tether, no telemetry | Uptime reset visible in history; staleness watchdog fires |
| Phone dies / battery swells | Uplink lost; alerts can't leave the boat | Charge cap, temperature zone, local watchdog |
| UDP port exposed beyond LAN | Anyone can inject deltas | Forward only on tether-side WAN, never from internet |
| Android update changes `dumpsys` output | Nulls or garbage values | Script sends `null` on missing RSRP; eyeball values after any OS update |
| Tasker killed by battery optimization | Gaps while unplugged | Optimization exemption (3.5) |

### 5. Build plan

- [ ] Record the tether topology (hotspot vs. USB, router WAN vs. Pi) in
  [Internet Connectivity](systems.md#internet-connectivity-cellular-hotspot)
- [ ] Export the existing Tasker tethering profile and grant script and
  document them there (closes the existing Planned Projects item)
- [ ] Confirm phone → Pi reachability; add the router port forward if
  needed
- [ ] Add the `pixel4a` UDP data connection in SignalK
- [ ] Run the script by hand from `adb shell su` and confirm all six paths
  appear in the SignalK data browser with sane values
- [ ] Add the Tasker 2-minute profile
- [ ] Build the Node-RED staleness watchdog; test by disabling the profile
- [ ] Add the temperature zones
- [ ] Install the charge cap; confirm via history over 48 h
- [ ] Add a KIP panel (phone battery %, temperature, RSRP)
- [ ] Optional: add the phone paths to the mermug.com telemetry allowlist
  once the [instrument log allowlist](project-ideas.md#payload-size) exists
- [ ] Document the final config in [SignalK Configuration](signalk.md) and
  log the change in the [Changelog](changelog.md)

### 6. Open questions

- How exactly is the phone tethered: Wi-Fi hotspot or USB, and into the
  router or the Pi? What does the "grant access" script do?
- Is the phone rooted via Magisk (which the ACC charge cap needs)?
- Should the script also report tether state and data used? Only worth it
  if Visible Plus hotspot throttling turns out to matter in practice.

### 7. Done when

- All six paths update in SignalK every ~2 min for 7 consecutive days.
- Unplugging the phone and killing Tasker raises the stale notification
  within 5 min.
- Phone battery temperature history shows the charge cap holding it below
  the warn threshold at the dock in warm weather.
