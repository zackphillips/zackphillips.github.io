#!/usr/bin/env python3
"""
Run a single sensor service.
This script is the entry point for individual sensor systemd services.
"""

import argparse
import logging
import sys
from pathlib import Path

from sensors import BME280Sensor, BNO055Sensor, MMC5603Sensor, SGP30Sensor
from utils import setup_logging

# Map sensor names to their classes
SENSOR_CLASSES = {
    "bme280": BME280Sensor,
    "bno055": BNO055Sensor,
    "mmc5603": MMC5603Sensor,
    "sgp30": SGP30Sensor,
}

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a single sensor service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "sensor",
        choices=list(SENSOR_CLASSES.keys()),
        help="Sensor name to run",
    )
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
        help="UDP port for publishing (default: 4123)",
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
        help="Update interval in seconds (overrides config)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Get sensor class
    sensor_class = SENSOR_CLASSES[args.sensor]

    try:
        # Create sensor instance
        sensor = sensor_class(
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            info_path=args.config,
            update_interval=args.interval,
        )

        # Initialize sensor
        if not sensor.initialize():
            logger.error(f"Failed to initialize {args.sensor} sensor")
            sys.exit(1)

        # Connect UDP
        sensor.connect_udp()

        # Run sensor
        if args.once:
            logger.info(f"Running {args.sensor} sensor once...")
            success = sensor.run_once()
            sys.exit(0 if success else 1)
        else:
            logger.info(f"Starting {args.sensor} sensor service...")
            sensor.run_loop()

    except KeyboardInterrupt:
        logger.info(f"{args.sensor} sensor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running {args.sensor} sensor: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
