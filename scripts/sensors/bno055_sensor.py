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
from .swell_analyzer import SwellAnalyzer

logger = logging.getLogger(__name__)

EULER_AVERAGING_COUNT = 5
EULER_AVERAGING_DELAY = 0.05

def normalize_angle_180(angle_degrees):
    """
    Normalize an angle to the range [-180, 180] degrees.
    
    Args:
        angle_degrees: Angle in degrees (can be any value)
    
    Returns:
        Angle normalized to [-180, 180] degrees
    """
    # Normalize to [0, 360) range first
    angle = angle_degrees % 360
    
    # Convert to [-180, 180] range
    if angle > 180:
        angle -= 360
    
    return angle


MAX_COMFORT_ANGLE_DEG = 30.0  # Angle at which comfort bottoms out


class BNO055Sensor(BaseSensor):
    """BNO055 IMU sensor for attitude and rate of turn."""

    def __init__(self, *args, **kwargs):
        """Initialize BNO055 sensor."""
        super().__init__("bno055", *args, **kwargs)
        self.bno055_sensor = None
        self._calibration_warned = False
        # Initialize swell analyzer
        # Use update_interval as sample rate (inverse of interval)
        # Handle inf or very large intervals
        try:
            # Convert to float, handling string "inf"
            if isinstance(self.update_interval, str):
                if self.update_interval.lower() == "inf":
                    update_interval_float = float("inf")
                else:
                    update_interval_float = float(self.update_interval)
            else:
                update_interval_float = float(self.update_interval)

            if (
                update_interval_float == float("inf")
                or update_interval_float <= 0
                or update_interval_float > 60
            ):
                sample_rate = 1.0  # Default to 1 Hz
            else:
                sample_rate = 1.0 / update_interval_float
        except (ValueError, TypeError):
            # Fallback to default if conversion fails
            sample_rate = 1.0
        self.swell_analyzer = SwellAnalyzer(sample_rate=sample_rate)

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
        bno055_config = sensors_config.get("bno055", {})
        cal_data = bno055_config.get("calibration")
        
        if cal_data is None:
            logger.info("No saved BNO055 calibration data found")
            return False

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

            roll_raw_deg = normalize_angle_180(euler_avg[1])
            pitch_raw_deg = normalize_angle_180(euler_avg[2])
            yaw_raw_deg = normalize_angle_180(euler_avg[0])

            # Convert to radians
            roll_rad = roll_raw_deg * math.pi / 180
            pitch_rad = pitch_raw_deg * math.pi / 180
            yaw_rad = yaw_raw_deg * math.pi / 180

            # Apply zero state calibration for pitch and roll
            sensors_config = self.vessel_info.get("sensors", {})
            bno055_config = sensors_config.get("bno055", {})
            calibration = bno055_config.get("calibration", {})
            roll_calibrated_rad = roll_rad - calibration.get("roll", 0)
            pitch_calibrated_rad = pitch_rad - calibration.get("pitch", 0)
            yaw_calibrated_rad = yaw_rad - calibration.get("yaw", 0)

            # Create data dictionary
            data["navigation.attitude.roll"] = {
                "value": roll_calibrated_rad,
                "units": "rad",
            }
            data["navigation.attitude.pitch"] = {
                "value": pitch_calibrated_rad,
                "units": "rad",
            }
            data["navigation.attitude.yaw"] = {
                "value": yaw_calibrated_rad,
                "units": "rad",
            }

            # Derived comfort metrics
            heel_deg = abs(roll_calibrated_rad) * 180 / math.pi
            data["environment.motion.heel"] = {
                "value": heel_deg,
                "units": "deg",
            }

            # Add sample to swell analyzer
            self.swell_analyzer.add_sample(pitch_calibrated_rad, roll_calibrated_rad)

            # Calculate swell characteristics
            swell_data = self.swell_analyzer.analyze()

            def add_swell_value(path: str, value: float | None, units: str):
                """Attach a swell measurement (even if None) so SignalK can clear stale data."""
                data[path] = {"value": value, "units": units}

            swell_height = swell_data.get("height")
            if swell_data.get("period") is not None:
                add_swell_value(
                    "environment.waves.swell.period",
                    swell_data.get("period"),
                    "s",
                )
            if swell_data.get("direction") is not None:
                add_swell_value(
                    "environment.waves.swell.direction",
                    swell_data.get("direction"),
                    "rad",
                )
            if swell_height is not None:
                add_swell_value(
                    "environment.waves.swell.height",
                    swell_height,
                    "m",
                )

            logger.info("BNO055 Data Readout:")
            for key, value in data.items():
                if "swell" in key:
                    logger.info(f"   {key}: {value['value']}")
                else:
                    logger.info(f"   {key}: {value['value'] * 180 / math.pi}deg")

        return data

    def _calculate_comfort_index(self, roll_rad: float, pitch_rad: float) -> float:
        """
        Compute a simple 1-10 comfort score based on instantaneous roll/pitch magnitude.

        10 = perfectly level, 1 = severe motion (>= MAX_COMFORT_ANGLE_DEG RMS).
        """
        combined_angle_rad = math.sqrt(roll_rad**2 + pitch_rad**2)
        combined_angle_deg = combined_angle_rad * 180 / math.pi
        severity_ratio = min(combined_angle_deg / MAX_COMFORT_ANGLE_DEG, 1.0)
        score = 10.0 - severity_ratio * 9.0
        return round(max(1.0, min(score, 10.0)), 1)
