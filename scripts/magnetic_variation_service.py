#!/usr/bin/env python3
"""
Magnetic Variation Service

This service calculates and publishes magnetic variation (declination) data
to SignalK server based on the current vessel position.
"""

import json
import logging
import os
import socket
import time
from datetime import UTC, datetime

import requests

# Import magnetic calculation functions
from magnetic_calculation import get_magnetic_declination_with_cache

# Constants
DEFAULT_UDP_PORT = 4123
MAGNETIC_SERVICE_LABEL = "Magnetic Variation Service"
MAGNETIC_SERVICE_SOURCE = "magnetic-variation"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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


class MagneticVariationService:
    def __init__(
        self,
        signalk_host=None,
        signalk_port=None,
        udp_port=None,
        info_path="data/vessel/info.json",
    ):
        """Initialize magnetic variation service and SignalK connection."""
        # Load vessel info from JSON file
        self.vessel_info = load_vessel_info(info_path)
        if not self.vessel_info:
            raise ValueError("Could not load vessel info")

        # SignalK connection settings
        self.signalk_host = signalk_host or self.vessel_info.get("signalk", {}).get("host")
        self.signalk_port = signalk_port or int(self.vessel_info.get("signalk", {}).get("port", 3000))
        self.udp_port = udp_port or DEFAULT_UDP_PORT

        if not self.signalk_host:
            raise ValueError("SignalK host not specified")

        # UDP socket for publishing
        self.udp_socket = None

        logger.info(f"Initialized {MAGNETIC_SERVICE_LABEL}")
        logger.info(f"SignalK server: {self.signalk_host}:{self.signalk_port}")
        logger.info(f"UDP port: {self.udp_port}")

    def create_signalk_delta(self, magnetic_variation):
        """Create SignalK delta message for magnetic variation."""
        delta = {
            "context": "vessels.self",
            "updates": [
                {
                    "source": {
                        "label": MAGNETIC_SERVICE_LABEL,
                        "type": "Magnetic Variation",
                        "src": "magnetic-variation",
                        "$source": MAGNETIC_SERVICE_SOURCE,
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                    "values": [
                        {
                            "path": "navigation.magneticVariation",
                            "value": magnetic_variation,
                            "$source": MAGNETIC_SERVICE_SOURCE,
                        }
                    ],
                }
            ],
        }

        return delta

    def publish_to_signalk(self, magnetic_variation):
        """Publish magnetic variation to SignalK server via UDP."""
        try:
            # Create delta message
            delta = self.create_signalk_delta(magnetic_variation)

            # Debug: log the delta message
            logger.debug(f"Sending delta: {json.dumps(delta, indent=2)}")

            # Publish via UDP
            logger.info("Publishing magnetic variation via UDP")
            if self._publish_via_udp(delta):
                logger.info("Successfully published magnetic variation via UDP")
            else:
                logger.error("UDP publishing failed")

        except Exception as e:
            logger.error(f"Error publishing to SignalK: {e}")

    def _publish_via_udp(self, delta):
        """Publish data to SignalK server via UDP."""
        try:
            # Ensure UDP socket is created
            if not self.udp_socket:
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                logger.info(f"UDP socket created for SignalK server at {self.signalk_host}:{self.udp_port}")

            # Convert delta to JSON
            message = json.dumps(delta)
            message_bytes = message.encode('utf-8')

            # Send via UDP
            self.udp_socket.sendto(message_bytes, (self.signalk_host, self.udp_port))
            logger.debug(f"UDP send successful: {len(message_bytes)}/{len(message_bytes)} bytes sent to {self.signalk_host}:{self.udp_port}")

            return True

        except Exception as e:
            logger.error(f"UDP send failed: {e}")
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
        """Calculate and publish magnetic variation once."""
        logger.info("Calculating and publishing magnetic variation...")

        try:

            # Calculate magnetic variation
            magnetic_variation = get_magnetic_declination_with_cache(
                self.signalk_host,
                self.signalk_port,
                force_refresh=False
            )

            if magnetic_variation is not None:
                logger.info(f"Magnetic variation calculated: {magnetic_variation:.4f} rad ({magnetic_variation * 180 / 3.14159:.2f}°)")
                
                # Publish to SignalK
                self.publish_to_signalk(magnetic_variation)
                
                logger.info("Successfully published magnetic variation")
            else:
                logger.warning("Could not calculate magnetic variation")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Magnetic Variation Service")
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

    args = parser.parse_args()

    try:
        # Create and run service
        service = MagneticVariationService(
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
        )
        service.run()

    except Exception as e:
        logger.error(f"Service failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
