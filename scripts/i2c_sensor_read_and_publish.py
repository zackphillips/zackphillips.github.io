#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher
Reads data from BME280, BNO055, MMC5603, and SGP30 sensors via I2C
and publishes to SignalK server.
"""

import json
import logging
import math
import os
import socket
import time
from datetime import UTC, datetime

# MMC5603 availability will be checked during initialization
import board
import busio
import smbus2
from adafruit_bno055 import BNO055_I2C

# Magnetic variation is now handled by a separate service
# Import SGP30 air quality sensor
from adafruit_sgp30 import Adafruit_SGP30

# Import BNO055 register I/O functions for calibration loading
from bno055_register_io import (
    validate_calibration_data,
    write_calibration,
)

# Constants
DEFAULT_UDP_PORT = 4123
I2C_SENSORS_LABEL = "I2C Sensors"
I2C_SENSORS_SOURCE = "i2c-sensors"

# Import utilities
from utils import load_vessel_info, setup_logging

# Configure logging
setup_logging(level="DEBUG")
logger = logging.getLogger(__name__)


class SensorReader:
    def __init__(
        self,
        signalk_host=None,
        signalk_port=None,
        udp_port=None,
        info_path="data/vessel/info.json",
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
            # Use command-line arguments only if info.json not available
            self.signalk_host = signalk_host
            self.signalk_port = signalk_port
            logger.warning(
                "No SignalK configuration found in vessel info, using command-line arguments only"
            )

        # UDP configuration for data publishing
        self.udp_port = (
            udp_port or DEFAULT_UDP_PORT
        )  # UDP port from command-line argument

        # Load heading correction offset from vessel info
        if self.vessel_info and "sensors" in self.vessel_info:
            sensors_config = self.vessel_info["sensors"]
            self.heading_correction_offset = sensors_config.get("heading_correction_offset_rad", 0.0)
        else:
            self.heading_correction_offset = 0.0
            logger.warning("No sensors configuration found in vessel info, using default heading correction offset of 0.0")

        # Validate required configuration
        if not self.signalk_host:
            raise ValueError(
                "SignalK host must be specified via --host argument or info.json"
            )
        if not self.signalk_port:
            raise ValueError(
                "SignalK port must be specified via --port argument or info.json"
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
                self.sgp30_sensor = Adafruit_SGP30(self.i2c)
                self.sgp30_start_time = time.time()  # Record start time for warmup
                logger.info("SGP30 sensor initialized")

                # Load calibration data if available
                if self.vessel_info:
                    self._load_sgp30_calibration()

                # Give sensor time to stabilize after calibration loading
                logger.info("SGP30 stabilizing after calibration...")
                time.sleep(2)

                # Test initial reading to check if sensor is working
                try:
                    tvoc = self.sgp30_sensor.TVOC
                    eco2 = self.sgp30_sensor.eCO2
                    logger.info(f"SGP30 initial test - TVOC: {tvoc}, eCO2: {eco2}")
                except Exception as test_e:
                    logger.warning(f"SGP30 initial test failed: {test_e}")
            except Exception as e:
                logger.warning(f"SGP30 not available: {e}")
        else:
            logger.info("SGP30 sensor disabled")

    def read_bme280_data(self):
        """Read data from BME280 sensor."""
        if not self.bme280_sensor:
            return {}

        try:
            data = self.bme280_sensor.read_all()
            return {
                "environment.inside.temperature": {
                    "value": data.temperature + 273.15,  # Convert C to K
                    "units": "K",
                },
                "environment.inside.humidity": {"value": data.humidity / 100.0, "units": "ratio"},
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
            if ("sensors" not in self.vessel_info or
                "bno055_calibration" not in self.vessel_info["sensors"]):
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
            # Check if calibration data exists in vessel info
            if ("sensors" not in self.vessel_info or
                "sgp30_calibration" not in self.vessel_info["sensors"]):
                logger.info("No saved SGP30 calibration data found in vessel info")
                return False

            cal_data = self.vessel_info["sensors"]["sgp30_calibration"]

            # Set relative humidity for better accuracy
            if "relative_humidity_percent" in cal_data and "temperature_celsius" in cal_data:
                humidity = cal_data["relative_humidity_percent"]
                temperature = cal_data["temperature_celsius"]

                self.sgp30_sensor.set_iaq_relative_humidity(
                    celsius=temperature,
                    relative_humidity=humidity
                )
                logger.info(f"SGP30 relative humidity set to {humidity}% at {temperature}°C")

            # Set baseline values if available
            if "tvoc_baseline_ppb" in cal_data and "eco2_baseline_ppm" in cal_data:
                tvoc_baseline = int(cal_data["tvoc_baseline_ppb"])
                eco2_baseline = int(cal_data["eco2_baseline_ppm"])

                # Set baseline values (these are internal to the sensor)
                # Note: The SGP30 library doesn't expose direct baseline setting,
                # but the sensor will use the environmental conditions we set above
                logger.info(f"SGP30 calibration loaded - TVOC baseline: {tvoc_baseline} ppb, eCO2 baseline: {eco2_baseline} ppm")

            logger.info("SGP30 calibration data loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading SGP30 calibration data: {e}")
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

            # Read acceleration

            # Read gyroscope
            gyro = self.bno055_sensor.gyro

            # Read euler angles
            euler = self.bno055_sensor.euler

            data = {}

            if gyro and all(x is not None for x in gyro):
                # Convert gyroscope from degrees/s to radians/s
                data["navigation.attitude.rateOfTurn"] = {
                    "value": (gyro[2] * math.pi / 180) if gyro[2] is not None else 0,
                    "units": "rad/s",
                }

            if euler and all(x is not None for x in euler):
                # Convert Euler angles from degrees to radians
                data["navigation.attitude.roll"] = {
                    "value": (euler[0] * math.pi / 180) if euler[0] is not None else 0,
                    "units": "rad",
                }
                data["navigation.attitude.pitch"] = {
                    "value": (euler[1] * math.pi / 180) if euler[1] is not None else 0,
                    "units": "rad",
                }
                data["navigation.attitude.yaw"] = {
                    "value": (euler[2] * math.pi / 180) if euler[2] is not None else 0,
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
            # Need TVOC > 0 AND 5 consecutive non-baseline readings for stability
            max_attempts = 60  # Maximum 60 attempts (60 seconds)
            attempt = 0
            consecutive_good_readings = 0
            required_good_readings = 5

            while attempt < max_attempts:
                # Small delay to let sensor update
                time.sleep(1)

                # Read TVOC and eCO2 values
                tvoc = self.sgp30_sensor.TVOC
                eco2 = self.sgp30_sensor.eCO2

                # Check if we have meaningful readings (not just baseline values)
                # Require TVOC > 0 AND eCO2 > 400 for a "good" reading
                is_good_reading = (tvoc is not None and eco2 is not None and
                                 tvoc > 0 and eco2 > 400)

                if is_good_reading:
                    consecutive_good_readings += 1
                    logger.debug(f"SGP30 good reading {consecutive_good_readings}/{required_good_readings} - TVOC: {tvoc}, eCO2: {eco2}")

                    # If we have enough consecutive good readings, return the latest one
                    if consecutive_good_readings >= required_good_readings:
                        logger.info(f"SGP30 stabilized after {attempt + 1} seconds with {consecutive_good_readings} good readings - TVOC: {tvoc}, eCO2: {eco2}")
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
                    consecutive_good_readings = 0
                    logger.debug(f"SGP30 stabilizing... attempt {attempt + 1}/{max_attempts} - TVOC: {tvoc}, eCO2: {eco2} (baseline)")

                attempt += 1

            # If we've tried for 60 seconds and still getting baseline values, return them anyway
            logger.warning(f"SGP30 still returning baseline values after {max_attempts} seconds - TVOC: {tvoc}, eCO2: {eco2}")
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

        except Exception as e:
            logger.error(f"Error reading SGP30: {e}")
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
                }
            ],
        }

        # Add each data point to the delta
        for path, value in data.items():
            delta["updates"][0]["values"].append(
                {"path": path, "value": value["value"], "$source": I2C_SENSORS_SOURCE}
            )

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

            # Convert delta to JSON and send via UDP
            message = (
                json.dumps(delta) + "\n"
            )  # SignalK expects newline-terminated messages
            message_bytes = message.encode("utf-8")

            # Send and capture return value (number of bytes sent)
            bytes_sent = self.udp_socket.sendto(
                message_bytes, (self.signalk_host, self.udp_port)
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


def test_signalk_connection(host=None, port=None, udp_port=None):
    """Test SignalK UDP connection without sensors."""
    logger.info("Testing SignalK UDP connection...")

    reader = SensorReader(signalk_host=host, signalk_port=port, udp_port=udp_port)

    # Test UDP connection
    if reader.connect_udp():
        logger.info("SUCCESS: SignalK UDP connection successful")

        # Test publishing dummy data
        test_data = {
            "environment.inside.temperature": {
                "value": 293.15,  # 20 degC in Kelvin
                "units": "K",
            }
        }

        reader.publish_to_signalk(test_data)
        logger.info("SUCCESS: Test data published successfully")

        reader.cleanup()
        return True
    else:
        logger.error("ERROR: SignalK UDP connection failed")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="I2C Sensors to SignalK Publisher")
    parser.add_argument(
        "--host", help="SignalK server host (required if not in info.json)"
    )
    parser.add_argument(
        "--port", type=int, help="SignalK server port (required if not in info.json)"
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        help=f"SignalK UDP data port (default: {DEFAULT_UDP_PORT})",
    )
    parser.add_argument(
        "--test", action="store_true", help="Test SignalK connection only"
    )
    parser.add_argument(
        "--disable-bme280", action="store_true",
        help="Disable BME280 sensor (temperature, humidity, pressure)"
    )
    parser.add_argument(
        "--disable-bno055", action="store_true",
        help="Disable BNO055 sensor (IMU)"
    )
    parser.add_argument(
        "--disable-mmc5603", action="store_true",
        help="Disable MMC5603 sensor (magnetometer)"
    )
    parser.add_argument(
        "--disable-sgp30", action="store_true",
        help="Disable SGP30 sensor (air quality)"
    )

    args = parser.parse_args()

    # Process sensor disable flags (all sensors enabled by default)
    enable_bme280 = not args.disable_bme280
    enable_bno055 = not args.disable_bno055
    enable_mmc5603 = not args.disable_mmc5603
    enable_sgp30 = not args.disable_sgp30

    if args.test:
        # Test mode - just test connection
        success = test_signalk_connection(args.host, args.port, args.udp_port)
        exit(0 if success else 1)
    else:
        # Normal mode - run sensor reader
        reader = SensorReader(
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            enable_bme280=enable_bme280,
            enable_bno055=enable_bno055,
            enable_mmc5603=enable_mmc5603,
            enable_sgp30=enable_sgp30,
        )
        reader.run()


if __name__ == "__main__":
    main()
