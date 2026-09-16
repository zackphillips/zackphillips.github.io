# Windlass chain counter and engine sensing

[SensESP](https://github.com/SignalK/SensESP/) firmware for a Heltec WiFi LoRa
32 V3 (ESP32-S3). It counts windlass rode on a Quick Eagle 1400 W and publishes
it to Signal K, and carries a set of general-purpose analog and digital inputs
for engine sensing. Current values are shown on the board's OLED.

The device joins the boat WiFi and talks to the Signal K server over its
websocket. SensESP handles WiFi, mDNS, the Signal K connection, the
configuration web UI and persistence; this repository is the sensor logic on
top of that.

## Build and flash

PlatformIO is pinned in `pyproject.toml` and driven through
[uv](https://docs.astral.sh/uv/), so there is nothing to install globally:

```bash
make sync      # install the pinned PlatformIO into .venv
make build     # compile
make flash     # compile and upload over USB
make monitor   # serial monitor at 115200
make lint      # clang-tidy
make format    # clang-format
```

`make help` lists the rest. Plain `pio run -e arduino_esp32s3` works too if you
have PlatformIO already.

Two environments are defined, both for the Heltec V3: `arduino_esp32s3`
(default, Arduino core 2.x) and `pioarduino_esp32s3` (Arduino core 3.x). The
source uses the Heltec board's `Vext`, `SDA_OLED`, `SCL_OLED` and `RST_OLED`
definitions, so another board needs those supplied or the display code removed.

## First run

The device comes up as a WiFi access point named after the hostname, password
`thisisfine`. Join it, give it your boat network and Signal K server details,
and after that the configuration UI lives at `http://windlass.local/`.

The hostname is set in `src/main.cpp`. Everything else -- Signal K paths,
calibration, counter state -- is editable at runtime in that web UI and
persists across reboots.

## Engine inputs

Three analog inputs (GPIO 5, 6 and 7, scaled to volts) and two digital inputs
(GPIO 3 and 4) are read and published on generic
`sensors.analog_inputN.voltage` and `sensors.digital_inputN.value` paths. They
are carried over from the SensESP template and are not yet mapped to anything
real: assign them to actual engine signals and rename the paths in the config
UI when you wire them.

## Windlass chain counter

`src/chain_counter.{h,cpp}` counts rode on a Quick Eagle 1400 W windlass. It
started as a standalone Arduino sketch and was reworked around SensESP, so WiFi,
the Signal K websocket, delta encoding and configuration persistence all come
from the library rather than being hand-rolled. The original's NMEA 2000 output
was dropped.

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
