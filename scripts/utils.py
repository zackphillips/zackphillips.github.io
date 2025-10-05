#!/usr/bin/env python3
"""
Shared utilities for vessel tracking scripts.
Provides common functions for configuration management, error handling, and validation.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VesselConfigError(Exception):
    """Raised when vessel configuration is invalid or missing."""
    pass


class SensorConfigError(Exception):
    """Raised when sensor configuration is invalid or missing."""
    pass


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def load_vessel_info(info_path: str = "data/vessel/info.json") -> dict[str, Any]:
    """
    Load vessel information from info.json file.
    
    Args:
        info_path: Relative path to the vessel info JSON file
        
    Returns:
        Dictionary containing vessel configuration
        
    Raises:
        VesselConfigError: If the file cannot be loaded or parsed
    """
    try:
        project_root = get_project_root()
        full_path = project_root / info_path

        if not full_path.exists():
            raise VesselConfigError(f"Vessel info file not found: {full_path}")

        with open(full_path) as f:
            info = json.load(f)

        logger.info(f"Loaded vessel info from {full_path}")
        return info

    except json.JSONDecodeError as e:
        raise VesselConfigError(f"Invalid JSON in vessel info file: {e}") from e
    except Exception as e:
        raise VesselConfigError(f"Failed to load vessel info from {info_path}: {e}") from e


def save_vessel_info(info: dict[str, Any], info_path: str = "data/vessel/info.json") -> bool:
    """
    Save vessel information to info.json file.
    
    Args:
        info: Dictionary containing vessel configuration
        info_path: Relative path to the vessel info JSON file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        project_root = get_project_root()
        full_path = project_root / info_path

        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, 'w') as f:
            json.dump(info, f, indent=2)

        logger.info(f"Saved vessel info to {full_path}")
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
    # Validate heading correction offset if present
    if "heading_correction_offset_rad" in sensor_config:
        offset = sensor_config["heading_correction_offset_rad"]
        if not isinstance(offset, (int, float)):
            raise SensorConfigError(f"Invalid heading correction offset: {offset} (must be numeric)")

        # Check if offset is reasonable (within ±2π radians)
        if abs(offset) > 2 * 3.14159:
            raise SensorConfigError(f"Unreasonable heading correction offset: {offset} (should be within ±2π radians)")


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
            "heading_correction_offset_rad": 0.0
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

