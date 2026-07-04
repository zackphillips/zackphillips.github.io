# S.V. Mermug — Systems Overview

42.7-ft sloop, Hull #BEY57004E494  
This document describes the major onboard systems: what's installed, where it is, how it works, and what to watch out for.

---

## Table of Contents

1. [Hull & Rig](#1-hull--rig)
2. [Engine & Drive](#2-engine--drive)
3. [Fuel System](#3-fuel-system)
4. [Electrical System](#4-electrical-system)
5. [Plumbing & Freshwater](#5-plumbing--freshwater)
6. [Navigation & Electronics](#6-navigation--electronics)
7. [Safety Equipment](#7-safety-equipment)
8. [Ground Tackle](#8-ground-tackle)
9. [Sails & Running Rigging](#9-sails--running-rigging)
10. [Vessel Data / Automation](#10-vessel-data--automation)

---

## 1. Hull & Rig

| Spec | Value |
|------|-------|
| LOA | 42.7 ft |
| Beam | 13.9 ft |
| Draft | 6.2 ft |
| Displacement | — |
| Ballast | — |
| Rig type | Sloop (masthead / fractional — confirm) |
| Mast material | Aluminum |
| Boom | — |

### Standing Rigging
- **Forestay**: [wire / rod] — [size]
- **Backstay**: [wire / rod] — adjustable? [yes/no]
- **Upper shrouds**: [size / chainplate location]
- **Lower shrouds**: [fore lowers, aft lowers]
- **Babystay / inner forestay**: [installed? yes/no]

### Last Rig Inspection
Date: —  
Inspector: —  
Notes: —

---

## 2. Engine & Drive

| Spec | Value |
|------|-------|
| Make/Model | — |
| Year | — |
| HP | — |
| Cylinders | — |
| Fuel | Diesel |
| Hours (as of last log) | — |
| Raw water pump impeller | — |
| Oil spec | — |
| Oil capacity | — |
| Coolant type | — |
| Drive | Shaft drive |
| Transmission | — |
| Propeller | [folding / feathering / fixed], [diameter × pitch] |
| Shaft zinc | Replace at haulout |

### Engine Location
Accessed via companionway steps (lift steps) and engine compartment panels. Raw water seacock is [location]. Bleed screws are [location].

### Starting & Stopping
See [Operations Guide — Engine Start Procedure](operations.md#engine-start-procedure).

### Raw Water Cooling Circuit
Raw water enters via seacock → strainer (starboard, under steps) → impeller pump → heat exchanger → exhaust mixing elbow → out transom. **Check exhaust flow within 30 seconds of start.**

### Engine Alarms
- **High temp**: [alarm sound / light — describe]
- **Low oil pressure**: [describe]
- **Alternator fault**: [describe]

---

## 3. Fuel System

| Spec | Value |
|------|-------|
| Tank capacity | — gallons |
| Tank material | [aluminum / poly / fiberglass] |
| Tank location | Under [salon sole / quarter berth] |
| Fuel type | Diesel |
| Primary filter | [location] |
| Racor (secondary filter) | [location] |
| Fill deck plate | [port / starboard / both] |

### Fuel Gauge
Located at [nav station / helm]. Accuracy: [note if gauge is unreliable — e.g., only accurate when heeled < X°].

### Bleeding the Engine
If air enters the fuel system (e.g., ran tank dry):
1. [Describe bleed procedure for this specific engine]
2. Bleed Racor first — open bowl petcock, pump primer until fuel flows.
3. Bleed injection pump at [location].

### Fuel Management
- Fill before offshore passages; diesel stores well.
- Treat with biocide if boat sits unused for extended periods.
- Log fuel additions in the [engine hours log / ship's log].

---

## 4. Electrical System

### Battery Bank

| Bank | Type | Capacity | Location |
|------|------|----------|----------|
| House bank | [AGM / lithium / flooded] | — Ah | [location] |
| Start battery | [type] | — Ah | [location] |

### Battery Monitor
- **Make/Model**: [e.g., Victron BMV-712]
- **Location**: Nav station / helm
- Monitors house bank state of charge, voltage, current draw, and time-to-empty.
- SignalK reports SOC and draw — visible on [mermug.com](https://mermug.com).

### Charging Sources

| Source | Capacity | Notes |
|--------|----------|-------|
| Shore power charger | [A] / [W] | [make/model] |
| Engine alternator | [A] | [size] |
| Solar | [W] | [panel count, location, controller make/model] |
| Wind gen | — | installed? |

### Shore Power
- **Inlet**: [30A / 50A], [location on boat]
- **Converter/Charger**: [make/model], located [location]
- Connects to dock pedestal via shore power cord; confirm polarity light is green.

### DC Panel
Located at nav station. Circuits labeled:
- [List circuits as you learn them, e.g.:]
  - 1: Navigation lights
  - 2: VHF
  - 3: Instruments
  - 4: Cabin lights
  - 5: Bilge pump (auto)
  - 6: Anchor windlass (via breaker at bow)
  - ...

### AC Panel
Located at [nav station / electrical panel].
- Main breaker: [location]
- Shore power breaker: [A]
- Circuits: [list as known]

### Inverter
- **Make/Model**: —
- Capacity: — W
- Location: —
- Note: do not run high-draw appliances (microwave, kettle) without engine running unless battery is at ≥80%.

---

## 5. Plumbing & Freshwater

### Freshwater System

| Spec | Value |
|------|-------|
| Tank capacity | — gallons |
| Tank location | [under V-berth / settee / other] |
| Pump | [make/model], [pressure switch or manual] |
| Hot water heater | [engine heat exchanger / AC element / both?] |
| Fill deck plate | [location] |

### Freshwater Conservation
Typical consumption underway: ~[X] gallons/day. Fill at marina before any offshore passage.

### Head (Marine Toilet)

| Spec | Value |
|------|-------|
| Type | [manual / electric] |
| Make/Model | — |
| Holding tank capacity | — gallons |
| Holding tank location | [forward, under V-berth?] |
| Pump-out deck fitting | [location] |
| Overboard discharge Y-valve | [location] — confirm legal (offshore only outside 3 nm) |

**Operating the head:**
1. Open inlet seacock.
2. [Manual: describe stroke procedure] / [Electric: describe button sequence]
3. Close inlet seacock when done at anchor or in sensitive areas.

**Pump-out**: at marina pump-out station or via [portable pump-out service].

### Bilge

- **Automatic bilge pump**: [location], float switch — activates automatically.
- **Manual bilge pump**: [location — cockpit?]
- **Inspection**: check bilge level on every departure; some accumulation (rain, condensation) is normal.

### Seacocks & Through-Hulls

| Location | Purpose | Normally |
|----------|---------|---------|
| Starboard under steps | Engine raw water intake | Open underway, closed at anchor/dock |
| Forward [location] | Head intake | Open when using head |
| [location] | Head discharge | Open when using head (offshore) |
| [location] | Cockpit drains | Open |
| [location] | Other | — |

> Know every seacock. Be able to close them all in the dark.

---

## 6. Navigation & Electronics

### Chartplotter / MFD
- **Make/Model**: —
- **Location**: Helm / nav station
- Connected to: GPS antenna, AIS, instruments, depth
- Charts loaded: —

### VHF Radio
- **Make/Model**: —
- **Location**: Nav station / helm
- DSC equipped: yes/no — MMSI programmed: **338543654**
- Always monitor **Ch 16**.

### AIS
- **Type**: Class B transponder (transmit + receive)
- **Make/Model**: —
- Integrated with chartplotter; MMSI: **338543654**
- Verify targets visible on chartplotter on departure.

### Depth Sounder
- **Make/Model**: —
- Transducer location: [under hull, forward/aft of keel]
- **Offset**: [keel depth below transducer: — ft] — displayed depth is from transducer, not keel.
- Alarm: set for 10 ft below keel minimum.

### Wind Instruments
- **Masthead unit**: [make/model]
- Displays: apparent wind angle, apparent wind speed; converts to true wind via boat speed/COG.
- Note any calibration offsets here when determined.

### Autopilot
- **Make/Model**: —
- **Type**: [below-decks ram / wheel drive / tiller]
- **Control head location**: helm
- Limits: [max sea state / wind it's trusted in]

### Compass
- **Location**: binnacle
- **Deviation card**: [on file / not yet swung]

### Radar
- **Installed**: [yes / no]
- **Make/Model**: —
- **Type**: [dome / open array], [kW], [range]

### SignalK Server
- Running on Raspberry Pi at `192.168.8.50:3000`.
- Aggregates all NMEA/instrument data onboard.
- Feeds the KIP display (main instrument dashboard) and the mermug.com tracker.
- See the [mermug.com tracker repo](https://github.com/zackphillips/zackphillips.github.io) for the telemetry pipeline.

---

## 7. Safety Equipment

| Item | Quantity | Location | Expiry/Service |
|------|----------|----------|----------------|
| Life jackets (USCG approved) | — | [location] | Inspect annually |
| Horseshoe buoy | 1 | Stern rail | — |
| Throwable cushion (Type IV) | 1 | Cockpit | — |
| Handheld flares | — | [location] | [date] |
| Parachute flares | — | [location] | [date] |
| Smoke signals | — | [location] | [date] |
| EPIRB | 1 | [location] | Battery: [date]; Registration: [date] |
| PLB(s) | — | [location] | — |
| Fire extinguishers | — | [locations] | [service date] |
| Life raft | [yes/no] | [location] | Inspect: [date] |
| Ditch bag | 1 | [location] | Contents current: [date] |
| Tethers / jacklines | — | [location] | — |
| Harnesses | — | [location] | — |

### Ditch Bag Contents
- [ ] EPIRB / PLB
- [ ] Handheld VHF (charged)
- [ ] Flares (in-date)
- [ ] Water (1 liter minimum per person)
- [ ] Knife
- [ ] Mirror
- [ ] Copies of ship's papers
- [ ] Cash
- [ ] First aid
- [ ] [any boat-specific additions]

---

## 8. Ground Tackle

### Primary Anchor
- **Type**: Delta (plough)
- **Weight**: 35 lb
- **Chain**: 200 ft, 5/16" BBB or G40
- **Rode**: 150 ft, 5/8" nylon
- **Storage**: bow anchor locker, starboard side

### Secondary Anchor
- **Type**: —
- **Weight**: —
- **Rode**: —
- **Storage**: —

### Windlass
- **Make/Model**: —
- **Type**: electric, foot switches at bow
- **Breaker**: nav station, [circuit label]
- **Manual override**: [location]
- **Note**: do not run more than [X] minutes continuously; allow to cool.

---

## 9. Sails & Running Rigging

### Inventory

| Sail | Type | Area (sq ft) | Condition | Notes |
|------|------|-------------|-----------|-------|
| Main | [full-batten / partial-batten] | — | — | In-mast or on boom? |
| Headsail #1 (genoa) | [% overlap] | — | — | Furling |
| Headsail #2 (working jib) | — | — | — | [hanked / furling] |
| Spinnaker | [sym / asym] | — | — | — |
| Storm jib | — | — | — | [hanked to inner stay?] |
| Trysail | [yes/no] | — | — | — |

### Running Rigging Summary

| Line | Purpose | Color/ID | Clutch/Cleat |
|------|---------|----------|-------------|
| Main halyard | Raise/lower main | — | [mast cleat / clutch] |
| Jib halyard | Raise/lower headsail | — | — |
| Mainsheet | Main trim | — | Traveler block to cleat |
| Port jib sheet | Headsail trim | — | — |
| Starboard jib sheet | Headsail trim | — | — |
| Vang | Leech tension | — | — |
| Cunningham | Luff tension | — | — |
| Outhaul | Foot tension | — | — |
| Reef 1 | First reef, leech | — | — |
| Reef 2 | Second reef, leech | — | — |
| Furling line (headsail) | Furl/unfurl headsail | — | — |
| Topping lift | Boom support | — | — |

### Sail Trim Notes
- [Add boat-specific tuning notes here over time — e.g., twist preferences, backstay settings for conditions]

---

## 10. Vessel Data / Automation

### SignalK
- **Server**: Raspberry Pi at `192.168.8.50:3000`
- Aggregates NMEA 2000 / NMEA 0183 instruments.
- Web interface at `http://192.168.8.50:3000` on local vessel network.

### KIP (Instrument Display)
- Running on [tablet / dedicated display] at helm / nav station.
- Connects to SignalK server; shows real-time wind, speed, depth, heading.

### Telemetry Pipeline (mermug.com)
- Python script (`scripts/update_signalk_data.py`) polls SignalK every ~150 sec.
- Writes JSON to `data/telemetry/` and commits to GitHub.
- GitHub Pages serves the static site.
- Privacy zone suppresses positions within 200 m of South Beach Harbor.
- See [AGENTS.md](../AGENTS.md) and [README.md](../README.md) for full technical details.

### Raspberry Pi
- **Location**: [nav station / electrical compartment]
- **OS**: Raspberry Pi OS (bookworm or later)
- **Services**: `mermug-website.service`, `mermug-polars.service`
- Manage via `make status`, `make show-logs-website`
- Pi connects to the internet via [marina WiFi / cellular / both].
