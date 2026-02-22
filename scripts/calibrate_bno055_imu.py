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
4. Zero State: Establish reference orientation for pitch/roll
5. Yaw Calibration: Align yaw reading with SignalK navigation.headingTrue

The script automatically fetches the current true heading from SignalK server
and calculates the necessary offset to align the BNO055 yaw reading.
"""

import math
import sys
import time

import board
import busio
import requests

# Import BNO055 sensor
from adafruit_bno055 import BNO055_I2C

# Import BNO055 register I/O functions
from bno055_register_io import (
    read_calibration,
    validate_calibration_data,
    write_calibration,
)

# Import vessel info loading from utils
from .utils import load_vessel_info, save_vessel_info as save_vessel_info_util


def get_heading_true_from_signalk(vessel_info):
    """Get current true heading from SignalK server."""
    try:
        # Get SignalK connection info from vessel info
        signalk_config = vessel_info.get("signalk", {})
        host = signalk_config.get("host")
        port = signalk_config.get("port", 3000)
        protocol = signalk_config.get("protocol", "http")

        if not host:
            print("Warning: SignalK host not configured in vessel info")
            return None

        # Construct API URL
        api_url = f"{protocol}://{host}:{port}/signalk/v1/api/vessels/self/navigation/headingTrue"

        print(f"Fetching heading from SignalK: {api_url}")
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        data = response.json()
        if "value" in data:
            heading_rad = data["value"]
            print(
                f"Current true heading from SignalK: {math.degrees(heading_rad):.1f}deg"
                f" ({heading_rad} rad)"
            )
            return heading_rad
        else:
            print("No heading value found in SignalK response")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching heading from SignalK: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching heading: {e}")
        return None


def save_vessel_info(info, info_path="data/vessel/info.yaml"):
    """Save vessel information to config file (YAML or JSON)."""
    if save_vessel_info_util(info, info_path):
        print(f"Saved vessel info to {info_path}")
        return True
    else:
        print(f"Failed to save vessel info to {info_path}")
        return False


def get_calibration_status(bno055):
    """Get calibration status for all sensors."""
    while True:
        try:
            return {
                "system": bno055.calibration_status[0],
                "gyro": bno055.calibration_status[1],
                "accel": bno055.calibration_status[2],
                "mag": bno055.calibration_status[3],
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
            print(
                f"\r{sensor_type}: {status[sensor_type.lower()]}/3", end="", flush=True
            )

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

            # Ensure bno055 section exists
            if "bno055" not in vessel_info["sensors"]:
                vessel_info["sensors"]["bno055"] = {}

            # Store calibration data under bno055.calibration
            vessel_info["sensors"]["bno055"]["calibration"] = cal_data

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
        sensors_config = vessel_info.get("sensors", {})
        bno055_config = sensors_config.get("bno055", {})
        cal_data = bno055_config.get("calibration")
        
        if cal_data is None:
            print("No saved calibration data found in vessel info")
            return False

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


def calibrate_zero_state(bno055, vessel_info):
    """Establish zero state for pitch and roll."""
    print("\n=== Zero State Calibration ===")
    print("This step establishes a reference orientation for pitch and roll.")
    print(
        "Ensure the current sensor orientation is the desired 'level' orientation (e.g., flat)"
    )
    print("This will be used as the zero reference for future readings.")
    print()

    print("Reading zero state orientation...")
    time.sleep(1)  # Allow sensor to stabilize

    try:
        # Read multiple samples for accuracy
        samples = []
        for _ in range(5):
            euler = bno055.euler
            if euler and all(x is not None for x in euler):
                # Convert to radians
                roll_rad = math.radians(euler[0])
                pitch_rad = math.radians(euler[1])
                samples.append((roll_rad, pitch_rad))
            time.sleep(0.2)

        if not samples:
            print("Error: Could not read orientation data from BNO055")
            return False

        # Calculate average zero state
        avg_roll = sum(s[0] for s in samples) / len(samples)
        avg_pitch = sum(s[1] for s in samples) / len(samples)

        print("Zero state established:")
        print(f"  Roll: {math.degrees(avg_roll):.1f}deg")
        print(f"  Pitch: {math.degrees(avg_pitch):.1f}deg")

        # Store zero state in vessel info under bno055.calibration
        if "sensors" not in vessel_info:
            vessel_info["sensors"] = {}
        
        if "bno055" not in vessel_info["sensors"]:
            vessel_info["sensors"]["bno055"] = {}
        
        if "calibration" not in vessel_info["sensors"]["bno055"]:
            vessel_info["sensors"]["bno055"]["calibration"] = {}
        
        # Merge zero state into calibration data
        vessel_info["sensors"]["bno055"]["calibration"]["roll"] = avg_roll
        vessel_info["sensors"]["bno055"]["calibration"]["pitch"] = avg_pitch
        vessel_info["sensors"]["bno055"]["calibration"]["zero_state_timestamp"] = time.time()

        print("Zero state saved to vessel info")
        return True

    except Exception as e:
        print(f"Error during zero state calibration: {e}")
        return False


def calibrate_zero_state_extended(bno055, vessel_info):
    """Establish zero state for pitch and roll with 30-second averaging."""
    print("\n=== Extended Zero State Calibration ===")
    print("This step establishes a reference orientation for pitch and roll.")
    print(
        "Leave the sensor in the desired 'level' orientation (e.g., flat on deck) for 30 seconds."
    )
    print("We will average readings for 30 seconds for maximum accuracy.")
    print()

    print("Starting 30-second averaging for zero state...")
    print("Please keep the sensor stationary during this time.")
    print("Progress: ", end="", flush=True)

    try:
        # Read samples for 30 seconds
        samples = []
        start_time = time.time()
        last_progress = 0

        while time.time() - start_time < 30:
            euler = bno055.euler
            if euler and all(x is not None for x in euler):
                # Convert to radians
                roll_rad = math.radians(euler[0])
                pitch_rad = math.radians(euler[1])
                samples.append((roll_rad, pitch_rad))

            # Show progress every 3 seconds
            elapsed = time.time() - start_time
            progress = int(elapsed / 3)
            if progress > last_progress:
                print(f"{progress * 10}% ", end="", flush=True)
                last_progress = progress

            time.sleep(0.1)  # Sample every 100ms

        print("100%")

        if not samples:
            print("Error: Could not read orientation data from BNO055")
            return False

        # Calculate average zero state
        avg_roll = sum(s[0] for s in samples) / len(samples)
        avg_pitch = sum(s[1] for s in samples) / len(samples)

        # Calculate standard deviation for quality assessment
        roll_std = math.sqrt(
            sum((s[0] - avg_roll) ** 2 for s in samples) / len(samples)
        )
        pitch_std = math.sqrt(
            sum((s[1] - avg_pitch) ** 2 for s in samples) / len(samples)
        )

        print(f"\nZero state established after {len(samples)} samples:")
        print(f"  Roll: {(avg_roll):.2f}rad (std: {(roll_std):.2f}rad)")
        print(f"  Pitch: {(avg_pitch):.2f}rad (std: {(pitch_std):.2f}rad)")

        # Store zero state in vessel info
        if "sensors" not in vessel_info:
            vessel_info["sensors"] = {}

        vessel_info["sensors"]["bno055_zero_state"] = {
            "roll": avg_roll,
            "pitch": avg_pitch,
            "roll_std": roll_std,
            "pitch_std": pitch_std,
            "sample_count": len(samples),
            "timestamp": time.time(),
        }

        print("Zero state saved to vessel info")
        return True

    except Exception as e:
        print(f"Error during extended zero state calibration: {e}")
        return False


def calibrate_yaw_to_signalk(bno055, vessel_info):
    """Calibrate yaw to match SignalK navigation.headingTrue."""
    print("\n=== Yaw Calibration to SignalK Heading ===")
    print("This step aligns the BNO055 yaw reading with SignalK's true heading.")
    print("Make sure your vessel is stationary and SignalK has a valid heading.")
    print()

    # Get current true heading from SignalK
    signalk_heading = get_heading_true_from_signalk(vessel_info)
    if signalk_heading is None:
        print("Could not fetch heading from SignalK. Skipping yaw calibration.")
        print("You can manually enter the current true heading if needed.")

        while True:
            try:
                manual_heading = input(
                    "Enter current true heading in degrees (0-360) or 'skip': "
                )
                if manual_heading.lower() == "skip":
                    return False
                heading_deg = float(manual_heading)
                if 0 <= heading_deg <= 360:
                    signalk_heading = math.radians(heading_deg)
                    break
                else:
                    print("Please enter a value between 0 and 360 degrees.")
            except ValueError:
                print("Please enter a valid number.")

    print(f"\nSignalK true heading: {math.degrees(signalk_heading):.1f}deg")

    print("Reading BNO055 yaw...")
    time.sleep(1)  # Allow sensor to stabilize

    try:
        # Read multiple samples for accuracy
        samples = []
        for _ in range(5):
            euler = bno055.euler
            if euler and all(x is not None for x in euler):
                # Convert to radians
                yaw_rad = math.radians(euler[2])
                samples.append(yaw_rad)
            time.sleep(0.2)

        if not samples:
            print("Error: Could not read yaw data from BNO055")
            return False

        # Calculate average BNO055 yaw
        avg_bno055_yaw = sum(samples) / len(samples)

        print(
            f"BNO055 yaw reading: {math.degrees(avg_bno055_yaw):.1f}deg ({avg_bno055_yaw} rad)"
        )

        # Calculate yaw offset
        yaw_offset = signalk_heading - avg_bno055_yaw

        print(
            f"Calculated yaw offset: {math.degrees(yaw_offset):.1f}deg ({yaw_offset} rad)"
        )
        print(
            f"Signalk heading: {math.degrees(signalk_heading):.1f}deg ({signalk_heading} rad)"
        )
        corrected_bno055_yaw = avg_bno055_yaw + yaw_offset
        print(
            f"BNO055 corrected yaw: {math.degrees(corrected_bno055_yaw):.1f}deg ({corrected_bno055_yaw} rad)"
        )

        # Store yaw offset in vessel info
        if "sensors" not in vessel_info:
            vessel_info["sensors"] = {}

        vessel_info["sensors"]["bno055_yaw_offset"] = {
            "offset": yaw_offset,
            "signalk_heading": signalk_heading,
            "bno055_yaw": avg_bno055_yaw,
            "timestamp": time.time(),
        }

        print("Yaw offset saved to vessel info")
        return True

    except Exception as e:
        print(f"Error during yaw calibration: {e}")
        return False


def main():
    """Main calibration function."""
    print("=== BNO055 IMU Calibration ===")
    print()
    print("This script will guide you through calibrating the BNO055 IMU sensor.")
    print("The BNO055 requires calibration for motion data.")

    # Save mounting orientation to vessel info
    if "sensors" not in vessel_info:
        vessel_info["sensors"] = {}
    if "bno055" not in vessel_info["sensors"]:
        vessel_info["sensors"]["bno055"] = {}
    if not save_vessel_info(vessel_info):
        print("Warning: Failed to save mounting orientation to vessel info.")

    print()

    # Load current vessel info
    vessel_info = load_vessel_info()
    if not vessel_info:
        print(
            "Error: Could not load vessel info. Make sure data/vessel/info.yaml (or info.json) exists."
        )
        sys.exit(1)

    try:
        # Initialize I2C bus and BNO055 sensor
        print("Initializing BNO055 sensor...")
        i2c = busio.I2C(board.SCL, board.SDA)
        bno055 = BNO055_I2C(i2c)

        print("BNO055 sensor initialized")

        # Ask user which calibration steps they want to perform
        print("\n=== Calibration Options ===")
        print("You can choose which calibration steps to perform:")
        print("1. Hardware calibration (accelerometer, gyroscope, magnetometer)")
        print("2. Zero state calibration (pitch/roll reference)")
        print("3. Yaw calibration (align with SignalK heading)")
        print()

        # Hardware calibration
        print("Would you like to perform hardware calibration?")
        print("This includes accelerometer, gyroscope, and magnetometer calibration.")
        hardware_choice = input("Perform hardware calibration? (y/n): ").lower().strip()

        if hardware_choice in ["y", "yes"]:
            print("\n=== Hardware Calibration ===")

            # Ask if user wants to load existing calibration data
            print(
                "\nWould you like to load existing calibration data from vessel info? (y/n)"
            )
            load_choice = input().lower().strip()
            if load_choice in ["y", "yes"]:
                if load_calibration_data(bno055, vessel_info):
                    print("Existing calibration data loaded successfully!")
                else:
                    print("No existing calibration data found or failed to load.")
                print()

            # Check current calibration status
            print("\n=== Current Calibration Status ===")
            status = get_calibration_status(bno055)
            print_calibration_status(status)

            print("The BNO055 requires calibration for three sensors:")
            print("1. Accelerometer: Move sensor in figure-8 pattern")
            print("2. Gyroscope: Keep sensor stationary")
            print(
                "3. Magnetometer: Move sensor in figure-8 pattern in different orientations"
            )
            print()

            # Calibrate accelerometer
            wait_for_calibration(
                bno055,
                "accel",
                "Move the sensor in a figure-8 pattern slowly and smoothly.\n"
                "Make sure to rotate through all orientations.\n"
                "The sensor should experience different gravitational orientations.",
            )

            # Calibrate gyroscope
            wait_for_calibration(
                bno055,
                "gyro",
                "Keep the sensor completely stationary.\n"
                "Do not move or rotate the sensor at all.\n"
                "This helps the gyroscope establish a zero reference.",
            )

            # Calibrate magnetometer
            wait_for_calibration(
                bno055,
                "mag",
                "Move the sensor in a figure-8 pattern in different orientations.\n"
                "Rotate the sensor through all three axes.\n"
                "Avoid magnetic interference (keep away from metal objects, electronics).",
            )

            # Calibrate system
            wait_for_calibration(
                bno055, "system", "Wait for the system to be calibrated overall."
            )
        else:
            print("Skipping hardware calibration.")

        # Zero state calibration
        print("\nWould you like to perform zero state calibration?")
        print("This establishes a reference orientation for pitch and roll.")
        zero_state_choice = (
            input("Perform zero state calibration? (y/n): ").lower().strip()
        )

        if zero_state_choice in ["y", "yes"]:
            calibrate_zero_state_extended(bno055, vessel_info)
        else:
            print("Skipping zero state calibration.")

        # Yaw calibration
        print("\nWould you like to calibrate yaw to current heading?")
        print("This aligns the BNO055 yaw reading with SignalK's true heading.")
        yaw_choice = input("Perform yaw calibration? (y/n): ").lower().strip()

        if yaw_choice in ["y", "yes"]:
            calibrate_yaw_to_signalk(bno055, vessel_info)
        else:
            print("Skipping yaw calibration.")

        # Final status check
        print("\n=== Final Calibration Status ===")
        final_status = get_calibration_status(bno055)
        print_calibration_status(final_status)

        # Save calibration data
        if save_calibration_data(bno055, vessel_info):
            if save_vessel_info(vessel_info):
                print("\n=== IMU Calibration Completed Successfully! ===")
                print("All calibration data saved to vessel info:")
                print(
                    "  - BNO055 sensor calibration (accelerometer, gyroscope, magnetometer)"
                )
                print("  - Zero state reference (pitch/roll)")
                print("  - Yaw offset calibration (aligned with SignalK heading)")
                print()
                print("The BNO055 sensor is now fully calibrated and ready for use.")
                print(
                    "You can run this calibration again anytime to update the calibration."
                )
            else:
                print("\nCalibration completed but failed to save data.")
                sys.exit(1)
        else:
            print("\nCalibration completed but no sensor calibration data was saved.")
            print("Zero state and yaw offset data may still be available.")
            print("The sensor may still work with default calibration.")

    except Exception as e:
        print(f"\nError during calibration: {e}")
        print("Make sure the BNO055 sensor is properly connected and accessible.")
        raise e
        # sys.exit(1)


if __name__ == "__main__":
    main()
