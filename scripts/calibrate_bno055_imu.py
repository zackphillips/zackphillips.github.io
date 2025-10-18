#!/usr/bin/env python3
"""
BNO055 IMU Calibration Script

This script guides users through the BNO055 IMU calibration process.
The BNO055 requires calibration for accelerometer, gyroscope, and magnetometer
to provide accurate orientation and motion data.

Calibration Process:
1. Accelerometer: Move sensor in figure-8 pattern
2. Gyroscope: Keep sensor stationary
3. Magnetometer: Move sensor in figure-8 pattern in different orientations
"""

import json
import os
import sys
import time

import board
import busio

# Import BNO055 sensor
from adafruit_bno055 import BNO055_I2C

# Import BNO055 register I/O functions
from bno055_register_io import (
    read_calibration,
    validate_calibration_data,
    write_calibration,
)

# Import vessel info loading from utils
from utils import load_vessel_info


def save_vessel_info(info, info_path="data/vessel/info.json"):
    """Save vessel information to info.json file."""
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


def get_calibration_status(bno055):
    """Get calibration status for all sensors."""
    while True:
        try:
            return {
                'system': bno055.calibration_status[0],
                'gyro': bno055.calibration_status[1],
                'accel': bno055.calibration_status[2],
                'mag': bno055.calibration_status[3]
            }
        except Exception as e:
            print(f"Exception in sensor read: {e}")


def print_calibration_status(status):
    """Print current calibration status."""
    print(f"  System: {status['system']}/3")
    print(f"  Gyroscope: {status['gyro']}/3")
    print(f"  Accelerometer: {status['accel']}/3")
    print(f"  Magnetometer: {status['mag']}/3")


def wait_for_calibration(bno055, sensor_type, instructions):
    """Wait for a specific sensor to be calibrated."""
    print(f"\n=== {sensor_type} Calibration ===")
    print(instructions)
    print("\nPress Enter when you're ready to start...")
    input()

    print(f"\nCalibrating {sensor_type}...")
    print("Watch the calibration status below. Press Ctrl+C to skip this sensor.")

    try:
        while True:
            status = get_calibration_status(bno055)
            print(status)
            print(f"\r{sensor_type}: {status[sensor_type.lower()]}/3", end="", flush=True)


            if status[sensor_type.lower()] >= 3:
                print(f"\n{sensor_type} calibration complete!")
                return True

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n{sensor_type} calibration skipped.")
        return False


def save_calibration_data(bno055, vessel_info):
    """Save calibration data to vessel info."""
    try:
        # Get calibration data from BNO055 using our register access functions
        cal_data = read_calibration(bno055)

        if cal_data:
            # Ensure sensors section exists
            if "sensors" not in vessel_info:
                vessel_info["sensors"] = {}

            if "bno055_calibration" not in vessel_info["sensors"]:
                vessel_info["sensors"]["bno055_calibration"] = {}

            # Store calibration data (cal_data is already a dictionary with named fields)
            vessel_info["sensors"]["bno055_calibration"] = cal_data

            print("Calibration data saved to vessel info")
            return True
        else:
            print("No calibration data available to save")
            return False

    except Exception as e:
        print(f"Error saving calibration data: {e}")
        return False


def load_calibration_data(bno055, vessel_info):
    """Load calibration data from vessel info and apply to BNO055."""
    try:
        # Check if calibration data exists in vessel info
        if ("sensors" not in vessel_info or
            "bno055_calibration" not in vessel_info["sensors"]):
            print("No saved calibration data found in vessel info")
            return False

        cal_data = vessel_info["sensors"]["bno055_calibration"]

        # Validate the calibration data
        is_valid, message = validate_calibration_data(cal_data)
        if not is_valid:
            print(f"Invalid calibration data: {message}")
            return False

        # Apply calibration data to BNO055
        if write_calibration(bno055, cal_data):
            print("Calibration data loaded and applied to BNO055")
            return True
        else:
            print("Failed to apply calibration data to BNO055")
            return False

    except Exception as e:
        print(f"Error loading calibration data: {e}")
        return False



def main():
    """Main calibration function."""
    print("=== BNO055 IMU Calibration ===")
    print()
    print("This script will guide you through calibrating the BNO055 IMU sensor.")
    print("The BNO055 requires calibration for accurate orientation and motion data.")
    print()


    # Load current vessel info
    vessel_info = load_vessel_info()
    if not vessel_info:
        print("Error: Could not load vessel info. Make sure data/vessel/info.json exists.")
        sys.exit(1)

    try:
        # Initialize I2C bus and BNO055 sensor
        print("Initializing BNO055 sensor...")
        i2c = busio.I2C(board.SCL, board.SDA)
        bno055 = BNO055_I2C(i2c)

        print("BNO055 sensor initialized")

        # Ask if user wants to load existing calibration data
        print("\nWould you like to load existing calibration data from vessel info? (y/n)")
        load_choice = input().lower().strip()
        if load_choice in ['y', 'yes']:
            if load_calibration_data(bno055, vessel_info):
                print("Existing calibration data loaded successfully!")
            else:
                print("No existing calibration data found or failed to load.")
            print()

        # Check current calibration status
        print("\n=== Current Calibration Status ===")
        status = get_calibration_status(bno055)
        print_calibration_status(status)


        print("\n=== Calibration Instructions ===")
        print("The BNO055 requires calibration for three sensors:")
        print("1. Accelerometer: Move sensor in figure-8 pattern")
        print("2. Gyroscope: Keep sensor stationary")
        print("3. Magnetometer: Move sensor in figure-8 pattern in different orientations")
        print()
        print("We'll calibrate each sensor one at a time.")

        # Calibrate accelerometer
        wait_for_calibration(
            bno055,
            "accel",
            "Move the sensor in a figure-8 pattern slowly and smoothly.\n"
            "Make sure to rotate through all orientations.\n"
            "The sensor should experience different gravitational orientations."
        )

        # Calibrate gyroscope
        wait_for_calibration(
            bno055,
            "gyro",
            "Keep the sensor completely stationary.\n"
            "Do not move or rotate the sensor at all.\n"
            "This helps the gyroscope establish a zero reference."
        )

        # Calibrate magnetometer
        wait_for_calibration(
            bno055,
            "mag",
            "Move the sensor in a figure-8 pattern in different orientations.\n"
            "Rotate the sensor through all three axes.\n"
            "Avoid magnetic interference (keep away from metal objects, electronics)."
        )

        # Calibrate system
        wait_for_calibration(
            bno055,
            "system",
            "Wait for the system to be calibrated overall."
        )

        # Final status check
        print("\n=== Final Calibration Status ===")
        final_status = get_calibration_status(bno055)
        print_calibration_status(final_status)

        # Save calibration data
        if save_calibration_data(bno055, vessel_info):
            if save_vessel_info(vessel_info):
                print("\nIMU calibration completed successfully!")
                print("Calibration data saved to vessel info")
                print()
                print("The BNO055 sensor is now calibrated and ready for use.")
                print("You can run this calibration again anytime to update the calibration.")
            else:
                print("\nCalibration completed but failed to save data.")
                sys.exit(1)
        else:
            print("\nCalibration completed but no data was saved.")
            print("The sensor may still work with default calibration.")

    except Exception as e:
        print(f"\nError during calibration: {e}")
        print("Make sure the BNO055 sensor is properly connected and accessible.")
        raise e
        #sys.exit(1)


if __name__ == "__main__":
    main()
