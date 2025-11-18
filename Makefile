.PHONY: server help install uninstall test pre-commit-install lint config sync-dev sync-pi status
.PHONY: install-sensors check-i2c check-signalk-token create-signalk-token run-bme280 run-bno055 run-mmc5603 run-sgp30
.PHONY: install-sensor-service uninstall-sensor-service check-sensor-service-status sensor-service-logs
.PHONY: install-bme280-service install-bno055-service install-mmc5603-service install-sgp30-service
.PHONY: uninstall-bme280-service uninstall-bno055-service uninstall-mmc5603-service uninstall-sgp30-service
.PHONY: check-bme280-service-status check-bno055-service-status check-mmc5603-service-status check-sgp30-service-status
.PHONY: bme280-logs bno055-logs mmc5603-logs sgp30-logs
.PHONY: install-magnetic-service uninstall-magnetic-service check-magnetic-service-status magnetic-service-logs
.PHONY: calibrate-heading calibrate-imu calibrate-air

# Default target
.DEFAULT_GOAL := help

# System check
UNAME_S := $(shell uname -s)

# Core configuration
SERVER_PORT ?= 8000
SENSOR_HOST ?= 192.168.8.50
SENSOR_PORT ?= 3000
UV_BIN ?= $(shell command -v uv 2>/dev/null || true)
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

# Service definitions (name:description:interval:script:args)
SERVICES := \
	website:vessel-tracker:Vessel Tracker Data Updater:600:update_signalk_data.py: \
	magnetic:vessel-magnetic-variation:Vessel Magnetic Variation Service (daily):86400:magnetic_variation_service.py:

# Service management functions
define install-service
	@echo "Installing $(2) systemd service..."
	@if [ -f "/etc/systemd/system/$(2).service" ]; then \
		echo "$(2) service already exists. Uninstalling first..."; \
		sudo systemctl stop $(2) 2>/dev/null || true; \
		sudo systemctl disable $(2) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Rendering $(2) service template..."
	@if [ "$(1)" = "website" ]; then \
		sed -e "s|{{DESCRIPTION}}|$(3)|g" \
			-e "s|{{USER}}|$$(whoami)|g" \
			-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
			-e "s|{{EXEC_START}}|$(UV_BIN) run scripts/$(4) $(5)|g" \
			-e "s|{{RESTART_POLICY}}|always|g" \
			-e "s|{{RESTART_SEC}}|$(6)|g" \
			-e "s|{{GIT_BRANCH}}|$(CURRENT_BRANCH)|g" \
			-e "s|{{GIT_REMOTE}}|origin|g" \
			-e "s|{{GIT_AMEND}}|false|g" \
			-e "s|{{GIT_FORCE_PUSH}}|false|g" \
			-e "s|{{SIGNALK_URL}}|http://$(SENSOR_HOST):$(SENSOR_PORT)/signalk/v1/api/vessels/self|g" \
			-e "s|{{OUTPUT_FILE}}|data/telemetry/signalk_latest.json|g" \
			"$(CURDIR)/services/systemd.service.tpl" | sudo tee /etc/systemd/system/$(2).service > /dev/null; \
	else \
		sed -e "s|{{DESCRIPTION}}|$(3)|g" \
			-e "s|{{USER}}|$$(whoami)|g" \
			-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
			-e "s|{{EXEC_START}}|$(UV_BIN) run scripts/$(4) --host $(SENSOR_HOST) --port $(SENSOR_PORT) $(5)|g" \
			-e "s|{{RESTART_SEC}}|$(6)|g" \
			-e "s|{{SENSOR_HOST}}|$(SENSOR_HOST)|g" \
			-e "s|{{SENSOR_PORT}}|$(SENSOR_PORT)|g" \
			"$(CURDIR)/services/sensor.service.tpl" | sudo tee /etc/systemd/system/$(2).service > /dev/null; \
	fi
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting $(2) service..."
	@sudo systemctl enable $(2)
	@sudo systemctl start $(2)
	@echo "$(2) service installed and started successfully!"
endef

# Macro for installing individual sensor services using i2c_sensor_read_and_publish.py
define install-sensor-service
	@echo "Installing $(2) systemd service..."
	@if [ -f "/etc/systemd/system/$(2).service" ]; then \
		echo "$(2) service already exists. Uninstalling first..."; \
		sudo systemctl stop $(2) 2>/dev/null || true; \
		sudo systemctl disable $(2) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Rendering $(2) service template..."
	@sed -e "s|{{DESCRIPTION}}|$(3)|g" \
		-e "s|{{USER}}|$$(whoami)|g" \
		-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
		-e "s|{{EXEC_START}}|$(UV_BIN) run python3 scripts/$(4) $(5) --host $(SENSOR_HOST) --port $(SENSOR_PORT)|g" \
		-e "s|{{RESTART_SEC}}|10|g" \
		-e "s|{{SENSOR_HOST}}|$(SENSOR_HOST)|g" \
		-e "s|{{SENSOR_PORT}}|$(SENSOR_PORT)|g" \
		"$(CURDIR)/services/sensor.service.tpl" | sudo tee /etc/systemd/system/$(2).service > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting $(2) service..."
	@sudo systemctl enable $(2)
	@sudo systemctl start $(2)
	@echo "$(2) service installed and started successfully!"
endef

define uninstall-service
	@echo "Uninstalling $(1) systemd service..."
	@if [ -f "/etc/systemd/system/$(1).service" ]; then \
		echo "Stopping and disabling $(1) service..."; \
		sudo systemctl stop $(1) 2>/dev/null || true; \
		sudo systemctl disable $(1) 2>/dev/null || true; \
		echo "Removing $(1) service file..."; \
		sudo rm -f /etc/systemd/system/$(1).service; \
		echo "Reloading systemd..."; \
		sudo systemctl daemon-reload; \
		echo "$(1) service uninstalled successfully!"; \
	else \
		echo "$(1) service file not found. Nothing to uninstall."; \
	fi
endef

define check-service-status
	@echo "Checking status of $(1) service..."
	@if [ -f "/etc/systemd/system/$(1).service" ]; then \
		echo "$(1) service file exists at /etc/systemd/system/$(1).service"; \
		echo ""; \
		echo "$(1) Service Status:"; \
		sudo systemctl status $(1) --no-pager -l; \
	else \
		echo "$(1) service file not found at /etc/systemd/system/$(1).service"; \
		echo "$(1) service is not installed. Run 'make install-$(2)-service' to install it."; \
	fi
endef

define show-service-logs
	@echo "Showing logs for $(1) service..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u $(1) -f
endef

# Check Linux requirement
check-linux:
	@if [ "$(UNAME_S)" != "Linux" ]; then \
		echo "Error: This command only works on Linux systems"; \
		echo "Current system: $(UNAME_S)"; \
		exit 1; \
	fi


# Default target
help:
	@echo "Available commands:"
	@echo "  make server         - Start Python HTTP server on port $(SERVER_PORT)"
	@echo "  make install        - Install all services (website, sensors, magnetic variation)"
	@echo "  make uninstall      - Uninstall all services (Linux only)"
	@echo "  make test           - Run unit/integration tests (requires git; uses uv if available)"
	@echo "  make status         - Reports all sensor and website statuses"
	@echo "  make check-i2c      - Check I2C devices and permissions"
	@echo "  make check-signalk-token - Check if SignalK token exists and is valid"
	@echo "  make create-signalk-token - Create a new SignalK access token"
	@echo "  make calibrate-heading - Calibrate MMC5603 magnetic heading sensor offset"
	@echo "  make calibrate-imu   - Calibrate BNO055 IMU sensor"
	@echo "  make calibrate-air   - Calibrate SGP30 air quality sensor"
	@echo "  make pre-commit-install - Install pre-commit hooks (requires uv)"
	@echo "  make lint          - Run ruff linter and auto-fix issues on all Python files"
	@echo "  make config        - Interactive vessel configuration wizard"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "Service management:"
	@echo "  make install-website-service    - Install website data updater service"
	@echo "  make install-sensor-service    - Install all individual sensor services"
	@echo "  make install-bme280-service    - Install BME280 sensor service"
	@echo "  make install-bno055-service    - Install BNO055 sensor service"
	@echo "  make install-mmc5603-service   - Install MMC5603 sensor service"
	@echo "  make install-sgp30-service     - Install SGP30 sensor service"
	@echo "  make install-magnetic-service   - Install magnetic variation service"
	@echo "  make check-website-service-status - Check website service status"
	@echo "  make check-sensor-service-status - Check all sensor service statuses"
	@echo "  make check-magnetic-service-status - Check magnetic variation service status"
	@echo "  make website-logs              - Show website service logs"
	@echo "  make sensor-service-logs       - Show all sensor service logs"
	@echo "  make bme280-logs              - Show BME280 sensor logs"
	@echo "  make bno055-logs              - Show BNO055 sensor logs"
	@echo "  make mmc5603-logs             - Show MMC5603 sensor logs"
	@echo "  make sgp30-logs               - Show SGP30 sensor logs"
	@echo "  make magnetic-service-logs     - Show magnetic variation service logs"
	@echo "  make run-website-update       - Run one website telemetry update now"

# Start Python HTTP server
server:
	@echo "Open http://localhost:$(SERVER_PORT) in your browser"
	@echo "Press Ctrl+C to stop the server"
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting server with uv environment: $(UV_BIN)"
	@"$(UV_BIN)" run python -m http.server $(SERVER_PORT)

# Install all services
install: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing all vessel tracker services..."
	@echo ""
	@echo "This will install:"
	@echo "  - Website data updater service"
	@echo "  - Individual sensor services (BME280, BNO055, MMC5603, SGP30)"
	@echo "  - Magnetic variation service"
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
	@echo "  - Fast sensor service: Publishes basic sensor data every 10 seconds"
	@echo "  - Slow sensor service: Publishes all sensor data every 240 seconds"
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
	@echo "  - Individual sensor services (BME280, BNO055, MMC5603, SGP30)"
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
install-website-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-service,website,vessel-tracker,Vessel Tracker Data Updater,update_signalk_data.py,,600)

install-sensor-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing all individual sensor services..."
	@$(MAKE) install-bme280-service
	@$(MAKE) install-bno055-service
	@$(MAKE) install-mmc5603-service
	@$(MAKE) install-sgp30-service
	@echo "All sensor services installed successfully!"

# Individual sensor service installation
install-bme280-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-sensor-service,bme280,vessel-sensor-bme280,BME280 Sensor Service,i2c_sensor_read_and_publish.py,bme280)

install-bno055-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-sensor-service,bno055,vessel-sensor-bno055,BNO055 Sensor Service,i2c_sensor_read_and_publish.py,bno055)

install-mmc5603-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-sensor-service,mmc5603,vessel-sensor-mmc5603,MMC5603 Sensor Service,i2c_sensor_read_and_publish.py,mmc5603)

install-sgp30-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-sensor-service,sgp30,vessel-sensor-sgp30,SGP30 Sensor Service,i2c_sensor_read_and_publish.py,sgp30)

install-magnetic-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-service,magnetic,vessel-magnetic-variation,Vessel Magnetic Variation Service (daily),magnetic_variation_service.py,,86400)

# Individual service uninstallation
uninstall-website-service: check-linux
	$(call uninstall-service,vessel-tracker)

uninstall-sensor-service: check-linux
	@echo "Uninstalling all individual sensor services..."
	@$(MAKE) uninstall-bme280-service
	@$(MAKE) uninstall-bno055-service
	@$(MAKE) uninstall-mmc5603-service
	@$(MAKE) uninstall-sgp30-service
	@echo "All sensor services uninstalled successfully!"

# Individual sensor service uninstallation
uninstall-bme280-service: check-linux
	$(call uninstall-service,vessel-sensor-bme280)

uninstall-bno055-service: check-linux
	$(call uninstall-service,vessel-sensor-bno055)

uninstall-mmc5603-service: check-linux
	$(call uninstall-service,vessel-sensor-mmc5603)

uninstall-sgp30-service: check-linux
	$(call uninstall-service,vessel-sensor-sgp30)

uninstall-magnetic-service: check-linux
	$(call uninstall-service,vessel-magnetic-variation)

# Service status checking
check-website-service-status: check-linux
	$(call check-service-status,vessel-tracker,website)

check-sensor-service-status: check-linux
	@echo "Checking status of all sensor services..."
	@$(MAKE) check-bme280-service-status
	@$(MAKE) check-bno055-service-status
	@$(MAKE) check-mmc5603-service-status
	@$(MAKE) check-sgp30-service-status

# Individual sensor service status checking
check-bme280-service-status: check-linux
	$(call check-service-status,vessel-sensor-bme280,bme280)

check-bno055-service-status: check-linux
	$(call check-service-status,vessel-sensor-bno055,bno055)

check-mmc5603-service-status: check-linux
	$(call check-service-status,vessel-sensor-mmc5603,mmc5603)

check-sgp30-service-status: check-linux
	$(call check-service-status,vessel-sensor-sgp30,sgp30)

check-magnetic-service-status: check-linux
	$(call check-service-status,vessel-magnetic-variation,magnetic)

# Report all sensor and website statuses
status: check-linux
	@echo "=========================================="
	@echo "Vessel Tracker Status Report"
	@echo "=========================================="
	@echo ""
	@echo "--- Website Service Status ---"
	@if [ -f "/etc/systemd/system/vessel-tracker.service" ]; then \
		echo "Service: vessel-tracker"; \
		sudo systemctl is-active vessel-tracker >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vessel-tracker >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "--- Sensor Services Status ---"
	@for sensor in bme280 bno055 mmc5603 sgp30; do \
		service_name="vessel-sensor-$$sensor"; \
		if [ -f "/etc/systemd/system/$$service_name.service" ]; then \
			echo "Service: $$service_name"; \
			sudo systemctl is-active $$service_name >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
			sudo systemctl is-enabled $$service_name >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
		else \
			echo "$$service_name: ✗ Not installed"; \
		fi; \
	done
	@echo ""
	@echo "--- Magnetic Variation Service Status ---"
	@if [ -f "/etc/systemd/system/vessel-magnetic-variation.service" ]; then \
		echo "Service: vessel-magnetic-variation"; \
		sudo systemctl is-active vessel-magnetic-variation >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vessel-magnetic-variation >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "--- I2C Hardware Status ---"
	@if [ -d /dev/i2c-1 ]; then \
		echo "I2C Interface: ✓ Available at /dev/i2c-1"; \
		if groups | grep -q i2c; then \
			echo "I2C Group: ✓ User is in i2c group"; \
		else \
			echo "I2C Group: ✗ User is NOT in i2c group"; \
		fi; \
		echo "I2C Devices:"; \
		sudo i2cdetect -y 1 2>/dev/null || echo "  (Unable to scan I2C bus)"; \
	else \
		echo "I2C Interface: ✗ Not available"; \
	fi
	@echo ""
	@echo "--- SignalK Connection Status ---"
	@if [ -n "$(UV_BIN)" ] && "$(UV_BIN)" run python3 scripts/signalk_token_management.py --check >/dev/null 2>&1; then \
		echo "SignalK Token: ✓ Valid"; \
		echo "SignalK Server: $(SENSOR_HOST):$(SENSOR_PORT)"; \
	else \
		echo "SignalK Token: ✗ Missing or invalid"; \
		echo "SignalK Server: $(SENSOR_HOST):$(SENSOR_PORT)"; \
	fi
	@echo ""
	@echo "=========================================="

# Service logs
website-logs: check-linux
	$(call show-service-logs,vessel-tracker)

sensor-service-logs: check-linux
	@echo "Showing logs for all sensor services..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u vessel-sensor-bme280 -u vessel-sensor-bno055 -u vessel-sensor-mmc5603 -u vessel-sensor-sgp30 -f

# Individual sensor service logs
bme280-logs: check-linux
	$(call show-service-logs,vessel-sensor-bme280)

bno055-logs: check-linux
	$(call show-service-logs,vessel-sensor-bno055)

mmc5603-logs: check-linux
	$(call show-service-logs,vessel-sensor-mmc5603)

sgp30-logs: check-linux
	$(call show-service-logs,vessel-sensor-sgp30)

magnetic-service-logs: check-linux
	$(call show-service-logs,vessel-magnetic-variation)

# Run one website telemetry update (single execution)
run-website-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one website telemetry update..."
	@echo "Fetching from SignalK and writing data..."; \
	"$(UV_BIN)" run scripts/update_signalk_data.py --no-reset --amend --force-push --signalk-url "http://$(SENSOR_HOST):$(SENSOR_PORT)/signalk/v1/api/vessels/self" --output data/telemetry/signalk_latest.json

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
pre-commit-install:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing pre-commit hooks..."
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Installing with uvx..."; \
		uvx pre-commit install; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi


# Run ruff linter and auto-fix issues on all Python files
lint:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running ruff linter with auto-fix on all Python files (uvx)..."
	@if command -v uvx >/dev/null 2>&1; then \
		echo "Running with uvx..."; \
		uvx ruff check --fix .; \
	else \
		echo "Error: 'uvx' is not available. Ensure 'uv' is installed and on PATH."; \
		exit 1; \
	fi

# Sync environments using extras
sync-dev:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Syncing dev-only dependencies (no Pi deps)..."
	@"$(UV_BIN)" sync --extra dev

sync-pi:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Syncing Pi + dev dependencies (on Raspberry Pi)..."
	@"$(UV_BIN)" sync --extra pi --extra dev

# Install I2C sensors to SignalK dependencies
install-sensors: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing I2C sensors to SignalK dependencies..."
	@echo "Updating package list..."
	@sudo apt update
	@echo "Installing I2C tools..."
	@sudo apt install -y i2c-tools
	@echo "Enabling I2C interface..."
	@sudo raspi-config nonint do_i2c 0
	@echo "Installing Python dependencies with uv..."
	@echo "Using uv to install sensor dependencies..."
	@"$(UV_BIN)" sync
	@echo "Making sensor script executable..."
	@chmod +x scripts/i2c_sensor_read_and_publish.py
	@echo "Installation complete!"
	@echo ""
	@echo "To run a specific sensor:"
	@echo "  uv run scripts/i2c_sensor_read_and_publish.py bme280 --host 192.168.8.50 --port 3000"
	@echo ""
	@echo "To run with custom settings:"
	@echo "  make run-bme280 SENSOR_HOST=192.168.8.50 SENSOR_PORT=3000"
	@echo ""
	@echo "To check I2C devices:"
	@echo "  make check-i2c"
	@echo ""


# Run I2C sensors to SignalK publisher (runs each sensor individually for consistency)
# run-sensors: check-signalk-token
# 	@if [ -z "$(UV_BIN)" ]; then \
# 		echo "Error: 'uv' is not installed. Please install uv first."; \
# 		echo "Visit: https://github.com/astral-sh/uv"; \
# 		exit 1; \
# 	fi
# 	@echo "Starting I2C sensors to SignalK publisher (individual sensor mode)..."
# 	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT)"
# 	@echo "Running with uv: $(UV_BIN)"
# 	@echo ""
# 	@echo "Running BME280 sensor..."
# 	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py bme280 --host $(SENSOR_HOST) --port $(SENSOR_PORT) || echo "BME280 failed"
# 	@echo ""
# 	@echo "Running BNO055 sensor..."
# 	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py bno055 --host $(SENSOR_HOST) --port $(SENSOR_PORT) || echo "BNO055 failed"
# 	@echo ""
# 	@echo "Running MMC5603 sensor..."
# 	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py mmc5603 --host $(SENSOR_HOST) --port $(SENSOR_PORT) || echo "MMC5603 failed"
# 	@echo ""
# 	@echo "Running SGP30 sensor..."
# 	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py sgp30 --host $(SENSOR_HOST) --port $(SENSOR_PORT) || echo "SGP30 failed"
# 	@echo ""
# 	@echo "All sensors completed."

# Run individual I2C sensors to SignalK publisher
run-bme280: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting BME280 sensor read and publish..."
	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py bme280 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-bno055: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting BNO055 sensor read and publish..."
	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py bno055 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-mmc5603: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting MMC5603 sensor read and publish..."
	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py mmc5603 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-sgp30: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting SGP30 sensor read and publish..."
	@"$(UV_BIN)" run scripts/i2c_sensor_read_and_publish.py sgp30 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

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
	@"$(UV_BIN)" run python3 scripts/signalk_token_management.py --check || ( \
		echo ""; \
		echo "SignalK token is missing or invalid."; \
		echo "To create a token, run one of these commands:"; \
		echo "  make create-signalk-token      # Create SignalK token"; \
		echo "  make config                    # Interactive vessel configuration"; \
		echo "  $(UV_BIN) run python3 scripts/signalk_token_management.py  # Direct token request"; \
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
	@"$(UV_BIN)" run python3 scripts/signalk_token_management.py --host $(SENSOR_HOST) --port $(SENSOR_PORT) --timeout 300
	@echo ""
	@echo "Token creation completed!"
	@echo "You can now run sensor-related commands:"
	@echo "  make install-sensors"
	@echo "  make run-sensors"

# Interactive vessel configuration wizard
config:
	@echo "Starting Vessel Configuration Wizard..."
	@"$(UV_BIN)" run python3 scripts/vessel_config_wizard.py

# Calibrate magnetic heading sensor offset
calibrate-heading: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Calibrating magnetic heading sensor..."
	@echo "This will help you set the correct heading offset for your vessel."
	@echo "You'll need to know the current true heading of your vessel."
	@echo ""
	@echo "Running heading calibration with uv: $(UV_BIN)"
	@"$(UV_BIN)" run python scripts/calibrate_mmc5603_heading.py

# Calibrate BNO055 IMU sensor
calibrate-imu: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Calibrating BNO055 IMU sensor..."
	@echo "This will guide you through calibrating the BNO055 IMU sensor."
	@echo "The sensor requires calibration for accurate orientation and motion data."
	@echo ""
	@echo "Running IMU calibration with uv: $(UV_BIN)"
	@"$(UV_BIN)" run python scripts/calibrate_bno055_imu.py

# Calibrate SGP30 air quality sensor
calibrate-air: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Calibrating SGP30 air quality sensor..."
	@echo "This will guide you through calibrating the SGP30 air quality sensor."
	@echo "The sensor measures TVOC and eCO2 and requires baseline calibration."
	@echo ""
	@echo "Running air quality calibration with uv: $(UV_BIN)"
	@"$(UV_BIN)" run python scripts/calibrate_sgp30_air_quality.py
