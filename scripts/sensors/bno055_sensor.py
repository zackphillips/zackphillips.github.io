#!/usr/bin/env python3
"""BNO055 IMU sensor implementation."""

import logging
import math
import sys
import time
from pathlib import Path

import board
import busio
from adafruit_bno055 import BNO055_I2C

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bno055_register_io import validate_calibration_data, write_calibration

from .base import BaseSensor

logger = logging.getLogger(__name__)

EULER_AVERAGING_COUNT = 10
EULER_AVERAGING_DELAY = 0.05


class BNO055Sensor(BaseSensor):
    """BNO055 IMU sensor for attitude and rate of turn."""

    def __init__(self, *args, **kwargs):
        """Initialize BNO055 sensor."""
        super().__init__("bno055", *args, **kwargs)
        self.bno055_sensor = None
        self._calibration_warned = False

    def initialize(self) -> bool:
        """Initialize BNO055 sensor hardware."""
        i2c = busio.I2C(board.SCL, board.SDA)
        self.bno055_sensor = BNO055_I2C(i2c)
        logger.info("BNO055 sensor initialized")

        # Load calibration if available
        self._load_calibration()

        return True

    def _load_calibration(self):
        """Load calibration data from vessel info and apply to BNO055."""
        sensors_config = self.vessel_info.get("sensors", {})
        if "bno055_calibration" not in sensors_config:
            logger.info("No saved BNO055 calibration data found")
            return False

        cal_data = sensors_config["bno055_calibration"]

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

    def read(self) -> dict[str, dict[str, float | str]]:
        """
        Read data from BNO055 sensor.

        Returns:
            Dictionary with SignalK paths and values with units
        """
        if not self.bno055_sensor:
            return {}

        # Check if sensor is calibrated
        if not self.bno055_sensor.calibrated and not self._calibration_warned:
            logger.warning(
                "BNO055 not calibrated - move sensor in figure-8 pattern to calibrate"
            )
            self._calibration_warned = True

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
            # Wait for non-zero euler angles
            t0 = time.time()
            while 0 in euler:
                time.sleep(0.1)
                euler = self.bno055_sensor.euler
                if time.time() - t0 > 10:
                    logger.error("BNO055 Euler angles still 0 after 10 seconds")
                    raise TimeoutError("BNO055 Euler angles still 0 after 10 seconds")

            # Perform averaging of euler angles
            euler_avg = [0, 0, 0]
            for _ in range(EULER_AVERAGING_COUNT):
                euler_avg = [euler_avg[i] + euler[i] for i in range(3)]
                time.sleep(EULER_AVERAGING_DELAY)
                euler = self.bno055_sensor.euler
            euler_avg = [e / EULER_AVERAGING_COUNT for e in euler_avg]

            # Load sensor-specific config to check for horizontal mounting
            sensor_config = self.vessel_info.get("sensors", {}).get("bno055", {})
            is_mounted_horizontally = sensor_config.get("mounted_horizontally", False)

            # Flip roll and pitch if sensor is mounted horizontally in the vessel
            if is_mounted_horizontally:
                euler_avg = [euler_avg[1], euler_avg[0], euler_avg[2]]

            # Convert Euler angles from degrees to radians
            roll_raw = euler_avg[0] * math.pi / 180
            pitch_raw = euler_avg[1] * math.pi / 180
            yaw_raw = euler_avg[2] * math.pi / 180

            # Apply zero state calibration for pitch and roll
            sensors_config = self.vessel_info.get("sensors", {})
            roll_calibrated = roll_raw
            pitch_calibrated = pitch_raw

            if "bno055_zero_state" in sensors_config:
                zero_state = sensors_config["bno055_zero_state"]
                roll_calibrated = roll_raw - zero_state.get("roll", 0)
                pitch_calibrated = pitch_raw - zero_state.get("pitch", 0)

            # Apply yaw offset calibration
            yaw_calibrated = yaw_raw
            if "bno055_yaw_offset" in sensors_config:
                yaw_offset = sensors_config["bno055_yaw_offset"]
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
