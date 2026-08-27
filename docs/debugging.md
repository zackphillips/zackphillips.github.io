---
title: Debugging Guide
category: Reference
order: 30
description: Diagnostic procedures for known issues, based on real troubleshooting experiences aboard S.V. Mermug.
---

# S.V. Mermug — Debugging Guide

This guide documents real problems encountered aboard and how they were
diagnosed and resolved. Use it as a first reference when something goes wrong.

---

## Wind Instruments

### Wind sensor reads impossibly high (e.g. 70 knots in calm conditions)

**Root cause (July 2026)**: the depth sensor had been pulled out of its
housing and was sitting sideways. The masthead wind sensor uses the depth
sensor's internal accelerometer to correct for mast angle — with the depth
sensor in the wrong orientation, the angle correction produced wildly
incorrect wind readings.

**Fix**: reinstall the depth sensor in its proper position and orientation.
Wind readings returned to normal immediately.

**Lesson**: the wind and depth sensors are coupled. Never remove or
reposition the depth sensor without expecting the wind readings to break.

### TackTick wind display shows no data (pre-2026)

The original Raymarine TackTick wireless instrument system used the chain:
sensors → wire → Micronet wireless → dash displays. The TackTick displays
were solar-powered and intermittently unreliable. They were replaced with
Garmin GNX instruments in 2026.

---

## VHF Radio

### Radio receives but does not transmit

**Diagnosed June 2025.** Radio check called on Ch 16 with no response.
Radio receives fine — the issue is transmit only.

**Suspected cause**: mast-mounted antenna connection or antenna itself.

**Workaround**: a handheld VHF is carried as backup.

**Status**: not yet resolved (as of August 2026).

---

## Engine / Mechanical

### Water in bilge after motoring

**Root cause (August 2025)**: the hot water tank's pressure relief valve was
not releasing pressure properly. During motoring, the engine heat exchanger
heats the water tank. If the relief valve doesn't vent, pressure builds and
blows a hose off the tank, dumping water into the bilge.

**Diagnosis steps**:
1. Check the bilge — is the water fresh or salt? Fresh points to the
   water tank; salt points to a thru-hull, shaft seal, or raw water system.
2. Locate the hot water tank pressure relief valve and exercise it manually —
   it should release water when pulled.
3. Check the hose connection. The current hose uses half-inch tubing which
   may not be an exact fit (the original fitting is likely metric).

**Fix**: exercise the pressure relief valve. Ensure the hose is properly
clamped and seated. Consider sourcing the correct metric tubing for a
tighter fit.

### Engine won't start — fuel system

If the engine cranks but won't fire, air may have entered the fuel system
(e.g., running the main tank dry while forgetting to switch to the reserve).

**Key info**:
- The reserve tank (30 gal, port cockpit locker) feeds the main tank via an
  ITT Jabsco 12 V transfer pump.
- The fuel flow valve for the reserve tank is in the **cabinet aft of the
  aft berth**.
- See the [Operations Guide](operations.md#engine-start-procedure) for the
  bleed procedure.

---

## Electrical

### Solar panel producing much less power than expected

**Root cause (June 2026)**: a **loose ground wire** on the original Blue Sky
Solar Boost charge controller. "The reading would triple when I shook the
wire."

**Diagnosis**: if solar output seems abnormally low, check the ground wire
connections at the charge controller first. With the new controller (installed
June 2026) and ground fixed, the 120 W Kyocera panel produces ~380 Wh/day
(~30 W average over 12 hours of sun).

**Note**: partial shade from the Bimini significantly reduces output. This
is normal, not a fault.

### Bilge pump "not working"

**Root cause (August 2025)**: the switch was simply turned off. The bilge
pump was never broken.

**Diagnosis**: before troubleshooting the pump, check the master
auto/manual/off selector switch (located below/left of the bilge pump
breaker). It should be in **AUTO**. Both float switches were confirmed
working in 2026.

### Steaming light / spreader lights not working

**Root cause (July 2026)**: these had been "wired in the most sketchy way
(not by us)" by a previous owner. Repaired and now working.

**Lesson**: when chasing an electrical fault, suspect wiring quality first —
the nav station wiring has been described as a "ratsnest" with cables added
over multiple owners without removing old ones.

### Navigation lights — motoring compliance

The masthead tri-color light is legal for **sailing** at night but **not for
motoring**. Under power, the red/green nav lights must be ~8 ft below the
steaming light (ref: Chapman's Piloting). The bow-mounted nav light wire was
found degraded in May 2025 and needs to be replaced before the bow light can
be used for motoring compliance.

---

## Refrigeration

### Fridge not cooling

**Diagnosis sequence (July 2026)**:
1. **Test the controller** — power it on and verify it cycles correctly.
   The controller was tested and works fine (July 2026).
2. **Check the compressor fan** — it was found broken (August 2025).
3. **Check the compressor** — the original Adler Barbour compressor
   (1994) was diagnosed as failed (July 2026).

**Replacement plan**: Isotherm 2017 Compact Classic air-cooled system
(~$1,100, Defender.com). The evaporator element dimensions fit the existing
fridge box.

**Important notes**:
- The old refrigerant has been banned by the EPA.
- Replacing the evaporator plate requires bleeding the refrigerant line —
  this requires a professional technician.
- Quick-disconnect pins exist on the refrigerant connections.

---

## Ground Tackle

### Windlass not hauling / grinding noise

**Root cause (April 2026)**: a ball bearing inside the windlass shattered
and fused itself to the shaft. The bearing had to be cut off. Until repaired,
the anchor was hauled by hand.

The windlass was fully serviced in May 2026 after this failure.

### Anchor not holding / boat swinging off the wind

**Experience (August 2025)**: anchor shackle failed in 20-knot winds.
The boat stopped pointing into the wind, alerting the crew.

**Post-incident findings**: the chain was inspected and was fine — the
**shackle** was the failure point. The anchor was lost in murky water.

**Lessons**:
- Inspect the shackle before every anchoring — it's a single point of
  failure.
- Use more rope scope in swells (rope is elastic and absorbs shock loads
  better than chain alone).
- The replacement anchor is a 55 lb Manson Supreme (up from the original
  ~44 lb).

---

## Plumbing

### Aft head not flushing / backing up

**Experience (June 2025)**: waste pipe found clogged. A drain snake was used
to attempt clearing.

**Also**: the aft head joker valve was replaced in August 2025. If the head
is sluggish or allowing backflow, the joker valve is the first suspect.

---

## Software / Telemetry

### mermug.com not updating

**Diagnosis steps**:
1. SSH into the Raspberry Pi (192.168.8.50).
2. Check the timer: `sudo systemctl list-timers --all | grep signalk-gitpush`
3. Check the service logs: `journalctl -u signalk-gitpush.service`
4. Check the data update script: look at `update_data.py` output.

**Known issue (July 2025)**: the Pi died during a `git pull`, corrupting
the local repo on the Pi. Fixed by re-cloning the repo.

**If data is stale**: check the repo state on the Pi first — a corrupted
repo is the most likely cause.

### SignalK server not responding

- Check that the Pi is powered. The new solar charge controller (June 2026)
  provides sufficient power; a loose ground wire on the old controller was
  previously causing intermittent power issues.
- Access the web interface at `http://192.168.8.50:3000` on the vessel
  network.
- Manage services: `make status`, `make show-logs-website`

---

## Quick Reference — "Is it plugged in?"

Many "failures" aboard have turned out to be simple switch/connection issues:

| Symptom | Check first |
|---------|-------------|
| Bilge pump not running | Master switch — should be in AUTO |
| Solar output low | Ground wire at the controller |
| Wind reads wrong | Depth sensor position/orientation |
| VHF won't transmit | Antenna connection (known issue) |
| Fridge not cooling | Compressor is dead (known); do not troubleshoot further until Isotherm replacement is installed |
| Lights not working | Check wiring quality — previous owner's work was poor |
| Hot water in bilge | Pressure relief valve on the water tank |
| mermug.com stale | Git repo state on the Pi |
