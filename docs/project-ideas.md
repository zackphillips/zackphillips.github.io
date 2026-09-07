---
title: Project Ideas
category: Ideas
order: 10
description: Speculative projects and system upgrades under consideration — not yet planned or committed, unlike Planned Projects.
---

# S.V. Mermug — Project Ideas

Unlike [Planned Projects](planned-projects.md) — known fixes pulled from
[Systems Overview](systems.md) that are just waiting to be done — this page
is for projects still at the idea stage: worth writing down, not yet
scoped, and with no commitment to build. When one of these firms up into
an actual plan, move it to Planned Projects instead of leaving it here.

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
