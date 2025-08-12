from playwright.sync_api import Playwright, sync_playwright, expect
import pytest


def test_basic_playwright_setup():
    """Basic test to ensure Playwright is working."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://example.com")
        expect(page).to_have_title("Example Domain")
        browser.close()


# Playwright configuration for pytest-playwright
def pytest_configure(config):
    """Configure Playwright for pytest."""
    config.addinivalue_line(
        "markers", "playwright: mark test as a Playwright test"
    )


# Browser configuration
BROWSER_CONFIG = {
    "chromium": {
        "browser_type": "chromium",
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor"
        ]
    },
    "firefox": {
        "browser_type": "firefox",
        "headless": True
    },
    "webkit": {
        "browser_type": "webkit",
        "headless": True
    }
}


# Test data configuration
TEST_DATA_CONFIG = {
    "vessel_info": {
        "name": "Test Vessel",
        "mmsi": "123456789",
        "uscg_number": "TEST123",
        "hull_number": "TEST456",
        "signalk": {
            "host": "localhost",
            "port": "3000",
            "protocol": "http"
        }
    },
    "tide_stations": {
        "stations": [
            {
                "id": "9414290",
                "name": "San Francisco",
                "lat": 37.806,
                "lon": -122.465
            }
        ]
    },
    "telemetry": {
        "navigation": {
            "position": {
                "value": {"latitude": 37.806, "longitude": -122.465},
                "timestamp": "2024-01-01T12:00:00Z"
            },
            "courseOverGroundTrue": {"value": 0.7853981633974483},
            "speedOverGround": {"value": 2.572222222222222},
            "speedThroughWater": {"value": 2.572222222222222}
        },
        "environment": {
            "wind": {
                "speedTrue": {"value": 5.144444444444444},
                "angleTrue": {"value": 1.5707963267948966}
            },
            "water": {"temperature": {"value": 288.15}}
        },
        "electrical": {
            "batteries": {
                "house": {
                    "voltage": {"value": 12.5},
                    "current": {"value": 0},
                    "power": {"value": 0},
                    "capacity": {
                        "stateOfCharge": {"value": 0.8},
                        "timeRemaining": {"value": 36000}
                    }
                }
            }
        }
    }
}

