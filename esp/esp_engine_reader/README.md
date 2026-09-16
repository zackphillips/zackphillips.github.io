# SensESP Project Template

This repository provides a template for [SensESP](https://github.com/SignalK/SensESP/) projects.
Fork, clone or download the repository and try building and uploading the project to an ESP32 device.
You should immediately see output on the serial monitor! Similarly, you should be able to connect to
the WiFi access point with the same name as the device. The password is `thisisfine`.

To customize the template for your own purposes, edit the `src/main.cpp` and `platformio.ini` files.

Comprehensive documentation for SensESP, including how to get started with your own project, is available at the [SensESP documentation site](https://signalk.org/SensESP/).

## Windlass chain counter

`src/chain_counter.cpp` adds rode counting for a Quick Eagle 1400 W windlass
alongside the existing analog and digital inputs. It is a port of a standalone
Arduino sketch into SensESP: the WiFi, Signal K websocket and configuration
persistence come from SensESP rather than being hand-rolled, and the NMEA 2000
output of the original was dropped.

### Signal K paths

| Path | Units | Notes |
| --- | --- | --- |
| `navigation.anchor.rodeDeployed` | m | Deployed rode. Also accepts a PUT (see below). |
| `sensors.windlass.pulseCount` | | Raw counter, useful for calibration. |
| `sensors.windlass.up` | | Haul contactor energized. |
| `sensors.windlass.down` | | Veer contactor energized. |

None of these are in the Signal K schema -- it has no windlass or rode key at
all. `navigation.anchor.rodeDeployed` was picked because it sits in the same
`navigation.anchor` tree the dashboard already reads for anchor radius and
bearing. Confirm it against whatever consumes it; every path is editable in the
SensESP web config UI.

### Wiring

Three inputs, default GPIOs, overridable with `-D CHAIN_SENSOR_GPIO=n`,
`-D CHAIN_UP_GPIO=n` and `-D CHAIN_DOWN_GPIO=n` in `platformio.ini`:

| Signal | Default GPIO |
| --- | --- |
| Gypsy sensor | 38 |
| Up (haul) contactor sense | 39 |
| Down (veer) contactor sense | 40 |

**The windlass harness is 12 V and these pins are 3.3 V only.** Opto-isolate
the two contactor sense lines (they sit across a solenoid coil, so they also
see inductive kick) and level shift the sensor. All three pins are configured
`INPUT_PULLUP`, which suits an open-collector or reed sensor pulling to ground
through an isolator. The contactor inputs are treated as active low by default;
flip `invert_direction_inputs` in the config UI if your interface is the other
way round.

Check the defaults against your board's pinout before wiring. GPIO 3-7 are
already taken by the analog and digital inputs in `main.cpp`.

### Calibration

`distance_per_pulse` defaults to 0.1675 m, which assumes a Quick gypsy and
counting both sensor edges. Measure it rather than trusting it:

1. Set `pulse_count` to 0 in the config UI with the anchor fully home.
2. Veer to a known mark on the chain, say 10 m.
3. Read `pulse_count` and set `distance_per_pulse` to `10 / pulse_count`.

If the sensor is electrically noisy you can count one edge per revolution
instead by clearing `count_both_edges`, which doubles the distance per pulse.
`debounce_ms` (default 15 ms) sets how long an edge must be stable before it
counts.

### Zeroing

The counter is persisted to the SensESP filesystem, so it survives a reboot.
Writes are throttled: the count is flushed once the chain has been still for
2 s, and at most every 30 s while it is running.

To zero it remotely, send a Signal K PUT of `0` to
`navigation.anchor.rodeDeployed` with the anchor home. A PUT of any other value
sets the counter to that rode length. It can also be set directly in the config
UI.

### Known limitation

The gypsy sensor reports movement, not direction, so direction comes from the
contactor sense lines and the last known direction is held when neither is
energized. A free-fall drop on the clutch immediately after hauling will
therefore count in the wrong direction until the down contactor is next used.
Fixing that properly needs a quadrature sensor.
