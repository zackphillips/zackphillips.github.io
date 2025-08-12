#!/usr/bin/env python3
"""
Interactive vessel configuration wizard.
Steps through each field sequentially with defaults shown in parentheses.
"""

import json
import sys
from pathlib import Path
from typing import Any


class VesselConfigWizard:
    def __init__(self, config_file: Path = Path("data/vessel/info.json")):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Load vessel configuration from JSON file."""
        try:
            if not self.config_file.exists():
                print(f"Configuration file not found: {self.config_file}")
                print("Creating default configuration...")
                return self.create_default_config()

            with open(self.config_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def create_default_config(self) -> dict[str, Any]:
        """Create a default vessel configuration."""
        return {
            "name": "S.V. Vessel",
            "mmsi": "123456789",
            "uscg_number": "1234567",
            "hull_number": "ABC12345",
            "signalk": {"host": "192.168.1.100", "port": "3000", "protocol": "https"},
        }

    def save_config(self) -> None:
        """Save vessel configuration to JSON file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            print("Configuration saved successfully!")
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
