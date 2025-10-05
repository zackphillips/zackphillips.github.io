#!/usr/bin/env python3
"""
BNO055 Register I/O Module

This module provides low-level register access functions for the BNO055 IMU sensor.
It allows reading and writing calibration data directly from/to the sensor's registers
without relying on the library's built-in calibration_data attribute.

Functions:
- read_calibration_registers(): Read raw calibration data from registers
- write_calibration_registers(): Write raw calibration data to registers
- parse_calibration_data(): Parse raw bytes into structured data
- pack_calibration_data(): Pack structured data into raw bytes
- read_calibration(): High-level function to read calibration data
- write_calibration(): High-level function to write calibration data
- validate_calibration_data(): Validate calibration data structure
- compare_calibration_data(): Compare two calibration datasets
"""

import json
import time

# BNO055 mode constants
CONFIG_MODE = 0x00
ACCONLY_MODE = 0x01
MAGONLY_MODE = 0x02
GYRONLY_MODE = 0x03
ACCMAG_MODE = 0x04
ACCGYRO_MODE = 0x05
MAGGYRO_MODE = 0x06
AMG_MODE = 0x07
IMUPLUS_MODE = 0x08
COMPASS_MODE = 0x09
M4G_MODE = 0x0A
NDOF_FMC_OFF_MODE = 0x0B
NDOF_MODE = 0x0C


def read_calibration_registers(bno055):
    """
    Read calibration data directly from BNO055 registers.

    Args:
        bno055: BNO055_I2C instance

    Returns:
        bytes: Raw calibration data (22 bytes) or None if failed
    """
    try:
        # Store current mode
        current_mode = bno055.mode

        # Switch to CONFIG mode to access calibration registers
        bno055.mode = CONFIG_MODE
        time.sleep(0.025)  # Datasheet recommends 25ms delay after mode change

        # Read 22 bytes of calibration data from registers 0x55-0x6A
        calibration_data = []
        for i in range(22):
            try:
                byte_value = bno055._read_register(0x55 + i)
                calibration_data.append(byte_value)
            except Exception as reg_error:
                print(f"Error reading register 0x{0x55 + i:02X}: {reg_error}")
                # Try to restore mode and return None
                try:
                    bno055.mode = current_mode
                    time.sleep(0.025)
                except Exception:
                    pass
                return None

        # Restore previous mode
        bno055.mode = current_mode
        time.sleep(0.025)  # Allow time for mode switch

        return bytes(calibration_data)

    except Exception as e:
        print(f"Error reading calibration registers: {e}")
        # Try to restore mode if possible
        try:
            bno055.mode = current_mode
            time.sleep(0.025)
        except Exception:
            pass
        return None


def write_calibration_registers(bno055, calibration_data):
    """
    Write calibration data directly to BNO055 registers.

    Args:
        bno055: BNO055_I2C instance
        calibration_data: bytes or list of calibration data (22 bytes)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate input data
        if len(calibration_data) != 22:
            raise ValueError("Calibration data must be exactly 22 bytes")

        # Convert to list if needed
        if isinstance(calibration_data, bytes):
            data = list(calibration_data)
        else:
            data = calibration_data

        # Store current mode
        current_mode = bno055.mode

        # Switch to CONFIG mode to access calibration registers
        bno055.mode = CONFIG_MODE
        time.sleep(0.025)  # Datasheet recommends 25ms delay after mode change

        # Write 22 bytes of calibration data to registers 0x55-0x6A
        for i in range(22):
            try:
                bno055._write_register(0x55 + i, data[i])
            except Exception as reg_error:
                print(f"Error writing register 0x{0x55 + i:02X}: {reg_error}")
                # Try to restore mode and return False
                try:
                    bno055.mode = current_mode
                    time.sleep(0.025)
                except Exception:
                    pass
                return False

        # Restore previous mode
        bno055.mode = current_mode
        time.sleep(0.025)  # Allow time for mode switch

        return True

    except Exception as e:
        print(f"Error writing calibration registers: {e}")
        # Try to restore mode if possible
        try:
            bno055.mode = current_mode
            time.sleep(0.025)
        except Exception:
            pass
        return False


def parse_calibration_data(calibration_bytes):
    """
    Parse raw calibration bytes into structured data.

    Args:
        calibration_bytes: bytes or list of calibration data (22 bytes)

    Returns:
        dict: Parsed calibration data with named fields
    """
    if len(calibration_bytes) != 22:
        raise ValueError("Calibration data must be exactly 22 bytes")

    # Convert to list if needed
    if isinstance(calibration_bytes, bytes):
        data = list(calibration_bytes)
    else:
        data = calibration_bytes

    # Parse calibration data according to BNO055 datasheet
    calibration = {
        # Accelerometer offsets (6 bytes: 3 x 2-byte values)
        'accel_offset_x': (data[0] | (data[1] << 8)) - (65536 if data[0] | (data[1] << 8) > 32767 else 0),
        'accel_offset_y': (data[2] | (data[3] << 8)) - (65536 if data[2] | (data[3] << 8) > 32767 else 0),
        'accel_offset_z': (data[4] | (data[5] << 8)) - (65536 if data[4] | (data[5] << 8) > 32767 else 0),

        # Accelerometer radius (2 bytes)
        'accel_radius': data[6] | (data[7] << 8),

        # Gyroscope offsets (6 bytes: 3 x 2-byte values)
        'gyro_offset_x': (data[8] | (data[9] << 8)) - (65536 if data[8] | (data[9] << 8) > 32767 else 0),
        'gyro_offset_y': (data[10] | (data[11] << 8)) - (65536 if data[10] | (data[11] << 8) > 32767 else 0),
        'gyro_offset_z': (data[12] | (data[13] << 8)) - (65536 if data[12] | (data[13] << 8) > 32767 else 0),

        # Magnetometer offsets (6 bytes: 3 x 2-byte values)
        'mag_offset_x': (data[14] | (data[15] << 8)) - (65536 if data[14] | (data[15] << 8) > 32767 else 0),
        'mag_offset_y': (data[16] | (data[17] << 8)) - (65536 if data[16] | (data[17] << 8) > 32767 else 0),
        'mag_offset_z': (data[18] | (data[19] << 8)) - (65536 if data[18] | (data[19] << 8) > 32767 else 0),

        # Magnetometer radius (2 bytes)
        'mag_radius': data[20] | (data[21] << 8)
    }

    return calibration


def pack_calibration_data(calibration_dict):
    """
    Pack structured calibration data into raw bytes.

    Args:
        calibration_dict: dict with calibration data fields

    Returns:
        bytes: Packed calibration data (22 bytes)
    """
    # Pack data into 22 bytes
    data = [
        # Accelerometer offsets (6 bytes)
        calibration_dict['accel_offset_x'] & 0xFF,
        (calibration_dict['accel_offset_x'] >> 8) & 0xFF,
        calibration_dict['accel_offset_y'] & 0xFF,
        (calibration_dict['accel_offset_y'] >> 8) & 0xFF,
        calibration_dict['accel_offset_z'] & 0xFF,
        (calibration_dict['accel_offset_z'] >> 8) & 0xFF,

        # Accelerometer radius (2 bytes)
        calibration_dict['accel_radius'] & 0xFF,
        (calibration_dict['accel_radius'] >> 8) & 0xFF,

        # Gyroscope offsets (6 bytes)
        calibration_dict['gyro_offset_x'] & 0xFF,
        (calibration_dict['gyro_offset_x'] >> 8) & 0xFF,
        calibration_dict['gyro_offset_y'] & 0xFF,
        (calibration_dict['gyro_offset_y'] >> 8) & 0xFF,
        calibration_dict['gyro_offset_z'] & 0xFF,
        (calibration_dict['gyro_offset_z'] >> 8) & 0xFF,

        # Magnetometer offsets (6 bytes)
        calibration_dict['mag_offset_x'] & 0xFF,
        (calibration_dict['mag_offset_x'] >> 8) & 0xFF,
        calibration_dict['mag_offset_y'] & 0xFF,
        (calibration_dict['mag_offset_y'] >> 8) & 0xFF,
        calibration_dict['mag_offset_z'] & 0xFF,
        (calibration_dict['mag_offset_z'] >> 8) & 0xFF,

        # Magnetometer radius (2 bytes)
        calibration_dict['mag_radius'] & 0xFF,
        (calibration_dict['mag_radius'] >> 8) & 0xFF,
    ]

    return bytes(data)


def read_calibration(bno055):
    """
    Read calibration data using register access methods.
    This is an alternative to the built-in calibration_data property.

    Args:
        bno055: BNO055_I2C instance

    Returns:
        dict: Parsed calibration data or None if failed
    """
    try:
        # Read raw calibration data from registers
        raw_data = read_calibration_registers(bno055)
        if raw_data is None:
            return None

        # Parse the raw data
        calibration = parse_calibration_data(raw_data)
        return calibration

    except Exception as e:
        print(f"Error reading calibration data: {e}")
        return None


def write_calibration(bno055, calibration_dict):
    """
    Write calibration data using register access methods.

    Args:
        bno055: BNO055_I2C instance
        calibration_dict: dict with calibration data fields

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Pack calibration data into bytes
        calibration_bytes = pack_calibration_data(calibration_dict)

        # Write to registers
        return write_calibration_registers(bno055, calibration_bytes)

    except Exception as e:
        print(f"Error writing calibration data: {e}")
        return False


def validate_calibration_data(calibration_dict):
    """
    Validate calibration data structure and ranges.

    Args:
        calibration_dict: dict with calibration data fields

    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = [
        'accel_offset_x', 'accel_offset_y', 'accel_offset_z', 'accel_radius',
        'gyro_offset_x', 'gyro_offset_y', 'gyro_offset_z',
        'mag_offset_x', 'mag_offset_y', 'mag_offset_z', 'mag_radius'
    ]

    # Check if all required fields are present
    for field in required_fields:
        if field not in calibration_dict:
            return False, f"Missing required field: {field}"

    # Check data types and ranges
    for field in required_fields:
        value = calibration_dict[field]
        if not isinstance(value, (int, float)):
            return False, f"Field {field} must be numeric"

        # Check reasonable ranges (these are approximate based on typical BNO055 values)
        if 'offset' in field:
            if not (-32768 <= value <= 32767):
                return False, f"Field {field} out of range (-32768 to 32767)"
        elif 'radius' in field:
            if not (0 <= value <= 65535):
                return False, f"Field {field} out of range (0 to 65535)"

    return True, "Valid"


def compare_calibration_data(cal1, cal2, tolerance=1):
    """
    Compare two calibration datasets.

    Args:
        cal1: First calibration dict
        cal2: Second calibration dict
        tolerance: Tolerance for comparison (default: 1)

    Returns:
        dict: Comparison results with differences and match status
    """
    comparison = {
        'matches': True,
        'differences': {},
        'total_difference': 0
    }

    # Compare each field
    for field in cal1.keys():
        if field in cal2:
            diff = abs(cal1[field] - cal2[field])
            comparison['differences'][field] = diff
            comparison['total_difference'] += diff

            if diff > tolerance:
                comparison['matches'] = False
        else:
            comparison['matches'] = False
            comparison['differences'][field] = "Missing in cal2"

    return comparison


def print_calibration_data(calibration_dict, title="Calibration Data"):
    """
    Print calibration data in a formatted way.

    Args:
        calibration_dict: dict with calibration data fields
        title: Title for the output
    """
    print(f"\n=== {title} ===")
    print("Accelerometer:")
    print(f"  Offset X: {calibration_dict.get('accel_offset_x', 'N/A')}")
    print(f"  Offset Y: {calibration_dict.get('accel_offset_y', 'N/A')}")
    print(f"  Offset Z: {calibration_dict.get('accel_offset_z', 'N/A')}")
    print(f"  Radius: {calibration_dict.get('accel_radius', 'N/A')}")

    print("Gyroscope:")
    print(f"  Offset X: {calibration_dict.get('gyro_offset_x', 'N/A')}")
    print(f"  Offset Y: {calibration_dict.get('gyro_offset_y', 'N/A')}")
    print(f"  Offset Z: {calibration_dict.get('gyro_offset_z', 'N/A')}")

    print("Magnetometer:")
    print(f"  Offset X: {calibration_dict.get('mag_offset_x', 'N/A')}")
    print(f"  Offset Y: {calibration_dict.get('mag_offset_y', 'N/A')}")
    print(f"  Offset Z: {calibration_dict.get('mag_offset_z', 'N/A')}")
    print(f"  Radius: {calibration_dict.get('mag_radius', 'N/A')}")


def save_calibration_to_file(calibration_dict, filename):
    """
    Save calibration data to a JSON file.

    Args:
        calibration_dict: dict with calibration data fields
        filename: Path to save the file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filename, 'w') as f:
            json.dump(calibration_dict, f, indent=2)
        print(f"Calibration data saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving calibration data to {filename}: {e}")
        return False


def load_calibration_from_file(filename):
    """
    Load calibration data from a JSON file.

    Args:
        filename: Path to the file

    Returns:
        dict: Calibration data or None if failed
    """
    try:
        with open(filename) as f:
            calibration_dict = json.load(f)
        print(f"Calibration data loaded from {filename}")
        return calibration_dict
    except Exception as e:
        print(f"Error loading calibration data from {filename}: {e}")
        return None

