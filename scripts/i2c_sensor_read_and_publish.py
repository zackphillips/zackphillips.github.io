#!/usr/bin/env python3
"""
I2C Sensors to SignalK Publisher

This script reads data from a specified I2C sensor and publishes it to a SignalK server.

Usage:
    python3 i2c_sensor_read_and_publish.py <sensor_name> [options]
    Example: python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50
"""

import argparse
import json
import logging
import math
import socket
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure imports work both when executed as a module (`python -m scripts...`)
# and when executed as a file (`python scripts/...py`).
if __package__ in (None, ""):
    # Running as a script: add project root so `import scripts.*` works.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from scripts.sensors import BME280Sensor, BNO055Sensor, MMC5603Sensor, SGP30Sensor
    from scripts.utils import load_vessel_info, send_delta_over_udp, setup_logging
else:
    # Running as a module inside the `scripts` package.
    from .sensors import BME280Sensor, BNO055Sensor, MMC5603Sensor, SGP30Sensor
    from .utils import load_vessel_info, send_delta_over_udp, setup_logging

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
    run_count: float = 1.0,
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
        run_count: Number of times to run (default: 1). Use math.inf for infinite runs.
    """
    # Setup logging
    setup_logging(level=log_level)

    # Get sensor class
    if sensor_name not in SENSOR_CLASSES:
        logger.error(f"Unknown sensor: {sensor_name}")
        logger.error(f"Available sensors: {', '.join(SENSOR_CLASSES.keys())}")
        sys.exit(1)

    sensor_class = SENSOR_CLASSES[sensor_name]

    # Determine if running in infinite mode
    is_infinite = math.isinf(run_count)
    if is_infinite:
        logger.info(f"Running {sensor_name} sensor in continuous mode (infinite runs, no delay)")
    else:
        logger.info(f"Running {sensor_name} sensor for {int(run_count)} run(s)")

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

        # Run sensor loop
        logger.info(f"Reading {sensor_name} sensor and publishing to SignalK...")
        
        run_number = 0
        while True:
            # Check if we've reached the run count (unless infinite)
            if not is_infinite:
                if run_number >= run_count:
                    logger.info(f"Completed {run_number} run(s)")
                    break
            
            run_number += 1
            if not is_infinite:
                logger.debug(f"Run {run_number}/{int(run_count)}")
            else:
                logger.debug(f"Run {run_number} (continuous mode)")

            # Run sensor once
            success = sensor.run()
            
            if not success:
                if is_infinite:
                    # In infinite mode, restart on failure
                    logger.warning(f"Run {run_number} failed, reinitializing sensor...")
                    try:
                        sensor.cleanup()
                    except Exception as e:
                        logger.debug(f"Error during cleanup: {e}")
                    
                    # Reinitialize
                    if not sensor.initialize():
                        logger.error(f"Failed to reinitialize {sensor_name} sensor")
                        # Wait a bit before retrying initialization
                        time.sleep(1.0)
                        continue
                    
                    sensor.connect_udp()
                    logger.info(f"Sensor reinitialized, continuing...")
                    continue
                else:
                    # In finite mode, exit on failure
                    logger.error(f"Run {run_number} failed")
                    sys.exit(1)
            
            # Delay between runs (skip in infinite mode)
            if not is_infinite and run_number < run_count:
                time.sleep(sensor.update_interval)

    except KeyboardInterrupt:
        logger.info(f"{sensor_name} sensor stopped by user after {run_number} run(s)")
        try:
            sensor.cleanup()
        except Exception:
            pass
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running {sensor_name} sensor: {e}", exc_info=True)
        try:
            sensor.cleanup()
        except Exception:
            pass
        sys.exit(1)


def test_signalk_connection(host=None, port=None, udp_port=None):
    """Test SignalK UDP connection without sensors."""
    setup_logging(level="INFO")
    logger.info("Testing SignalK UDP connection...")

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
  # Run individual sensor service once (default):
  python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50
  
  # Run sensor 10 times:
  python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50 --run-count 10
  
  # Run sensor continuously with automatic restarts on failure:
  python3 i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50 --run-count inf
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
        "--run-count",
        type=str,
        default=None,
        help="Number of times to run the sensor (default: read from config, or 1). Use 'inf' for infinite runs with automatic restarts on failure.",
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
        # Parse run_count argument (default to 1.0, or read from config if not specified)
        run_count = None
        if args.run_count:
            # Parse explicit run_count argument
            if args.run_count.lower() in ["inf", "infinite", "infinity"]:
                run_count = math.inf
            else:
                try:
                    run_count = float(args.run_count)
                    if run_count <= 0:
                        parser.error("--run-count must be positive or 'inf'")
                    if not math.isinf(run_count) and run_count != int(run_count):
                        parser.error("--run-count must be an integer or 'inf'")
                except ValueError:
                    parser.error(f"Invalid --run-count value: {args.run_count}. Must be a number or 'inf'")
        else:
            # Read from config if not explicitly provided
            try:
                vessel_info = load_vessel_info(args.config)
                sensor_config = vessel_info.get("sensors", {}).get(args.sensor, {})
                config_run_count = sensor_config.get("run_count")
                
                if config_run_count is not None:
                    if isinstance(config_run_count, str) and config_run_count.lower() in ["inf", "infinite", "infinity"]:
                        run_count = math.inf
                    elif isinstance(config_run_count, (int, float)):
                        run_count = float(config_run_count)
                        if math.isinf(run_count):
                            # Handle numpy.inf or math.inf
                            run_count = math.inf
                        elif run_count <= 0:
                            logger.warning(f"Invalid run_count in config: {config_run_count}. Using default: 1.0")
                            run_count = 1.0
                    else:
                        logger.warning(f"Invalid run_count type in config: {type(config_run_count)}. Using default: 1.0")
                        run_count = 1.0
                else:
                    # If run_count not set, check if update_interval is inf (legacy way to enable continuous mode)
                    config_update_interval = sensor_config.get("update_interval")
                    if config_update_interval is not None:
                        if isinstance(config_update_interval, str) and config_update_interval.lower() in ["inf", "infinite", "infinity"]:
                            logger.info(f"Interpreting update_interval: inf as run_count: inf (continuous mode)")
                            run_count = math.inf
                        elif isinstance(config_update_interval, (int, float)) and math.isinf(float(config_update_interval)):
                            logger.info(f"Interpreting update_interval: inf as run_count: inf (continuous mode)")
                            run_count = math.inf
                        else:
                            # Default to 1.0 if not in config (legacy one-shot mode)
                            run_count = 1.0
                    else:
                        # Default to 1.0 if not in config (legacy one-shot mode)
                        run_count = 1.0
            except Exception as e:
                logger.warning(f"Could not read run_count from config: {e}. Using default: 1.0")
                run_count = 1.0
        run_individual_sensor(
            sensor_name=args.sensor,
            signalk_host=args.host,
            signalk_port=args.port,
            udp_port=args.udp_port,
            info_path=args.config,
            update_interval=args.interval,
            log_level=args.log_level,
            run_count=run_count,
        )
    else:
        # No sensor specified, raise an error
        parser.error("Please specify a sensor name to run (e.g., bme280, bno055).")


if __name__ == "__main__":
    main()
