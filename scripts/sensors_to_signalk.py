#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher
Reads data from BME280, BNO055, SGP30, and MMC5603 sensors via I2C
and publishes to SignalK server.
"""

import json
import logging
import math
import time
from datetime import UTC, datetime

import adafruit_mmc56x3
import board
import busio
import jwt
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


class SensorReader:
    def __init__(self, signalk_host="192.168.8.50", signalk_port=3000):
        """Initialize sensor reader and SignalK connection."""
        self.signalk_host = signalk_host
        self.signalk_port = signalk_port
        self.signalk_ws_url = (
            f"ws://{signalk_host}:{signalk_port}/signalk/v1/stream?subscribe=self"
        )

        # SignalK authentication
        self.device_id = "I2C-SENSORS-156E6713"
        self.secret_key = "384be8119536488e85baa23a64c3560e33095656907349c4b856fd33651835ebdf19b5ce155d45d2a1011de6c7e1ec9f8b84d59ec5084ac4841b83436e03b599c5ac6f92ff7a48a9bebf1a4ed62e4fb23637d3662f7f423ab995f8a20c255adbc6a74d96924048e9899701a047b9e4c89083b80c0a294bd3aab151ec4900c89882d676101d634152af71054e8da58a4cd2956b540fc9484c988c09306762ff07ed7ce318b9d448ae9e1a55b32ea7e115370a0e6f09024010a8fbca0167d1806e0e2c27fa494e4268885f9b216172538afee5d1b7d9794730b947bc166d7742f3d396c09e0eab4239aace5c61c46719bcd8d2eadcf11646cc82e766c2c54e3843"

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

    def generate_jwt_token(self):
        """Generate JWT token for SignalK authentication."""
        payload = {
            "exp": int(time.time()) + 3600,  # Expires in 1 hour
            "iat": int(time.time()),
            "sub": self.device_id,
            "permissions": "readwrite",
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def get_auth_token(self):
        """Get authentication token using SignalK device authentication."""
        if not hasattr(self, "_auth_token") or not self._auth_token:
            try:
                # Try device authentication first - use the existing device
                device_url = f"http://{self.signalk_host}:{self.signalk_port}/signalk/v1/access/request"
                device_payload = {
                    "clientId": "sensor-client",
                    "description": "I2C Sensor Data Publisher",
                }

                response = requests.post(device_url, json=device_payload, timeout=5)
                if response.status_code == 200:
                    device_data = response.json()
                    token = device_data.get("token")
                    if token:
                        logger.info("Successfully obtained device token")
                        self._auth_token = token
                        return token

                # If device auth fails, try user auth with the existing user
                login_url = f"http://{self.signalk_host}:{self.signalk_port}/signalk/v1/auth/login"
                login_payload = {
                    "username": "mermug",
                    "password": "mermug",  # Correct password
                }

                response = requests.post(login_url, json=login_payload, timeout=5)
                if response.status_code == 200:
                    login_data = response.json()
                    token = login_data.get("token")
                    if token:
                        logger.info("Successfully obtained user token")
                        self._auth_token = token
                        return token

                logger.error("Failed to get authentication token")
                return None

            except Exception as e:
                logger.error(f"Error getting access token: {e}")
                return None
        return self._auth_token

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

        # Try a simpler delta format
        delta = {
            "context": context,
            "updates": [
                {
                    "source": {"label": "I2C Sensors", "type": "I2C", "src": "inside"},
                    "timestamp": timestamp,
                    "values": [],
                }
            ],
        }

        # Add each data point to the delta
        for path, value in data.items():
            delta["updates"][0]["values"].append(
                {"path": path, "value": value["value"]}
            )

        return delta

    def connect_websocket(self):
        """Connect to SignalK WebSocket."""
        try:
            # First try without authentication (if security allows it)
            try:
                self.ws = websocket.WebSocket()
                self.ws.connect(self.signalk_ws_url)
                self.ws_connected = True
                logger.info("Connected to SignalK WebSocket without authentication")

                # Wait for and handle hello message
                self._handle_hello_message()
                return

            except Exception as auth_error:
                logger.warning(f"Connection without auth failed: {auth_error}")

            # If that fails, try with JWT authentication
            token = self.generate_jwt_token()
            headers = {"Authorization": f"JWT {token}"}

            self.ws = websocket.WebSocket()
            self.ws.connect(self.signalk_ws_url, header=headers)
            self.ws_connected = True
            logger.info("Connected to SignalK WebSocket with JWT authentication")

            # Wait for and handle hello message
            self._handle_hello_message()

        except Exception as e:
            logger.error(f"Failed to connect to SignalK WebSocket: {e}")
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
        """Publish data to SignalK server via WebSocket with authentication."""
        if not data:
            logger.warning("No data to publish")
            return

        try:
            # Create delta message
            delta = self.create_signalk_delta(data)

            # Debug: log the delta message
            logger.debug(f"Sending delta: {json.dumps(delta, indent=2)}")

            # Send delta via WebSocket
            if self.ws and self.ws_connected:
                # Send delta directly
                self.ws.send(json.dumps(delta))
                logger.info(
                    f"Published {len(data)} data points to SignalK via WebSocket"
                )
            else:
                logger.warning("WebSocket not connected, cannot publish data")

        except Exception as e:
            logger.error(f"Error publishing to SignalK: {e}")

    def cleanup(self):
        """Clean up resources."""
        if self.ws and self.ws_connected:
            try:
                self.ws.close()
                logger.info("WebSocket connection closed")
            except Exception:
                pass
        self.ws_connected = False

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


def test_signalk_connection(host="192.168.8.50", port=3000):
    """Test SignalK connection without sensors."""
    logger.info("Testing SignalK connection...")

    reader = SensorReader(host, port)

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
        "--interval", type=float, default=1.0, help="Reading interval in seconds"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test SignalK connection only"
    )

    args = parser.parse_args()

    if args.test:
        # Test mode - just test connection
        success = test_signalk_connection(args.host, args.port)
        exit(0 if success else 1)
    else:
        # Normal mode - run sensor reader
        reader = SensorReader(args.host, args.port)
        reader.run(args.interval)


if __name__ == "__main__":
    main()
