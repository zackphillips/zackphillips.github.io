#!/usr/bin/env python3
"""BME280 temperature, humidity, and pressure sensor implementation."""

import logging

import board
import busio
import smbus2
import bme280

from .base import BaseSensor

logger = logging.getLogger(__name__)


class BME280Sensor(BaseSensor):
    """BME280 sensor for temperature, humidity, and pressure."""

    def __init__(self, *args, **kwargs):
        """Initialize BME280 sensor."""
        super().__init__("bme280", *args, **kwargs)
        self.bme280_sensor = None

    def initialize(self) -> bool:
        """Initialize BME280 sensor hardware."""
        try:
            # Try using smbus2 first (more reliable on Raspberry Pi)
            try:
                bus = smbus2.SMBus(1)
                self.bme280_sensor = bme280.BME280(i2c_dev=bus)
                logger.info("BME280 initialized using smbus2")
            except Exception as e:
                logger.warning(f"Failed to initialize BME280 with smbus2: {e}, trying busio")
                # Fallback to busio
                i2c = busio.I2C(board.SCL, board.SDA)
                self.bme280_sensor = bme280.BME280(i2c_device=i2c)
                logger.info("BME280 initialized using busio")

            # Test read
            _ = self.bme280_sensor.read_all()
            logger.info("BME280 sensor initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize BME280: {e}")
            return False

    def read(self) -> dict[str, dict[str, float | str]]:
        """
        Read data from BME280 sensor.

        Returns:
            Dictionary with SignalK paths and values with units
        """
        if not self.bme280_sensor:
            return {}

        try:
            # Read sensor data
            data = self.bme280_sensor.read_all()

            # Validate readings
            if (
                data.temperature < -40
                or data.temperature > 85
                or data.humidity < 0
                or data.humidity > 100
                or data.pressure < 300
                or data.pressure > 1200
            ):
                logger.debug(
                    f"BME280 reading invalid: temp={data.temperature}°C, "
                    f"humidity={data.humidity}%, pressure={data.pressure}hPa"
                )
                return {}

            # Return valid readings with units
            return {
                "environment.inside.temperature": {
                    "value": data.temperature + 273.15,  # Convert C to K
                    "units": "K",
                },
                "environment.inside.humidity": {
                    "value": data.humidity / 100.0,  # Convert % to ratio
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
