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

### 2025-05-12 | Safety | Safety/documentation items purchased
- Kidde Mariner PWC fire extinguisher (5-B:C, KD57W-5BC) installed under the nav station.
- Navigation Rules and Regulations Handbook installed above the nav station.
- SeaSense air horn (118 dB) installed in the port lazarette — satisfies the sound-signaling-device requirement.
- Bernard Engraving Corp waste discharge placard installed atop the port lazarette.

### 2025-05-14 | Safety | Inflatable PFD purchased
- Onyx A/M-24 automatic/manual inflatable life jacket (USCG approved) purchased and put into use.

### 2025-05-16 | Other | Reference library — Chapman's Piloting added
- Chapman Piloting & Seamanship, 69th Edition, added to the ship's library —
  cited elsewhere in this changelog and in [Systems Overview](systems.md)
  for navigation-light compliance.

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

### 2025-06-27 | Electrical | Interior lighting converted to LED
- All halogen dome lights replaced with acegoo 12 V dimmable LED puck lights
  (8 fixtures total).

### 2025-07-05 | Outboard | Dinghy outboard carburetor fixed
- An initial MARKGOO carb rebuild kit didn't fit and was discarded; a
  CHAMPAN replacement carburetor was installed instead and resolved the
  carb issues.
- A second attempt at a VHF/AIS antenna power splitter (Amazon) did not
  work for sharing one antenna between the two radios.

### 2025-07-17 | Electrical | Wave One Marine LED deck light installed
- Dual-color LED spreader/flood light installed in the bimini, toggled by
  the bottom switch on the starboard control panel.

### 2025-07-20 | Electronics | Temporary VHF antenna installed
- A HYS low-profile VHF antenna, L-bracket NMO mount, and coax adapters
  installed as a workaround while the June 2025 "receives but doesn't
  transmit" issue was outstanding.

### 2025-07-20 to 2025-09-18 | Hull/Deck | King's chairs designed and installed
- Two elevated seat backs, designed and built in-house from stainless tube
  and marine rail hardware (bimini jaw slides, hand-rail elbows, tee
  fittings), attached to the port and starboard railings. See
  [King's Chairs & Deck Hardware](systems.md#12-kings-chairs-deck-hardware).

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

### 2025-08-31 | Ground Tackle | Anchor shackle failure; anchor lost; Rocna 20 replacement purchased
- Anchor shackle failed while anchored in 20-knot winds at a beach;
  boat stopped pointing into the wind, alerting crew.
- Chain inspected and confirmed fine — the shackle was the failure point.
- Original anchor, a **Manson Supreme** (~44 lb), lost and could not be
  retrieved (murky water).
- Replacement: a **Rocna 20**, purchased from West Marine, approximately
  **$1,200** (purchase records list this as "55 lb").
- Contributing factor: may have needed more rope scope to absorb swell.

### 2025-09-24 | Electronics | Fusion NMEA 2000 wired remote installed
- Fusion MS-NRX300 wired remote mounted port side, in place of the old
  dead dataline display that was removed.

### 2025-09-30 | Audio | New stereo installed
- Fusion MS-RA70NSX stereo (BT/AM/FM/SiriusXM, 2-zone) installed, replacing
  the previous stereo. See [Audio, Video & Entertainment](systems.md#11-audio-video-entertainment).

### 2025-10-05 | Rigging | Winch stripper ring replaced
- Lewmar winch replacement stripper ring installed on the port rear winch.

### 2025-10-14 | Electronics | Autopilot control head replaced
- The original Simrad AP22 control head died; replaced with a Simrad AP44
  control head (p/n 000-13289-001, via eBay). A matching AP44 suncover
  (p/n 000-13724-001) was ordered a few days later.

### 2025-10-29 | Audio | Amplifier installed
- Garmin Fusion AM Series 400 W 2-channel amplifier installed in the aft
  cabin wardrobe.

### 2025-11-03 | Audio | New speakers installed
- Fusion Signature 7.7" marine speakers (pair) installed, wired with new
  12-gauge speaker wire and 6-gauge amp power/ground wire.

### 2025-11-16 to 2025-11-26 | Electronics | TackTick display batteries replaced
- Replacement battery/seal kits (Tacktick TA119) installed in the
  remaining TackTick displays still aboard, despite the Garmin GNX
  instruments now being the active wind/depth source.

### 2025-12-03 | Electronics | Actisense EMU-1 engine management unit installed
- Installed behind the engine control panel, accessible via a panel in the
  aft cabin — bridges engine/tank analog senders onto NMEA 2000.

### 2025-12-07 to 2025-12-18 | Plumbing | Freshwater tank sending units installed
- Two 100TECH 240-33 ohm resistive sending units (13" and 16", sized to
  each tank's depth) installed in the two freshwater tanks.

### 2025-12-14 | Electronics | Garmin GNX 20 display installed
- Garmin GNX 20 marine instrument (4" display) installed above the port
  line cleats under the dodger, next to the other GNX displays.

### 2025-12-19 | Engine | RPM sensor tap wired
- Genuine Yanmar wiring harness (p/n 127610-77710) used to tap the RPM
  sensor circuit for broadcast via the Actisense EMU-1.

### 2025-12-20 | Electronics | Garmin wind/depth/speed instrument pack installed
- "Garmin sail pack 52" (Atlantic Marine) installed in one go: replaced the
  paddle wheel speed sensor, the masthead wind sensor, and two of the three
  cockpit displays. See [Wind Instruments](systems.md#wind-instruments) and
  [Depth Sounder](systems.md#depth-sounder).

### 2025-12-22 | Electronics | AIS NMEA gateway installed
- Actisense NGT-1-ISO (NMEA 0183-to-NMEA 2000) gateway installed as the
  connector between the AIS transceiver and the N2K backbone.

### 2026-01-01 | Plumbing | Bilge level sending unit installed
- 100TECH 6.5" 240-33 ohm sending unit installed as a bilge level sensor
  (wiring/integration destination unconfirmed).

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

### 2026-02-14 | Electronics | VHF hailer horn installed
- Icom SP37 40 W hailer horn installed, wired to the VHF radio as both a
  speaker and a foghorn.

### 2026-02-19 | Electronics | VHF/AIS antenna splitter installed
- Digital Yacht SPL1500 ZeroLoss VHF/AIS antenna splitter installed behind
  the breaker panel, letting the VHF and AIS transponder properly share the
  single mast antenna (an Amazon splitter tried for this in July 2025 had
  not worked).

### 2026-03-XX | Electronics | Temporary VHF antenna removed
- The temporary HYS antenna installed 2025-07-20 as a workaround was
  removed now that the antenna splitter above resolves the sharing issue.
  Confirm the VHF transmits reliably through the mast antenna.

### 2026-03-18 | Plumbing | Aft black-water tank vent replacement — discarded
- A SEAFLO angled thru-hull fitting bought to replace the aft tank's vent
  was found unnecessary once inspected.

### 2026-03-24 | Plumbing | Forward black-water tank level sensing — unsuccessful
- Attempt to bring a level-sender signal out of the forward holding tank
  via an Ancor NMEA 2000 through-bulkhead connector did not work out. The
  forward tank still has no digital level sensing.

### 2026-03-29 | Safety | Major PFD/MOB safety equipment upgrade
- ACR HemiLight3 survivor locator lights (×3) hung from handles above the stairs.
- ACR ResQLink PLB-450 personal locator beacons (×2) fitted inside the two
  blue offshore life jackets, registered to Chris and Zack, and tested.
- LuxoGear emergency whistles installed in all inflatable PFDs; NRS leg
  straps added to the two offshore jackets.
- Scotty #0793 rescue throw bags (×2) stowed in the starboard lazarette.
- Sirius Signal C-1003 SOS LED electronic flare installed in the port
  lazarette, replacing the pyrotechnic flare requirement.

### 2026-03-XX | Rigging | All six winches serviced

### 2026-04-07 | Safety | Life jacket light and CO2 rearming kit installed
- Water-activated life jacket light installed below the nav station.
- New 33 g CO2 rearming kit installed, replacing the cartridge that
  accidentally triggered in July 2025.

### 2026-04-20 | Electrical | Bilge pump control switch panel replaced
- AMOMD 12 V bilge pump control switch panel (3-way manual/off/auto, LED
  indicator, 5 A fuse) installed. A spare Quick Eagle windlass foot switch
  (Five Oceans FO3291) and a 12 V reverse-polarity rocker switch (earmarked
  for a future windlass control rework, not yet installed) were purchased
  the same day.

### 2026-04-24 | Electronics | Garmin GPS 19x installed
- Garmin GPS 19x NMEA 2000 GPS puck installed in the cockpit — becomes the
  primary NMEA 2000 GPS source in SignalK's failover chain.

### 2026-04-27 | Hull/Deck | Hull professionally cleaned

### 2026-04-29 | Ground Tackle | Windlass ball bearing failure
- A ball bearing shattered and fused itself to the windlass shaft.
- Bearing had to be cut off the shaft. Anchor was being hauled by hand
  until this was resolved.

### 2026-05-XX | Ground Tackle | Windlass serviced
- Serviced following the April 2026 ball bearing failure.

### 2026-05-07 | Ground Tackle | Anchor rode parted; anchor lost; Rocna 20 replaced again
- The anchor line (rode) snapped, and the Rocna 20 installed after the
  August 2025 loss was lost with it.
- Replacement: a second **Rocna 20** (West Marine), installed along with a
  new stainless screw-pin anchor shackle (4,000 lb SWL) and floating buoy
  anchor-chain markers.

### 2026-05-18 | Electrical | DC panel upgraded
- Blue Sea Systems 8025 traditional metal DC panel (3 positions) installed,
  replacing the old battery-monitor panel. Adds dedicated "Lights" and
  "Electronics" breakers for cockpit lighting and the nav-station
  PC/Raspberry Pi, fed by an additional RVBOATPAT 12 V 150 A bus bar.

### 2026-05-25 | Ground Tackle | First anchor rode reorder — returned
- An initial order of 9/16" three-strand nylon rode, 5/16" G4 chain, a
  stainless thimble, and a chain hook (West Marine) was returned — sizing
  did not match what was ultimately delivered in August (5/8" nylon). See
  the 2026-08-26 entry below.

### 2026-05-25 | Electrical | Battery added
- Group 31 dual-purpose AGM battery (105 Ah, West Marine) installed — bank
  assignment not yet confirmed in [Systems Overview](systems.md#battery-bank).

### 2026-06-01 | Electrical | Solar charge controller model confirmed
- The June 2026 solar charge controller replacement (see below) is a
  Victron Energy SmartSolar MPPT 100/20 (100 V, 20 A, Bluetooth).

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

### 2026-07-18 | Electrical | Refrigeration replacement purchased
- Isotherm 2017 Compact Classic air-cooled system (p/n U260X086P12111AA,
  Defender.com) purchased — ready to install, not yet installed.

### 2026-02-01 | Electrical | Dehumidifier added
- Waykar 1500 sq ft, 30-pint Energy Star dehumidifier installed next to the
  refrigerator, secured, draining via a hose to the sink. Considered
  essential to keeping the boat dry and preventing mold/rust.

### 2026-XX-XX | Electrical | Apple TV and projector installed
- Apple TV HD (modified to run on 12 V directly) and a projector installed
  on the "Electronics" breaker, switched from the starboard side of the
  salon. Projector screen stored in the port-side salon cabinet, hangs
  from the bar below the port windows. **Exact date TBD.**

### 2026-XX-XX | Software | Cellular hotspot set up as boat internet uplink
- A rooted Google Pixel 4a (Visible Plus plan) tethers its 5G/LTE
  connection to provide the boat's internet, automated via Tasker
  (tethering enabled on charge-start, followed by a script granting the
  boat's client network access). Also loads KIP as a generic status page.
  This is the Raspberry Pi's actual internet uplink. **Tasker
  profile/script details and exact setup date TBD.**

### 2026-08-26 | Ground Tackle | New anchor rode, swivel & shackle ordered and delivered
- 450 ft of 5/8" three-strand nylon rope.
- 150 ft of G4 5/16" galvanized chain.
- Rope-to-chain splice.
- Whip & burn (rope end finish).
- Anchor swivel (plus freight).
- HS galvanized bow shackle, 5/16", 2,500 lb WLL.
- Labor: package for shipment and install swivel.
- Confirms/updates the primary anchor rode length and materials — see
  [Ground Tackle](systems.md#8-ground-tackle).

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
| Anchor | Rocna 20 | — | Original Manson Supreme (~44 lb) lost to a shackle failure Aug 2025, replaced with a Rocna 20; that Rocna 20 was lost when the rode parted, replaced with another Rocna 20 in May 2026 |
| Anchor shackle | Stainless screw-pin, 4,000 lb SWL | — | West Marine, installed May 2026 |
| Anchor rode — chain | G4 5/16" galvanized | — | 150 ft, ordered/delivered 2026-08-26 |
| Anchor rode — rope | 5/8" three-strand nylon | — | 450 ft, spliced to chain; ordered/delivered 2026-08-26 |
| Anchor swivel | — | — | Ordered/delivered 2026-08-26 |
| Bow shackle | HS galvanized, 5/16", 2,500 lb WLL | — | Ordered/delivered 2026-08-26 |
| Anchor windlass | Quick Eagle 12 V | — | 1400 W; serviced May 2026. Foot switch: Five Oceans FO3291 (spare, April 2026) |
| Winches | Lewmar 54ST-2 ×2, 44ST-2 ×3, 44ST-2 electric ×1 | — | All six serviced March 2026 |
| Mainsail track | Tides Marine Strong Track | — | |
| Headsail furler | Profurl | — | |
| Jib | — new jib, 2026 | — | Replaces the sail with the chafed Sunbrella UV cover (May 2025 survey finding) |
| Mast / boom | Selden aluminum | — | Keel stepped, double spreader |
| Standing rigging | 1×19 stainless rod | — | Replaced 2015 (corrected from a previous 2012 record; matches the May 2025 survey's ~10-years-old estimate) |
| VHF radio | Icom IC-M504 + RAM mic | — | Antenna shared with AIS via a Digital Yacht SPL1500 ZeroLoss splitter (Feb 2026); hailer horn: Icom SP37, 40 W (Feb 2026) |
| SSB radio | Icom IC-706MKIIG | — | |
| Chartplotter / MFD | Furuno NavNet | — | GPS, radar, sonar (sonar faulty) |
| Radar | Furuno 24-mile, closed array | — | |
| Autopilot | Simrad AP44 (p/n 000-13289-001) | — | Replaced the original AP22 head (died Oct 2025); suncover p/n 000-13724-001 |
| Wind/depth/speed instruments | Garmin GNX wind instrument + depth/speed triducer + GNX 20 display | — | Installed 2025-12-14/12-20 ("Garmin sail pack 52"), replacing dead TackTick/Robertson displays; wind, depth, and paddle wheel all working. Fusion MS-NRX300 wired remote also installed Sept 2025 |
| Compass | Ritchie 4" | — | Helm |
| EPIRB | ACR Global-Fix | — | Registered to Christopher Lalau Keraly (2026); battery replaced, not yet tested |
| AIS transponder | — | — | Confirm what is actually installed |
| House battery | 12 V 4-D AGM | — | |
| Battery (added May 2026) | Group 31 dual-purpose AGM, 105 Ah | — | West Marine; bank assignment unconfirmed |
| Start battery | 12 V AGM | — | Replaced June 2025 (health had dropped to 59% per May 2025 survey); site previously listed this as Group 27 sealed lead acid — corrected here. Still needs terminal covers |
| Oil cooler | — | — | Replaced June 2025 |
| Freshwater pump | — | — | Pump, gaskets, and thermostat replaced June 2025 |
| Exhaust hose (muffler to transom) | Vetus | — | Replaced June 2025 |
| Shaft seal | PSS dripless | — | Rear clamp replaced (316 SS) June 2025; full unit (new Pro PSS) replaced 2026-02-05 (CO1, $1,596.00 T&M, WO #514953) |
| Thru-hulls (2× head overboard, engine raw water intake) | 1-1/4" ball valves | — | Replaced February 2026 |
| Battery charger | Xantrex Tru-Charge 12 V | — | 40+ A |
| Inverter | Outbound | — | 1500 W |
| Solar panel | Kyocera KC120-1 | — | 120 W; original Blue Sky Solar Boost controller replaced June 2026 with a Victron Energy SmartSolar MPPT 100/20 (100 V, 20 A, Bluetooth). Measured 380 Wh/day (~30 W avg over 12 hrs). Bimini shade reduces output |
| Wind generator | Air-X Marine | — | Control panel missing |
| Freshwater pump | ParMax 3.5, 12 V | — | Demand type |
| Water heater | Raritan | — | 6 gal, 120 V + engine heat exchanger |
| Heads | Jabsco manual ×2 | — | Type III MSD |
| Bilge pump | Jabsco 12 V diaphragm | — | Manual backup: Whale Gulper |
| Refrigeration | Adler Barbour 12 V | — | Top and front load. **Compressor failed** (original 1994); fan also broken. Replacement: Isotherm 2017 Compact Classic (p/n U260X086P12111AA, Defender.com, purchased 2026-07-18) — ready to install, not yet installed |
| Stove | Tesco 3-burner propane w/ oven | — | |
| Steering | Edson rack and pinion | — | |
| DC panel | Blue Sea Systems 8025, 3-position | — | Installed May 2026, replacing old battery-monitor panel; adds "Lights"/"Electronics" breakers |
| Engine/tank NMEA 2000 gateway | Actisense EMU-1 | — | Installed Dec 2025, behind engine control panel, accessible via aft cabin panel |
| AIS NMEA 2000 gateway | Actisense NGT-1-ISO | — | Installed Dec 2025 |
| GPS (NMEA 2000) | Garmin GPS 19x | — | Installed cockpit, April 2026; missing T-connector |
| Freshwater tank senders | 100TECH 240-33 ohm, 13" & 16" | — | Installed Dec 2025, one per tank |
| Bilge level sender | 100TECH 240-33 ohm, 6.5" | — | Installed Jan 2026; integration unconfirmed |
| Audio head unit | Fusion MS-RA70NSX | — | Installed Sept 2025; amp: Garmin Fusion AM Series 400 W; speakers: Fusion Signature 7.7" pair |
| Hot water fittings | 316 SS hex nipple adapters, 1" & 3/4" NPT | — | Feb 2026, part of ongoing stern re-plumbing project |
