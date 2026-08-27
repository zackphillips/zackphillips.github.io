---
title: Vessel Changelog
category: Reference
order: 20
description: Running log of modifications, repairs, upgrades and significant maintenance events.
---

# S.V. Mermug — Vessel Changelog

Running log of modifications, repairs, upgrades, and significant maintenance events.

Format: `YYYY-MM-DD | Category | Description`

Categories: **Electronics** | **Engine** | **Rigging** | **Sails** | **Electrical** | **Plumbing** | **Safety** | **Hull/Deck** | **Software** | **Other**

---

## 2025

### 2025-03-14 | Other | Vessel purchased
- Hauled at KKMI Boatyard, Richmond, CA for inspection.
- Engine hours: **6,376**.

### 2025-05-XX | Electronics | Vessel tracker deployed
- Launched [mermug.com](https://mermug.com) — Raspberry Pi aboard running SignalK → GitHub Pages pipeline.
- SignalK server running on `192.168.8.50:3000`.
- Data update cadence: ~150 seconds.
- Privacy zone configured for South Beach Harbor (200 m radius).

### 2025-05-08 | Other | Pre-purchase marine survey (Keiser Marine + Bay Marine Diesel)
- Full hull/rig/systems survey by Jeff Keiser, SAMS/AMS, Keiser Marine, at
  Svendsen's Bay Marine, Pt. Richmond, CA. Overall rating: Average. Estimated
  fair market value $65,000; estimated replacement cost $750,000.
- Companion engine survey by Marty Chin, Bay Marine Diesel — engine hours
  6,381.7 at time of survey.
- Vessel was named "Tivoli" at this time; buyer of record Christopher Lalau
  Keraly. Renamed "Mermug" by early 2026.
- **Note:** this survey is dated ~7 weeks after the "Vessel purchased" entry
  above (2025-03-14, KKMI Boatyard, 6,376 hrs) — the two haul dates/yards and
  hour readings don't fully reconcile with each other. Both kept as recorded
  on their respective source documents; not reconciled here.
- Findings are reflected throughout [Systems Overview](systems.md) (Known
  Hull Findings, Last Rig Inspection, Safety Equipment) rather than repeated
  here. Source PDFs are not committed to this repo.

### 2025-06-XX | Engine | Engine survey findings addressed
- Mechanic addressed the actionable findings from the May 2025 Bay Marine
  Diesel engine survey:
  - Exhaust hose, muffler to transom, replaced (Vetus).
  - Degraded engine-box foam sound insulation removed.
  - Shaft-seal rear hose clamp replaced with solid 316 stainless (not the
    full PSS unit — see February 2026 below).
  - Racor 500 primary filter assembly and tank-to-engine fuel hose updated.
  - Corrosion at the port aft engine mount/bell housing addressed; seawater
    hose (engine → anti-siphon valve → mixing elbow) replaced.
  - Oil cooler replaced.
  - Engine start battery replaced (AGM).
  - Oil dipstick straightened, rubber stopper reseated, excess oil removed.
  - Freshwater pump, gaskets, and thermostat replaced; front of engine
    repainted where antifreeze had gotten under the paint.

### 2025-05-17 | Other | Vessel delivered to South Beach Harbor
- First sail as new owners; motoring practice with surveyor Jeff.
- Three co-owners: Zack Phillips, Christopher "Krug" Lalau Keraly, and
  Brandon "Bug".

### 2025-05-24 | Navigation | Navigation light compliance issue identified
- Masthead tri-color light (red/green/white) is legal for sailing at night
  but **not legal for motoring** — under power, the red/green lights must be
  ~8 ft below the steaming light, so the combo atop the mast does not comply.
- Bow-mounted red/green navigation light needed for motoring compliance.
- Reference: Chapman's Piloting, Seamanship and Small Boat Handling.

### 2025-05-25 | Engine | Reserve fuel tank and transfer pump located
- Reserve diesel tank (30 gal, port cockpit storage locker) investigated.
- Transfer pump between reserve and main tank located and photographed.
- Fuel flow valve found in the cabinet aft of the aft berth.
- Propane shutoff switch located in the port cabinet behind the helm.

### 2025-05-28 | Electrical | Bow navigation light wire found degraded
- Wire powering the bow navigation lights is degraded — cannot be stripped
  without breaking the copper (tested with auto-stripper). Will need to run
  new wire; drilling may be required (needs marina permission).

### 2025-06-01 | Navigation | Boat touched bottom briefly
- Boat briefly grounded on mud during a sail. No damage observed.

### 2025-06-03 | Electronics | VHF radio diagnosed — receives but does not transmit
- Radio check called on Ch 16 with no response; handheld VHF used as backup.
- Mast-mounted antenna suspected as the issue.

### 2025-06-03 | Electronics | Autopilot confirmed working
- Simrad AP22 used extensively during sailing; working well.

### 2025-06-03 | Electronics | Radar confirmed working; system fully proprietary
- Furuno radar tested and working. Current display unit: **Furuno RDP-143**.
- System is fully proprietary — cannot integrate with non-Furuno displays.
- A compass is needed for radar overlay on charts (bearing derived from GPS
  COG only, not from a compass sensor — reads incorrectly when stationary).

### 2025-06-03 | Electronics | Wind instruments and SSB radio assessed
- TackTick wireless wind instruments aboard but not working properly.
- SSB radio (Icom IC-706MKIIG) identified at nav station bottom unit.
- Wiring behind the nav station described as a "ratsnest" — previous owner(s)
  added cables without removing old ones.

### 2025-06-15 | Other | Cowl vents purchased and installed

### 2025-06-16 | Plumbing | Head waste pipe clogged
- Aft head waste pipe clogged. Drain snake purchased to attempt clearing.

### 2025-06-20 | Electrical | 12V socket wired under nav table
- New 12V socket installed under the table behind the drawer, connected to
  an existing breaker circuit.

### 2025-06-20 | Electronics | NMEA / instrument system architecture documented
- Instrument chain: Raymarine TackTick sensors → wire → Micronet wireless →
  dash displays.
- Raymarine TackTick T122 converter identified as needed to make instrument
  data available on the NMEA network.
- OpenCPN on Raspberry Pi with spare monitor at nav station planned as a
  navigation computer.
- Yacht Devices Python Gateway YDPG-01 identified for NMEA conversion.

### 2025-08-07 | Plumbing | Aft toilet joker valve replaced
- Krug replaced the joker valve on the aft head.

### 2025-08-07 | Electrical | Fridge compressor fan found broken
- Adler Barbour refrigeration compressor fan discovered broken.

### 2025-08-07 | Electrical | Bilge pump confirmed working — switch was off
- Bilge pump was never broken; the switch had been left off.

### 2025-08-10 | Plumbing | Hot water tank pressure relief issue diagnosed
- Water found in bilge — hot water tank not releasing pressure properly,
  causing a hose to blow off after motoring (engine heats the water tank).
- Pressure relief valve located and exercised; it does release water.
- Hose connection uses half-inch tubing which may not be an exact fit
  (likely metric tubing on the original fitting).

### 2025-08-11 | Software | ESP32 LoRa boards acquired for bilge water sensors
- 2× Heltec ESP32 LoRa V3 development boards purchased for fore/aft
  water-height sensors. Natively supported by SignalK. Stored under rug in
  stern box.

### 2025-08-24 | Software | BNO055 IMU acquired for swell measurement
- Adafruit BNO055 absolute orientation sensor (IMU, SPI interface)
  purchased for measuring swell.

### 2025-08-29 | Other | First polar diagram from real sailing data
- First true polar diagram generated from race analysis data.

### 2025-08-31 | Ground Tackle | Anchor shackle failure; anchor lost; 55 lb replacement purchased
- Anchor shackle failed while anchored in 20-knot winds at a beach;
  boat stopped pointing into the wind, alerting crew.
- Chain inspected and confirmed fine — the shackle was the failure point.
- Original anchor (~44 lb) lost and could not be retrieved (murky water).
- Replacement: **55 lb Manson Supreme** purchased from West Marine,
  approximately **$1,200**.
- Contributing factor: may have needed more rope scope to absorb swell.

### 2026-02-10 | Hull/Deck | Bottom paint, keel seam repair, thru-hull replacement
- Haul-out at Svendsen's Bay Marine (Richmond, CA); Quote/Est #26-0026,
  WO #514953.
- Underwater body prepped and repainted: 2 coats Petit Trinidad anti-fouling,
  keel to waterline.
- **Keel/hull seam repair**: reefed out the failed seam, cleaned out debris,
  applied flexible marine adhesive compound, torqued the keel bolts —
  resolves the "keel trailing edge separated from the hull" item in Known
  Hull Findings.
- Replaced the two head-system overboard thru-hulls and the engine raw
  water intake thru-hull with new 1-1/4" ball valves and fittings — resolves
  the forward head discharge seacock seizure noted in the May 2025 survey.
- Zincs/anodes replaced.

### 2026-02-05 | Engine | Shaft seal replaced
- New Pro PSS dripless shaft seal installed (full unit replacement, beyond
  the clamp serviced in June 2025) — propeller and shaft coupling removed,
  engine alignment checked/verified before and after, seal procured and
  installed, shaft and coupling reconnected. Change order CO1 to the Feb
  2026 haul-out above (WO #514953, Svendsen's Bay Marine), time & materials
  @ $160/hr, estimated **$1,596.00**. Approved/signed 2026-02-06.

### 2026-02-05 | Hull/Deck | Topsides buffed and waxed
- Single-step buff and wax to topsides, waterline to deck edge, using super
  duty rubbing compound and electric buffer. Change order CO2 to the Feb
  2026 haul-out above (WO #514953), **$1,602.14**. Approved/signed
  2026-02-06.

### 2026-XX-XX | Safety | Survey safety/deficiency items resolved
- Steering-quadrant shelf: round latches added — fully resolved.
- Fire extinguishers: recalled Kidde unit (quarter berth) replaced; two more
  added in the food-storage area — 4+ aboard now, satisfying the 3-minimum
  requirement.
- VDS: battery-powered USCG-approved electronic flare added, stored in the
  port lazarette.
- Windlass breaker secured to the hull.
- USCG Inland Navigation Rules book added, stored under the AIS transceiver
  above the nav station.
- Waste management plan added, located under the nav station desk.
- Smoke detectors added (incl. one on the port side of the main cabin near
  the speaker, another added later) — all double as CO2 alarms.
- Bilge: both float switches confirmed working (previously not both
  functional); bilge pump breaker upgraded to feed a master auto/manual/off
  selector switch, located below/left of the breaker — **leave in AUTO**.
- EPIRB: registration updated, now registered to Christopher Lalau Keraly;
  battery replaced (not yet tested).
- Gelcoat cracks at the bow pulpit stanchions patched (some remain); boat
  waxed. Loose stanchion base fittings themselves not confirmed addressed.
- Still open: cockpit teak decking/sealant, ~1/8" rudder shaft bearing play.

### 2026-03-XX | Rigging | All six winches serviced

### 2026-04-27 | Hull/Deck | Hull professionally cleaned

### 2026-04-29 | Ground Tackle | Windlass ball bearing failure
- A ball bearing shattered and fused itself to the windlass shaft.
- Bearing had to be cut off the shaft. Anchor was being hauled by hand
  until this was resolved.

### 2026-05-XX | Ground Tackle | Windlass serviced
- Serviced following the April 2026 ball bearing failure.

### 2026-06-11 | Electrical | New solar charge controller installed
- New solar charge controller installed, replacing the original.
- Additional electrical work done to provide sufficient power to the
  Raspberry Pi and its frame.
- Electrical components aboard labeled.

### 2026-06-12 | Electrical | Solar panel output measured; loose ground wire fixed
- Previous poor solar performance traced to a **loose ground wire** on the
  old controller — "the reading would triple when I shook the wire."
- With the new controller and ground fixed, panel produced **380 Wh** total
  over one day (~30 W average over 12 hours of sun).
- Partial shade from the Bimini significantly reduces output.

### 2026-06-27 | Sails | Mainsail ripped during Friday Night Sailing race
- Mainsail ripped during an FNS (Friday Night Sailing) race; retired
  from the race immediately.

### 2026-07-07 | Electronics | Wind sensor 70 kt false reading diagnosed and fixed
- Masthead wind sensor was erroneously reading 70 knots.
- Root cause: the depth sensor (which contains an accelerometer) had been
  pulled out and was sitting sideways. The wind sensor uses the depth
  sensor's accelerometer to correct for sensor angle — with the depth
  sensor sideways, the angle correction produced incorrect readings.
- Reinstalling the depth sensor in its proper position fixed the wind
  readings immediately.

### 2026-07-07 | Electrical | Steaming light and spreader lights repaired
- Both lights had been "wired in the most sketchy way (not by us)" — now
  repaired and working.

### 2026-07-XX | Sails | New jib purchased
- Replaces the roller-furling jib whose Sunbrella UV cover had chafed
  2–4 ft above the deck (May 2025 survey finding).

### 2026-07-15 | Sails | Mainsail removed for repair
- Mainsail removed and dropped off at sailmaker (~July 17) for repair of
  the race-day rip, the UV-damaged clew eyelet, and two additional minor
  rips.

### 2026-07-23 | Sails | Repaired mainsail reinstalled
- Zack reinstalled the repaired mainsail solo.
- Repairs: clew eyelet replaced, two minor rips repaired, race-day rip
  repaired.

### 2026-07-16 | Electrical | Refrigeration controller tested — working
- Refrigeration controller tested and confirmed working as expected.

### 2026-07-17 | Electrical | Refrigeration compressor diagnosed as failed
- Adler Barbour compressor (original 1994 equipment) diagnosed as shot.
- Old refrigerant has been banned by the EPA; evaporator plate replacement
  requires bleeding the refrigerant line (professional technician needed).
- Quick-disconnect pins exist on the refrigerant connections.
- Replacement selected: **Isotherm 2017 Compact Classic** air-cooled
  refrigeration component system, approximately **$1,100** (from
  Defender.com). Evaporator element dimensions line up with existing
  fridge box.

<!-- Add entries above this line, newest first -->

---

## 2024

<!-- Add 2024 entries here -->

---

## 2023

<!-- Add 2023 entries here -->

---

## Recurring Maintenance Schedule

Reference table for planned maintenance intervals. Update "Last Done" column after each service.

| Item | Interval | Last Done | Notes |
|------|----------|-----------|-------|
| Engine oil & filter | 100 hrs or annually | — | **Overdue** — annual maintenance identified as needed Aug 2026 |
| Raw water impeller | Annually (spring) | — | Carry spare aboard |
| Transmission fluid | 2 years | — | |
| Fuel filter (primary) | Annually | — | |
| Fuel filter (Racor) | 200 hrs or annually | June 2025 | Filter assembly and tank-to-engine hose updated |
| Coolant flush | 2 years | June 2025 | Freshwater pump, gaskets, thermostat replaced |
| Engine zincs | Annually | — | |
| Drive belt(s) | Inspect annually / replace as needed | — | Carry spare |
| Standing rigging inspection | Annually | May 8, 2025 | Visual only (mast ascended), no haul; Keiser Marine pre-purchase survey. Rod rigging reported replaced 2015 (corrected from a previous 2012 record) |
| Keel bolt torque / keel seam | Haulout | February 2026 | Seam repaired, adhesive applied, bolts torqued — see changelog |
| Running rigging inspection | Annually | May 8, 2025 | Same pre-purchase survey |
| Sail inspection | Annually | — | Formally not inspected (sails not raised during May 2025 survey); ad hoc repairs July 2026 (new jib, mainsail clew/rips) |
| Lifeline & stanchion inspection | Annually | May 8, 2025 | Found loose stanchion bases at bow pulpit; gelcoat cracks since patched, base fittings not confirmed addressed |
| Seacocks — cycle and grease | Annually | — | Two head overboards + engine raw water intake replaced outright Feb 2026; others not confirmed serviced |
| Through-hull inspection | Haulout | February 2026 | Forward head discharge seacock (seized, per May 2025 survey) replaced along with engine raw water intake |
| Bottom paint | Annually (spring haulout) | February 2026 | Petit Trinidad anti-fouling, 2 coats |
| Hull zinc replacement | Haulout | February 2026 | |
| Prop & shaft inspection | Haulout | February 2026 | Shaft seal (PSS) fully replaced same haulout |
| Fire extinguisher service | 6 years (hydrotest 12 yr) | 2026 | Recalled unit replaced; 2 more added (now 4+ aboard) |
| EPIRB registration & battery | Per label / 5 years | 2026 | Registration updated (Christopher Lalau Keraly); battery replaced but **not yet tested** |
| Flare expiration | Check annually | 2026 | Battery-powered USCG-approved electronic flare added (port lazarette) |
| Life jacket inspection | Annually | — | |
| Bilge pump test | Monthly | 2026 | Both float switches confirmed working; new auto/manual/off master switch installed (leave in AUTO) |
| Hull cleaning (diver) | Quarterly or as needed | April 2026 | |
| Engine raw water strainer | Monthly or as needed | — | |

---

## Parts & Specs Reference

Useful cross-references for ordering parts.

Part numbers still need to be filled in as parts are ordered.

| Component | Make/Model | Part # | Notes |
|-----------|-----------|--------|-------|
| Engine | Yanmar 4JH2E | s/n 07744 | 1994, 46 metric HP @ 3400 RPM, 4 cyl |
| Transmission | Kanzaki KBW20 | s/n 7735 | 2.62:1 reduction |
| Propeller | PYI Max-Prop, 3-blade feathering | — | 18" diameter |
| Propeller shaft | Stainless steel | — | 1‑1/8" dia., dripless seal |
| Raw water impeller | — | — | Carry a spare |
| Primary fuel filter | Racor 500-FG | — | Needs an ASTM F1201 heat shield |
| Secondary fuel filter | Engine mounted | — | |
| Engine oil spec | — | — | |
| Drive belt | — | — | |
| Alternator | Balmar 12 V / 120 A | — | Belt driven |
| Anchor | Manson Supreme, 55 lb | — | Upgraded from 44 lb after shackle failure Aug 2025 (~$1,200, West Marine) |
| Anchor windlass | Quick Eagle 12 V | — | 1400 W; serviced May 2026 |
| Winches | Lewmar 54ST-2 ×2, 44ST-2 ×3, 44ST-2 electric ×1 | — | All six serviced March 2026 |
| Mainsail track | Tides Marine Strong Track | — | |
| Headsail furler | Profurl | — | |
| Jib | — new jib, 2026 | — | Replaces the sail with the chafed Sunbrella UV cover (May 2025 survey finding) |
| Mast / boom | Selden aluminum | — | Keel stepped, double spreader |
| Standing rigging | 1×19 stainless rod | — | Replaced 2015 (corrected from a previous 2012 record; matches the May 2025 survey's ~10-years-old estimate) |
| VHF radio | Icom IC-M504 + RAM mic | — | |
| SSB radio | Icom IC-706MKIIG | — | |
| Chartplotter / MFD | Furuno NavNet | — | GPS, radar, sonar (sonar faulty) |
| Radar | Furuno 24-mile, closed array | — | |
| Autopilot | Simrad AP22 | — | |
| Wind/depth/speed instruments | Garmin GNX wind instrument + depth/speed triducer | — | Installed 2026, replacing dead TackTick/Robertson displays; wind, depth, and paddle wheel all working |
| Compass | Ritchie 4" | — | Helm |
| EPIRB | ACR Global-Fix | — | Registered to Christopher Lalau Keraly (2026); battery replaced, not yet tested |
| AIS transponder | — | — | Confirm what is actually installed |
| House battery | 12 V 4-D AGM | — | |
| Start battery | 12 V AGM | — | Replaced June 2025 (health had dropped to 59% per May 2025 survey); site previously listed this as Group 27 sealed lead acid — corrected here. Still needs terminal covers |
| Oil cooler | — | — | Replaced June 2025 |
| Freshwater pump | — | — | Pump, gaskets, and thermostat replaced June 2025 |
| Exhaust hose (muffler to transom) | Vetus | — | Replaced June 2025 |
| Shaft seal | PSS dripless | — | Rear clamp replaced (316 SS) June 2025; full unit (new Pro PSS) replaced 2026-02-05 (CO1, $1,596.00 T&M, WO #514953) |
| Thru-hulls (2× head overboard, engine raw water intake) | 1-1/4" ball valves | — | Replaced February 2026 |
| Battery charger | Xantrex Tru-Charge 12 V | — | 40+ A |
| Inverter | Outbound | — | 1500 W |
| Solar panel | Kyocera KC120-1 | — | 120 W; original Blue Sky Solar Boost controller replaced June 2026. Measured 380 Wh/day (~30 W avg over 12 hrs). Bimini shade reduces output |
| Wind generator | Air-X Marine | — | Control panel missing |
| Freshwater pump | ParMax 3.5, 12 V | — | Demand type |
| Water heater | Raritan | — | 6 gal, 120 V + engine heat exchanger |
| Heads | Jabsco manual ×2 | — | Type III MSD |
| Bilge pump | Jabsco 12 V diaphragm | — | Manual backup: Whale Gulper |
| Refrigeration | Adler Barbour 12 V | — | Top and front load. **Compressor failed** (original 1994); fan also broken. Replacement: Isotherm 2017 Compact Classic (~$1,100, Defender.com) — not yet installed |
| Stove | Tesco 3-burner propane w/ oven | — | |
| Steering | Edson rack and pinion | — | |
