#!/usr/bin/env python3
"""SGP30 air quality sensor implementation."""

import logging
import time

import board
import busio
from adafruit_sgp30 import Adafruit_SGP30

from .base import BaseSensor

logger = logging.getLogger(__name__)


class SGP30Sensor(BaseSensor):
    """SGP30 air quality sensor for TVOC and eCO2."""

    def __init__(self, *args, **kwargs):
        """Initialize SGP30 sensor."""
        super().__init__("sgp30", *args, **kwargs)
        self.sgp30_sensor = None
        self._stabilized = False

    def initialize(self) -> bool:
        """Initialize SGP30 sensor hardware."""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sgp30_sensor = Adafruit_SGP30(i2c)
            logger.info("SGP30 sensor initialized")

            # Load calibration if available
            self._load_calibration()

            # Test read
            try:
                _ = self.sgp30_sensor.TVOC
                _ = self.sgp30_sensor.eCO2
                logger.info("SGP30 initial test successful")
            except Exception as test_e:
                logger.warning(f"SGP30 initial test failed: {test_e}")

            return True
        except Exception as e:
            logger.error(f"Failed to initialize SGP30: {e}")
            return False

    def _load_calibration(self):
        """Load calibration data from vessel info and apply to SGP30."""
        try:
            sensors_config = self.vessel_info.get("sensors", {})
            if "sgp30_calibration" not in sensors_config:
                logger.info("No saved SGP30 calibration data found")
                return False

            cal_data = sensors_config["sgp30_calibration"]

            # Set relative humidity for better accuracy
            if (
                "relative_humidity_percent" in cal_data
                and "temperature_celsius" in cal_data
            ):
                humidity = cal_data["relative_humidity_percent"]
                temperature = cal_data["temperature_celsius"]

                self.sgp30_sensor.set_iaq_relative_humidity(
                    celsius=temperature, relative_humidity=humidity
                )
                logger.info(
                    f"SGP30 relative humidity set to {humidity}% at {temperature}°C"
                )

            # Set baseline values if available
            if "tvoc_baseline_ppb" in cal_data and "eco2_baseline_ppm" in cal_data:
                tvoc_baseline = int(cal_data["tvoc_baseline_ppb"])
                eco2_baseline = int(cal_data["eco2_baseline_ppm"])

                logger.info(
                    f"SGP30 calibration loaded - TVOC baseline: {tvoc_baseline} ppb, "
                    f"eCO2 baseline: {eco2_baseline} ppm"
                )

            logger.info("SGP30 calibration data loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading SGP30 calibration data: {e}")
            return False

    def read(self) -> dict[str, dict[str, float | str]]:
        """
        Read data from SGP30 sensor.

        Returns:
            Dictionary with SignalK paths and values with units
        """
        if not self.sgp30_sensor:
            return {}

        try:
            # Wait for SGP30 to stabilize and provide real readings
            # Need TVOC > 0 AND eCO2 > 400 for a "good" reading
            if not self._stabilized:
                max_attempts = 60  # Maximum 60 attempts (60 seconds)
                attempt = 0
                consecutive_good_readings = 0
                required_good_readings = 20

                while attempt < max_attempts:
                    # Small delay to let sensor update
                    time.sleep(1)

                    # Read TVOC and eCO2 values
                    tvoc = self.sgp30_sensor.TVOC
                    eco2 = self.sgp30_sensor.eCO2

                    # Check if we have meaningful readings
                    is_good_reading = (
                        tvoc is not None
                        and eco2 is not None
                        and tvoc > 0
                        and eco2 > 400
                    )

                    if is_good_reading:
                        consecutive_good_readings += 1
                        logger.debug(
                            f"SGP30 good reading {consecutive_good_readings}/{required_good_readings} - "
                            f"TVOC: {tvoc}, eCO2: {eco2}"
                        )

                        # If we have enough consecutive good readings, mark as stabilized
                        if consecutive_good_readings >= required_good_readings:
                            logger.info(
                                f"SGP30 stabilized after {attempt + 1} seconds with "
                                f"{consecutive_good_readings} good readings"
                            )
                            self._stabilized = True
                            break
                    else:
                        # Reset counter if we get a bad reading
                        consecutive_good_readings = 0
                        logger.debug(
                            f"SGP30 stabilizing... attempt {attempt + 1}/{max_attempts} - "
                            f"TVOC: {tvoc}, eCO2: {eco2} (baseline)"
                        )

                    attempt += 1

                # If we've tried for 60 seconds and still getting baseline values, proceed anyway
                if not self._stabilized:
                    logger.warning(
                        f"SGP30 still returning baseline values after {max_attempts} seconds"
                    )
                    self._stabilized = True  # Proceed anyway

            # Read current values
            tvoc = self.sgp30_sensor.TVOC
            eco2 = self.sgp30_sensor.eCO2

            if tvoc is None or eco2 is None:
                return {}

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
