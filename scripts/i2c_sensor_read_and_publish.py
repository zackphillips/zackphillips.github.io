#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher
Reads data from BME280, BNO055, SGP30, and MMC5603 sensors via I2C
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

# Constants
DEFAULT_UDP_PORT = 4123
I2C_SENSORS_LABEL = "I2C Sensors"
I2C_SENSORS_SOURCE = "i2c-sensors"
# HEADING_CORRECTION_OFFSET is now loaded from vessel info.json
SGP30_WARMUP_POLL_PERIOD_S = 0.5
SGP30_WARMUP_TIMEOUT_S = 5.0
SGP30_VOC_PLACEHOLDER_VALUE = 0.0
SGP30_CO2_PLACEHOLDER_VALUE = 400

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_vessel_info(info_path="data/vessel/info.json"):
    """Load vessel information from info.json file."""
    try:
        # Get the absolute path relative to the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        full_path = os.path.join(project_root, info_path)

        with open(full_path) as f:
            info = json.load(f)

        logger.info(f"Loaded vessel info from {full_path}")
        return info
    except Exception as e:
        logger.error(f"Failed to load vessel info from {info_path}: {e}")
        return None


class SensorReader:
    def __init__(
        self,
        signalk_host=None,
        signalk_port=None,
        udp_port=None,
        info_path="data/vessel/info.json",
    ):
        """Initialize sensor reader and SignalK connection."""
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
        self.sgp30_sensor = None
        self.mmc5603_sensor = None

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
        try:
            import bme280.bme280 as bme280_module

            # Initialize BME280 with smbus2
            bme280_module.full_setup(1, 0x77)  # bus_number=1, i2c_address=0x77
            self.bme280_sensor = bme280_module
            logger.info("BME280 sensor initialized")
        except Exception as e:
            logger.warning(f"BME280 not available: {e}")

        # BNO055 (9-DOF IMU)
        try:
            self.bno055_sensor = BNO055_I2C(self.i2c)
            logger.info("BNO055 sensor initialized")
        except Exception as e:
            logger.warning(f"BNO055 not available: {e}")

        # SGP30 (Air Quality)
        try:
            from adafruit_sgp30 import Adafruit_SGP30

            self.sgp30_sensor = Adafruit_SGP30(self.i2c)

            self.sgp30_sensor.set_iaq_baseline(0x8973, 0x8AAE)
            self.sgp30_sensor.set_iaq_relative_humidity(
                celsius=25.0, relative_humidity=50.0
            )

            # Read initial values to warm-start
            voc, co2 = SGP30_VOC_PLACEHOLDER_VALUE, SGP30_CO2_PLACEHOLDER_VALUE
            t0 = datetime.now()
            while (voc == SGP30_VOC_PLACEHOLDER_VALUE) and (
                co2 == SGP30_CO2_PLACEHOLDER_VALUE
            ):
                if (datetime.now() - t0).total_seconds() > SGP30_WARMUP_TIMEOUT_S:
                    raise TimeoutError("SGP30 warm-up timeout.")

                voc = self.sgp30_sensor.TVOC
                co2 = self.sgp30_sensor.eCO2
                time.sleep(SGP30_WARMUP_POLL_PERIOD_S)
                logger.info(f"SGP30 initial values: {voc} TVOC, {co2} eCO2")
        except Exception as e:
            logger.warning(f"SGP30 not available: {e}")

        # MMC5603 (Magnetometer)
        try:
            import adafruit_mmc56x3

            self.mmc5603_sensor = adafruit_mmc56x3.MMC5603(self.i2c)
            logger.info("MMC5603 sensor initialized")
        except Exception as e:
            logger.warning(f"MMC5603 not available: {e}")

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
                "environment.inside.humidity": {"value": data.humidity, "units": "%"},
                "environment.inside.pressure": {
                    "value": data.pressure * 100,  # Convert hPa to Pa
                    "units": "Pa",
                },
            }
        except Exception as e:
            logger.error(f"Error reading BME280: {e}")
            return {}

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
            accel = self.bno055_sensor.acceleration

            # Read gyroscope
            gyro = self.bno055_sensor.gyro

            # Read euler angles
            euler = self.bno055_sensor.euler

            data = {}

            if accel and all(x is not None for x in accel):
                data["navigation.attitude.rateOfTurn"] = {
                    "value": gyro[2] if gyro and gyro[2] is not None else 0,
                    "units": "rad/s",
                }

            if euler and all(x is not None for x in euler):
                data["navigation.attitude.roll"] = {
                    "value": euler[0] if euler[0] is not None else 0,
                    "units": "rad",
                }
                data["navigation.attitude.pitch"] = {
                    "value": euler[1] if euler[1] is not None else 0,
                    "units": "rad",
                }
                data["navigation.attitude.yaw"] = {
                    "value": euler[2] if euler[2] is not None else 0,
                    "units": "rad",
                }

            return data
        except Exception as e:
            logger.error(f"Error reading BNO055: {e}")
            return {}

    def read_sgp30_data(self):
        """Read data from SGP30 sensor."""
        if not self.sgp30_sensor:
            return {}

        try:
            # Read TVOC and eCO2
            tvoc = self.sgp30_sensor.TVOC
            eco2 = self.sgp30_sensor.eCO2

            # Log sensor status for debugging
            if tvoc == 0 and eco2 == 400:
                raise RuntimeError(
                    "SGP30: Reas default values (sensor may need calibration)"
                )
            logger.debug(f"SGP30: TVOC={tvoc} ppb, eCO2={eco2} ppm")

            return {
                "environment.inside.airQuality.tvoc": {"value": tvoc, "units": "ppb"},
                "environment.inside.airQuality.co2": {"value": eco2, "units": "ppm"},
            }
        except Exception as e:
            logger.error(f"Error reading SGP30: {e}")
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
                "navigation.magneticVariation": {
                    "value": 0,  # Would need to calculate based on location
                    "units": "rad",
                },
            }
        except Exception as e:
            logger.error(f"Error reading MMC5603: {e}")
            return {}

    def read_all_sensors(self):
        """Read data from all available sensors."""
        data = {}

        # Read from each sensor
        data.update(self.read_bme280_data())
        data.update(self.read_bno055_data())
        data.update(self.read_sgp30_data())
        data.update(self.read_mmc5603_data())

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
        logger.info("✓ SignalK UDP connection successful")

        # Test publishing dummy data
        test_data = {
            "environment.inside.temperature": {
                "value": 293.15,  # 20°C in Kelvin
                "units": "K",
            }
        }

        reader.publish_to_signalk(test_data)
        logger.info("✓ Test data published successfully")

        reader.cleanup()
        return True
    else:
        logger.error("✗ SignalK UDP connection failed")
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

    args = parser.parse_args()

    if args.test:
        # Test mode - just test connection
        success = test_signalk_connection(args.host, args.port, args.udp_port)
        exit(0 if success else 1)
    else:
        # Normal mode - run sensor reader
        reader = SensorReader(
            signalk_host=args.host, signalk_port=args.port, udp_port=args.udp_port
        )
        reader.run()


if __name__ == "__main__":
    main()
