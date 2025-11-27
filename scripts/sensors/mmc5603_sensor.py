#!/usr/bin/env python3
"""MMC5603 magnetometer sensor implementation."""

import logging
import math

import board
import busio
from adafruit_mmc56x3 import MMC5603

from .base import BaseSensor

logger = logging.getLogger(__name__)


class MMC5603Sensor(BaseSensor):
    """MMC5603 magnetometer sensor for magnetic heading."""

    def __init__(self, *args, **kwargs):
        """Initialize MMC5603 sensor."""
        super().__init__("mmc5603", *args, **kwargs)
        self.mmc5603_sensor = None
        self.heading_correction_offset = 0.0

    def initialize(self) -> bool:
        """Initialize MMC5603 sensor hardware."""
        i2c = busio.I2C(board.SCL, board.SDA)
        self.mmc5603_sensor = MMC5603(i2c)
        logger.info("MMC5603 sensor initialized")

        # Load heading correction offset
        sensors_config = self.vessel_info.get("sensors", {})
        mmc5603_config = sensors_config.get("mmc5603", {})
        calibration = mmc5603_config.get("calibration", {})
        self.heading_correction_offset = calibration.get(
            "heading_correction_offset_rad", 0.0
        )
        logger.info(
            f"MMC5603 heading correction offset: {self.heading_correction_offset} rad"
        )

        return True

    def read(self) -> dict[str, dict[str, float | str]]:
        """
        Read data from MMC5603 sensor.

        Returns:
            Dictionary with SignalK paths and values with units
        """
        if not self.mmc5603_sensor:
            return {}

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
            "navigation.headingMagnetic": {
                "value": heading,
                "units": "rad",
            },
        }
