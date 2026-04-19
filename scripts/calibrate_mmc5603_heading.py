#!/usr/bin/env python3
"""
Heading Calibration Script

This script helps calibrate the magnetic heading by:
1. Asking the user for the current true heading
2. Reading the MMC5603 sensor to get the raw magnetic heading
3. Calculating the correction offset needed
4. Updating the vessel info.json file with the new offset
"""

import json
import math
import os
import sys
import time

# Import MMC5603 magnetometer
import adafruit_mmc56x3
import board
import busio

# Import vessel info loading from utils
from .utils import load_vessel_info, save_vessel_info as save_vessel_info_util


def save_vessel_info(info, info_path="data/vessel/info.yaml"):
    """Save vessel information to config file (YAML or JSON)."""
    if save_vessel_info_util(info, info_path):
        print(f"Saved vessel info to {info_path}")
        return True
    else:
        print(f"Failed to save vessel info to {info_path}")
        return False


def _old_save_vessel_info(info, info_path="data/vessel/info.json"):
    """Legacy save function - kept for reference."""
    try:
        # Get the absolute path relative to the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        full_path = os.path.join(project_root, info_path)

        with open(full_path, "w") as f:
            json.dump(info, f, indent=2)

        print(f"Saved vessel info to {full_path}")
        return True
    except Exception as e:
        print(f"Failed to save vessel info to {info_path}: {e}")
        return False


def read_mmc5603_heading():
    """Read magnetic heading from MMC5603 sensor."""

    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)

        # Initialize MMC5603 sensor
        mmc5603 = adafruit_mmc56x3.MMC5603(i2c)

        # Read magnetic field
        mag_x, mag_y, mag_z = mmc5603.magnetic

        # Calculate raw magnetic heading
        if mag_x != 0 or mag_y != 0:
            raw_heading = 3.14159 / 2 - math.atan2(mag_y, mag_x)
            if raw_heading < 0:
                raw_heading += 3.14159 * 2
            return raw_heading
        else:
            print("Warning: No magnetic field detected")
            return None

    except Exception as e:
        print(f"Error reading MMC5603 sensor: {e}")
        return None


def degrees_to_radians(degrees):
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0


def radians_to_degrees(radians):
    """Convert radians to degrees."""
    return radians * 180.0 / math.pi


def normalize_heading(heading_rad):
    """Normalize heading to 0-2*pi range."""
    while heading_rad < 0:
        heading_rad += 2 * math.pi
    while heading_rad >= 2 * math.pi:
        heading_rad -= 2 * math.pi
    return heading_rad


def main():
    """Main calibration function."""
    print("=== Magnetic Heading Calibration ===")
    print()
    print("This script will help you calibrate the magnetic heading sensor.")
    print("You'll need to know the current true heading of your vessel.")
    print()


    # Load current vessel info
    vessel_info = load_vessel_info()
    if not vessel_info:
        print("Error: Could not load vessel info. Make sure data/vessel/info.yaml (or info.json) exists.")
        sys.exit(1)

    # Get current true heading from user
    while True:
        try:
            true_heading_input = input("Enter the current true heading in degrees (0-360): ")
            true_heading_deg = float(true_heading_input)
            if 0 <= true_heading_deg <= 360:
                break
            else:
                print("Please enter a value between 0 and 360 degrees.")
        except ValueError:
            print("Please enter a valid number.")

    true_heading_rad = degrees_to_radians(true_heading_deg)

    print()
    print("Reading magnetic sensor...")

    # Read multiple samples for better accuracy
    samples = []
    for i in range(5):
        print(f"Reading sample {i+1}/5...")
        raw_heading = read_mmc5603_heading()
        if raw_heading is not None:
            samples.append(raw_heading)
        time.sleep(0.5)

    if not samples:
        print("Error: Could not read magnetic sensor. Check connections and permissions.")
        sys.exit(1)

    # Calculate average raw heading
    avg_raw_heading = sum(samples) / len(samples)
    print(f"Average raw magnetic heading: {radians_to_degrees(avg_raw_heading):.1f} deg")

    # Calculate correction offset
    correction_offset = true_heading_rad - avg_raw_heading

    # Normalize the offset to -pi to pi range
    while correction_offset > math.pi:
        correction_offset -= 2 * math.pi
    while correction_offset < -math.pi:
        correction_offset += 2 * math.pi

    print(f"Calculated correction offset: {radians_to_degrees(correction_offset):.1f} deg ({correction_offset:.4f} rad)")

    # Update vessel info under mmc5603.calibration
    if "sensors" not in vessel_info:
        vessel_info["sensors"] = {}
    
    if "mmc5603" not in vessel_info["sensors"]:
        vessel_info["sensors"]["mmc5603"] = {}
    
    if "calibration" not in vessel_info["sensors"]["mmc5603"]:
        vessel_info["sensors"]["mmc5603"]["calibration"] = {}
    
    vessel_info["sensors"]["mmc5603"]["calibration"]["heading_correction_offset_rad"] = correction_offset

    # Save updated info
    if save_vessel_info(vessel_info):
        print()
        print("Heading calibration completed successfully!")
        print(f"Correction offset saved: {radians_to_degrees(correction_offset):.1f} deg")
        print()
        print("The sensor will now use this offset for all future readings.")
        print("You can run this calibration again anytime to update the offset.")
    else:
        print("Error: Failed to save calibration data.")
        sys.exit(1)


if __name__ == "__main__":
    main()
