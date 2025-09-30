#!/usr/bin/env python3
"""
SignalK Access Token Request Script

This script requests an access token from SignalK server using the device access request API.
The token can then be used to authenticate WebSocket connections and API calls.
"""

import json
import os
import sys
import time

import requests


class SignalKTokenRequester:
    def __init__(self, host="192.168.8.50", port=3000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.token = None

    def request_device_access(
        self,
        device_name="I2C Sensor Publisher",
        device_description="I2C sensors to SignalK data publisher",
    ):
        """Request device access from SignalK server."""
        print(f"Requesting device access from SignalK server at {self.base_url}")

        # Device access request payload
        import uuid

        payload = {
            "clientId": f"i2c-sensors-{uuid.uuid4().hex[:8]}",
            "description": device_description,
            "permissions": [
                "admin:skServer:read",
                "admin:skServer:write",
                "vessels:read",
                "vessels:write",
                "signalk:read",
                "signalk:write",
            ],
        }

        try:
            # Send device access request
            response = requests.post(
                f"{self.base_url}/signalk/v1/access/requests",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code in [200, 202]:
                data = response.json()
                print("[OK] Device access request sent successfully")
                print(f"Request ID: {data.get('requestId', 'N/A')}")
                print(f"Status: {data.get('state', data.get('status', 'N/A'))}")
                return data
            elif response.status_code == 400:
                # Check if it's because request already exists
                data = response.json()
                if "already requested access" in data.get("message", ""):
                    print("[INFO] Device access request already exists")
                    print(f"Request ID: {data.get('requestId', 'N/A')}")
                    print(f"Status: {data.get('state', 'N/A')}")
                    return data
                else:
                    print(f"[ERROR] Bad request: {response.status_code}")
                    print(f"Response: {response.text}")
                    return None
            else:
                print(
                    f"[ERROR] Failed to send device access request: {response.status_code}"
                )
                print(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error connecting to SignalK server: {e}")
            return None

    def check_request_status(self, request_id):
        """Check the status of a device access request."""
        try:
            response = requests.get(
                f"{self.base_url}/signalk/v1/requests/{request_id}", timeout=10
            )
            print(response.text)
            print(response.status_code)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"[ERROR] Failed to check request status: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error checking request status: {e}")
            return None

    def wait_for_approval(self, request_id, timeout=300):
        """Wait for device access request to be approved."""
        print(f"Waiting for approval (timeout: {timeout}s)...")
        print("Please approve the request in the SignalK web interface:")
        print(f"  {self.base_url}/admin/#/security/accessrequests")

        start_time = time.time()
        while time.time() - start_time < timeout:
            status_data = self.check_request_status(request_id)
            if status_data:
                status = status_data.get("state", "UNKNOWN")
                if status == "COMPLETED":
                    token = status_data.get("accessRequest").get("token", None)
                    if token:
                        self.token = token
                        print("[OK] Access token received!")
                        return token
                elif status == "REJECTED":
                    print("[ERROR] Request was rejected")
                    return None

            time.sleep(2)

        print("[ERROR] Timeout waiting for approval")
        return None

    def test_token(self, token):
        """Test the access token by making an authenticated request."""
        print("Testing access token...")

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = requests.get(
                f"{self.base_url}/signalk/v1/api/vessels/self",
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                print("[OK] Token is valid and working")
                return True
            else:
                print(f"[ERROR] Token test failed: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error testing token: {e}")
            return False

    def save_token_to_file(self, token, filename="signalk_token.txt"):
        """Save the access token to a file."""
        try:
            with open(filename, "w") as f:
                f.write(token)
            print(f"[OK] Token saved to {filename}")
            return True
        except Exception as e:
            print(f"[ERROR] Error saving token: {e}")
            return False

    def save_token_to_info_json(self, token, info_json_path="data/vessel/info.json"):
        """Save the access token to info.json file."""
        try:
            # Read existing info.json
            if os.path.exists(info_json_path):
                with open(info_json_path) as f:
                    info_data = json.load(f)
            else:
                info_data = {}

            # Ensure signalk section exists
            if "signalk" not in info_data:
                info_data["signalk"] = {}

            # Add token
            info_data["signalk"]["token"] = token

            # Write back to file
            with open(info_json_path, "w") as f:
                json.dump(info_data, f, indent=2)

            print(f"[OK] Token saved to {info_json_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Error saving token to info.json: {e}")
            return False

    def get_token_from_file(self, filename="signalk_token.txt"):
        """Load access token from file."""
        try:
            with open(filename) as f:
                token = f.read().strip()
            if token:
                print(f"[OK] Token loaded from {filename}")
                return token
            return None
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"[ERROR] Error loading token: {e}")
            return None

    def get_token_from_info_json(self, info_json_path="data/vessel/info.json"):
        """Load access token from info.json file."""
        try:
            if not os.path.exists(info_json_path):
                return None

            with open(info_json_path) as f:
                info_data = json.load(f)

            token = info_data.get("signalk", {}).get("token")
            if token:
                print(f"[OK] Token loaded from {info_json_path}")
                return token
            return None
        except Exception as e:
            print(f"[ERROR] Error loading token from info.json: {e}")
            return None

    def check_token_exists(self, info_json_path="data/vessel/info.json"):
        """Check if a valid token exists in info.json."""
        token = self.get_token_from_info_json(info_json_path)
        if token:
            # Test if token is valid
            if self.test_token(token):
                return token
            else:
                print("[WARNING] Token exists but is invalid")
                return None
        return None


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
    import argparse

    parser = argparse.ArgumentParser(description="SignalK token management")
    parser.add_argument("--host", default="192.168.8.50", help="SignalK server host")
    parser.add_argument("--port", type=int, default=3000, help="SignalK server port")
    parser.add_argument(
        "--device-name", default="I2C Sensor Publisher", help="Device name"
    )
    parser.add_argument(
        "--device-description",
        default="I2C sensors to SignalK data publisher",
        help="Device description",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Approval timeout in seconds"
    )
    parser.add_argument(
        "--token-file", default="signalk_token.txt", help="Token file path"
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Only test existing token"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check if token exists and is valid"
    )
    parser.add_argument(
        "--info-json", default="data/vessel/info.json", help="Path to info.json"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Quiet output (exit code only)"
    )

    args = parser.parse_args()

    # If --check flag is provided, run the check functionality
    if args.check:
        token_valid, message = check_token_exists(args.info_json)

        if not args.quiet:
            if token_valid:
                print("[OK] SignalK token is valid")
            else:
                print(f"[ERROR] SignalK token issue: {message}")
                print("\nTo create a token, run:")
                print("  python3 scripts/signalk_token_management.py")
                print("\nOr run the vessel configuration wizard:")
                print("  make config")

        sys.exit(0 if token_valid else 1)

    requester = SignalKTokenRequester(args.host, args.port)

    if args.test_only:
        # Test existing token
        token = requester.get_token_from_file(args.token_file)
        if token:
            if requester.test_token(token):
                print("[OK] Existing token is valid")
                sys.exit(0)
            else:
                print("[ERROR] Existing token is invalid")
                sys.exit(1)
        else:
            print("[ERROR] No token file found")
            sys.exit(1)

    # Check if we already have a valid token in info.json
    existing_token = requester.check_token_exists()
    if existing_token:
        print("[OK] Using existing valid token from info.json")
        print(f"Token: {existing_token}")
        sys.exit(0)

    # Request new token
    request_data = requester.request_device_access(
        args.device_name, args.device_description
    )
    if not request_data:
        print("[ERROR] Failed to send device access request")
        sys.exit(1)

    request_id = request_data.get("requestId")
    if not request_id:
        print("[ERROR] No request ID received")
        sys.exit(1)

    # Wait for approval
    token = requester.wait_for_approval(request_id, args.timeout)
    if not token:
        print("[ERROR] Failed to get access token")
        sys.exit(1)

    # Test the token
    if not requester.test_token(token):
        print("[ERROR] Token test failed")
        sys.exit(1)

    # Save the token to info.json
    if requester.save_token_to_info_json(token):
        print("\n[SUCCESS] Access token obtained and saved to info.json.")
        print(f"Token: {token}")
        print("Use this token in your WebSocket connections:")
        print(
            f"  ws://{args.host}:{args.port}/signalk/v1/stream?stream=delta&token={token}"
        )
    else:
        print("\n[SUCCESS] Access token obtained.")
        print(f"Token: {token}")
        print("(Token not saved to info.json)")


if __name__ == "__main__":
    main()
