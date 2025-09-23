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
import requests
import smbus2
import websocket
from adafruit_bno055 import BNO055_I2C
from adafruit_sgp30 import Adafruit_SGP30

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
        tcp_port=None,
        info_path="data/vessel/info.json",
    ):
        """Initialize sensor reader and SignalK connection."""
        # Load vessel info from JSON file
        self.vessel_info = load_vessel_info(info_path)

        if self.vessel_info and "signalk" in self.vessel_info:
            signalk_config = self.vessel_info["signalk"]
            self.signalk_host = signalk_host or signalk_config.get(
                "host", "192.168.8.50"
            )
            self.signalk_port = signalk_port or signalk_config.get("port", 3000)
            self.signalk_protocol = signalk_config.get("protocol", "http")
            self.signalk_token = signalk_config.get("token")
        else:
            # Fallback to defaults if info.json not available
            self.signalk_host = signalk_host or "192.168.8.50"
            self.signalk_port = signalk_port or 3000
            self.signalk_protocol = "http"
            self.signalk_token = None
            logger.warning(
                "No SignalK configuration found in vessel info, using defaults"
            )

        # UDP configuration for data publishing
        self.udp_port = (
            tcp_port or 4123
        )  # Default SignalK UDP port (reusing tcp_port parameter)
        self.udp_socket = None

        self.signalk_ws_url = f"ws://{self.signalk_host}:{self.signalk_port}/signalk/v1/stream?subscribe=self"
        self.signalk_ws_publish_url = (
            f"ws://{self.signalk_host}:{self.signalk_port}/signalk/v1/stream/self"
        )

        self.ws = None
        self.ws_connected = False
        self.vessel_self = None  # Will be set from hello message

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

    def get_auth_token(self):
        """Get authentication token from info.json."""
        if self.signalk_token:
            logger.info("Using SignalK token from vessel info")
            return self.signalk_token
        else:
            logger.error("No SignalK token available in vessel info")
            return None

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

            bme280_module.full_setup(1, 0x76)  # bus_number=1, i2c_address=0x76
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
            self.sgp30_sensor = Adafruit_SGP30(self.i2c)
            logger.info("SGP30 sensor initialized")
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
                "environment.outside.temperature": {
                    "value": data.temperature + 273.15,  # Convert C to K
                    "units": "K",
                },
                "environment.outside.humidity": {"value": data.humidity, "units": "%"},
                "environment.outside.pressure": {
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
                heading = (180 / 3.14159) * (3.14159 / 2 - math.atan2(mag_y, mag_x))
                if heading < 0:
                    heading += 360

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

        # Use the vessel self ID from hello message, fallback to vessels.self
        context = self.vessel_self if self.vessel_self else "vessels.self"

        # Create delta with proper SignalK format including $source
        delta = {
            "context": context,
            "updates": [
                {
                    "source": {
                        "label": "I2C Sensors",
                        "type": "I2C",
                        "src": "inside",
                        "$source": "i2c-sensors",
                    },
                    "timestamp": timestamp,
                    "values": [],
                }
            ],
        }

        # Add each data point to the delta
        for path, value in data.items():
            delta["updates"][0]["values"].append(
                {"path": path, "value": value["value"], "$source": "i2c-sensors"}
            )

        return delta

    def connect_websocket(self):
        """Connect to SignalK WebSocket using token from info.json."""
        try:
            # Get token from info.json
            token = self.get_auth_token()
            if not token:
                logger.error(
                    "Cannot connect to SignalK WebSocket: no authentication token available"
                )
                self.ws_connected = False
                return

            # Connect with Bearer token authentication
            headers = {"Authorization": f"Bearer {token}"}
            logger.debug(f"Connecting to SignalK WebSocket: {self.signalk_ws_url}")
            logger.debug(f"Using Authorization header: Bearer {token[:20]}...")

            self.ws = websocket.WebSocket()
            self.ws.connect(self.signalk_ws_url, header=headers)
            self.ws_connected = True
            logger.info("Connected to SignalK WebSocket with token from vessel info")

            # Wait for and handle hello message
            self._handle_hello_message()

        except Exception as e:
            logger.error(f"Failed to connect to SignalK WebSocket: {e}")
            logger.debug(f"WebSocket URL: {self.signalk_ws_url}")
            logger.debug(f"Token available: {token is not None}")
            self.ws_connected = False

    def _handle_hello_message(self):
        """Handle the initial hello message from SignalK server."""
        try:
            # Set a timeout for receiving the hello message
            self.ws.settimeout(5.0)
            message = self.ws.recv()
            hello_data = json.loads(message)

            if "self" in hello_data:
                self.vessel_self = hello_data["self"]
                logger.info(
                    f"Received hello from SignalK server: {hello_data.get('name', 'Unknown')} v{hello_data.get('version', 'Unknown')}"
                )
                logger.info(f"Vessel self ID: {self.vessel_self}")
            else:
                logger.warning("Hello message received but no 'self' field found")

        except Exception as e:
            logger.warning(f"Failed to receive hello message: {e}")
            # Continue anyway, we'll use fallback context

    def publish_to_signalk(self, data):
        """Publish data to SignalK server via TCP."""
        if not data:
            logger.warning("No data to publish")
            return

        try:
            # Create delta message
            delta = self.create_signalk_delta(data)

            # Debug: log the delta message
            logger.debug(f"Sending delta: {json.dumps(delta, indent=2)}")

            # Try UDP publishing first (most reliable for sensor data)
            logger.info("Publishing via UDP")
            if self._publish_via_udp(delta):
                logger.info(f"Successfully published {len(data)} data points via UDP")
            else:
                logger.warning("UDP publishing failed, trying WebSocket as fallback")
                self._publish_via_websocket_delta(delta)

        except Exception as e:
            logger.error(f"Error publishing to SignalK: {e}")
            logger.debug(
                f"TCP socket: {self.tcp_socket is not None}, WebSocket: {self.ws_connected}"
            )

    def _publish_via_http(self, delta):
        """Publish data to SignalK server via HTTP API."""
        try:
            token = self.get_auth_token()
            if not token:
                logger.error(
                    "Cannot publish via HTTP: no authentication token available"
                )
                return

            # Use HTTP API to publish delta
            url = f"http://{self.signalk_host}:{self.signalk_port}/signalk/v1/api/vessels/self"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Send each value individually via HTTP API
            for update in delta["updates"]:
                for value in update["values"]:
                    path = value["path"]
                    val = value["value"]

                    # Create HTTP API payload
                    payload = {"value": val}

                    # Send to HTTP API
                    response = requests.put(
                        f"{url}/{path.replace('.', '/')}/value",
                        json=payload,
                        headers=headers,
                        timeout=5,
                    )

                    if response.status_code in [200, 201]:
                        logger.debug(f"HTTP API: Published {path} = {val}")
                    else:
                        logger.warning(
                            f"HTTP API: Failed to publish {path}: {response.status_code} - {response.text}"
                        )

            logger.info(
                f"Published {len(delta['updates'][0]['values'])} data points to SignalK via HTTP API"
            )

        except Exception as e:
            logger.error(f"Error publishing via HTTP API: {e}")

    def _publish_via_websocket_delta(self, delta):
        """Publish data to SignalK server via WebSocket delta endpoint."""
        try:
            token = self.get_auth_token()
            if not token:
                logger.error(
                    "Cannot publish via WebSocket delta: no authentication token available"
                )
                return

            # Create a separate WebSocket connection for publishing deltas
            headers = {"Authorization": f"Bearer {token}"}
            logger.debug(
                f"Connecting to delta publishing endpoint: {self.signalk_ws_publish_url}"
            )

            publish_ws = websocket.WebSocket()
            publish_ws.connect(self.signalk_ws_publish_url, header=headers)

            # Send the delta
            message = json.dumps(delta)
            publish_ws.send(message)
            logger.info(
                f"Published delta via WebSocket to {self.signalk_ws_publish_url}"
            )
            logger.debug(f"Delta sent successfully, length: {len(message)} bytes")

            # Close the publishing connection
            publish_ws.close()

        except Exception as e:
            logger.error(f"Error publishing via WebSocket delta: {e}")
            logger.debug(f"Delta endpoint: {self.signalk_ws_publish_url}")

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
        # Close WebSocket connection
        if self.ws and self.ws_connected:
            try:
                self.ws.close()
                logger.info("WebSocket connection closed")
            except Exception:
                pass
        self.ws_connected = False

        # Close TCP connection
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
                logger.info("TCP connection closed")
            except Exception:
                pass
            self.tcp_socket = None

    def run(self, interval=1.0):
        """Main loop to read sensors and publish data."""
        logger.info("Starting sensor reading loop...")

        # Establish WebSocket connection first
        self.connect_websocket()

        try:
            while True:
                # Read all sensors
                data = self.read_all_sensors()

                if data:
                    # Publish to SignalK
                    self.publish_to_signalk(data)

                    # Log some key values
                    if "environment.outside.temperature" in data:
                        temp = data["environment.outside.temperature"]["value"]
                        logger.info(f"Temperature: {temp:.1f}K")

                else:
                    logger.warning("No sensor data available")

                # Wait before next reading
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Stopping sensor reader...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()


def test_signalk_connection(host=None, port=None, tcp_port=None):
    """Test SignalK connection without sensors."""
    logger.info("Testing SignalK connection...")

    reader = SensorReader(signalk_host=host, signalk_port=port, tcp_port=tcp_port)

    # Test connection
    reader.connect_websocket()
    if reader.ws_connected:
        logger.info("✓ SignalK connection successful")

        # Test publishing dummy data
        test_data = {
            "environment.outside.temperature": {
                "value": 293.15,  # 20°C in Kelvin
                "units": "K",
            }
        }

        reader.publish_to_signalk(test_data)
        logger.info("✓ Test data published successfully")

        reader.cleanup()
        return True
    else:
        logger.error("✗ SignalK connection failed")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="I2C Sensors to SignalK Publisher")
    parser.add_argument("--host", default="192.168.8.50", help="SignalK server host")
    parser.add_argument("--port", type=int, default=3000, help="SignalK server port")
    parser.add_argument(
        "--tcp-port", type=int, default=4123, help="SignalK TCP data port"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Reading interval in seconds"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test SignalK connection only"
    )

    args = parser.parse_args()

    if args.test:
        # Test mode - just test connection
        success = test_signalk_connection(args.host, args.port, args.tcp_port)
        exit(0 if success else 1)
    else:
        # Normal mode - run sensor reader
        reader = SensorReader(
            signalk_host=args.host, signalk_port=args.port, tcp_port=args.tcp_port
        )
        reader.run(args.interval)


if __name__ == "__main__":
    main()
