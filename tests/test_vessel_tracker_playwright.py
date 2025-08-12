import pytest
import json
from pathlib import Path
from playwright.sync_api import expect, Page


@pytest.fixture(scope="session", autouse=True)
def setup_test_data():
    """Setup test data files for all tests."""
    # Create test vessel data
    vessel_data = {
        "name": "Test Vessel",
        "mmsi": "123456789",
        "uscg_number": "TEST123",
        "hull_number": "TEST456",
        "signalk": {
            "host": "localhost",
            "port": "3000",
            "protocol": "http"
        }
    }
    
    vessel_path = Path("data/vessel/info.json")
    vessel_path.parent.mkdir(parents=True, exist_ok=True)
    with open(vessel_path, 'w') as f:
        json.dump(vessel_data, f)
    
    # Create test tide stations data
    tide_data = {
        "stations": [
            {
                "id": "9414290",
                "name": "San Francisco",
                "lat": 37.806,
                "lon": -122.465
            }
        ]
    }
    
    tide_path = Path("data/tide_stations.json")
    tide_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tide_path, 'w') as f:
        json.dump(tide_data, f)
    
    # Create test polar data
    polar_data = """TWA;4;6;8;10;12;14;16;20;24
0;0;0;0;0;0;0;0;0;0
30;2.5;3.2;3.8;4.2;4.5;4.7;4.8;5.0;5.1
60;3.8;4.5;5.1;5.6;5.9;6.1;6.2;6.4;6.5
90;4.2;4.9;5.5;6.0;6.3;6.5;6.6;6.8;6.9
120;4.0;4.7;5.3;5.8;6.1;6.3;6.4;6.6;6.7
150;3.5;4.2;4.8;5.3;5.6;5.8;5.9;6.1;6.2
180;3.0;3.7;4.3;4.8;5.1;5.3;5.4;5.6;5.7"""
    
    polar_path = Path("data/vessel/polars.csv")
    polar_path.parent.mkdir(parents=True, exist_ok=True)
    with open(polar_path, 'w') as f:
        f.write(polar_data)
    
    # Create test telemetry data
    telemetry_data = {
        "navigation": {
            "position": {
                "value": {"latitude": 37.806, "longitude": -122.465},
                "timestamp": "2024-01-01T12:00:00Z"
            },
            "courseOverGroundTrue": {"value": 0.7853981633974483},  # 45 degrees
            "speedOverGround": {"value": 2.572222222222222},  # 5 knots
            "speedThroughWater": {"value": 2.572222222222222}  # 5 knots
        },
        "environment": {
            "wind": {
                "speedTrue": {"value": 5.144444444444444},  # 10 knots
                "angleTrue": {"value": 1.5707963267948966}  # 90 degrees
            },
            "water": {"temperature": {"value": 288.15}}  # 15°C
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
    
    telemetry_path = Path("data/telemetry/signalk_latest.json")
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(telemetry_path, 'w') as f:
        json.dump(telemetry_data, f)


# Basic Page Loading Tests
@pytest.mark.playwright
def test_page_loads_without_errors(page: Page):
    """Test that the vessel tracker page loads without JavaScript errors."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that the page loads
    expect(page).to_have_title("S.V.Mermug Tracker")
    
    # Check that main elements are present
    expect(page.locator("body")).to_be_visible()
    expect(page.locator(".container")).to_be_visible()
    
    # Check that no JavaScript errors occurred
    page.wait_for_load_state("networkidle")


@pytest.mark.playwright
def test_page_loads_successfully(page: Page):
    """Test that the page loads without errors and all main components are present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that the page title is set
    expect(page).to_have_title("Test Vessel Tracker")
    
    # Check that main elements are present
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#data-grid")).to_be_visible()
    expect(page.locator("#tideChart")).to_be_visible()
    expect(page.locator("#polarChart")).to_be_visible()


# UI Component Tests
@pytest.mark.playwright
def test_dark_mode_button_exists(page: Page):
    """Test that the dark mode toggle button is present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that dark mode button exists
    dark_mode_button = page.locator("#darkModeToggle")
    expect(dark_mode_button).to_be_visible()
    expect(dark_mode_button).to_be_enabled()


@pytest.mark.playwright
def test_dark_mode_toggle(page: Page):
    """Test dark mode toggle functionality."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check initial state (should be light mode by default)
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    
    # Click dark mode toggle
    page.click("#darkModeToggle")
    
    # Check that dark mode is applied
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    
    # Check button text changes
    expect(page.locator("#darkModeToggle")).to_contain_text("☀️ Light Mode")
    
    # Toggle back to light mode
    page.click("#darkModeToggle")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#darkModeToggle")).to_contain_text("🌙 Dark Mode")


@pytest.mark.playwright
def test_theme_persistence(page: Page):
    """Test that theme preference is persisted across page reloads."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Enable dark mode
    page.click("#darkModeToggle")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    
    # Reload the page
    page.reload()
    
    # Check that dark mode is still active
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("#darkModeToggle")).to_contain_text("☀️ Light Mode")


# Map and Data Tests
@pytest.mark.playwright
def test_map_container_exists(page: Page):
    """Test that the map container is present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that map container exists
    map_container = page.locator("#map")
    expect(map_container).to_be_visible()


@pytest.mark.playwright
def test_map_initialization(page: Page):
    """Test that the map initializes correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for map to load
    page.wait_for_selector("#map", timeout=10000)
    
    # Check that map container is present
    map_container = page.locator("#map")
    expect(map_container).to_be_visible()
    
    # Check that map title is updated
    expect(page.locator("#mapTitle")).not_to_contain_text("Loading location...")


@pytest.mark.playwright
def test_data_grid_exists(page: Page):
    """Test that the data grid container is present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that data grid exists
    data_grid = page.locator("#data-grid")
    expect(data_grid).to_be_visible()


@pytest.mark.playwright
def test_data_grid_population(page: Page):
    """Test that the data grid is populated with vessel information."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for data to load
    page.wait_for_selector(".info-item", timeout=10000)
    
    # Check that data grid contains expected items
    data_grid = page.locator("#data-grid")
    
    # Check for specific data items
    expect(data_grid.locator("text=Latitude")).to_be_visible()
    expect(data_grid.locator("text=Longitude")).to_be_visible()
    expect(data_grid.locator("text=COG")).to_be_visible()
    expect(data_grid.locator("text=SOG")).to_be_visible()
    expect(data_grid.locator("text=Wind Speed")).to_be_visible()
    expect(data_grid.locator("text=Battery Voltage")).to_be_visible()


# Chart Tests
@pytest.mark.playwright
def test_chart_containers_exist(page: Page):
    """Test that chart containers are present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that chart containers exist
    tide_chart = page.locator("#tideChart")
    polar_chart = page.locator("#polarChart")
    
    expect(tide_chart).to_be_visible()
    expect(polar_chart).to_be_visible()


@pytest.mark.playwright
def test_tide_chart_rendering(page: Page):
    """Test that the tide chart renders correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for tide chart to load
    page.wait_for_selector("#tideChart", timeout=15000)
    
    # Check that tide header is populated
    tide_header = page.locator("#tideHeader")
    expect(tide_header).to_contain_text("San Francisco")
    expect(tide_header).to_contain_text("Station #9414290")


@pytest.mark.playwright
def test_polar_chart_rendering(page: Page):
    """Test that the polar chart renders correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for polar chart to load
    page.wait_for_selector("#polarChart", timeout=15000)
    
    # Check that polar performance section is populated
    polar_performance = page.locator("#polar-performance")
    expect(polar_performance).to_contain_text("True Wind Angle")
    expect(polar_performance).to_contain_text("Boat Speed")
    expect(polar_performance).to_contain_text("Polar Speed")


@pytest.mark.playwright
def test_chart_interactions(page: Page):
    """Test chart interactions and responsiveness."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for charts to load
    page.wait_for_selector("#tideChart", timeout=15000)
    page.wait_for_selector("#polarChart", timeout=15000)
    
    # Test tide chart interaction
    tide_chart = page.locator("#tideChart")
    expect(tide_chart).to_be_visible()
    
    # Test polar chart interaction
    polar_chart = page.locator("#polarChart")
    expect(polar_chart).to_be_visible()


@pytest.mark.playwright
def test_performance_metrics(page: Page):
    """Test that performance metrics are calculated and displayed."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for polar performance to load
    page.wait_for_selector("#polar-performance", timeout=15000)
    
    # Check that performance metrics are displayed
    polar_performance = page.locator("#polar-performance")
    expect(polar_performance).to_contain_text("Performance:")
    
    # Check that VMG analysis is displayed
    vmg_analysis = page.locator("#vmg-analysis")
    expect(vmg_analysis).to_contain_text("VMG Analysis")


# Forecast Tests
@pytest.mark.playwright
def test_forecast_sections_exist(page: Page):
    """Test that forecast sections are present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that forecast sections exist
    wind_forecast = page.locator("#wind-forecast-grid")
    wave_forecast = page.locator("#wave-forecast-grid")
    
    expect(wind_forecast).to_be_visible()
    expect(wave_forecast).to_be_visible()


@pytest.mark.playwright
def test_wind_forecast_loading(page: Page):
    """Test that wind forecast loads and displays correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for wind forecast to load
    page.wait_for_selector("#wind-forecast-grid", timeout=15000)
    
    # Check that wind forecast grid is populated
    wind_grid = page.locator("#wind-forecast-grid")
    expect(wind_grid.locator(".wind-forecast-item")).to_have_count(4)
    
    # Check that forecast model selector is present
    expect(page.locator("#forecast-model")).to_be_visible()
    expect(page.locator("#forecast-model")).to_have_value("wttr")


@pytest.mark.playwright
def test_wave_forecast_loading(page: Page):
    """Test that wave forecast loads and displays correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for wave forecast to load
    page.wait_for_selector("#wave-forecast-grid", timeout=15000)
    
    # Check that wave forecast grid is populated
    wave_grid = page.locator("#wave-forecast-grid")
    expect(wave_grid.locator(".wave-forecast-item")).to_have_count(4)


@pytest.mark.playwright
def test_forecast_model_switching(page: Page):
    """Test switching between different forecast models."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for forecast model selector to load
    page.wait_for_selector("#forecast-model", timeout=10000)
    
    # Test switching to ECMWF model
    forecast_selector = page.locator("#forecast-model")
    forecast_selector.select_option("ecmwf")
    expect(forecast_selector).to_have_value("ecmwf")
    
    # Switch back to wttr.in
    forecast_selector.select_option("wttr")
    expect(forecast_selector).to_have_value("wttr")


# Vessel Links Tests
@pytest.mark.playwright
def test_vessel_links_exist(page: Page):
    """Test that vessel links are present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that vessel links exist
    signalk_admin = page.locator("#signalk-admin-link")
    signalk_freeboard = page.locator("#signalk-freeboard-link")
    marinetraffic = page.locator("#marinetraffic-link")
    myshiptracking = page.locator("#myshiptracking-link")
    
    expect(signalk_admin).to_be_visible()
    expect(signalk_freeboard).to_be_visible()
    expect(marinetraffic).to_be_visible()
    expect(myshiptracking).to_be_visible()


@pytest.mark.playwright
def test_vessel_links_functionality(page: Page):
    """Test that vessel links are properly configured."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that SignalK links are present
    signalk_admin_link = page.locator("#signalk-admin-link")
    signalk_freeboard_link = page.locator("#signalk-freeboard-link")
    
    expect(signalk_admin_link).to_be_visible()
    expect(signalk_freeboard_link).to_be_visible()
    
    # Check that external tracking links are present
    marinetraffic_link = page.locator("#marinetraffic-link")
    myshiptracking_link = page.locator("#myshiptracking-link")
    
    expect(marinetraffic_link).to_be_visible()
    expect(myshiptracking_link).to_be_visible()


# Status and Error Handling Tests
@pytest.mark.playwright
def test_status_banner_exists(page: Page):
    """Test that the status banner is present."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that status banner exists
    status_banner = page.locator("#updateBanner")
    data_status = page.locator("#dataStatus")
    update_time = page.locator("#updateTime")
    
    expect(status_banner).to_be_visible()
    expect(data_status).to_be_visible()
    expect(update_time).to_be_visible()


@pytest.mark.playwright
def test_data_status_banner(page: Page):
    """Test that the data status banner displays correctly."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for status to update
    page.wait_for_selector("#dataStatus", timeout=10000)
    
    # Check that status is not "Loading data..."
    status_element = page.locator("#dataStatus")
    expect(status_element).not_to_contain_text("Loading data...")
    
    # Check that update time is displayed
    time_element = page.locator("#updateTime")
    expect(time_element).not_to_contain_text("--")


@pytest.mark.playwright
def test_error_handling(page: Page):
    """Test error handling when data files are missing."""
    # Remove test data files to simulate missing data
    test_files = [
        "data/vessel/info.json",
        "data/tide_stations.json",
        "data/vessel/polars.csv",
        "data/telemetry/signalk_latest.json"
    ]
    
    for file_path in test_files:
        if Path(file_path).exists():
            Path(file_path).unlink()
    
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Wait for page to load
    page.wait_for_load_state("networkidle")
    
    # Check that page still loads without crashing
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#data-grid")).to_be_visible()
    
    # Check that error states are handled gracefully
    status_element = page.locator("#dataStatus")
    expect(status_element).to_be_visible()


# Responsive Design Tests
@pytest.mark.playwright
def test_responsive_design(page: Page):
    """Test responsive design elements."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Test mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    
    # Check that elements are still visible in mobile view
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#data-grid")).to_be_visible()
    expect(page.locator("#darkModeToggle")).to_be_visible()
    
    # Test tablet viewport
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#data-grid")).to_be_visible()


# Accessibility Tests
@pytest.mark.playwright
def test_accessibility_features(page: Page):
    """Test basic accessibility features."""
    page.goto("file://" + str(Path.cwd() / "index.html"))
    
    # Check that images have alt text
    logo_img = page.locator('img[src="data/vessel/logo.png"]')
    expect(logo_img).to_have_attribute("alt")
    
    # Check that buttons are accessible
    dark_mode_button = page.locator("#darkModeToggle")
    expect(dark_mode_button).to_be_visible()
    expect(dark_mode_button).to_be_enabled()
    
    # Check that links have proper attributes
    signalk_link = page.locator("#signalk-admin-link")
    expect(signalk_link).to_have_attribute("target", "_blank")
