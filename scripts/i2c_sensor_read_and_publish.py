#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher

This script reads data from a specified I2C sensor and publishes it to a SignalK server.

Usage:
    python3 i2c_sensor_read_and_publish.py <sensor_name> [options]
    Example: python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sensors import BME280Sensor, BNO055Sensor, MMC5603Sensor, SGP30Sensor
from utils import load_vessel_info, send_delta_over_udp, setup_logging

# Constants
DEFAULT_UDP_PORT = 4123

# Map sensor names to their classes
SENSOR_CLASSES = {
    "bme280": BME280Sensor,
    "bno055": BNO055Sensor,
    "mmc5603": MMC5603Sensor,
    "sgp30": SGP30Sensor,
}

logger = logging.getLogger(__name__)


def run_individual_sensor(
    sensor_name: str,
    signalk_host: str = None,
    signalk_port: int = None,
    udp_port: int = None,
    info_path: str = "data/vessel/info.yaml",
    update_interval: float = None,
    log_level: str = "INFO",
):
    """
    Run a single sensor service (recommended mode).

    Args:
        sensor_name: Name of the sensor to run
        signalk_host: SignalK server host (overrides config)
        signalk_port: SignalK server port (overrides config)
        udp_port: UDP port for publishing (default: 4123)
        info_path: Path to vessel config file
        update_interval: Update interval in seconds (overrides config)
        log_level: Logging level
    """
    # Setup logging
    setup_logging(level=log_level)

    # Get sensor class
    if sensor_name not in SENSOR_CLASSES:
        logger.error(f"Unknown sensor: {sensor_name}")
        logger.error(f"Available sensors: {', '.join(SENSOR_CLASSES.keys())}")
        sys.exit(1)

    sensor_class = SENSOR_CLASSES[sensor_name]

    try:
        # Create sensor instance
        sensor = sensor_class(
            signalk_host=signalk_host,
            signalk_port=signalk_port,
            udp_port=udp_port,
            info_path=info_path,
            update_interval=update_interval,
        )

        # Initialize sensor
        if not sensor.initialize():
            logger.error(f"Failed to initialize {sensor_name} sensor")
            sys.exit(1)

        # Connect UDP
        sensor.connect_udp()

        # Run sensor
        logger.info(f"Reading {sensor_name} sensor and publishing to SignalK...")
        success = sensor.run()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info(f"{sensor_name} sensor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running {sensor_name} sensor: {e}", exc_info=True)
        sys.exit(1)


def test_signalk_connection(host=None, port=None, udp_port=None):
    """Test SignalK UDP connection without sensors."""
    setup_logging(level="INFO")
    logger.info("Testing SignalK UDP connection...")

    import json
    import socket
    from datetime import UTC, datetime

    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(5.0)

        # Create test delta
        timestamp = datetime.now(UTC).isoformat()
        test_data = {
            "environment.inside.temperature": {
                "value": 293.15,  # 20 degC in Kelvin
                "units": "K",
            }
        }

        delta = {
            "context": "vessels.self",
            "updates": [
                {
                    "source": {
                        "label": "Test",
                        "type": "I2C",
                        "src": "test",
                        "$source": "test",
                    },
                    "timestamp": timestamp,
                    "values": [
                        {
                            "path": "environment.inside.temperature",
                            "value": 293.15,
                            "units": "K",
                            "$source": "test",
                        }
                    ],
                }
            ],
        }

        bytes_sent = send_delta_over_udp(udp_socket, host, udp_port or DEFAULT_UDP_PORT, delta)
        logger.info(f"SUCCESS: SignalK UDP connection successful ({bytes_sent} bytes sent)")
        udp_socket.close()
        return True
    except Exception as e:
        logger.error(f"ERROR: SignalK UDP connection failed: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="I2C Sensors to SignalK Publisher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run individual sensor service (recommended):
  python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50
        """,
    )

    # Sensor name (optional, for individual sensor mode)
    parser.add_argument(
        "sensor",
        nargs="?",
        choices=list(SENSOR_CLASSES.keys()) + [None],
        help="Sensor name to run (individual sensor mode). If not provided, will raise an error.",
    )

    # Common arguments
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="SignalK server host (overrides config)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="SignalK server port (overrides config)",
    )
    parser.add_argument(
        "--udp-port",
        type=int,
        default=None,
        help=f"UDP port for publishing (default: {DEFAULT_UDP_PORT})",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="data/vessel/info.yaml",
        help="Path to vessel config file",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Update interval in seconds (overrides config, individual sensor mode only)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test SignalK connection only",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Test mode
    if args.test:
        success = test_signalk_connection(args.host, args.port, args.udp_port)
        sys.exit(0 if success else 1)

    # Individual sensor mode (recommended)
    if args.sensor:
        run_individual_sensor(
            sensor_name=args.sensor,
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            info_path=args.config,
            update_interval=args.interval,
            log_level=args.log_level,
        )
    else:
        # No sensor specified, raise an error
        parser.error("Please specify a sensor name to run (e.g., bme280, bno055).")


if __name__ == "__main__":
    main()
