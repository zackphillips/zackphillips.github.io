# Playwright Testing Guide

This document explains how to use Playwright for testing the JavaScript components in the vessel tracker dashboard.

## Overview

Playwright is a browser automation tool that allows us to test the vessel tracker dashboard in real browsers. This ensures that all JavaScript functionality works correctly across different browsers and environments.

## Prerequisites

1. **uv**: The Python package manager (install with `make check-uv`)
2. **Python 3.12+**: Required for the project
3. **Git**: For version control

## Quick Start

### 1. Install Dependencies

```bash
# Check if uv is installed
make check-uv

# Install Playwright browsers
uv run playwright install
```

### 2. Run Tests

```bash
# Run all Playwright tests
make test-playwright

# Run all tests (unit + Playwright)
make test-all

# Run specific test files
uv run pytest tests/test_vessel_tracker_playwright.py -v -m playwright
```

## Test Structure

### Vessel Tracker Tests (`tests/test_vessel_tracker_playwright.py`)
- **Purpose**: Comprehensive testing of all vessel tracker dashboard features
- **Test Categories**:
  - **Basic Page Loading**: Page loads without errors, main components present
  - **UI Components**: Dark mode toggle, theme persistence
  - **Map and Data**: Map initialization, data grid population
  - **Charts**: Tide chart, polar chart rendering and interactions
  - **Forecasts**: Wind and wave forecast loading, model switching
  - **Vessel Links**: External links and SignalK integration
  - **Status and Error Handling**: Data status banner, error handling
  - **Responsive Design**: Mobile and tablet viewport testing
  - **Accessibility**: Basic accessibility features

## Test Data

The tests automatically create test data files:

- `data/vessel/info.json`: Vessel configuration
- `data/tide_stations.json`: Tide station data
- `data/vessel/polars.csv`: Polar performance data
- `data/telemetry/signalk_latest.json`: Telemetry data

## Configuration

### Playwright Configuration (`playwright.config.toml`)
- **Timeouts**: Global timeouts for tests and actions
- **Browsers**: Support for Chromium, Firefox, and WebKit
- **Reporters**: HTML, JSON, and JUnit reporters
- **Retries**: Automatic retry of failed tests

### Test Configuration (`pytest.ini`)
- **Markers**: `@pytest.mark.playwright` for Playwright tests
- **Options**: Verbose output, short tracebacks
- **Filtering**: Warning filters and test discovery

## Running Tests

### Command Line Options

```bash
# Run all Playwright tests
uv run pytest -m playwright

# Run specific test file
uv run pytest tests/test_vessel_tracker_playwright.py -v

# Run with specific browser
uv run pytest --browser=firefox -m playwright

# Run with headed mode (see browser)
uv run pytest --headed -m playwright

# Run with debug mode
uv run pytest --headed --debug -m playwright
```

### Test Scripts

```bash
# Use the test runner script
python scripts/run_playwright_tests.py

# Use Makefile targets
make test-playwright
make test-all
```

## Continuous Integration

### GitHub Actions (`/.github/workflows/playwright-tests.yml`)
- **Triggers**: Push to main/develop, pull requests
- **Environment**: Ubuntu with Python 3.12
- **Browsers**: Chromium, Firefox, WebKit
- **Artifacts**: Test reports and screenshots

### Local CI
```bash
# Run tests locally as CI would
uv run playwright install --with-deps
uv run pytest tests/test_vessel_tracker_playwright.py -v -m playwright
```

## Debugging

### View Test Results
```bash
# Open HTML report
uv run playwright show-report

# View test results directory
ls test-results/
```

### Debug Failed Tests
```bash
# Run with headed mode and debug
uv run pytest --headed --debug tests/test_vessel_tracker_playwright.py::test_dark_mode_toggle

# Run with slow motion
uv run pytest --headed --slowmo=1000 tests/test_vessel_tracker_playwright.py
```

### Common Issues

1. **Browser Installation**: Run `uv run playwright install`
2. **File Permissions**: Ensure test data files are writable
3. **Network Issues**: Some tests require internet access for external APIs
4. **Timeout Issues**: Increase timeouts in `playwright.config.toml`

## Best Practices

### Writing Tests
1. **Use descriptive test names**: Clear, specific test names
2. **Test one thing at a time**: Each test should verify one feature
3. **Use proper selectors**: Prefer data attributes over CSS classes
4. **Handle async operations**: Use `wait_for_selector` and `wait_for_load_state`
5. **Clean up test data**: Use fixtures to set up and tear down data

### Test Organization
1. **Group related tests**: Use test classes for related functionality
2. **Use fixtures**: Share setup code between tests
3. **Mark tests appropriately**: Use `@pytest.mark.playwright` for browser tests
4. **Keep tests independent**: Tests should not depend on each other

### Performance
1. **Run tests in parallel**: Use `pytest-xdist` for parallel execution
2. **Use headless mode**: Faster execution in CI environments
3. **Optimize selectors**: Use efficient selectors for better performance
4. **Minimize network calls**: Mock external APIs when possible

## Troubleshooting

### Test Failures
1. **Check browser logs**: Look for JavaScript errors
2. **Verify test data**: Ensure test data files are created correctly
3. **Check network connectivity**: Some tests require internet access
4. **Review screenshots**: Check `test-results/` for failure screenshots

### Environment Issues
1. **Update dependencies**: Run `uv sync` to update packages
2. **Reinstall browsers**: Run `uv run playwright install`
3. **Check Python version**: Ensure Python 3.12+ is installed
4. **Verify file paths**: Ensure test files are in the correct location

## Contributing

When adding new tests:

1. **Follow naming conventions**: Use descriptive test names
2. **Add appropriate markers**: Use `@pytest.mark.playwright`
3. **Update documentation**: Document new test functionality
4. **Run existing tests**: Ensure new tests don't break existing ones
5. **Add to CI**: Update GitHub Actions workflow if needed

## Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [pytest-playwright](https://github.com/microsoft/playwright-python)
- [Playwright Best Practices](https://playwright.dev/python/docs/best-practices)
- [Test Automation Guide](https://playwright.dev/python/docs/test-automation)
