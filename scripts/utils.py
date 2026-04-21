#!/usr/bin/env python3
"""
Shared utilities for vessel tracking scripts.
Provides common functions for configuration management, error handling, and validation.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class VesselConfigError(Exception):
    """Raised when vessel configuration is invalid or missing."""
    pass


class SensorConfigError(Exception):
    """Raised when sensor configuration is invalid or missing."""
    pass


def setup_logging(level: str = "INFO", format_string: str = None) -> None:
    """
    Set up logging configuration for scripts.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string
    )


def create_signalk_delta(values: list[dict], source_label: str, source_type: str, source_src: str) -> dict:
    """
    Create a SignalK delta message.

    Args:
        values: List of value dictionaries with 'path' and 'value' keys
        source_label: Human-readable source label
        source_type: Source type identifier
        source_src: Source identifier
    Returns:
        SignalK delta message dictionary
    """
    return {
        "context": "vessels.self",
        "updates": [
            {
                "source": {
                    "label": source_label,
                    "type": source_type,
                    "src": source_src,
                    "$source": source_src,
                },
                "timestamp": datetime.now(UTC).isoformat(),
                "values": values,
            }
        ],
    }


def encode_signalk_udp_message(delta: dict) -> bytes:
    """
    Encode a SignalK delta for UDP transport.

    Ensures messages are newline-terminated as expected by SignalK UDP input.
    """
    return (json.dumps(delta) + "\n").encode("utf-8")


def send_delta_over_udp(udp_socket, host: str, port: int, delta: dict) -> int:
    """
    Send a SignalK delta over an existing UDP socket.

    Returns the number of bytes sent.
    """
    message_bytes = encode_signalk_udp_message(delta)
    return udp_socket.sendto(message_bytes, (host, port))


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def load_vessel_info(info_path: str = "data/vessel/info.yaml") -> dict[str, Any]:
    """
    Load vessel information from YAML or JSON file.

    Tries to load from YAML first (info.yaml), then falls back to JSON (info.json)
    for backward compatibility.

    Args:
        info_path: Relative path to the vessel info file (YAML or JSON)

    Returns:
        Dictionary containing vessel configuration

    Raises:
        VesselConfigError: If the file cannot be loaded or parsed
    """
    try:
        project_root = get_project_root()

        # Try YAML first (preferred format)
        yaml_path = project_root / info_path.replace('.json', '.yaml')
        json_path = project_root / info_path.replace('.yaml', '.json')

        # If explicit path given, use it; otherwise try both formats
        if info_path.endswith('.yaml') or info_path.endswith('.yml'):
            # Explicit YAML path
            full_path = project_root / info_path
            if full_path.exists():
                return _load_yaml_file(full_path)
            # Fallback to JSON version
            json_fallback = full_path.with_suffix('.json')
            if json_fallback.exists():
                logger.info(f"YAML file not found, falling back to JSON: {json_fallback}")
                return _load_json_file(json_fallback)
        elif info_path.endswith('.json'):
            # Explicit JSON path
            full_path = project_root / info_path
            if full_path.exists():
                return _load_json_file(full_path)
        else:
            # No extension - try YAML first, then JSON
            yaml_path = project_root / f"{info_path}.yaml"
            json_path = project_root / f"{info_path}.json"

            if yaml_path.exists():
                return _load_yaml_file(yaml_path)
            elif json_path.exists():
                logger.info(f"YAML file not found, falling back to JSON: {json_path}")
                return _load_json_file(json_path)

        # If we get here, neither file exists
        raise VesselConfigError(
            f"Vessel info file not found. Tried: {yaml_path} and {json_path}"
        )

    except Exception as e:
        if isinstance(e, VesselConfigError):
            raise
        raise VesselConfigError(f"Failed to load vessel info from {info_path}: {e}") from e


def _load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            info = yaml.safe_load(f)

        if info is None:
            info = {}

        logger.info(f"Loaded vessel info from YAML: {file_path}")
        return info
    except yaml.YAMLError as e:
        raise VesselConfigError(f"Invalid YAML in vessel info file: {e}") from e


def _load_json_file(file_path: Path) -> dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            info = json.load(f)

        logger.info(f"Loaded vessel info from JSON: {file_path}")
        return info
    except json.JSONDecodeError as e:
        raise VesselConfigError(f"Invalid JSON in vessel info file: {e}") from e


def save_vessel_info(
    info: dict[str, Any],
    info_path: str = "data/vessel/info.yaml",
    format: str = "yaml"
) -> bool:
    """
    Save vessel information to YAML or JSON file.

    Args:
        info: Dictionary containing vessel configuration
        info_path: Relative path to the vessel info file
        format: Output format - "yaml" (default) or "json"

    Returns:
        True if successful, False otherwise
    """
    try:
        project_root = get_project_root()

        # Determine output format from path extension or format parameter
        if info_path.endswith('.json'):
            output_format = 'json'
            full_path = project_root / info_path
        elif info_path.endswith('.yaml') or info_path.endswith('.yml'):
            output_format = 'yaml'
            full_path = project_root / info_path
        else:
            # Use format parameter to determine extension
            output_format = format.lower()
            if output_format == 'yaml':
                full_path = project_root / f"{info_path}.yaml"
            else:
                full_path = project_root / f"{info_path}.json"

        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == 'yaml':
            with open(full_path, 'w', encoding='utf-8') as f:
                yaml.dump(info, f, default_flow_style=False, sort_keys=False, indent=2)
        else:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)

        logger.info(f"Saved vessel info to {full_path} ({output_format.upper()})")
        return True

    except Exception as e:
        logger.error(f"Failed to save vessel info to {info_path}: {e}")
        return False


def validate_vessel_config(config: dict[str, Any]) -> None:
    """
    Validate vessel configuration.

    Args:
        config: Dictionary containing vessel configuration

    Raises:
        VesselConfigError: If configuration is invalid
    """
    required_fields = ["name", "mmsi"]

    for field in required_fields:
        if field not in config:
            raise VesselConfigError(f"Missing required field: {field}")

        if not config[field] or not isinstance(config[field], str):
            raise VesselConfigError(f"Invalid value for field '{field}': must be non-empty string")

    # Validate MMSI format (9 digits)
    mmsi = config["mmsi"]
    if not mmsi.isdigit() or len(mmsi) != 9:
        raise VesselConfigError(f"Invalid MMSI format: {mmsi} (must be 9 digits)")


def validate_signalk_config(config: dict[str, Any]) -> None:
    """
    Validate SignalK configuration.

    Args:
        config: Dictionary containing SignalK configuration

    Raises:
        VesselConfigError: If SignalK configuration is invalid
    """
    required_fields = ["host", "port"]

    for field in required_fields:
        if field not in config:
            raise VesselConfigError(f"Missing required SignalK field: {field}")

        if not config[field]:
            raise VesselConfigError(f"SignalK {field} cannot be empty")

    # Validate port is numeric
    try:
        port = int(config["port"])
        if not (1 <= port <= 65535):
            raise VesselConfigError(f"Invalid SignalK port: {port} (must be 1-65535)")
    except ValueError as e:
        raise VesselConfigError(f"Invalid SignalK port format: {config['port']} (must be numeric)") from e

    # Validate protocol
    protocol = config.get("protocol", "https")
    if protocol not in ["http", "https"]:
        raise VesselConfigError(f"Invalid SignalK protocol: {protocol} (must be 'http' or 'https')")


def get_sensor_config(vessel_info: dict[str, Any]) -> dict[str, Any]:
    """
    Get sensor configuration from vessel info.

    Args:
        vessel_info: Dictionary containing vessel configuration

    Returns:
        Dictionary containing sensor configuration
    """
    return vessel_info.get("sensors", {})


def get_signalk_config(vessel_info: dict[str, Any]) -> dict[str, Any]:
    """
    Get SignalK configuration from vessel info.

    Args:
        vessel_info: Dictionary containing vessel configuration

    Returns:
        Dictionary containing SignalK configuration
    """
    return vessel_info.get("signalk", {})


def validate_sensor_config(sensor_config: dict[str, Any]) -> None:
    """
    Validate sensor configuration.

    Args:
        sensor_config: Dictionary containing sensor configuration

    Raises:
        SensorConfigError: If sensor configuration is invalid
    """
    # Validate heading correction offset if present (under mmc5603.calibration)
    mmc5603_config = sensor_config.get("mmc5603", {})
    calibration = mmc5603_config.get("calibration", {})
    if "heading_correction_offset_rad" in calibration:
        offset = calibration["heading_correction_offset_rad"]
        if not isinstance(offset, (int, float)):
            raise SensorConfigError(f"Invalid heading correction offset: {offset} (must be numeric)")

        # Check if offset is reasonable (within ±2π radians)
        if abs(offset) > 2 * 3.14159:
            raise SensorConfigError(f"Unreasonable heading correction offset: {offset} (should be within +/-2*pi radians)")


def create_default_vessel_config() -> dict[str, Any]:
    """
    Create a default vessel configuration.

    Returns:
        Dictionary containing default vessel configuration
    """
    return {
        "name": "S.V. Vessel",
        "mmsi": "123456789",
        "uscg_number": "1234567",
        "hull_number": "ABC12345",
        "signalk": {
            "host": "192.168.1.100",
            "port": "3000",
            "protocol": "https"
        },
        "sensors": {
            "mmc5603": {
                "calibration": {
                    "heading_correction_offset_rad": 0.0
                }
            }
        }
    }


def safe_get_nested_value(data: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    """
    Safely get a nested value from a dictionary.

    Args:
        data: Dictionary to search
        keys: Tuple of keys to traverse
        default: Default value if key path doesn't exist

    Returns:
        Value at the key path or default value
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current

