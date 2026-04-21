#!/usr/bin/env python3
"""SGP30 air quality sensor implementation."""

import logging
import time

import board
import busio
from adafruit_sgp30 import Adafruit_SGP30

from .base import BaseSensor

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 240
REQUIRED_GOOD_READINGS = 20


class SGP30Sensor(BaseSensor):
    """SGP30 air quality sensor for TVOC and eCO2."""

    def __init__(self, *args, **kwargs):
        """Initialize SGP30 sensor."""
        super().__init__("sgp30", *args, **kwargs)
        self.sgp30_sensor = None
        self._stabilized = False

    def initialize(self) -> bool:
        """Initialize SGP30 sensor hardware."""
        logger.info("SGP30: Starting initialization...")
        logger.info("SGP30: Creating I2C bus connection...")
        i2c = busio.I2C(board.SCL, board.SDA)
        logger.info("SGP30: Creating Adafruit_SGP30 sensor instance...")
        self.sgp30_sensor = Adafruit_SGP30(i2c)
        logger.info("SGP30: Sensor hardware initialized successfully")

        # Load calibration if available
        logger.info("SGP30: Loading calibration data...")
        calibration_loaded = self._load_calibration()
        if not calibration_loaded:
            logger.info("SGP30: No calibration data found, using default settings")

        # Test read
        logger.info("SGP30: Performing initial sensor test read...")
        tvoc = self.sgp30_sensor.TVOC
        eco2 = self.sgp30_sensor.eCO2
        logger.info(
            f"SGP30: Initial test successful - TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
        )
        logger.info(
            "SGP30: Note - Initial readings may be baseline values. "
            "Sensor needs time to stabilize for accurate readings."
        )

        logger.info("SGP30: Initialization complete")
        return True

    def _load_calibration(self):
        """Load calibration data from vessel info and apply to SGP30."""
        logger.debug("SGP30: Checking for calibration data in vessel config...")
        sensors_config = self.vessel_info.get("sensors", {})
        sgp30_config = sensors_config.get("sgp30", {})
        cal_data = sgp30_config.get("calibration")
        
        if cal_data is None:
            logger.info("SGP30: No saved calibration data found in vessel config")
            return False

        logger.info("SGP30: Calibration data found, loading...")

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

    def read(self) -> dict[str, dict[str, float | str]]:
        """
        Read data from SGP30 sensor.

        Returns:
            Dictionary with SignalK paths and values with units
        """
        if not self.sgp30_sensor:
            return {}

        # Wait for SGP30 to stabilize and provide real readings
        # Need TVOC > 0 AND eCO2 > 400 for a "good" reading
        if not self._stabilized:
            logger.info("SGP30: Starting stabilization process...")
            logger.info(
                "SGP30: Waiting for sensor to stabilize (requires TVOC > 0 and eCO2 > 400)"
            )
            max_attempts = MAX_ATTEMPTS
            attempt = 0
            consecutive_good_readings = 0
            required_good_readings = REQUIRED_GOOD_READINGS

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

                # Check if we have meaningful readings
                is_good_reading = (
                    tvoc is not None
                    and eco2 is not None
                    and tvoc > 0
                    and eco2 > 400
                )

                if is_good_reading:
                    consecutive_good_readings += 1
                    logger.info(
                        f"SGP30: Good reading detected ({consecutive_good_readings}/{required_good_readings}) - "
                        f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                    )

                    # If we have enough consecutive good readings, mark as stabilized
                    if consecutive_good_readings >= required_good_readings:
                        logger.info(
                            f"SGP30: Sensor stabilized after {attempt + 1} seconds "
                            f"with {consecutive_good_readings} consecutive good readings"
                        )
                        logger.info(
                            f"SGP30: Final stabilization values - "
                            f"TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                        )
                        self._stabilized = True
                        break
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

            # If we've tried for 60 seconds and still getting baseline values, proceed anyway
            if not self._stabilized:
                logger.warning(
                    f"SGP30: Still returning baseline values after {max_attempts} seconds"
                )
                logger.warning(
                    f"SGP30: Final attempt values - TVOC: {tvoc} ppb, eCO2: {eco2} ppm"
                )
                logger.warning(
                    "SGP30: Proceeding with readings anyway. "
                    "Sensor may need more time or environmental conditions may be very stable."
                )
                self._stabilized = True  # Proceed anyway

        # Read current values
        logger.debug("SGP30: Reading current sensor values...")
        tvoc = self.sgp30_sensor.TVOC
        eco2 = self.sgp30_sensor.eCO2

        if tvoc is None or eco2 is None:
            logger.warning(
                f"SGP30: Received None values - TVOC: {tvoc}, eCO2: {eco2}"
            )
            return {}

        logger.debug(f"SGP30: Current readings - TVOC: {tvoc} ppb, eCO2: {eco2} ppm")

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
