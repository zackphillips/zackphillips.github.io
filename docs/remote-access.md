---
title: Remote Access (VPN)
category: Systems
order: 15
description: Connect to the boat's network from off the boat using AstroWarp, then SSH, VNC, or VS Code Remote into the Pi.
---

# Remote Access (VPN)

The Pi and the boat's onboard network aren't reachable from the open
internet — you need to be on the boat's Wi-Fi, or connected in over the
VPN, to reach them. This is how to set up the VPN and get in remotely.

## VPN: AstroWarp

We use [AstroWarp](https://www.astrowarp.net/download) for remote access
to the boat's network.

- [ ] Download and install the AstroWarp app on your device from
  <https://www.astrowarp.net/download>.
- [ ] Ask Zack for the **share link** — paste it into the setup wizard
  when prompted.
- [ ] Connect. Once the VPN is active, the boat's network is reachable as
  if you were aboard.

**We're on the free plan, which allows only two devices connected at
once.** If you can't connect, someone else is probably already on —
check with Zack before assuming something is broken, and disconnect when
you're done so the slot is free for the next person.

## Once connected

With the VPN active, the Raspberry Pi is reachable at `10.0.1.1`.

### SSH

```
ssh pi@10.0.1.1
```

### Remote desktop (RealVNC)

Use [RealVNC](https://www.realvnc.com/en/) to view and control the Pi's
desktop directly, same as sitting at the nav station.

### VS Code Remote

The Pi is also reachable via VS Code's Remote-SSH extension, using the
same `pi@10.0.1.1` address — useful for editing code or this repo
directly on the Pi.

**Note**: Claude Code is installed on the Pi, under Zack's personal
account (see [Systems → Raspberry Pi](systems.md#raspberry-pi)).

## If it goes wrong

- Can't connect to AstroWarp at all → confirm you have the current share
  link from Zack; links can be rotated.
- AstroWarp connects but `10.0.1.1` doesn't respond → the Pi itself may be
  down or off the boat's network — see
  [Debugging → SignalK server not responding](debugging.md#signalk-server-not-responding).
- "Connection refused" on the free plan → check whether two devices are
  already connected and disconnect one.
