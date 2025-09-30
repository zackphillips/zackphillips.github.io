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
import math
import os
import sys
import time

import board
import busio

# BNO055 availability will be checked during initialization
try:
    from adafruit_bno055 import BNO055_I2C
    BNO055_AVAILABLE = True
except ImportError:
    BNO055_AVAILABLE = False


def load_vessel_info(info_path="data/vessel/info.json"):
    """Load vessel information from info.json file."""
    try:
        # Get the absolute path relative to the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        full_path = os.path.join(project_root, info_path)

        with open(full_path) as f:
            info = json.load(f)

        print(f"Loaded vessel info from {full_path}")
        return info
    except Exception as e:
        print(f"Failed to load vessel info from {info_path}: {e}")
        return None


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
    return {
        'system': bno055.calibration_status[0],
        'gyro': bno055.calibration_status[1],
        'accel': bno055.calibration_status[2],
        'mag': bno055.calibration_status[3]
    }


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
            print(f"\r{sensor_type}: {status[sensor_type.lower()]}/3", end="", flush=True)
            
            if status[sensor_type.lower()] >= 3:
                print(f"\n✓ {sensor_type} calibration complete!")
                return True
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print(f"\n⚠ {sensor_type} calibration skipped.")
        return False


def save_calibration_data(bno055, vessel_info):
    """Save calibration data to vessel info."""
    try:
        # Get calibration data from BNO055
        cal_data = bno055.calibration_data
        
        if cal_data:
            # Ensure sensors section exists
            if "sensors" not in vessel_info:
                vessel_info["sensors"] = {}
            
            # Store calibration data
            vessel_info["sensors"]["bno055_calibration"] = {
                "accel_offset_x": cal_data[0],
                "accel_offset_y": cal_data[1], 
                "accel_offset_z": cal_data[2],
                "accel_radius": cal_data[3],
                "gyro_offset_x": cal_data[4],
                "gyro_offset_y": cal_data[5],
                "gyro_offset_z": cal_data[6],
                "mag_offset_x": cal_data[7],
                "mag_offset_y": cal_data[8],
                "mag_offset_z": cal_data[9],
                "mag_radius": cal_data[10]
            }
            
            print("✓ Calibration data saved to vessel info")
            return True
        else:
            print("⚠ No calibration data available to save")
            return False
            
    except Exception as e:
        print(f"Error saving calibration data: {e}")
        return False


def main():
    """Main calibration function."""
    print("=== BNO055 IMU Calibration ===")
    print()
    print("This script will guide you through calibrating the BNO055 IMU sensor.")
    print("The BNO055 requires calibration for accurate orientation and motion data.")
    print()
    
    # Check if BNO055 is available
    if not BNO055_AVAILABLE:
        print("Error: BNO055 library not available.")
        print("Please install it with: pip install adafruit-circuitpython-bno055")
        sys.exit(1)
    
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
        
        print("✓ BNO055 sensor initialized")
        
        # Check current calibration status
        print("\n=== Current Calibration Status ===")
        status = get_calibration_status(bno055)
        print_calibration_status(status)
        
        if all(v >= 3 for v in status.values()):
            print("\n✓ All sensors are already calibrated!")
            save_calibration_data(bno055, vessel_info)
            if save_vessel_info(vessel_info):
                print("✓ Calibration data saved successfully!")
            sys.exit(0)
        
        print("\n=== Calibration Instructions ===")
        print("The BNO055 requires calibration for three sensors:")
        print("1. Accelerometer: Move sensor in figure-8 pattern")
        print("2. Gyroscope: Keep sensor stationary")
        print("3. Magnetometer: Move sensor in figure-8 pattern in different orientations")
        print()
        print("We'll calibrate each sensor one at a time.")
        
        # Calibrate accelerometer
        accel_success = wait_for_calibration(
            bno055, 
            "Accelerometer",
            "Move the sensor in a figure-8 pattern slowly and smoothly.\n"
            "Make sure to rotate through all orientations.\n"
            "The sensor should experience different gravitational orientations."
        )
        
        # Calibrate gyroscope
        gyro_success = wait_for_calibration(
            bno055,
            "Gyroscope", 
            "Keep the sensor completely stationary.\n"
            "Do not move or rotate the sensor at all.\n"
            "This helps the gyroscope establish a zero reference."
        )
        
        # Calibrate magnetometer
        mag_success = wait_for_calibration(
            bno055,
            "Magnetometer",
            "Move the sensor in a figure-8 pattern in different orientations.\n"
            "Rotate the sensor through all three axes.\n"
            "Avoid magnetic interference (keep away from metal objects, electronics)."
        )
        
        # Final status check
        print("\n=== Final Calibration Status ===")
        final_status = get_calibration_status(bno055)
        print_calibration_status(final_status)
        
        # Save calibration data
        if save_calibration_data(bno055, vessel_info):
            if save_vessel_info(vessel_info):
                print("\n✓ IMU calibration completed successfully!")
                print("✓ Calibration data saved to vessel info")
                print()
                print("The BNO055 sensor is now calibrated and ready for use.")
                print("You can run this calibration again anytime to update the calibration.")
            else:
                print("\n⚠ Calibration completed but failed to save data.")
                sys.exit(1)
        else:
            print("\n⚠ Calibration completed but no data was saved.")
            print("The sensor may still work with default calibration.")
            
    except Exception as e:
        print(f"\nError during calibration: {e}")
        print("Make sure the BNO055 sensor is properly connected and accessible.")
        sys.exit(1)


if __name__ == "__main__":
    main()
