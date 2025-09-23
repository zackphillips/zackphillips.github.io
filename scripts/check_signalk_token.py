#!/usr/bin/env python3
"""
SignalK Token Checker Script

This script checks if a SignalK access token exists and is valid.
Used by Makefile targets to ensure token is available before running sensor operations.
"""

import json
import os
import sys

import requests


def check_token_exists(info_json_path="data/vessel/info.json"):
    """Check if a valid token exists in info.json."""
    try:
        if not os.path.exists(info_json_path):
            return False, "info.json not found"

        with open(info_json_path) as f:
            info_data = json.load(f)

        token = info_data.get("signalk", {}).get("token")
        if not token:
            return False, "No token found in info.json"

        # Test if token is valid
        host = info_data.get("signalk", {}).get("host", "192.168.8.50")
        port = info_data.get("signalk", {}).get("port", "3000")

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
                return True, "Token is valid"
            else:
                return False, f"Token test failed: {response.status_code}"

        except Exception as e:
            return False, f"Error testing token: {e}"

    except Exception as e:
        return False, f"Error reading info.json: {e}"


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Check SignalK token")
    parser.add_argument(
        "--info-json", default="data/vessel/info.json", help="Path to info.json"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Quiet output (exit code only)"
    )

    args = parser.parse_args()

    token_valid, message = check_token_exists(args.info_json)

    if not args.quiet:
        if token_valid:
            print("[OK] SignalK token is valid")
        else:
            print(f"[ERROR] SignalK token issue: {message}")
            print("\nTo create a token, run:")
            print("  python3 scripts/request_signalk_token.py")
            print("\nOr run the vessel configuration wizard:")
            print("  make config")

    sys.exit(0 if token_valid else 1)


if __name__ == "__main__":
    main()
