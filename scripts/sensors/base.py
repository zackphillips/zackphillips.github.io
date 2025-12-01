#!/usr/bin/env python3
"""
Base sensor class for all sensor implementations.
Handles common SignalK publishing logic, configuration, and main loop.
"""

import json
import logging
import socket
import sys
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..utils import load_vessel_info, send_delta_over_udp

logger = logging.getLogger(__name__)

DEFAULT_UDP_PORT = 4123


class BaseSensor(ABC):
    """Base class for all sensors with common SignalK publishing logic."""

    def __init__(
        self,
        sensor_name: str,
        signalk_host: str = None,
        signalk_port: int = None,
        udp_port: int = None,
        info_path: str = "data/vessel/info.yaml",
        update_interval: float = 1.0,
    ):
        """
        Initialize base sensor.

        Args:
            sensor_name: Name of the sensor (e.g., 'bme280', 'bno055')
            signalk_host: SignalK server host (overrides config)
            signalk_port: SignalK server port (overrides config)
            udp_port: UDP port for publishing (default: 4123)
            info_path: Path to vessel config file
            update_interval: Update interval in seconds (overrides config)
        """
        self.sensor_name = sensor_name
        self.info_path = info_path
        self.vessel_info = load_vessel_info(info_path)

        # Load SignalK config
        signalk_config = self.vessel_info.get("signalk", {})
        self.signalk_host = signalk_host or signalk_config.get("host")
        self.signalk_port = signalk_port or int(signalk_config.get("port", 3000))
        self.udp_port = udp_port or DEFAULT_UDP_PORT

        if not self.signalk_host:
            raise ValueError("SignalK host must be specified")

        # Load sensor-specific config
        sensor_config = self.vessel_info.get("sensors", {}).get(sensor_name, {})
        self.update_interval = update_interval or sensor_config.get("update_interval", 1.0)

        # Sensor source identifiers
        self.source_label = f"{sensor_name.upper()} Sensor"
        self.source_type = "I2C"
        self.source_src = f"sensor-{sensor_name}"

        # UDP socket (created on first use)
        self.udp_socket = None

        logger.info(f"Initialized {self.source_label}")
        logger.info(f"SignalK server: {self.signalk_host}:{self.signalk_port}")
        logger.info(f"Update interval: {self.update_interval}s")

    def connect_udp(self):
        """Create UDP socket for SignalK publishing."""
        if not self.udp_socket:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"UDP socket created for {self.source_label}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the sensor hardware.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def read(self) -> dict[str, dict[str, Any]]:
        """
        Read data from the sensor.

        Returns:
            Dictionary mapping SignalK paths to value dictionaries.
            Each value dict should have 'value' and optionally 'units' keys.
            Example: {
                "environment.inside.temperature": {
                    "value": 293.15,
                    "units": "K"
                }
            }
        """
        pass

    def create_signalk_delta(self, data: dict[str, dict[str, Any]]) -> dict:
        """
        Create SignalK delta message from sensor data.

        Args:
            data: Dictionary mapping paths to value dicts with 'value' and optionally 'units'

        Returns:
            SignalK delta message dictionary
        """
        timestamp = datetime.now(UTC).isoformat()

        delta = {
            "context": "vessels.self",
            "updates": [
                {
                    "source": {
                        "label": self.source_label,
                        "type": self.source_type,
                        "src": self.source_src,
                        "$source": self.source_src,
                    },
                    "timestamp": timestamp,
                    "values": [],
                    "meta": [],
                }
            ],
        }

        # Add each data point to the delta
        for path, value_dict in data.items():
            value_entry = {
                "path": path,
                "value": value_dict["value"],
                "$source": self.source_src,
            }
            # Include units if available (some SignalK servers support this)
            if "units" in value_dict:
                value_entry["units"] = value_dict["units"]
            delta["updates"][0]["values"].append(value_entry)

            # Also add metadata for units (SignalK standard way)
            if "units" in value_dict:
                meta_entry = {
                    "path": path,
                    "value": {
                        "units": value_dict["units"],
                    },
                }
                delta["updates"][0]["meta"].append(meta_entry)

        return delta

    def publish_to_signalk(self, data: dict[str, dict[str, Any]]) -> bool:
        """
        Publish sensor data to SignalK server.

        Args:
            data: Dictionary mapping paths to value dicts

        Returns:
            True if successful, False otherwise
        """
        if not data:
            logger.warning(f"{self.source_label}: No data to publish")
            return False

        try:
            # Create delta message
            delta = self.create_signalk_delta(data)

            # Debug: log the delta message
            logger.debug(f"{self.source_label} sending delta: {json.dumps(delta, indent=2)}")

            # Publish via UDP
            if self._publish_via_udp(delta):
                logger.debug(f"{self.source_label} successfully published {len(data)} data points")
                return True
            else:
                logger.error(f"{self.source_label} UDP publishing failed")
                return False

        except Exception as e:
            logger.error(f"{self.source_label} error publishing to SignalK: {e}")
            return False

    def _publish_via_udp(self, delta: dict) -> bool:
        """Publish data to SignalK server via UDP."""
        try:
            # Ensure UDP socket is created
            if not self.udp_socket:
                self.connect_udp()

            # Send via UDP
            bytes_sent = send_delta_over_udp(
                self.udp_socket, self.signalk_host, self.udp_port, delta
            )
            logger.debug(
                f"{self.source_label} UDP send: {bytes_sent} bytes to {self.signalk_host}:{self.udp_port}"
            )
            return True

        except Exception as e:
            logger.error(f"{self.source_label} UDP send failed: {e}")
            return False

    def run(self) -> bool:
        """
        Read sensor once and publish to SignalK.

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self.read()
            if data:
                return self.publish_to_signalk(data)
            return False
        except Exception as e:
            logger.error(f"{self.source_label} error in run: {e}")
            return False
            
    def cleanup(self):
        """Clean up resources."""
        if self.udp_socket:
            try:
                self.udp_socket.close()
                logger.info(f"{self.source_label} UDP socket closed")
            except Exception:
                pass
            self.udp_socket = None
