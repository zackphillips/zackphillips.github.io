---
title: SignalK Configuration
category: Reference
order: 11
description: What's running on the onboard SignalK server — data sources, sensors, and what each enabled plugin does.
---

# S.V. Mermug — SignalK Configuration

SignalK is the data hub aboard: it pulls in NMEA 2000, NMEA 0183 and
Bluetooth sensor data, derives additional values, and feeds both the onboard
[KIP](https://github.com/mxtommy/Kip) instrument display and the
[mermug.com](https://mermug.com) tracker (see [Systems Overview §6](systems.md#6-navigation-electronics)
and [§11](systems.md#11-vessel-data-automation)).

This page summarizes what's actually **enabled and in use** on the server —
not every plugin option. Where useful, plugin names link to their source
repo (GitHub where confirmed, npm otherwise) rather than repeating their
full documentation here.

---

## Server

| Setting | Value |
|---|---|
| Server | SignalK Node server, Raspberry Pi at `192.168.8.50:3000` |
| SSL | Disabled |
| Security | Token-based; `allow_readonly` on, device-access requests open, new-user registration open |
| mDNS | Disabled |
| Context pruning | Stale contexts (other vessels/AIS targets) pruned after 60 min |

> The open device-access/registration settings are fine for a private vessel
> LAN but worth tightening before any port-forwarding or public exposure.

---

## Data Sources (`pipedProviders`)

| id | Type | Details |
|---|---|---|
| `can0` | NMEA 2000 via [canboatjs](https://github.com/canboat/canboatjs) (SocketCAN) | Filters 2 PGNs by source: source 1 drops PGN 130850, source 6 drops PGN 127489 |
| `tacktick` | NMEA 0183 serial, `/dev/ttyOP_tacktick`, 4800 baud | Legacy Raymarine/Tacktick wireless pack — SignalK is configured to **ignore** RMC/RMB/GLL/MWV/VWR from it, so it's wired but not the active wind/nav source (see [Systems §6, Wind Instruments](systems.md#wind-instruments)) |
| `furuno` | NMEA 0183 serial, `/dev/ttyOP_furuno`, 4800 baud, checksum validated | Furuno NavNet chartplotter/radar — used as fallback next-waypoint/course source |
| `i2c-sensors` | SignalK-over-UDP, `localhost:4123`, `useRemoteSelf` | Local bridge for the I2C BME280 temp/humidity/pressure sensor (bus 1, addr `0x77`) |
| `nmea0183-tcp` | NMEA 0183 TCP server | Ignores RMC, no checksum validation — feeds external NMEA 0183 clients (e.g. nav apps) |
| `gpspuck` | NMEA 0183 serial, `/dev/ttyOP_gpspuck`, 4800 baud, checksum validated, overrides timestamp | Primary GPS ("puck"); ignores its own RMC (position comes via other sentences) |

**Autopilot**: Simrad, v2 API enabled — device ID 204, converter 115, Simrad
ID 4. Output goes to `seatalkOut`.

> **Open item**: the GPS antenna offset is recorded twice and disagrees —
> `baseDeltas.json` has 7.95 m from bow / 0.45 m from centerline, while
> `settings.json`'s `gnssSensors` (gps1 @ `gpspuck.GP`) has 6.5 m / 1.7 m.
> Worth reconciling with an actual measurement before trusting either for
> anchor-swing or docking calculations.

---

## Sensors & Instrumentation

| Source | What it provides |
|---|---|
| NMEA 2000 network (`can0`) | Engine (port only), tanks, GPS/AIS, depth, wind |
| [signalk-victron-ble](https://github.com/stefanor/signalk-victron-ble) | Two Victron devices over BLE: house battery monitor, and a second device ("bimini") reporting solar charger power/voltage — see [Systems §4](systems.md#4-electrical-system) |
| [bt-sensors-plugin-sk](https://github.com/naugehyde/bt-sensors-plugin-sk) (Mopeka ultrasonic, BLE) | `fuel.reserve` (diesel, 400 mm tank height), `propane.a` / `propane.b` (230 mm each), `blackwater.stern` (355.6 mm) |
| I2C bus | BME280 environmental sensor — chip-ID readout configured; presumably also feeds temp/humidity/pressure through the `i2c-sensors` bridge above |
| [signalk-rpi-monitor](https://github.com/sberl/signalk-rpi-monitor) | Pi CPU temp/utilization, GPU temp, memory, SD card utilization — polled every 30 s |
| Internet speed test plugin | Enabled, hourly |

---

## Calibration (raw NMEA 2000 tank-sender curves)

- Freshwater tanks 0 & 1: capacity fixed at 0.265 m³ each (~70 gal), level curve 0→0%, 0.1→100%
- Fuel tank 0: capacity 0.151 m³ (~40 gal), near-linear level curve
- Live well: capacity curve, 0→0, 0.001→100%
- Port engine shaft RPM correction table (raw sender Hz → true prop shaft RPM), e.g. 108.2 Hz → 48.33 RPM

Managed by [@signalk/calibration](https://github.com/SignalK/calibration).

---

## Derived Data

[signalk-derived-data](https://github.com/SignalK/signalk-derived-data) is
configured for: magnetic COG, set/drift, calculated heading (kFactor 12),
depth-below-keel (variant 2), port engine running-state, sun/sun-time, true
wind + apparent wind angle over water, ground wind, a secondary tank-volume
calc for `fuel.0`/`freshWater.0`/`freshWater.1`, and a manual volume curve
for `fuel.reserve` (0→0 gal, 100%→30 gal).

Tracked instances: engine — port only; battery — house; tanks —
`liveWell.0`, `fuel.0`, `fuel.reserve`, `freshWater.0`, `freshWater.1`; air —
inside/outside.

---

## Alarms / Zones

Set via [@signalk/zones](https://github.com/SignalK/zones) (meta) plus
[signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin):

| Path | Thresholds |
|---|---|
| House battery SOC | Alarm <20%, warn 20–40%, alert (charging/discharging) 40–80% |
| Freezer temp | Warn if it drifts into fridge range (274–295 K), alert if effectively off (>295 K) |
| Fridge temp | Warn if below freezing, alert if off (≥295 K) |
| Propane A | Alert below 30% |
| Propane B | Alert below 25% |
| Inside temp | Alert below freezing (274 K) |
| Fuel tank 0 volume | Alert under ~0.04 m³, again under ~0.02 m³ |
| Live well / bilge level | Nominal to 60%, alert 60–80%, warn 90–100% |
| RPi SD card usage | Alert 75–90%, alarm 90–100% |

**Anchor alarm**: emergency on drag, no-position alarm after 10 min,
"incomplete anchor alarm" after 10 min. Currently the live autostate shows
anchored.

---

## Automation & State

| Plugin | What it does |
|---|---|
| [signalk-autostate](https://github.com/meri-imperiumi/signalk-autostate) | Derives `navigation.state` automatically (currently reporting "anchored") |
| [signalk-switch-automation](https://github.com/sbender9/signalk-switch-automation) | Fires `notifications.navigation.state.moored` / `...sailing` based on `navigation.state` |
| signalk-notify | Emits a "vessel-moored" event notification |
| signalk-services-to-signalk | Surfaces the `vesselwebsite.service` systemd unit's health into SignalK at `environment.{service}.serviceStatus` — this is the mermug.com Pi-side service being monitored |
| signalk-engine-hours | Monitors `propulsion.*.revolutions` (port), 60 s update; its own independent counter reads ≈6,659 hrs since it was installed — **not** the same as the engine's true lifetime hours (6,381.7 hrs @ May 2025 survey, see [Systems §2](systems.md#2-engine-drive)); don't conflate the two without checking install date |
| [signalk-triplogger](https://github.com/meri-imperiumi/signalk-triplogger) | Cumulative log since 2026-07-09 — 284,195 total distance units, split 227,183 motoring / 57,012 sailing / 0 moored / 0 anchored (units likely nm×100 or similar raw log ticks — verify scale before quoting) |
| set-system-time | Keeps the Pi clock synced, prefers network time, 60 s interval |

---

## Priorities (multi-source failover)

15 s fallback timeout on all groups.

| Value | Order |
|---|---|
| Outside air temp | Local GPIO 1-Wire sensor → merged virtual weather sensor |
| Water temp | NMEA 2000 sender → Open-Meteo marine forecast |
| Navigation core (position/COG/SOG/GNSS) | NMEA 2000 GPS sources (chained) → `gpspuck` → derived-data (last resort) |
| Next-waypoint course data | `courseApi` → Furuno NMEA 0183 chartplotter |
| Trip log | `signalk-triplogger` → NMEA 2000 log sender → Tacktick log |

---

## Charts & Mapping

| Plugin | What it does |
|---|---|
| [@signalk/freeboard-sk](https://github.com/SignalK/freeboard-sk) + [@signalk/charts-plugin](https://github.com/SignalK/charts-plugin) | Layered NOAA ENC chart stack (composite, land-only, depth-only, aids-to-nav tile layers) plus NCEI bathymetry shaded relief, with OpenStreetMap as a worldwide fallback base layer |
| signalk-crows-nest | Points-of-interest/hazard overlay: NOAA ENC wrecks/obstructions, USCG Light List, USCG Notice to Mariners all enabled and caching. OpenSeaMap, NOAA CO-OPS tide-current-stations, WPI, and USACE lock-dam layers exist but are disabled |
| signalk-marinetraffic-public | Public AIS overlay, 120 s refresh, 10 nm box |
| sk-ais-status | Tracks AIS target confirmation timing |

---

## Weather / Tides

| Plugin | What it does |
|---|---|
| `tides` / `tides-api` | NOAA tide source, 60 s refresh |
| signalk-virtual-weather-sensors | Currently **disabled**; configured to merge Open-Meteo + met.no marine forecasts when on |
| signalk-nws-alerts | NWS marine weather alerts, position-subscribed, polling every 60 s |
| [signalk-windy-plugin](https://github.com/Saillogger/signalk-windy-plugin) (npm `signalk-windy`) | Enabled — feeds Windy.com community weather station data |
| signalk-gusts | Enabled |

---

## NMEA Cross-Conversion / Multiplexer Role

| Plugin | What it does |
|---|---|
| [@signalk/signalk-to-nmea0183](https://github.com/SignalK/signalk-to-nmea0183) | Converts SignalK back to NMEA 0183 — APB, DPT, GGA, GLL, HDM, HDTC, MTW, MWVR/MWVT, RMB, RSA, VWR/VWT, XTE/XTE-GC, ZDA — feeds legacy instruments/autopilot from modern sources |
| [signalk-n2kais-to-nmea0183](https://github.com/sbender9/signalk-n2kais-to-nmea0183) | Converts AIS from NMEA 2000 to NMEA 0183 output |
| [sk-to-nmea2000](https://github.com/SignalK/signalk-to-nmea2000) | Mostly disabled except navigation data, route/waypoint info, XTE, bearing/distance-to-marks, time-to-mark — feeds a legacy NMEA 2000 chartplotter/autopilot the active route |
| signalk-nmea2000-emitter-cannon | Similar role: nav/route/XTE data and house battery broadcast enabled out to NMEA 2000; most other PGNs disabled |

---

## Notifications / Alerting

| Plugin | What it does |
|---|---|
| signalk-notification-player | Browser/audio alarm player, mapped to `Alarm.playAlarmNr` sound levels for warn/alert/alarm/emergency |
| signalk-alarm-silencer | Enabled |
| signalk-pushover-notification-relay | Pushes battery SOC and SD-card-utilization notifications to a phone via Pushover |
| signalk-twilio-notifications | SMS alert for house battery <20% — currently **disabled** |
| [signalk-mob-notifier](https://github.com/meri-imperiumi/signalk-mob-notifier) | Man-overboard BLE-tag notifier — currently **disabled** |

---

## Cloud / Remote Integrations

| Plugin | What it does |
|---|---|
| [signalk-postgsail](https://github.com/xbgmsharp/signalk-postgsail) | Enabled — reports depth, battery voltage/SOC, solar (bimini) power/voltage, fuel reserve level, inside humidity/pressure/temp, fridge/freezer temp, both propane levels, and water temp to `api.openplotter.cloud` |
| signalk-to-influxdb2 | Present but **disabled** (org "Mermug", bucket "signalk"; would exclude GNSS metadata and derived-data/tides as sources) |
| @signalk/app-dock | Local kiosk launcher — autostarts Freeboard-SK, also exposes KIP and the admin Settings page |
| [@mxtommy/kip](https://github.com/mxtommy/Kip) | Instrument display webapp; SQLite-backed history series enabled and registered as a SignalK History API provider |
| signalk-node-red | Installed but **disabled** |

---

## Entertainment / Other

| Plugin | What it does |
|---|---|
| [fusionstereo](https://github.com/sbender9/signalk-fusion-stereo) | Fusion NMEA 2000 stereo control; alarm-zone integration configured (cockpit/cabin zones, alarm on Aux1 input) but alarms currently disabled |
| signalk-garmin-race-timer / signalk-racer | Racing start-line timer/bias tools — `racer` enabled, no start lines currently saved |
| signalk-restricted-areas | NE Pacific dataset, geofencing (anchoring/entry alerts, 1 nm approach) — currently **disabled** |
| [collision-detector](https://github.com/VladimirKalachikhin/collision-detector) | CPA/velocity-vector risk-of-collision plugin — currently **disabled** |
| speedtest.net plugin | Disabled (distinct from the internet speed test plugin listed under Sensors, which is enabled) |
| signalk-timezone-plugin | Disabled (position-based mode configured) |

---

## Package Manifest

`package.json` tracks the core install:
[@signalk/freeboard-sk](https://github.com/SignalK/freeboard-sk),
[@mxtommy/kip](https://github.com/mxtommy/Kip),
@signalk/app-dock,
[@signalk/charts-plugin](https://github.com/SignalK/charts-plugin),
@signalk/course-provider,
[@signalk/calibration](https://github.com/SignalK/calibration),
@signalk/zones,
@signalk/resources-provider,
@signalk/tracks-plugin,
[@signalk/signalk-to-nmea0183](https://github.com/SignalK/signalk-to-nmea0183),
@signalk/open-meteo-provider,
@sailingnaturali/signalk-currents,
[@meri-imperiumi/signalk-autostate](https://github.com/meri-imperiumi/signalk-autostate),
[@meri-imperiumi/signalk-mob-notifier](https://github.com/meri-imperiumi/signalk-mob-notifier),
[@meri-imperiumi/signalk-triplogger](https://github.com/meri-imperiumi/signalk-triplogger),
[@canboat/visual-analyzer](https://github.com/canboat/canboatjs),
plus the third-party plugins named above.

Several plugins referenced here (e.g. signalk-logbook, signalk-saillogger,
signalk-noaa-weather, signalk-node-red, signalk-to-influxdb2,
signalk-restricted-areas, signalk-timezone-plugin,
signalk-nmea2000-emitter-cannon, sk-to-nmea2000, voyage-data-recorder) have
config files on disk but aren't in `package.json`'s dependency list — they
were most likely installed directly via the SignalK App Store rather than
tracked in that file. **`package.json` alone is not the full plugin
inventory.**

---

## Known Data-Quality Notes

Worth resolving before treating this page (or the SignalK config) as ground
truth for anything safety-critical:

- **GPS antenna offset** is recorded twice, disagreeing (see above).
- **Engine hours**: `signalk-engine-hours`'s ≈6,659 hr counter is its own
  running total since installation, not the engine's documented lifetime
  hours (6,381.7 @ May 2025 survey) — check when the plugin was installed
  before comparing the two.
- **Trip log units**: `signalk-triplogger`'s totals (284,195 / 227,183 /
  57,012) are likely nm×100 or similar raw ticks — verify the scale before
  quoting a distance.
- **Vessel dimensions**: `baseDeltas.json` records metric dimensions (LOA
  12.95 m, beam 4.11 m, max draft 2.31 m) that don't exactly match the
  imperial specs in [Systems §1](systems.md#1-hull-rig) (42' 06" LOA, 13'
  06" beam, 7' 07" draft) once converted and rounded — worth a careful
  cross-check rather than overwriting either side blindly.
