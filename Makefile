.PHONY: server help install uninstall test test-py test-js js-install pre-commit-install lint config sync-dev sync-pi status
.PHONY: install-sensors check-i2c check-signalk-token create-signalk-token run-sensors run-bme280 run-bno055 run-mmc5603 run-sgp30
.PHONY: install-all-sensor-services uninstall-all-sensor-services check-service-status-all-sensors show-logs-all-sensors
.PHONY: install-bme280-service install-bno055-service install-mmc5603-service install-sgp30-service
.PHONY: uninstall-bme280-service uninstall-bno055-service uninstall-mmc5603-service uninstall-sgp30-service
.PHONY: check-bme280-service-status check-bno055-service-status check-mmc5603-service-status check-sgp30-service-status
.PHONY: show-logs-website show-logs-bme280 show-logs-bno055 show-logs-mmc5603 show-logs-sgp30
.PHONY: calibrate-mmc5603 calibrate-bno055 calibrate-sgp30

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
	website:vesselwebsite:Vessel Tracker Data Updater:150:update_signalk_data.py:

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
			-e "s|{{EXEC_START}}|$(UV_BIN) run python -m $(4) $(5)|g" \
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
			-e "s|{{EXEC_START}}|$(UV_BIN) run python -m $(4) --host $(SENSOR_HOST) --port $(SENSOR_PORT) $(5)|g" \
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
define install-all-sensor-services
	@echo "Checking config for $(5) sensor..."
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@SENSOR_EXISTS=$$("$(UV_BIN)" run python3 -c "import yaml; config = yaml.safe_load(open('$(CURDIR)/data/vessel/info.yaml')); sensors = config.get('sensors', {}); sensor_config = sensors.get('$(5)', {}); update_interval = sensor_config.get('update_interval') if sensor_config else None; print('yes' if update_interval is not None else 'no')" 2>/dev/null || echo "error"); \
	if [ "$$SENSOR_EXISTS" != "yes" ]; then \
		echo "  Skipping $(5) service installation: sensor key '$(5)' not found in config or update_interval is null/missing: $$SENSOR_EXISTS"; \
	else \
		echo "Installing $(2) systemd service..."; \
		if [ -f "/etc/systemd/system/$(2).service" ]; then \
			echo "$(2) service already exists. Uninstalling first..."; \
			sudo systemctl stop $(2) 2>/dev/null || true; \
			sudo systemctl disable $(2) 2>/dev/null || true; \
		fi; \
		echo "Reading run_count from config for $(5)..."; \
		RUN_COUNT=$$("$(UV_BIN)" run python3 -c "import yaml; config = yaml.safe_load(open('$(CURDIR)/data/vessel/info.yaml')); sensor_config = config.get('sensors', {}).get('$(5)', {}); run_count = sensor_config.get('run_count') if sensor_config else None; update_interval = sensor_config.get('update_interval') if sensor_config else None; result = 'inf' if (isinstance(run_count, str) and run_count.lower() in ['inf', 'infinite', 'infinity']) or (isinstance(run_count, (int, float)) and run_count == float('inf')) else (str(int(run_count)) if isinstance(run_count, (int, float)) and run_count > 0 else ('inf' if update_interval is not None and ((isinstance(update_interval, str) and update_interval.lower() in ['inf', 'infinite', 'infinity']) or (isinstance(update_interval, (int, float)) and float(update_interval) == float('inf'))) else '1')); print(result)" 2>/dev/null || echo "1"); \
		if [ "$$RUN_COUNT" = "inf" ]; then \
			echo "  Configuring $(5) for infinite mode (continuous with systemd restart)"; \
			RESTART_POLICY="always"; \
			RESTART_SEC="10"; \
			RUN_COUNT_ARG="--run-count inf"; \
		else \
			echo "  Configuring $(5) for one-shot mode (run_count=$$RUN_COUNT, legacy mode if update_interval set)"; \
			RESTART_POLICY="on-failure"; \
			RESTART_SEC="10"; \
			RUN_COUNT_ARG=""; \
		fi; \
		echo "Rendering $(2) service template..."; \
		sed -e "s|{{DESCRIPTION}}|$(3)|g" \
			-e "s|{{USER}}|$$(whoami)|g" \
			-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
			-e "s|{{EXEC_START}}|$(UV_BIN) run python -m $(4) $(5) --host $(SENSOR_HOST) --port $(SENSOR_PORT) $$RUN_COUNT_ARG|g" \
			-e "s|{{RESTART_POLICY}}|$$RESTART_POLICY|g" \
			-e "s|{{RESTART_SEC}}|$$RESTART_SEC|g" \
			-e "s|{{SENSOR_HOST}}|$(SENSOR_HOST)|g" \
			-e "s|{{SENSOR_PORT}}|$(SENSOR_PORT)|g" \
			"$(CURDIR)/services/sensor.service.tpl" | sudo tee /etc/systemd/system/$(2).service > /dev/null; \
		echo "Reloading systemd..."; \
		sudo systemctl daemon-reload; \
		echo "Enabling and starting $(2) service..."; \
		sudo systemctl enable $(2); \
		sudo systemctl start $(2); \
		echo "$(2) service installed and started successfully!"; \
	fi
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
	@echo "Installation and General Usage:"
	@echo "  make install        - Install all services (website, sensors)"
	@echo "  make uninstall      - Uninstall all services (Linux only)"
	@echo "  make status         - Reports all sensor and website statuses"
	@echo "  make config        - Interactive vessel configuration wizard"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "Development Commands:"
	@echo "  make server         - Start Python HTTP server on port $(SERVER_PORT)"
	@echo "  make test           - Run Python and JavaScript test suites"
	@echo "  make test-js        - Run JavaScript unit tests (vitest)"
	@echo "  make js-install     - Install JavaScript dependencies (npm)"
	@echo "  make check-i2c      - Check I2C devices and permissions"
	@echo "  make check-signalk-token - Check if SignalK token exists and is valid"
	@echo "  make create-signalk-token - Create a new SignalK access token"
	@echo "  make pre-commit-install - Install pre-commit hooks (requires uv)"
	@echo "  make lint          - Run ruff linter and auto-fix issues on all Python files"
	@echo "  make run-website-update       - Run one website telemetry update now"
	@echo "  make run-bme280        - Run BME280 sensor read and publish"
	@echo "  make run-bno055        - Run BNO055 sensor read and publish"
	@echo "  make run-mmc5603      - Run MMC5603 sensor read and publish"
	@echo "  make run-sgp30        - Run SGP30 sensor read and publish"
	@echo ""
	@echo "Sensor Calibration:"
	@echo "  make calibrate-mmc5603 - Calibrate MMC5603 magnetic heading sensor offset"
	@echo "  make calibrate-bno055   - Calibrate BNO055 IMU sensor"
	@echo "  make calibrate-sgp30   - Calibrate SGP30 air quality sensor"
	@echo ""
	@echo "Service management:"
	@echo "  make install-website-service    - Install website data updater service"
	@echo "  make install-all-sensor-services    - Install all individual sensor services"
	@echo "  make install-bme280-service    - Install BME280 sensor service"
	@echo "  make install-bno055-service    - Install BNO055 sensor service"
	@echo "  make install-mmc5603-service   - Install MMC5603 sensor service"
	@echo "  make install-sgp30-service     - Install SGP30 sensor service"
	@echo "  make check-service-status-website - Check website service status"
	@echo "  make check-service-status-all-sensors - Check all sensor service statuses"
	@echo ""
	@echo "Logs:"
	@echo "  make show-logs-website             - Show website service logs"
	@echo "  make show-logs-all-sensors       - Show all sensor service logs"
	@echo "  make show-logs-bme280          - Show BME280 sensor logs"
	@echo "  make show-logs-bno055          - Show BNO055 sensor logs"
	@echo "  make show-logs-mmc5603         - Show MMC5603 sensor logs"
	@echo "  make show-logs-sgp30           - Show SGP30 sensor logs"

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
	@echo ""
	@echo ""
	@$(MAKE) install-website-service
	@echo ""
	@$(MAKE) install-all-sensor-services
	@echo ""
	@echo "All services installed successfully!"
	@echo ""
	@echo "Service Summary:"
	@echo "  - Website service: Updates telemetry data every 150 seconds"
	@echo "  - Fast sensor service: Publishes basic sensor data every 10 seconds"
	@echo "  - Slow sensor service: Publishes all sensor data every 240 seconds"
	@echo ""
	@echo "Check status of all services:"
	@echo "  make check-service-status-website"
	@echo "  make check-service-status-all-sensors"

# Uninstall all services
uninstall: check-linux
	@echo "Uninstalling all vessel tracker services..."
	@echo ""
	@echo "This will uninstall:"
	@echo "  - Website data updater service"
	@echo "  - Individual sensor services (BME280, BNO055, MMC5603, SGP30)"
	@echo ""
	@echo ""
	@$(MAKE) uninstall-website-service
	@echo ""
	@$(MAKE) uninstall-all-sensor-services
	@echo ""
	@echo "All services uninstalled successfully!"

# Individual service installation
install-website-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-service,website,vesselwebsite,Vessel Tracker Data Updater,scripts.update_signalk_data,--interval 150,150)

install-all-sensor-services: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Uninstalling all sensor services first (to ensure clean state)..."
	@$(MAKE) uninstall-all-sensor-services
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
	$(call install-all-sensor-services,bme280,vessel_sensor_bme280,BME280 Sensor Service,scripts.i2c_sensor_read_and_publish,bme280)

install-bno055-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-all-sensor-services,bno055,vessel_sensor_bno055,BNO055 Sensor Service,scripts.i2c_sensor_read_and_publish,bno055)

install-mmc5603-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-all-sensor-services,mmc5603,vessel_sensor_mmc5603,MMC5603 Sensor Service,scripts.i2c_sensor_read_and_publish,mmc5603)

install-sgp30-service: check-linux check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-all-sensor-services,sgp30,vessel_sensor_sgp30,SGP30 Sensor Service,scripts.i2c_sensor_read_and_publish,sgp30)

# Individual service uninstallation
uninstall-website-service: check-linux
	$(call uninstall-service,vesselwebsite)

uninstall-all-sensor-services: check-linux
	@echo "Uninstalling all individual sensor services..."
	@$(MAKE) uninstall-bme280-service
	@$(MAKE) uninstall-bno055-service
	@$(MAKE) uninstall-mmc5603-service
	@$(MAKE) uninstall-sgp30-service
	@echo "All sensor services uninstalled successfully!"

# Individual sensor service uninstallation
uninstall-bme280-service: check-linux
	$(call uninstall-service,vessel_sensor_bme280)

uninstall-bno055-service: check-linux
	$(call uninstall-service,vessel_sensor_bno055)

uninstall-mmc5603-service: check-linux
	$(call uninstall-service,vessel_sensor_mmc5603)

uninstall-sgp30-service: check-linux
	$(call uninstall-service,vessel_sensor_sgp30)

# Service status checking
check-service-status-website: check-linux
	$(call check-service-status,vesselwebsite,website)

check-service-status-all-sensors: check-linux
	@echo "Checking status of all sensor services..."
	@$(MAKE) check-bme280-service-status
	@$(MAKE) check-bno055-service-status
	@$(MAKE) check-mmc5603-service-status
	@$(MAKE) check-sgp30-service-status

# Individual sensor service status checking
check-bme280-service-status: check-linux
	$(call check-service-status,vessel_sensor_bme280,bme280)

check-bno055-service-status: check-linux
	$(call check-service-status,vessel_sensor_bno055,bno055)

check-mmc5603-service-status: check-linux
	$(call check-service-status,vessel_sensor_mmc5603,mmc5603)

check-sgp30-service-status: check-linux
	$(call check-service-status,vessel_sensor_sgp30,sgp30)

# Report all sensor and website statuses
status: check-linux
	@echo "=========================================="
	@echo "Vessel Tracker Status Report"
	@echo "=========================================="
	@echo ""
	@echo "--- Website Service Status ---"
	@if [ -f "/etc/systemd/system/vesselwebsite.service" ]; then \
		echo "Service: vesselwebsite"; \
		sudo systemctl is-active vesselwebsite >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vesselwebsite >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "--- Sensor Services Status ---"
	@for sensor in bme280 bno055 mmc5603 sgp30; do \
		service_name="vessel_sensor_$$sensor"; \
		if [ -f "/etc/systemd/system/$$service_name.service" ]; then \
			echo "Service: $$service_name"; \
			sudo systemctl is-active $$service_name >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
			sudo systemctl is-enabled $$service_name >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
		else \
			echo "$$service_name: ✗ Not installed"; \
		fi; \
	done
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
	@if [ -n "$(UV_BIN)" ] && "$(UV_BIN)" run python -m scripts.signalk_token_management --check >/dev/null 2>&1; then \
		echo "SignalK Token: ✓ Valid"; \
		echo "SignalK Server: $(SENSOR_HOST):$(SENSOR_PORT)"; \
	else \
		echo "SignalK Token: ✗ Missing or invalid"; \
		echo "SignalK Server: $(SENSOR_HOST):$(SENSOR_PORT)"; \
	fi
	@echo ""
	@echo "=========================================="

# Service logs
show-logs-website: check-linux
	$(call show-service-logs,vesselwebsite)

show-logs-all-sensors: check-linux
	@echo "Showing logs for all sensor services..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u vessel_sensor_bme280 -u vessel_sensor_bno055 -u vessel_sensor_mmc5603 -u vessel_sensor_sgp30 -f

# Individual sensor service logs
show-logs-bme280: check-linux
	$(call show-service-logs,vessel_sensor_bme280)

show-logs-bno055: check-linux
	$(call show-service-logs,vessel_sensor_bno055)

show-logs-mmc5603: check-linux
	$(call show-service-logs,vessel_sensor_mmc5603)

show-logs-sgp30: check-linux
	$(call show-service-logs,vessel_sensor_sgp30)

# Run one website telemetry update (single execution)
run-website-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one website telemetry update..."
	@echo "Fetching from SignalK and writing data..."; \
	"$(UV_BIN)" run python -m scripts.update_signalk_data --no-reset --amend --force-push --signalk-url "http://$(SENSOR_HOST):$(SENSOR_PORT)/signalk/v1/api/vessels/self" --output data/telemetry/signalk_latest.json

# Run tests
test: test-py test-js

test-py:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running Python tests inside uv-managed virtualenv..."
	@PYTHONPATH="$(CURDIR):$(CURDIR)/scripts" "$(UV_BIN)" run pytest -q

test-js:
	@if ! command -v npm >/dev/null 2>&1; then \
		echo "Error: 'npm' is not installed. Please install Node.js first."; \
		exit 1; \
	fi
	@if [ ! -d node_modules ]; then \
		echo "Installing JavaScript dependencies..."; \
		npm install; \
	fi
	@npm test

js-install:
	@if ! command -v npm >/dev/null 2>&1; then \
		echo "Error: 'npm' is not installed. Please install Node.js first."; \
		exit 1; \
	fi
	@npm install

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
	# Only install lgpio if running on Linux
	@if [ "$(UNAME_S)" == "Linux" ]; then \
		@echo "Installing lgpio..."; \
		sudo apt install -y lgpio;
	fi;
	@echo "Installing Python dependencies with uv..."
	@echo "Using uv to install sensor dependencies..."
	@"$(UV_BIN)" sync
	@echo "Making sensor script executable..."
	@chmod +x scripts/i2c_sensor_read_and_publish.py
	@echo "Installation complete!"
	@echo ""
	@echo "To run a specific sensor:"
	@echo "  uv run python -m scripts.i2c_sensor_read_and_publish bme280 --host 192.168.8.50 --port 3000"
	@echo ""
	@echo "To run with custom settings:"
	@echo "  make run-bme280 SENSOR_HOST=192.168.8.50 SENSOR_PORT=3000"
	@echo ""
	@echo "To check I2C devices:"
	@echo "  make check-i2c"
	@echo ""


# Run I2C sensors to SignalK publisher (runs each sensor individually, reading run_count from config)
run-sensors: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting I2C sensors to SignalK publisher (one-shot mode, one run per sensor)..."
	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT)"
	@echo "Running with uv: $(UV_BIN)"
	@echo "Note: Each sensor will run once, regardless of run_count in config"
	@echo ""
	@echo "Running BME280 sensor (one run)..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish bme280 --host $(SENSOR_HOST) --port $(SENSOR_PORT) --run-count 1 || echo "BME280 failed"
	@echo ""
	@echo "Running BNO055 sensor (one run)..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish bno055 --host $(SENSOR_HOST) --port $(SENSOR_PORT) --run-count 1 || echo "BNO055 failed"
	@echo ""
	@echo "Running MMC5603 sensor (one run)..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish mmc5603 --host $(SENSOR_HOST) --port $(SENSOR_PORT) --run-count 1 || echo "MMC5603 failed"
	@echo ""
	@echo "Running SGP30 sensor (one run)..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish sgp30 --host $(SENSOR_HOST) --port $(SENSOR_PORT) --run-count 1 || echo "SGP30 failed"
	@echo ""
	@echo "All sensors completed (one run each)."

# Run individual I2C sensors to SignalK publisher
run-bme280: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting BME280 sensor read and publish..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish bme280 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-bno055: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting BNO055 sensor read and publish..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish bno055 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-mmc5603: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting MMC5603 sensor read and publish..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish mmc5603 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

run-sgp30: check-signalk-token
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting SGP30 sensor read and publish..."
	@"$(UV_BIN)" run python -m scripts.i2c_sensor_read_and_publish sgp30 --host $(SENSOR_HOST) --port $(SENSOR_PORT)

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
	@"$(UV_BIN)" run python -m scripts.signalk_token_management --check || ( \
		echo ""; \
		echo "SignalK token is missing or invalid."; \
		echo "To create a token, run one of these commands:"; \
		echo "  make create-signalk-token      # Create SignalK token"; \
		echo "  make config                    # Interactive vessel configuration"; \
		echo "  $(UV_BIN) run python -m scripts.signalk_token_management  # Direct token request"; \
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
	@"$(UV_BIN)" run python -m scripts.signalk_token_management --host $(SENSOR_HOST) --port $(SENSOR_PORT) --timeout 300
	@echo ""
	@echo "Token creation completed!"
	@echo "You can now run sensor-related commands:"
	@echo "  make install-sensors"
	@echo "  make run-bme280    # or run-bno055, run-mmc5603, run-sgp30"

# Interactive vessel configuration wizard
config:
	@echo "Starting Vessel Configuration Wizard..."
	@"$(UV_BIN)" run python -m scripts.vessel_config_wizard

# Calibrate magnetic heading sensor offset
calibrate-mmc5603: check-linux
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
	@"$(UV_BIN)" run python -m scripts.calibrate_mmc5603_heading

# Calibrate BNO055 IMU sensor
calibrate-bno055: check-linux
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
	@"$(UV_BIN)" run python -m scripts.calibrate_bno055_imu

# Calibrate SGP30 air quality sensor
calibrate-sgp30: check-linux
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
	@"$(UV_BIN)" run python -m scripts.calibrate_sgp30_air_quality
