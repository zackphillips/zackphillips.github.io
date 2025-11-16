#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher
Supports both individual sensor services and legacy multi-sensor mode.

Individual sensor mode (recommended):
    python3 i2c_sensor_read_and_publish.py <sensor_name> [options]
    Example: python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50

Legacy multi-sensor mode:
    python3 i2c_sensor_read_and_publish.py [options] [--disable-<sensor>]
    Example: python3 i2c_sensor_read_and_publish.py --host 192.168.8.50 --disable-sgp30
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sensors import BME280Sensor, BNO055Sensor, MMC5603Sensor, SGP30Sensor
from utils import load_vessel_info, send_delta_over_udp, setup_logging

# Constants
DEFAULT_UDP_PORT = 4123

# Map sensor names to their classes
SENSOR_CLASSES = {
    "bme280": BME280Sensor,
    "bno055": BNO055Sensor,
    "mmc5603": MMC5603Sensor,
    "sgp30": SGP30Sensor,
}

logger = logging.getLogger(__name__)


def run_individual_sensor(
    sensor_name: str,
    signalk_host: str = None,
    signalk_port: int = None,
    udp_port: int = None,
    info_path: str = "data/vessel/info.yaml",
    update_interval: float = None,
    once: bool = False,
    log_level: str = "INFO",
):
    """
    Run a single sensor service (recommended mode).

    Args:
        sensor_name: Name of the sensor to run
        signalk_host: SignalK server host (overrides config)
        signalk_port: SignalK server port (overrides config)
        udp_port: UDP port for publishing (default: 4123)
        info_path: Path to vessel config file
        update_interval: Update interval in seconds (overrides config)
        once: Run once and exit (for testing)
        log_level: Logging level
    """
    # Setup logging
    setup_logging(level=log_level)

    # Get sensor class
    if sensor_name not in SENSOR_CLASSES:
        logger.error(f"Unknown sensor: {sensor_name}")
        logger.error(f"Available sensors: {', '.join(SENSOR_CLASSES.keys())}")
        sys.exit(1)

    sensor_class = SENSOR_CLASSES[sensor_name]

    try:
        # Create sensor instance
        sensor = sensor_class(
            signalk_host=signalk_host,
            signalk_port=signalk_port,
            udp_port=udp_port,
            info_path=info_path,
            update_interval=update_interval,
        )

        # Initialize sensor
        if not sensor.initialize():
            logger.error(f"Failed to initialize {sensor_name} sensor")
            sys.exit(1)

        # Connect UDP
        sensor.connect_udp()

        # Run sensor
        if once:
            logger.info(f"Running {sensor_name} sensor once...")
            success = sensor.run_once()
            sys.exit(0 if success else 1)
        else:
            logger.info(f"Starting {sensor_name} sensor service...")
            sensor.run_loop()

    except KeyboardInterrupt:
        logger.info(f"{sensor_name} sensor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running {sensor_name} sensor: {e}", exc_info=True)
        sys.exit(1)


def run_legacy_multi_sensor_mode(
    signalk_host: str = None,
    signalk_port: int = None,
    udp_port: int = None,
    info_path: str = "data/vessel/info.yaml",
    enable_bme280: bool = True,
    enable_bno055: bool = True,
    enable_mmc5603: bool = True,
    enable_sgp30: bool = True,
    log_level: str = "DEBUG",
):
    """
    Run in legacy multi-sensor mode (reads from multiple sensors in one process).

    This mode is deprecated in favor of individual sensor services.
    """
    import json
    import math
    import socket
    from datetime import UTC, datetime

    import board
    import busio
    import smbus2
    from adafruit_bno055 import BNO055_I2C
    from adafruit_sgp30 import Adafruit_SGP30

    from bno055_register_io import validate_calibration_data, write_calibration

    # Setup logging
    setup_logging(level=log_level)

    I2C_SENSORS_LABEL = "I2C Sensors"
    I2C_SENSORS_SOURCE = "i2c-sensors"

    class LegacySensorReader:
        """Legacy multi-sensor reader (deprecated)."""

        def __init__(
            self,
            signalk_host=None,
            signalk_port=None,
            udp_port=None,
            info_path="data/vessel/info.yaml",
            enable_bme280=True,
            enable_bno055=True,
            enable_mmc5603=True,
            enable_sgp30=True,
        ):
            """Initialize sensor reader and SignalK connection."""
            # Store sensor enable flags
            self.enable_bme280 = enable_bme280
            self.enable_bno055 = enable_bno055
            self.enable_mmc5603 = enable_mmc5603
            self.enable_sgp30 = enable_sgp30

            # Load vessel info from JSON file
            self.vessel_info = load_vessel_info(info_path)

            if self.vessel_info and "signalk" in self.vessel_info:
                signalk_config = self.vessel_info["signalk"]
                self.signalk_host = signalk_host or signalk_config.get("host")
                self.signalk_port = signalk_port or signalk_config.get("port")
            else:
                # Use command-line arguments only if config file not available
                self.signalk_host = signalk_host
                self.signalk_port = signalk_port
                logger.warning(
                    "No SignalK configuration found in vessel info, using command-line arguments only"
                )

            # UDP configuration for data publishing
            self.udp_port = udp_port or DEFAULT_UDP_PORT

            # Load heading correction offset from vessel info
            if self.vessel_info and "sensors" in self.vessel_info:
                sensors_config = self.vessel_info["sensors"]
                self.heading_correction_offset = sensors_config.get(
                    "heading_correction_offset_rad", 0.0
                )
            else:
                self.heading_correction_offset = 0.0
                logger.warning(
                    "No sensors configuration found in vessel info, using default heading correction offset of 0.0"
                )

            # Validate required configuration
            if not self.signalk_host:
                raise ValueError(
                    "SignalK host must be specified via --host argument or config file"
                )
            if not self.signalk_port:
                raise ValueError(
                    "SignalK port must be specified via --port argument or config file"
                )
            if not self.udp_port:
                raise ValueError(
                    "SignalK UDP port must be specified via --udp-port argument"
                )
            self.udp_socket = None

            # Initialize I2C bus
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.bus = smbus2.SMBus(1)  # For BME280

            # Sensor objects
            self.bme280_sensor = None
            self.bno055_sensor = None
            self.mmc5603_sensor = None
            self.sgp30_sensor = None
            self.sgp30_start_time = None

            # Initialize sensors
            self._initialize_sensors()

        def connect_udp(self):
            """Connect to SignalK server via UDP."""
            try:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.settimeout(5.0)
                logger.info(
                    f"UDP socket created for SignalK server at {self.signalk_host}:{self.udp_port}"
                )
                return True
            except Exception as e:
                logger.error(f"Failed to create UDP socket: {e}")
                if self.udp_socket:
                    self.udp_socket.close()
                    self.udp_socket = None
                return False

        def _initialize_sensors(self):
            """Initialize all available sensors."""
            # BME280 (Temperature, Humidity, Pressure)
            if self.enable_bme280:
                try:
                    import bme280.bme280 as bme280_module

                    # Initialize BME280 with smbus2
                    bme280_module.full_setup(1, 0x77)  # bus_number=1, i2c_address=0x77
                    self.bme280_sensor = bme280_module
                    logger.info("BME280 sensor initialized")
                except Exception as e:
                    logger.warning(f"BME280 not available: {e}")
            else:
                logger.info("BME280 sensor disabled")

            # BNO055 (9-DOF IMU)
            if self.enable_bno055:
                try:
                    self.bno055_sensor = BNO055_I2C(self.i2c)
                    logger.info("BNO055 sensor initialized")

                    # Load calibration data if available
                    if self.vessel_info:
                        self._load_bno055_calibration()
                except Exception as e:
                    logger.warning(f"BNO055 not available: {e}")
            else:
                logger.info("BNO055 sensor disabled")

            # MMC5603 (Magnetometer)
            if self.enable_mmc5603:
                try:
                    import adafruit_mmc56x3

                    self.mmc5603_sensor = adafruit_mmc56x3.MMC5603(self.i2c)
                    logger.info("MMC5603 sensor initialized")
                except Exception as e:
                    logger.warning(f"MMC5603 not available: {e}")
            else:
                logger.info("MMC5603 sensor disabled")

            # SGP30 (Air Quality Sensor)
            if self.enable_sgp30:
                try:
                    logger.info("SGP30: Starting initialization...")
                    logger.info("SGP30: Creating Adafruit_SGP30 sensor instance...")
                    self.sgp30_sensor = Adafruit_SGP30(self.i2c)
                    self.sgp30_start_time = time.time()  # Record start time for warmup
                    logger.info("SGP30: Sensor hardware initialized successfully")

                    # Load calibration data if available
                    if self.vessel_info:
                        logger.info("SGP30: Loading calibration data...")
                        self._load_sgp30_calibration()
                    else:
                        logger.info("SGP30: No vessel info available, skipping calibration")

                    # Give sensor time to stabilize after calibration loading
                    logger.info("SGP30: Waiting 2 seconds for sensor to stabilize after calibration...")
                    time.sleep(2)

                    # Test initial reading to check if sensor is working
                    logger.info("SGP30: Performing initial sensor test read...")
                    try:
                        tvoc = self.sgp30_sensor.TVOC
                        eco2 = self.sgp30_sensor.eCO2
                        logger.info(
                            f"SGP30: Initial test successful - TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                        )
                        logger.info(
                            "SGP30: Note - Initial readings may be baseline values. "
                            "Sensor needs time to stabilize for accurate readings."
                        )
                    except Exception as test_e:
                        logger.warning(f"SGP30: Initial test failed: {test_e}")
                        logger.warning("SGP30: Sensor may still work, but test read failed")

                    logger.info("SGP30: Initialization complete")
                except Exception as e:
                    logger.warning(f"SGP30: Not available: {e}")
                    logger.warning(f"SGP30: Error details: {type(e).__name__}: {str(e)}")
            else:
                logger.info("SGP30: Sensor disabled")

        def read_bme280_data(self):
            """Read data from BME280 sensor."""
            if not self.bme280_sensor:
                return {}

            try:
                data = self.bme280_sensor.read_all()

                # Validate temperature, humidity, and pressure readings
                if (
                    data.temperature is None
                    or data.temperature == 0
                    or data.temperature < -50
                    or data.temperature > 100
                ):
                    logger.debug(
                        f"BME280 temperature reading invalid: {data.temperature}°C"
                    )
                    return {}
                if (
                    data.humidity is None
                    or data.humidity == 0
                    or data.humidity < 0
                    or data.humidity > 100
                ):
                    logger.debug(f"BME280 humidity reading invalid: {data.humidity}%")
                    return {}
                if (
                    data.pressure is None
                    or data.pressure == 0
                    or data.pressure < 800
                    or data.pressure > 1200
                ):
                    logger.debug(f"BME280 pressure reading invalid: {data.pressure} hPa")
                    return {}

                # Return valid readings
                return {
                    "environment.inside.temperature": {
                        "value": data.temperature + 273.15,  # Convert C to K
                        "units": "K",
                    },
                    "environment.inside.humidity": {
                        "value": data.humidity / 100.0,
                        "units": "ratio",
                    },
                    "environment.inside.pressure": {
                        "value": data.pressure * 100,  # Convert hPa to Pa
                        "units": "Pa",
                    },
                }
            except Exception as e:
                logger.error(f"Error reading BME280: {e}")
                return {}

        def _load_bno055_calibration(self):
            """Load calibration data from vessel info and apply to BNO055."""
            try:
                # Check if calibration data exists in vessel info
                if (
                    "sensors" not in self.vessel_info
                    or "bno055_calibration" not in self.vessel_info["sensors"]
                ):
                    logger.info("No saved BNO055 calibration data found in vessel info")
                    return False

                cal_data = self.vessel_info["sensors"]["bno055_calibration"]

                # Validate the calibration data
                is_valid, message = validate_calibration_data(cal_data)
                if not is_valid:
                    logger.warning(f"Invalid BNO055 calibration data: {message}")
                    return False

                # Apply calibration data to BNO055
                if write_calibration(self.bno055_sensor, cal_data):
                    logger.info("BNO055 calibration data loaded and applied successfully")
                    return True
                else:
                    logger.warning("Failed to apply BNO055 calibration data")
                    return False

            except Exception as e:
                logger.error(f"Error loading BNO055 calibration data: {e}")
                return False

        def _load_sgp30_calibration(self):
            """Load calibration data from vessel info and apply to SGP30."""
            try:
                logger.debug("SGP30: Checking for calibration data in vessel config...")
                # Check if calibration data exists in vessel info
                if (
                    "sensors" not in self.vessel_info
                    or "sgp30_calibration" not in self.vessel_info["sensors"]
                ):
                    logger.info("SGP30: No saved calibration data found in vessel config")
                    return False

                logger.info("SGP30: Calibration data found, loading...")
                cal_data = self.vessel_info["sensors"]["sgp30_calibration"]

                # Set relative humidity for better accuracy
                if (
                    "relative_humidity_percent" in cal_data
                    and "temperature_celsius" in cal_data
                ):
                    humidity = cal_data["relative_humidity_percent"]
                    temperature = cal_data["temperature_celsius"]

                    logger.info(
                        f"SGP30: Setting environmental conditions - "
                        f"Temperature: {temperature}°C, Humidity: {humidity}%"
                    )
                    self.sgp30_sensor.set_iaq_relative_humidity(
                        celsius=temperature, relative_humidity=humidity
                    )
                    logger.info(
                        f"SGP30: Relative humidity compensation set to {humidity}% at {temperature}°C"
                    )
                else:
                    logger.info(
                        "SGP30: No temperature/humidity data in calibration, "
                        "sensor will use default environmental compensation"
                    )

                # Set baseline values if available
                if "tvoc_baseline_ppb" in cal_data and "eco2_baseline_ppm" in cal_data:
                    tvoc_baseline = int(cal_data["tvoc_baseline_ppb"])
                    eco2_baseline = int(cal_data["eco2_baseline_ppm"])

                    logger.info(
                        f"SGP30: Calibration baselines loaded - "
                        f"TVOC baseline: {tvoc_baseline} ppb, "
                        f"eCO2 baseline: {eco2_baseline} ppm"
                    )
                    logger.info(
                        "SGP30: Note - Baselines are informational. "
                        "Sensor uses internal baseline management."
                    )
                else:
                    logger.info(
                        "SGP30: No baseline values in calibration data, "
                        "sensor will establish baselines automatically"
                    )

                logger.info("SGP30: Calibration data loaded and applied successfully")
                return True

            except Exception as e:
                logger.error(f"SGP30: Error loading calibration data: {e}")
                logger.error(f"SGP30: Calibration error details: {type(e).__name__}: {str(e)}")
                return False

        def read_bno055_data(self):
            """Read data from BNO055 sensor."""
            if not self.bno055_sensor:
                return {}

            try:
                # Check if sensor is calibrated (only warn once)
                if not self.bno055_sensor.calibrated and not hasattr(
                    self, "_bno055_calibration_warned"
                ):
                    logger.warning(
                        "BNO055 not calibrated - move sensor in figure-8 pattern to calibrate"
                    )
                    self._bno055_calibration_warned = True

                # Read gyroscope
                gyro = self.bno055_sensor.gyro

                # Read euler angles
                euler = self.bno055_sensor.euler

                data = {}

                if gyro and all(x is not None for x in gyro) and gyro[2] != 0.0:
                    # Convert gyroscope from degrees/s to radians/s
                    data["navigation.attitude.rateOfTurn"] = {
                        "value": (gyro[2] * math.pi / 180),
                        "units": "rad/s",
                    }

                if euler and all(x is not None for x in euler):

                    t0 = time.time()
                    while 0 in euler:
                        time.sleep(0.1)
                        euler = self.bno055_sensor.euler
                        if time.time() - t0 > 10:
                            logger.error("BNO055 Euler angles still 0 after 10 seconds")
                            raise TimeoutError("BNO055 Euler angles still 0 after 10 seconds")

                    # Convert Euler angles from degrees to radians
                    roll_raw = euler[0] * math.pi / 180
                    pitch_raw = euler[1] * math.pi / 180
                    yaw_raw = euler[2] * math.pi / 180

                    # Apply zero state calibration for pitch and roll
                    roll_calibrated = roll_raw
                    pitch_calibrated = pitch_raw

                    if (
                        "sensors" in self.vessel_info
                        and "bno055_zero_state" in self.vessel_info["sensors"]
                    ):
                        zero_state = self.vessel_info["sensors"]["bno055_zero_state"]
                        roll_calibrated = roll_raw - zero_state.get("roll", 0)
                        pitch_calibrated = pitch_raw - zero_state.get("pitch", 0)

                    # Apply yaw offset calibration
                    yaw_calibrated = yaw_raw
                    if (
                        "sensors" in self.vessel_info
                        and "bno055_yaw_offset" in self.vessel_info["sensors"]
                    ):
                        yaw_offset = self.vessel_info["sensors"]["bno055_yaw_offset"]
                        yaw_calibrated = yaw_raw + yaw_offset.get("offset", 0)

                        # Normalize yaw to 0-2π range
                        while yaw_calibrated < 0:
                            yaw_calibrated += 2 * math.pi
                        while yaw_calibrated >= 2 * math.pi:
                            yaw_calibrated -= 2 * math.pi

                    data["navigation.attitude.roll"] = {
                        "value": roll_calibrated,
                        "units": "rad",
                    }
                    data["navigation.attitude.pitch"] = {
                        "value": pitch_calibrated,
                        "units": "rad",
                    }
                    data["navigation.attitude.yaw"] = {
                        "value": yaw_calibrated,
                        "units": "rad",
                    }
                return data
            except Exception as e:
                logger.error(f"Error reading BNO055: {e}")
                return {}

        def read_mmc5603_data(self):
            """Read data from MMC5603 sensor."""
            if not self.mmc5603_sensor:
                return {}

            try:
                # Read magnetic field
                mag_x, mag_y, mag_z = self.mmc5603_sensor.magnetic

                # Calculate magnetic heading (simplified)
                heading = 0
                if mag_x != 0 or mag_y != 0:
                    heading = 3.14159 / 2 - math.atan2(mag_y, mag_x)
                    heading += self.heading_correction_offset
                    if heading < 0:
                        heading += 3.14159 * 2

                if heading is None or heading == 0:
                    logger.debug(f"MMC5603 heading reading invalid: {heading} rad")
                    return {}

                return {
                    "navigation.headingMagnetic": {"value": heading, "units": "rad"},
                }
            except Exception as e:
                logger.error(f"Error reading MMC5603: {e}")
                return {}

        def read_sgp30_data(self):
            """Read data from SGP30 air quality sensor."""
            if not self.sgp30_sensor:
                return {}

            try:
                # Wait for SGP30 to stabilize and provide real readings
                # Need TVOC > 0 AND eCO2 > 400 for a "good" reading
                logger.info("SGP30: Starting stabilization process...")
                logger.info(
                    "SGP30: Waiting for sensor to stabilize (requires TVOC > 0 and eCO2 > 400)"
                )
                max_attempts = 60  # Maximum 60 attempts (60 seconds)
                attempt = 0
                consecutive_good_readings = 0
                required_good_readings = 20

                logger.info(
                    f"SGP30: Stabilization parameters - "
                    f"Max attempts: {max_attempts}, "
                    f"Required consecutive good readings: {required_good_readings}"
                )

                while attempt < max_attempts:
                    # Small delay to let sensor update
                    time.sleep(1)

                    # Read TVOC and eCO2 values
                    tvoc = self.sgp30_sensor.TVOC
                    eco2 = self.sgp30_sensor.eCO2

                    # Log every 5 attempts for progress visibility
                    if attempt % 5 == 0:
                        logger.info(
                            f"SGP30: Stabilization progress - "
                            f"Attempt {attempt + 1}/{max_attempts}, "
                            f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm, "
                            f"Consecutive good: {consecutive_good_readings}/{required_good_readings}"
                        )

                    # Check if we have meaningful readings (not just baseline values)
                    # Require TVOC > 0 AND eCO2 > 400 for a "good" reading
                    is_good_reading = (
                        tvoc is not None and eco2 is not None and tvoc > 0 and eco2 > 400
                    )

                    if is_good_reading:
                        consecutive_good_readings += 1
                        logger.info(
                            f"SGP30: Good reading detected ({consecutive_good_readings}/{required_good_readings}) - "
                            f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                        )

                        # If we have enough consecutive good readings, return the latest one
                        if consecutive_good_readings >= required_good_readings:
                            logger.info(
                                f"SGP30: ✓ Sensor stabilized after {attempt + 1} seconds "
                                f"with {consecutive_good_readings} consecutive good readings"
                            )
                            logger.info(
                                f"SGP30: Final stabilization values - "
                                f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                            )
                            logger.info(
                                f"SGP30: Publishing readings - TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                            )
                            return {
                                "environment.inside.airQuality.tvoc": {
                                    "value": tvoc,
                                    "units": "ppb",
                                },
                                "environment.inside.airQuality.eco2": {
                                    "value": eco2,
                                    "units": "ppm",
                                },
                            }
                    else:
                        # Reset counter if we get a bad reading
                        if consecutive_good_readings > 0:
                            logger.info(
                                f"SGP30: Good reading streak broken (was {consecutive_good_readings}), "
                                f"resetting counter. Current: TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                            )
                        consecutive_good_readings = 0
                        logger.debug(
                            f"SGP30: Stabilizing... attempt {attempt + 1}/{max_attempts} - "
                            f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm (baseline/warming up)"
                        )

                    attempt += 1

                # If we've tried for 60 seconds and still getting baseline values, return them anyway
                logger.warning(
                    f"SGP30: ⚠ Still returning baseline values after {max_attempts} seconds"
                )
                logger.warning(
                    f"SGP30: Final attempt values - TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                )
                logger.warning(
                    "SGP30: Proceeding with readings anyway. "
                    "Sensor may need more time or environmental conditions may be very stable."
                )
                return {}

            except Exception as e:
                logger.error(f"SGP30: Error reading sensor: {e}")
                logger.error(f"SGP30: Error details: {type(e).__name__}: {str(e)}")
                return {}

        def read_all_sensors(self):
            """Read data from all available sensors."""
            data = {}

            # Read from each sensor
            data.update(self.read_bme280_data())
            data.update(self.read_bno055_data())
            data.update(self.read_mmc5603_data())
            data.update(self.read_sgp30_data())

            return data

        def create_signalk_delta(self, data):
            """Create SignalK delta message."""
            timestamp = datetime.now(UTC).isoformat()

            # Use standard vessel context for UDP publishing
            context = "vessels.self"

            # Create delta with proper SignalK format including $source
            delta = {
                "context": context,
                "updates": [
                    {
                        "source": {
                            "label": I2C_SENSORS_LABEL,
                            "type": "I2C",
                            "src": "inside",
                            "$source": I2C_SENSORS_SOURCE,
                        },
                        "timestamp": timestamp,
                        "values": [],
                        "meta": [],
                    }
                ],
            }

            # Add each data point to the delta
            for path, value_dict in data.items():
                value_entry = {
                    "path": path,
                    "value": value_dict["value"],
                    "$source": I2C_SENSORS_SOURCE,
                }
                # Include units if available (some SignalK servers support this)
                if "units" in value_dict:
                    value_entry["units"] = value_dict["units"]
                delta["updates"][0]["values"].append(value_entry)

                # Also add metadata for units (SignalK standard way)
                if "units" in value_dict:
                    meta_entry = {
                        "path": path,
                        "value": {
                            "units": value_dict["units"],
                        },
                    }
                    delta["updates"][0]["meta"].append(meta_entry)

            return delta

        def publish_to_signalk(self, data):
            """Publish data to SignalK server via UDP."""
            if not data:
                logger.warning("No data to publish")
                return

            try:
                # Create delta message
                delta = self.create_signalk_delta(data)

                # Debug: log the delta message
                logger.debug(f"Sending delta: {json.dumps(delta, indent=2)}")

                # Publish via UDP
                logger.info("Publishing via UDP")
                if self._publish_via_udp(delta):
                    logger.info(f"Successfully published {len(data)} data points via UDP")
                else:
                    logger.error("UDP publishing failed")

            except Exception as e:
                logger.error(f"Error publishing to SignalK: {e}")

        def _publish_via_udp(self, delta):
            """Publish data to SignalK server via UDP."""
            try:
                # Ensure UDP socket is created
                if not self.udp_socket:
                    if not self.connect_udp():
                        return False

                # Calculate message length for verification
                message_bytes = (json.dumps(delta) + "\n").encode("utf-8")

                # Send and capture return value (number of bytes sent)
                bytes_sent = send_delta_over_udp(
                    self.udp_socket, self.signalk_host, self.udp_port, delta
                )

                # Check if all bytes were sent
                if bytes_sent == len(message_bytes):
                    logger.debug(
                        f"UDP send successful: {bytes_sent}/{len(message_bytes)} bytes sent to {self.signalk_host}:{self.udp_port}"
                    )
                    return True
                else:
                    logger.warning(
                        f"UDP send incomplete: {bytes_sent}/{len(message_bytes)} bytes sent to {self.signalk_host}:{self.udp_port}"
                    )
                    return False

            except TimeoutError:
                logger.error(f"UDP send timeout to {self.signalk_host}:{self.udp_port}")
                return False
            except OSError as e:
                logger.error(f"UDP socket error: {e}")
                # Close and reset UDP socket on error
                if self.udp_socket:
                    try:
                        self.udp_socket.close()
                    except Exception:
                        pass
                    self.udp_socket = None
                return False
            except Exception as e:
                logger.error(f"Error publishing via UDP: {e}")
                # Close and reset UDP socket on error
                if self.udp_socket:
                    try:
                        self.udp_socket.close()
                    except Exception:
                        pass
                    self.udp_socket = None
                return False

        def cleanup(self):
            """Clean up resources."""
            # Close UDP socket
            if self.udp_socket:
                try:
                    self.udp_socket.close()
                    logger.info("UDP socket closed")
                except Exception:
                    pass
                self.udp_socket = None

        def run(self):
            """Read sensors and publish data once."""
            logger.info("Reading sensors and publishing data...")

            try:
                # Read all sensors
                data = self.read_all_sensors()

                if data:
                    # Publish to SignalK
                    self.publish_to_signalk(data)

                    # Log some key values
                    if "environment.inside.temperature" in data:
                        temp = data["environment.inside.temperature"]["value"]
                        logger.info(f"Temperature: {temp:.1f}K")

                    logger.info(f"Successfully published {len(data)} sensor readings")

                else:
                    logger.warning("No sensor data available")

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            finally:
                self.cleanup()

    # Run in legacy mode
    logger.warning(
        "Running in legacy multi-sensor mode. "
        "Consider using individual sensor services instead: "
        "python3 i2c_sensor_read_and_publish.py <sensor_name>"
    )

    reader = LegacySensorReader(
        signalk_host=signalk_host,
        signalk_port=signalk_port,
        udp_port=udp_port,
        info_path=info_path,
        enable_bme280=enable_bme280,
        enable_bno055=enable_bno055,
        enable_mmc5603=enable_mmc5603,
        enable_sgp30=enable_sgp30,
    )
    reader.run()


def test_signalk_connection(host=None, port=None, udp_port=None):
    """Test SignalK UDP connection without sensors."""
    setup_logging(level="INFO")
    logger.info("Testing SignalK UDP connection...")

    import json
    import socket
    from datetime import UTC, datetime

    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(5.0)

        # Create test delta
        timestamp = datetime.now(UTC).isoformat()
        test_data = {
            "environment.inside.temperature": {
                "value": 293.15,  # 20 degC in Kelvin
                "units": "K",
            }
        }

        delta = {
            "context": "vessels.self",
            "updates": [
                {
                    "source": {
                        "label": "Test",
                        "type": "I2C",
                        "src": "test",
                        "$source": "test",
                    },
                    "timestamp": timestamp,
                    "values": [
                        {
                            "path": "environment.inside.temperature",
                            "value": 293.15,
                            "units": "K",
                            "$source": "test",
                        }
                    ],
                }
            ],
        }

        bytes_sent = send_delta_over_udp(udp_socket, host, udp_port or DEFAULT_UDP_PORT, delta)
        logger.info(f"SUCCESS: SignalK UDP connection successful ({bytes_sent} bytes sent)")
        udp_socket.close()
        return True
    except Exception as e:
        logger.error(f"ERROR: SignalK UDP connection failed: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="I2C Sensors to SignalK Publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run individual sensor service (recommended):
  python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50
  
  # Run once for testing:
  python3 i2c_sensor_read_and_publish.py bno055 --once
  
  # Legacy multi-sensor mode (deprecated):
  python3 i2c_sensor_read_and_publish.py --host 192.168.8.50 --disable-sgp30
        """,
    )

    # Sensor name (optional, for individual sensor mode)
    parser.add_argument(
        "sensor",
        nargs="?",
        choices=list(SENSOR_CLASSES.keys()) + [None],
        help="Sensor name to run (individual sensor mode). If not provided, runs in legacy multi-sensor mode.",
    )

    # Common arguments
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="SignalK server host (overrides config)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="SignalK server port (overrides config)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=None,
        help=f"UDP port for publishing (default: {DEFAULT_UDP_PORT})",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="data/vessel/info.yaml",
        help="Path to vessel config file",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Update interval in seconds (overrides config, individual sensor mode only)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing, individual sensor mode only)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test SignalK connection only",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    # Legacy multi-sensor mode arguments
    parser.add_argument(
        "--disable-bme280",
        action="store_true",
        help="Disable BME280 sensor (legacy mode only)",
    )
    parser.add_argument(
        "--disable-bno055",
        action="store_true",
        help="Disable BNO055 sensor (legacy mode only)",
    )
    parser.add_argument(
        "--disable-mmc5603",
        action="store_true",
        help="Disable MMC5603 sensor (legacy mode only)",
    )
    parser.add_argument(
        "--disable-sgp30",
        action="store_true",
        help="Disable SGP30 sensor (legacy mode only)",
    )

    args = parser.parse_args()

    # Test mode
    if args.test:
        success = test_signalk_connection(args.host, args.port, args.udp_port)
        sys.exit(0 if success else 1)

    # Individual sensor mode (recommended)
    if args.sensor:
        run_individual_sensor(
            sensor_name=args.sensor,
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            info_path=args.config,
            update_interval=args.interval,
            once=args.once,
            log_level=args.log_level,
        )
    else:
        # Legacy multi-sensor mode
        run_legacy_multi_sensor_mode(
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            info_path=args.config,
            enable_bme280=not args.disable_bme280,
            enable_bno055=not args.disable_bno055,
            enable_mmc5603=not args.disable_mmc5603,
            enable_sgp30=not args.disable_sgp30,
            log_level=args.log_level,
        )


if __name__ == "__main__":
    main()
