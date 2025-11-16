#!/usr/bin/env python3
"""
Magnetic Variation Service

This service calculates and publishes magnetic variation (declination) data
to SignalK server based on the current vessel position.
"""

import json
import logging
import math
import socket
import time
from datetime import UTC, datetime

import requests

# Import utilities
from utils import (
    create_signalk_delta,
    load_vessel_info,
    send_delta_over_udp,
    setup_logging,
)

# Constants
DEFAULT_UDP_PORT = 4123
MAGNETIC_SERVICE_LABEL = "Magnetic Variation Service"
MAGNETIC_SERVICE_SOURCE = "magnetic-variation"

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)


def calculate_magnetic_declination(
    latitude: float,
    longitude: float,
    date: datetime | None = None,
    elevation: float = 0.0,
) -> float | None:
    """Calculate magnetic declination (variation) in radians using geomag, fallback NOAA."""
    if date is None:
        date = datetime.now(UTC)

    try:
        import geomag  # local import to avoid hard dependency at import time

        elevation_km = elevation / 1000.0
        date_for_geomag = date.date()
        declination_deg = geomag.declination(latitude, longitude, h=elevation_km, time=date_for_geomag)
        return math.radians(declination_deg)
    except Exception:
        pass

    try:
        NOAA_MAGNETIC_API_URL = "https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
        params = {
            'lat1': latitude,
            'lon1': longitude,
            'model': 'WMM',
            'startYear': date.year,
            'startMonth': date.month,
            'startDay': date.day,
            'endYear': date.year,
            'endMonth': date.month,
            'endDay': date.day,
            'resultFormat': 'json'
        }
        if elevation > 0:
            params['height'] = elevation

        response = requests.get(NOAA_MAGNETIC_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'result' in data and len(data['result']) > 0:
            declination_deg = data['result'][0].get('declination', 0.0)
            return math.radians(declination_deg)
    except Exception:
        return None


def get_position_from_signalk(signalk_host: str, signalk_port: int, protocol: str | None = None) -> tuple[float, float] | None:
    """Get current vessel position from SignalK server."""
    if not protocol:
        protocol = "http"
    api_url = f"{protocol}://{signalk_host}:{signalk_port}/signalk/v1/api/vessels/self/navigation/position"
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if 'value' in data:
            position = data['value']
            latitude = position.get('latitude')
            longitude = position.get('longitude')
            if latitude is not None and longitude is not None:
                return (latitude, longitude)
    except requests.exceptions.RequestException:
        return None
    return None


def calculate_magnetic_declination_from_signalk(
    signalk_host: str,
    signalk_port: int,
    date: datetime | None = None,
    elevation: float = 0.0,
    protocol: str | None = None,
) -> float | None:
    """Calculate magnetic declination using current vessel position from SignalK."""
    position = get_position_from_signalk(signalk_host, signalk_port, protocol)
    if position is None:
        return None
    latitude, longitude = position
    return calculate_magnetic_declination(latitude, longitude, date, elevation)


class MagneticVariationService:
    def __init__(
        self,
        signalk_host=None,
        signalk_port=None,
        udp_port=None,
        info_path="data/vessel/info.yaml",
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

        # Protocol from vessel info (default http)
        self.signalk_protocol = self.vessel_info.get("signalk", {}).get("protocol", "http")

        logger.info(f"Initialized {MAGNETIC_SERVICE_LABEL}")
        logger.info(f"SignalK server: {self.signalk_host}:{self.signalk_port}")
        logger.info(f"UDP port: {self.udp_port}")

        # Default publish interval (seconds)
        self.interval_seconds = 600

    def create_signalk_delta(self, magnetic_variation):
        """Create SignalK delta message for magnetic variation."""
        from datetime import UTC, datetime
        
        values = [
            {
                "path": "navigation.magneticVariation",
                "value": magnetic_variation,
                "units": "rad",  # Include in value entry
                "$source": MAGNETIC_SERVICE_SOURCE,
            }
        ]
        
        # Also include metadata for units (SignalK standard way)
        meta = [
            {
                "path": "navigation.magneticVariation",
                "value": {
                    "units": "rad",
                    "description": "Magnetic variation (declination) in radians",
                },
            }
        ]

        return {
            "context": "vessels.self",
            "updates": [
                {
                    "source": {
                        "label": MAGNETIC_SERVICE_LABEL,
                        "type": "Magnetic Variation",
                        "src": MAGNETIC_SERVICE_SOURCE,
                        "$source": MAGNETIC_SERVICE_SOURCE,
                    },
                    "timestamp": datetime.now(UTC).isoformat(),
                    "values": values,
                    "meta": meta,
                }
            ],
        }

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

            # Send via UDP using shared helper
            bytes_sent = send_delta_over_udp(self.udp_socket, self.signalk_host, self.udp_port, delta)
            logger.debug(f"UDP send successful: {bytes_sent} bytes sent to {self.signalk_host}:{self.udp_port}")

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
        """Calculate and publish magnetic variation at a fixed interval."""
        logger.info(f"Starting magnetic variation publishing every {self.interval_seconds} seconds...")

        try:
            while True:
                try:
                    # Calculate magnetic variation using live SignalK API (no cache)
                    magnetic_variation = calculate_magnetic_declination_from_signalk(
                        self.signalk_host,
                        self.signalk_port,
                        protocol=self.signalk_protocol,
                    )

                    if magnetic_variation is not None:
                        # Retrieve current position for logging context
                        pos = get_position_from_signalk(self.signalk_host, self.signalk_port, protocol=self.signalk_protocol)

                        deg = magnetic_variation * 180 / 3.14159
                        if pos and isinstance(pos, tuple):
                            lat, lon = pos
                            logger.info(f"Magnetic variation: {deg:.2f}deg at lat={lat:.6f}, lon={lon:.6f}")
                        else:
                            logger.info(f"Magnetic variation: {deg:.2f}deg (position unavailable)")

                        # Publish to SignalK
                        self.publish_to_signalk(magnetic_variation)

                        logger.info("Successfully published magnetic variation")
                    else:
                        logger.warning("Could not calculate magnetic variation")
                except Exception as loop_err:
                    logger.error(f"Unexpected error: {loop_err}")

                # Sleep until next publish
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping magnetic variation service (Ctrl+C)")
        finally:
            self.cleanup()


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Magnetic Variation Service")
    parser.add_argument(
        "--host", help="SignalK server host (required if not in config file)"
    )
    parser.add_argument(
        "--port", type=int, help="SignalK server port (required if not in config file)"
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        help=f"SignalK UDP data port (default: {DEFAULT_UDP_PORT})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Publish interval in seconds (default: 600)",
    )

    args = parser.parse_args()

    try:
        # Create and run service
        service = MagneticVariationService(
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
        )
        if args.interval and args.interval > 0:
            service.interval_seconds = args.interval
        service.run()

    except Exception as e:
        logger.error(f"Service failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
