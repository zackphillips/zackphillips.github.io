#!/usr/bin/env python3
"""
SGP30 Air Quality Sensor Calibration Script

This script helps calibrate the SGP30 air quality sensor by:
1. Setting baseline values for TVOC and eCO2 measurements
2. Configuring relative humidity for better accuracy
3. Storing calibration data in vessel info.json

The SGP30 requires baseline calibration to provide accurate air quality readings.
"""

import json
import os
import sys
import time
from datetime import datetime

import board
import busio

# Import SGP30 air quality sensor
from adafruit_sgp30 import Adafruit_SGP30

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


def get_environmental_conditions():
    """Get current environmental conditions from user."""
    print("\n=== Environmental Conditions Setup ===")
    print("For accurate air quality readings, the SGP30 needs to know the current")
    print("environmental conditions. This helps the sensor provide more accurate measurements.")
    print()

    # Get temperature
    while True:
        try:
            temp_input = input("Enter current temperature in Celsius (e.g., 25): ")
            temperature = float(temp_input)
            if -50 <= temperature <= 100:
                break
            else:
                print("Please enter a temperature between -50 and 100 degC.")
        except ValueError:
            print("Please enter a valid number.")

    # Get humidity
    while True:
        try:
            humidity_input = input("Enter current relative humidity percentage (e.g., 50): ")
            humidity = float(humidity_input)
            if 0 <= humidity <= 100:
                break
            else:
                print("Please enter a humidity between 0 and 100%.")
        except ValueError:
            print("Please enter a valid number.")

    return temperature, humidity


def read_sgp30_baseline(sgp30, duration=60):
    """Read SGP30 baseline values over a specified duration."""
    print(f"\nReading SGP30 baseline values for {duration} seconds...")
    print("Keep the sensor in a stable environment during this time.")
    print("Avoid sources of air pollution or rapid environmental changes.")
    print()

    tvoc_values = []
    eco2_values = []

    start_time = time.time()
    sample_count = 0

    print("Reading sensor values...")
    while time.time() - start_time < duration:

            tvoc = sgp30.TVOC
            eco2 = sgp30.eCO2

            # Only record non-placeholder values
            if tvoc > 0 or eco2 > 400:
                tvoc_values.append(tvoc)
                eco2_values.append(eco2)
                sample_count += 1

                print(f"\rSamples: {sample_count}, TVOC: {tvoc} ppb, eCO2: {eco2} ppm", end="", flush=True)

            time.sleep(1)


    print(f"\n\nCollected {sample_count} valid samples")

    if sample_count == 0:
        print("Warning: No valid sensor readings collected")
        return None, None

    # Calculate average baseline values
    avg_tvoc = sum(tvoc_values) / len(tvoc_values)
    avg_eco2 = sum(eco2_values) / len(eco2_values)

    print(f"Average TVOC baseline: {avg_tvoc:.1f} ppb")
    print(f"Average eCO2 baseline: {avg_eco2:.1f} ppm")

    return avg_tvoc, avg_eco2


def save_sgp30_calibration(temperature, humidity, tvoc_baseline, eco2_baseline, vessel_info):
    """Save SGP30 calibration data to vessel info."""
    try:
        # Ensure sensors section exists
        if "sensors" not in vessel_info:
            vessel_info["sensors"] = {}
        
        # Ensure sgp30 section exists
        if "sgp30" not in vessel_info["sensors"]:
            vessel_info["sensors"]["sgp30"] = {}

        # Store SGP30 calibration data under sgp30.calibration
        vessel_info["sensors"]["sgp30"]["calibration"] = {
            "temperature_celsius": temperature,
            "relative_humidity_percent": humidity,
            "tvoc_baseline_ppb": tvoc_baseline,
            "eco2_baseline_ppm": eco2_baseline,
            "calibration_timestamp": datetime.now().isoformat()
        }

        print("SGP30 calibration data saved to vessel info")
        return True

    except Exception as e:
        print(f"Error saving SGP30 calibration data: {e}")
        return False


def main():
    """Main calibration function."""
    print("=== SGP30 Air Quality Sensor Calibration ===")
    print()
    print("This script will help you calibrate the SGP30 air quality sensor.")
    print("The SGP30 measures TVOC (Total Volatile Organic Compounds) and eCO2 (equivalent CO2).")
    print()


    # Load current vessel info
    vessel_info = load_vessel_info()
    if not vessel_info:
        print("Error: Could not load vessel info. Make sure data/vessel/info.yaml (or info.json) exists.")
        sys.exit(1)

    try:
        # Initialize I2C bus and SGP30 sensor
        print("Initializing SGP30 sensor...")
        i2c = busio.I2C(board.SCL, board.SDA)
        sgp30 = Adafruit_SGP30(i2c)

        print("SGP30 sensor initialized")

        # Get environmental conditions
        temperature, humidity = get_environmental_conditions()

        # Set relative humidity for better accuracy
        print(f"\nSetting relative humidity to {humidity}% at {temperature} degC...")
        sgp30.set_iaq_relative_humidity(celsius=temperature, relative_humidity=humidity)

        # Read baseline values
        print("\n=== Baseline Reading ===")
        print("The sensor needs to establish baseline values for accurate measurements.")
        print("This process takes about 1 minute and should be done in a stable environment.")

        while True:
            confirm = input("\nReady to start baseline reading? (y/N): ").lower()
            if confirm in ['y', 'yes']:
                break
            elif confirm in ['n', 'no', '']:
                print("Calibration cancelled.")
                sys.exit(0)
            else:
                print("Please enter 'y' for yes or 'n' for no.")

        # Read baseline values
        tvoc_baseline, eco2_baseline = read_sgp30_baseline(sgp30, duration=60)

        if tvoc_baseline is None or eco2_baseline is None:
            print("Error: Could not establish baseline values.")
            print("Make sure the sensor is properly connected and the environment is stable.")
            sys.exit(1)

        # Save calibration data
        if save_sgp30_calibration(temperature, humidity, tvoc_baseline, eco2_baseline, vessel_info):
            if save_vessel_info(vessel_info):
                print("\nSGP30 calibration completed successfully!")
                print("Calibration data saved to vessel info")
                print()
                print("The SGP30 sensor is now calibrated and ready for use.")
                print("You can run this calibration again anytime to update the calibration.")
                print()
                print("Calibration Summary:")
                print(f"  Temperature: {temperature} degC")
                print(f"  Humidity: {humidity}%")
                print(f"  TVOC Baseline: {tvoc_baseline:.1f} ppb")
                print(f"  eCO2 Baseline: {eco2_baseline:.1f} ppm")
            else:
                print("\nCalibration completed but failed to save data.")
                sys.exit(1)
        else:
            print("\nWARNING: Calibration completed but no data was saved.")
            print("The sensor may still work with default calibration.")

    except Exception as e:
        print(f"\nError during calibration: {e}")
        print("Make sure the SGP30 sensor is properly connected and accessible.")
        sys.exit(1)


if __name__ == "__main__":
    main()
