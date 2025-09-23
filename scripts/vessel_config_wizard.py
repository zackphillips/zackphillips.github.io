#!/usr/bin/env python3
"""
Interactive vessel configuration wizard.
Steps through each field sequentially with defaults shown in parentheses.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests


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

    def test_existing_token(self) -> bool:
        """Test if the existing token is valid."""
        token = self.config["signalk"].get("token")
        if not token:
            print("No token to test.")
            return False

        host = self.config["signalk"].get("host", "192.168.8.50")
        port = self.config["signalk"].get("port", "3000")

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"http://{host}:{port}/signalk/v1/api/vessels/self",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                print("[OK] Token is valid and working!")
                return True
            else:
                print(f"[ERROR] Token test failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[ERROR] Error testing token: {e}")
            return False

    def request_new_token(self) -> None:
        """Request a new SignalK token."""
        print("\nRequesting new SignalK token...")
        print("This will open a browser window for approval.")

        host = self.config["signalk"].get("host", "192.168.8.50")
        port = self.config["signalk"].get("port", "3000")

        try:
            # Run the token request script
            result = subprocess.run(
                [
                    "python3",
                    "scripts/request_signalk_token.py",
                    "--host",
                    host,
                    "--port",
                    port,
                    "--timeout",
                    "60",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("[SUCCESS] Token request completed!")
                # The token should now be saved to info.json
                # Reload the config to get the new token
                self.config = self.load_config()
            else:
                print("[ERROR] Token request failed:")
                print(result.stderr)
                print("\nYou can manually request a token by running:")
                print(
                    f"python3 scripts/request_signalk_token.py --host {host} --port {port}"
                )

        except subprocess.TimeoutExpired:
            print("[ERROR] Token request timed out.")
            print("Please approve the request in your browser and try again.")
        except Exception as e:
            print(f"[ERROR] Error requesting token: {e}")
            print("You can manually request a token by running:")
            print(
                f"python3 scripts/request_signalk_token.py --host {host} --port {port}"
            )

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

        # SignalK Token Management
        print("\n--- SignalK Token Management ---")

        # Check if token exists
        existing_token = self.config["signalk"].get("token")
        if existing_token:
            print(f"Existing token found: {existing_token[:20]}...")
            token_action = self.get_input(
                "Token action (keep/regenerate/test)", "keep"
            ).lower()

            if token_action in ["regenerate", "new"]:
                self.request_new_token()
            elif token_action == "test":
                self.test_existing_token()
        else:
            print("No SignalK token found.")
            create_token = self.get_input("Create SignalK token? (y/N)", "y").lower()
            if create_token in ["y", "yes"]:
                self.request_new_token()

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
