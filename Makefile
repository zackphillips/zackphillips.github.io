.PHONY: help server install uninstall test check-uv pre-commit-install pre-commit-run lint config sync-dev sync-pi check-sensors
.PHONY: install-sensors run-sensors check-i2c check-signalk-token create-signalk-token
.PHONY: install-sensor-service uninstall-sensor-service check-sensor-service-status sensor-service-logs
.PHONY: install-magnetic-service uninstall-magnetic-service check-magnetic-service-status magnetic-service-logs
.PHONY: calibrate-heading calibrate-imu calibrate-air

# System check
UNAME_S := $(shell uname -s)

# Core configuration
SERVER_PORT ?= 8000
SENSOR_HOST ?= 192.168.8.50
SENSOR_PORT ?= 3000
UV_BIN ?= $(shell command -v uv 2>/dev/null || true)
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

# Default target - show help when called with no arguments
help:
	@echo "Available commands:"
	@echo "  make server         - Start Python HTTP server on port $(SERVER_PORT)"
	@echo "  make install        - Install all services (website, sensors, magnetic variation)"
	@echo "  make uninstall      - Uninstall all services (Linux only)"
	@echo "  make test           - Run unit/integration tests (requires git; uses uv if available)"
	@echo "  make check-uv       - Check if uv is installed and install if necessary"
	@echo "  make run-sensors    - Run I2C sensors to SignalK publisher (one-time)"
	@echo "  make test-sensors   - Test SignalK connection without running sensors"
	@echo "  make check-sensors  - Run I2C checks and SignalK test together"
	@echo "  make check-i2c      - Check I2C devices and permissions"
	@echo "  make check-signalk-token - Check if SignalK token exists and is valid"
	@echo "  make create-signalk-token - Create a new SignalK access token"
	@echo "  make calibrate-heading - Calibrate MMC5603 magnetic heading sensor offset"
	@echo "  make calibrate-imu   - Calibrate BNO055 IMU sensor"
	@echo "  make calibrate-air   - Calibrate SGP30 air quality sensor"
	@echo "  make pre-commit-install - Install pre-commit hooks (requires uv)"
	@echo "  make pre-commit-run - Run pre-commit on all files (requires uv)"
	@echo "  make lint          - Run ruff linter and auto-fix issues on all Python files"
	@echo "  make config        - Interactive vessel configuration wizard"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "Service management:"
	@echo "  make install-website-service    - Install website data updater service"
	@echo "  make install-sensor-service     - Install both fast and slow sensor services"
	@echo "  make install-magnetic-service   - Install magnetic variation service"
	@echo "  make check-website-service-status - Check website service status"
	@echo "  make check-sensor-service-status - Check sensor service status"
	@echo "  make check-magnetic-service-status - Check magnetic variation service status"
	@echo "  make website-logs              - Show website service logs"
	@echo "  make sensor-service-logs       - Show sensor service logs"
	@echo "  make magnetic-service-logs     - Show magnetic variation service logs"
	@echo "  make run-website-update       - Run one website telemetry update now"

# Start Python HTTP server
server:
	@echo "Open http://localhost:$(SERVER_PORT) in your browser"
	@echo "Press Ctrl+C to stop the server"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Starting server with uv environment: $(UV_BIN)"; \
		"$(UV_BIN)" run python -m http.server $(SERVER_PORT); \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Check Linux requirement
check-linux:
	@if [ "$(UNAME_S)" != "Linux" ]; then \
		echo "Error: This command only works on Linux systems"; \
		echo "Current system: $(UNAME_S)"; \
		exit 1; \
	fi

# Check if uv is installed and install if necessary
check-uv:
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "uv is not installed. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "uv installed successfully!"; \
		echo "Please restart your shell or run 'source ~/.bashrc' to use uv"; \
	else \
		echo "uv is already installed at: $$(command -v uv)"; \
	fi

# Install all services
install: check-linux check-uv check-signalk-token
	@echo "Installing all vessel tracker services..."
	@echo ""
	@echo "This will install:"
	@echo "  - Website data updater service (updates telemetry data)"
	@echo "  - Fast sensor service (1s interval, basic sensors)"
	@echo "  - Slow sensor service (60s interval, includes SGP30)"
	@echo "  - Magnetic variation service (daily)"
	@echo ""
	@echo ""
	@$(MAKE) install-website-service
	@echo ""
	@$(MAKE) install-sensor-service
	@echo ""
	@$(MAKE) install-magnetic-service
	@echo ""
	@echo "All services installed successfully!"
	@echo ""
	@echo "Service Summary:"
	@echo "  - Website service: Updates telemetry data every 600 seconds"
	@echo "  - Fast sensor service: Publishes basic sensor data every 1 second"
	@echo "  - Slow sensor service: Publishes all sensor data every 60 seconds"
	@echo "  - Magnetic variation service: Updates magnetic variation daily"
	@echo ""
	@echo "Check status of all services:"
	@echo "  make check-website-service-status"
	@echo "  make check-sensor-service-status"
	@echo "  make check-magnetic-service-status"

# Uninstall all services
uninstall: check-linux
	@echo "Uninstalling all vessel tracker services..."
	@echo ""
	@echo "This will uninstall:"
	@echo "  - Website data updater service"
	@echo "  - Fast and slow sensor services"
	@echo "  - Magnetic variation service"
	@echo ""
	@echo ""
	@$(MAKE) uninstall-website-service
	@echo ""
	@$(MAKE) uninstall-sensor-service
	@echo ""
	@$(MAKE) uninstall-magnetic-service
	@echo ""
	@echo "All services uninstalled successfully!"

# Individual service installation
install-website-service: check-linux check-uv check-signalk-token
	$(call install-service,website,vessel-tracker,Vessel Tracker Data Updater,update_signalk_data.py,,600)

install-sensor-service: check-linux check-uv check-signalk-token
	$(call install-service,fast-sensors,vessel-sensors-fast,Vessel Fast Sensor Data Publisher (1s),i2c_sensor_read_and_publish.py,--disable-sgp30,1)
	$(call install-service,slow-sensors,vessel-sensors-slow,Vessel Slow Sensor Data Publisher (60s),i2c_sensor_read_and_publish.py,,60)

install-magnetic-service: check-linux check-uv check-signalk-token
	$(call install-service,magnetic,vessel-magnetic-variation,Vessel Magnetic Variation Service (daily),magnetic_variation_service.py,,86400)

# Individual service uninstallation
uninstall-website-service: check-linux
	$(call uninstall-service,vessel-tracker)

uninstall-sensor-service: check-linux
	$(call uninstall-service,vessel-sensors-fast)
	$(call uninstall-service,vessel-sensors-slow)

uninstall-magnetic-service: check-linux
	$(call uninstall-service,vessel-magnetic-variation)

# Service status checking
check-website-service-status: check-linux
	$(call check-service-status,vessel-tracker,website)

check-sensor-service-status: check-linux
	$(call check-service-status,vessel-sensors-fast,fast-sensor)
	$(call check-service-status,vessel-sensors-slow,slow-sensor)

check-magnetic-service-status: check-linux
	$(call check-service-status,vessel-magnetic-variation,magnetic)

# Service logs
website-logs: check-linux
	$(call show-service-logs,vessel-tracker)

sensor-service-logs: check-linux
	$(call show-service-logs,vessel-sensors-fast)
	$(call show-service-logs,vessel-sensors-slow)

magnetic-service-logs: check-linux
	$(call show-service-logs,vessel-magnetic-variation)

# Run one website telemetry update (single execution)
run-website-update: check-uv
	@echo "Running one website telemetry update..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Fetching from SignalK and writing data..."; \
		"$(UV_BIN)" run scripts/update_signalk_data.py --no-reset --amend --force-push --signalk-url "http://$(SENSOR_HOST):$(SENSOR_PORT)/signalk/v1/api/vessels/self" --output data/telemetry/signalk_latest.json; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Run tests
test:
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Running tests with uvx (no project sync required)..."; \
		uvx pytest -q; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi

# Install pre-commit hooks
pre-commit-install: check-uv
	@echo "Installing pre-commit hooks..."
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Installing with uvx..."; \
		uvx pre-commit install; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi

# Run pre-commit on all files
pre-commit-run: check-uv
	@echo "Running pre-commit on all files..."
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Running with uvx..."; \
		uvx pre-commit run --all-files; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi

# Run ruff linter and auto-fix issues on all Python files
lint: check-uv
	@echo "Running ruff linter with auto-fix on all Python files (uvx)..."
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Running with uvx..."; \
		uvx ruff check --fix .; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi

# Sync environments using extras
sync-dev: check-uv
	@echo "Syncing dev-only dependencies (no Pi deps)..."
	@"$(UV_BIN)" sync --extra dev

sync-pi: check-uv
	@echo "Syncing Pi + dev dependencies (on Raspberry Pi)..."
	@"$(UV_BIN)" sync --extra pi --extra dev

# Install I2C sensors to SignalK dependencies
install-sensors: check-linux check-uv check-signalk-token
	@echo "Installing I2C sensors to SignalK dependencies..."
	@echo "Updating package list..."
	@sudo apt update
	@echo "Installing I2C tools..."
	@sudo apt install -y i2c-tools
	@echo "Enabling I2C interface..."
	@sudo raspi-config nonint do_i2c 0
	@echo "Installing Python dependencies with uv..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Using uv to install sensor dependencies..."; \
		"$(UV_BIN)" sync; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi
	@echo "Making sensor script executable..."
	@chmod +x scripts/i2c_sensor_read_and_publish.py
	@echo "Installation complete!"
	@echo ""
	@echo "To run the sensor reader:"
	@echo "  make run-sensors"
	@echo ""
	@echo "To run with custom settings:"
	@echo "  make run-sensors SENSOR_HOST=192.168.8.50 SENSOR_PORT=3000"
	@echo ""
	@echo "To check I2C devices:"
	@echo "  make check-i2c"
	@echo ""
	@echo "To test SignalK connection:"
	@echo "  make test-sensors"

# Test SignalK connection without running sensors
test-sensors: check-uv check-signalk-token
	@echo "Testing SignalK connection..."
	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Testing with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py --host $(SENSOR_HOST) --port $(SENSOR_PORT) --test; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Combined sensor checks (I2C devices and SignalK connectivity)
check-sensors: check-linux
	@echo "Running combined sensor checks (I2C + SignalK)..."
	@$(MAKE) check-i2c
	@$(MAKE) test-sensors

# Run I2C sensors to SignalK publisher
run-sensors: check-uv check-signalk-token
	@echo "Starting I2C sensors to SignalK publisher..."
	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py --host $(SENSOR_HOST) --port $(SENSOR_PORT); \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Check I2C devices and permissions
check-i2c: check-linux
	@echo "Checking I2C devices and permissions..."
	@echo "I2C devices detected:"
	@sudo i2cdetect -y 1 || echo "No I2C devices found or I2C not enabled"
	@echo ""
	@echo "I2C group membership:"
	@if groups | grep -q i2c; then \
		echo "✓ User is in i2c group"; \
	else \
		echo "✗ User is NOT in i2c group"; \
		echo "  Run: sudo usermod -a -G i2c $$USER"; \
		echo "  Then logout and login again"; \
	fi
	@echo ""
	@echo "I2C interface status:"
	@if [ -d /dev/i2c-1 ]; then \
		echo "✓ I2C interface is available at /dev/i2c-1"; \
	else \
		echo "✗ I2C interface not found. Run 'make install-sensors' to enable it."; \
	fi

# Check SignalK token
check-signalk-token:
	@echo "Checking SignalK token..."
	@python3 scripts/signalk_token_management.py --check || ( \
		echo ""; \
		echo "SignalK token is missing or invalid."; \
		echo "To create a token, run one of these commands:"; \
		echo "  make create-signalk-token      # Create SignalK token"; \
		echo "  make config                    # Interactive vessel configuration"; \
		echo "  python3 scripts/signalk_token_management.py  # Direct token request"; \
		exit 1 \
	)

# Create SignalK token
create-signalk-token:
	@echo "Creating SignalK access token..."
	@echo "This will request a token from your SignalK server."
	@echo "You'll need to approve the request in your browser."
	@echo ""
	@echo "SignalK server: $(SENSOR_HOST):$(SENSOR_PORT)"
	@echo ""
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo ""
	@python3 scripts/signalk_token_management.py --host $(SENSOR_HOST) --port $(SENSOR_PORT) --timeout 300
	@echo ""
	@echo "Token creation completed!"
	@echo "You can now run sensor-related commands:"
	@echo "  make install-sensors"
	@echo "  make run-sensors"
	@echo "  make test-sensors"

# Interactive vessel configuration wizard
config:
	@echo "Starting Vessel Configuration Wizard..."
	@python scripts/vessel_config_wizard.py

# Calibrate magnetic heading sensor offset
calibrate-heading: check-linux check-uv
	@echo "Calibrating magnetic heading sensor..."
	@echo "This will help you set the correct heading offset for your vessel."
	@echo "You'll need to know the current true heading of your vessel."
	@echo ""
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running heading calibration with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run python scripts/calibrate_mmc5603_heading.py; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Calibrate BNO055 IMU sensor
calibrate-imu: check-linux check-uv
	@echo "Calibrating BNO055 IMU sensor..."
	@echo "This will guide you through calibrating the BNO055 IMU sensor."
	@echo "The sensor requires calibration for accurate orientation and motion data."
	@echo ""
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running IMU calibration with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run python scripts/calibrate_bno055_imu.py; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Calibrate SGP30 air quality sensor
calibrate-air: check-linux check-uv
	@echo "Calibrating SGP30 air quality sensor..."
	@echo "This will guide you through calibrating the SGP30 air quality sensor."
	@echo "The sensor measures TVOC and eCO2 and requires baseline calibration."
	@echo ""
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running air quality calibration with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run python scripts/calibrate_sgp30_air_quality.py; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi
