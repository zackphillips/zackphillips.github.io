#!/usr/bin/env python3
"""
Playwright test runner script for the vessel tracker dashboard.

This script sets up the test environment and runs Playwright tests
for the JavaScript components in index.html.
"""

import subprocess
import sys
import os
from pathlib import Path


def check_uv_installed():
    """Check if uv is installed and available."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ uv found: {result.stdout.strip()}")
            return True
        else:
            print("✗ uv is not working properly")
            return False
    except FileNotFoundError:
        print("✗ uv is not installed")
        return False


def install_playwright_browsers():
    """Install Playwright browsers."""
    print("Installing Playwright browsers...")
    try:
        result = subprocess.run(
            ["uv", "run", "playwright", "install"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Playwright browsers installed successfully")
            return True
        else:
            print(f"✗ Failed to install Playwright browsers: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error installing Playwright browsers: {e}")
        return False


def run_playwright_tests():
    """Run the Playwright tests."""
    print("Running Playwright tests...")
    
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Change to project root
    os.chdir(project_root)
    
    try:
        # Run the tests with verbose output
        result = subprocess.run([
            "uv", "run", "pytest",
            "tests/test_vessel_tracker_playwright.py",
            "-v",
            "-m", "playwright",
            "--tb=short"
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("✓ All Playwright tests passed!")
            return True
        else:
            print(f"✗ Some Playwright tests failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ Error running Playwright tests: {e}")
        return False


def main():
    """Main function to run the Playwright test suite."""
    print("🚢 Vessel Tracker - Playwright Test Runner")
    print("=" * 50)
    
    # Check if uv is installed
    if not check_uv_installed():
        print("\nPlease install uv first:")
        print("curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    
    # Install Playwright browsers
    if not install_playwright_browsers():
        print("\nFailed to install Playwright browsers.")
        sys.exit(1)
    
    # Run the tests
    if not run_playwright_tests():
        print("\nPlaywright tests failed.")
        sys.exit(1)
    
    print("\n🎉 All tests completed successfully!")


if __name__ == "__main__":
    main()

