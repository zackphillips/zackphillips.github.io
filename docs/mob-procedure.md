---
title: Man Overboard Procedure
category: Operations
order: 15
description: Immediate actions, the cockpit MOB button, what happens automatically, and how to clear it afterward.
---

# Man Overboard Procedure

What to do the moment someone goes over the side. Steps first, background below.

## 1. Immediate Actions

Do these **before** touching anything electronic:

1. **Shout "Man overboard!"** — loud, once, unmistakable.
2. **Assign a spotter.** One person's only job is to point at the person in
   the water and never look away, not even to help sail the boat. If no
   one else is available, the skipper does this.
3. **Throw flotation** — whatever is at hand and reachable now: the
   horseshoe ring, a cushion, anything that floats. Don't wait for the
   "right" gear.

## 2. Press the MOB Button

4. **Press the MOB button** — momentary push button, **cockpit coaming,
   starboard side**. One press. Don't hold it.
5. **Confirms it worked**: the alarm sounds (see below) and
   `notifications.mob.button` shows `emergency` on KIP / Freeboard-SK. If
   you don't hear or see that within a couple of seconds, the button may
   not have registered — press it again.

## 3. What Happens Automatically

- SignalK raises `notifications.mob.button` at state `emergency`.
- **signalk-notification-player** sounds the alarm.
- **signalk-mob-course** sets the autopilot/plotter destination back
  toward the MOB position (falling back to the boat's current position if
  none was carried — see Limitations below).
- The notification and course change show up on **Freeboard-SK** and
  **KIP**.
- The Garmin chartplotter most likely shows **nothing** — see Limitations.

Full technical chain: [Systems §6 — MOB
Button](systems.md#mob-man-overboard-button) and [SignalK Configuration —
MOB Button](signalk.md#mob-button-notificationsmobbutton).

## 4. Recovery Manoeuvre

6. Turn back toward the position using the course now set on the autopilot
   — verify it visually and with the spotter, don't steer on the
   instrument alone.
7. Use a standard recovery approach (Quick-Stop, Figure-8, or a controlled
   reciprocal course) appropriate to the conditions and crew aboard — this
   procedure doesn't prescribe one; the crew should already know one.
8. **Before engaging gear or approaching close aboard**: check for lines,
   sheets, or the person themselves near the prop — see [Operations —
   Engine Start Procedure](operations.md#engine-start-procedure) and the
   "Line around prop" kit in [Safety
   Equipment](systems.md#7-safety-equipment). Don't put the engine in gear
   until you're sure nothing and no one is near the propeller.

## 5. Retrieval Gear

Everything below is in [Safety Equipment](systems.md#7-safety-equipment):

- **Lalizas Life Link retrieval sling** — stbd lazarette
- **Lalizas inflatable MOB raft/system** — mounted on the stbd railing
- **Dan buoy** — stbd lazarette
- **Scotty #0793 rescue throw bags** (×2) — stbd lazarette
- **Swim ladder** — stern lazarette, port side, hooks onto the swim platform
- **Swim platform** — fold-down, see [Systems — Swim
  Platform](systems.md#swim-platform) for how to lower it

## 6. Escalation

The MOB button does **nothing off the boat** — it only marks a position
and sets a course aboard Mermug. If recovery isn't immediate:

9. **VHF Ch 16** — call a Mayday / PAN-PAN as appropriate. DSC distress is
   available from the Icom IC-M504 at the nav station.
10. **EPIRB** — nav station.
11. **PLBs** — carried inside the two offshore life jackets.
12. Call for help **early**, not as a last resort — a MOB in open water is
    time-critical.

## 7. Clearing Afterward

Only once the person is safely aboard:

13. **Hold the MOB button 5 seconds** to clear `notifications.mob.button`
    back to `normal`.
14. **Separately cancel the course destination** — clearing the
    notification does **not** do this; `signalk-mob-course` never calls
    `clearDestination()`. Cancel it in Freeboard-SK or via the Course API.

## 8. Practice

Press the button for drills, and for genuinely trivial cases too — a hat
overboard, a fender adrift. This is by design: the whole point of an
instant, cheap, reversible press is that using it often keeps the muscle
memory real. Don't save it for "real" emergencies only.

---

## Background & Limitations

- **Hardware**: momentary push button (cockpit coaming, starboard side) →
  Actisense EMU-1 alarm/switch input → NMEA 2000 →
  `notifications.propulsion.port.neutralStartProtect` in SignalK. The
  EMU-1 can only emit engine-related PGNs, so the button is deliberately
  mapped to an engine alarm channel irrelevant to Mermug's actual engine.
- **Software**: a Node-RED flow turns that raw path into
  `notifications.mob.button`; the `signalk-mob-course` plugin sets the
  course. Full chain: [Systems §6](systems.md#mob-man-overboard-button),
  [SignalK Configuration](signalk.md#mob-button-notificationsmobbutton).
- <span class="doc-tag doc-tag--issue">Unresolved</span> **Untested on
  hardware as of 2026-09-04** — built and bench-tested with simulated
  notifications only. Treat it as an aid, not a proven system, until it's
  been exercised with the real button and EMU-1.
- <span class="doc-tag doc-tag--issue">Unresolved</span> **No position is
  embedded in the notification** — the course is set from the boat's
  position at the moment SignalK processes the delta, not the moment of
  the press. At speed that's a boat length or two of offset.
- <span class="doc-tag doc-tag--issue">Unresolved</span> **The course is
  never auto-cancelled** — see step 14 above.
- <span class="doc-tag doc-tag--planned">Planned</span> **No PGN 127233 or
  AIS SART is transmitted** — this is a SignalK-side system only.
  Chartplotter support for the MOB PGN is essentially absent in the wild,
  and this flow doesn't attempt it.
- **Not a substitute for AIS MOB beacons or DSC.** This button marks a
  position and sets a course aboard Mermug. It alerts no one off the boat
  — see Escalation above for that.
