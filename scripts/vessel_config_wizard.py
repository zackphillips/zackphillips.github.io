#!/usr/bin/env python3
"""
Interactive vessel configuration wizard.
Steps through each field sequentially with defaults shown in parentheses.
"""

import json
import sys
from pathlib import Path
from typing import Any

from .utils import load_vessel_info, save_vessel_info


class VesselConfigWizard:
    def __init__(self, config_file: Path = Path("data/vessel/info.yaml")):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Load vessel configuration from YAML or JSON file."""
        try:
            # Try to load config (will try YAML first, then JSON)
            try:
                config = load_vessel_info(str(self.config_file))
                if config:
                    return config
            except Exception:
                # If loading fails, check if file exists
                if not self.config_file.exists():
                    # Try .yaml extension if .json was given, or vice versa
                    alt_file = self.config_file.with_suffix('.yaml' if self.config_file.suffix == '.json' else '.json')
                    if alt_file.exists():
                        config = load_vessel_info(str(alt_file))
                        if config:
                            return config

                # If still no config, create default
                print(f"Configuration file not found: {self.config_file}")
                print("Creating default configuration...")
                return self.create_default_config()

            # Fallback to default if load_vessel_info returned None
            print(f"Configuration file not found: {self.config_file}")
            print("Creating default configuration...")
            return self.create_default_config()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def create_default_config(self) -> dict[str, Any]:
        """Create a default vessel configuration."""
        return {
            "name": "S.V. Vessel",
            "mmsi": "123456789",
            "marinetraffic_ship_id": "",
            "uscg_number": "1234567",
            "hull_number": "ABC12345",
            "signalk": {"host": "192.168.1.100", "port": "3000", "protocol": "https"},
        }

    def save_config(self) -> None:
        """Save vessel configuration to YAML or JSON file."""
        try:
            # Use utils.save_vessel_info for YAML/JSON support
            if save_vessel_info(self.config, str(self.config_file)):
                print("Configuration saved successfully!")
            else:
                print("Error: Failed to save configuration")
                sys.exit(1)
        except Exception as e:
            print(f"Error saving configuration: {e}")
            sys.exit(1)

    def get_input(self, prompt: str, current_value: str = "") -> str:
        """Get user input with current value as default."""
        if current_value:
            user_input = input(f"{prompt} ({current_value}): ").strip()
            return user_input if user_input else current_value
        else:
            return input(f"{prompt}: ").strip()

    def run(self) -> None:
        """Run the step-by-step configuration wizard."""
        print("Welcome to the Vessel Configuration Wizard!")
        print(f"Configuration file: {self.config_file}")
        print("\nPress Enter to keep current values, or type new values.")
        print("=" * 60)

        # Vessel Information
        print("\n--- Vessel Information ---")
        self.config["name"] = self.get_input("Vessel name", self.config.get("name", ""))

        self.config["mmsi"] = self.get_input(
            "MMSI (Maritime Mobile Service Identity)", self.config.get("mmsi", "")
        )

        self.config["marinetraffic_ship_id"] = self.get_input(
            "MarineTraffic ship ID (find at marinetraffic.com, e.g. shipid:XXXXXXX in the URL)",
            self.config.get("marinetraffic_ship_id", ""),
        )

        self.config["uscg_number"] = self.get_input(
            "USCG number", self.config.get("uscg_number", "")
        )

        self.config["hull_number"] = self.get_input(
            "Hull number", self.config.get("hull_number", "")
        )

        # SignalK Configuration
        print("\n--- SignalK Configuration ---")

        # Ensure signalk section exists
        if "signalk" not in self.config:
            self.config["signalk"] = {}

        self.config["signalk"]["host"] = self.get_input(
            "SignalK host IP address", self.config["signalk"].get("host", "")
        )

        self.config["signalk"]["port"] = self.get_input(
            "SignalK port", self.config["signalk"].get("port", "")
        )

        protocol = self.get_input(
            "SignalK protocol (http/https)",
            self.config["signalk"].get("protocol", "https"),
        )

        # Validate protocol
        if protocol.lower() not in ["http", "https"]:
            print("Invalid protocol. Using 'https' as default.")
            protocol = "https"

        self.config["signalk"]["protocol"] = protocol.lower()

        # Show final configuration
        print("\n" + "=" * 60)
        print("FINAL CONFIGURATION")
        print("=" * 60)
        print(json.dumps(self.config, indent=2))
        print("=" * 60)

        # Ask to save
        save = input("\nSave this configuration? (y/N): ").strip().lower()
        if save in ["y", "yes"]:
            self.save_config()
            print("Configuration saved successfully!")
        else:
            print("Configuration not saved.")


def main():
    """Main function."""
    wizard = VesselConfigWizard()
    wizard.run()


if __name__ == "__main__":
    main()
