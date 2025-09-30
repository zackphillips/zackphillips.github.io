.PHONY: server help install-website-service website-logs uninstall-website-service check-website-service-status
.PHONY: test check-uv pre-commit-install pre-commit-run config
.PHONY: install-sensors run-sensors check-i2c check-signalk-token create-signalk-token
.PHONY: install-sensor-service uninstall-sensor-service check-sensor-service-status sensor-logs
.PHONY: calibrate-heading calibrate-imu calibrate-air

# Check if running on Linux
UNAME_S := $(shell uname -s)
WEBSITE_SERVICE_NAME := vessel-tracker
WEBSITE_SERVICE_FILE := /etc/systemd/system/$(WEBSITE_SERVICE_NAME).service

# Sensor service configuration
SENSOR_SERVICE_NAME := vessel-sensors
SENSOR_SERVICE_FILE := /etc/systemd/system/$(SENSOR_SERVICE_NAME).service
SENSOR_SERVICE_DESCRIPTION ?= Vessel Sensor Data Publisher
SENSOR_SERVICE_USER ?= $(shell whoami)
SENSOR_SERVICE_WORKING_DIR ?= $(CURDIR)
SENSOR_SERVICE_INTERVAL ?= 1
SENSOR_TEMPLATE_FILE ?= $(CURDIR)/services/sensor.service.tpl
SENSOR_SERVICE_EXEC_START ?= $(UV_BIN) run scripts/i2c_sensor_read_and_publish.py --host $(SENSOR_HOST) --port $(SENSOR_PORT)

# Optional: server port
SERVER_PORT ?= 8000

# Sensor configuration
SENSOR_HOST ?= 192.168.8.50
SENSOR_PORT ?= 3000

# Resolve uv binary (absolute path for systemd); allow override
UV_BIN ?= $(shell command -v uv 2>/dev/null || true)

# Update job entrypoint (can override)
UPDATE_SCRIPT ?= $(CURDIR)/scripts/update_signalk_data.py

# Compute default ExecStart for updater based on available runtime
ifeq (,$(UV_BIN))
  DEFAULT_EXEC_START :=
else
  DEFAULT_EXEC_START := $(UV_BIN) run python "$(UPDATE_SCRIPT)"
endif

# Service template and default values (override with: make VAR=value target)
TEMPLATE_FILE ?= $(CURDIR)/services/systemd.service.tpl
SERVICE_DESCRIPTION ?= Vessel Tracker Data Updater
SERVICE_USER ?= $(shell whoami)
SERVICE_WORKING_DIR ?= $(CURDIR)
SERVICE_EXEC_START ?= $(DEFAULT_EXEC_START)
# Restart behavior (period)
RESTART_POLICY ?= always
RESTART_SEC ?= 600

# Git/environment parameters for updater
# Detect current git branch; fallback to main if unavailable
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)
GIT_BRANCH ?= $(CURRENT_BRANCH)
GIT_REMOTE ?= origin
GIT_AMEND ?= true
GIT_FORCE_PUSH ?= true
SIGNALK_URL ?= http://localhost:3000/signalk/v1/api/vessels/self
OUTPUT_FILE ?= $(CURDIR)/data/telemetry/signalk_latest.json

# Default target
help:
	@echo "Available commands:"
	@echo "  make server         - Start Python HTTP server on port 8000"
	@echo "  make install-website-service - Install website data updater service (Linux only)"
	@echo "  make check-website-service-status - Check website service status (Linux only)"
	@echo "  make website-logs   - Show website service logs (Linux only)"
	@echo "  make uninstall-website-service - Uninstall website service (Linux only)"
	@echo "  make change-server-update-period RESTART_SEC=600 - Change systemd update period in seconds (Linux only)"
	@echo "  make change-server-branch [BRANCH=<name>] - Switch updater branch (defaults to current git branch)"
	@echo "  make test           - Run unit/integration tests (requires git; uses uv if available)"
	@echo "  make check-uv       - Check if uv is installed and install if necessary"
	@echo "  make install-sensors - Install I2C sensor dependencies and enable I2C (Raspberry Pi only)"
	@echo "  make run-sensors    - Run I2C sensors to SignalK publisher (one-time)"
	@echo "  make test-sensors   - Test SignalK connection without running sensors"
	@echo "  make check-i2c      - Check I2C devices and permissions"
	@echo "  make install-sensor-service - Install recurring sensor service (runs every 1s)"
	@echo "  make check-sensor-service-status - Check sensor service status (Linux only)"
	@echo "  make sensor-logs    - Show sensor service logs (Linux only)"
	@echo "  make uninstall-sensor-service - Uninstall sensor service (Linux only)"
	@echo "  make check-signalk-token - Check if SignalK token exists and is valid"
	@echo "  make create-signalk-token - Create a new SignalK access token"
	@echo "  make calibrate-heading - Calibrate MMC5603 magnetic heading sensor offset"
	@echo "  make calibrate-imu   - Calibrate BNO055 IMU sensor"
	@echo "  make calibrate-air   - Calibrate SGP30 air quality sensor"
	@echo "  make pre-commit-install - Install pre-commit hooks (requires uv)"
	@echo "  make pre-commit-run - Run pre-commit on all files (requires uv)"
	@echo "  make config         - Interactive vessel configuration wizard"
	@echo "  make help           - Show this help message"

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

# Install systemd service
install-website-service: check-linux
	@echo "Installing $(WEBSITE_SERVICE_NAME) systemd service..."
	@if [ -f "$(WEBSITE_SERVICE_FILE)" ]; then \
		echo "Website service already exists. Uninstalling first..."; \
		sudo systemctl stop $(WEBSITE_SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(WEBSITE_SERVICE_NAME) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi
	@echo "Rendering website service template from $(TEMPLATE_FILE)..."
	@if [ ! -f "$(TEMPLATE_FILE)" ]; then \
		echo "Error: Template file not found at $(TEMPLATE_FILE)"; \
		exit 1; \
	fi
	@sed -e "s|{{DESCRIPTION}}|$(SERVICE_DESCRIPTION)|g" \
	     -e "s|{{USER}}|$(SERVICE_USER)|g" \
	     -e "s|{{WORKING_DIRECTORY}}|$(SERVICE_WORKING_DIR)|g" \
	     -e "s|{{EXEC_START}}|$(SERVICE_EXEC_START)|g" \
	     -e "s|{{RESTART_POLICY}}|$(RESTART_POLICY)|g" \
	     -e "s|{{RESTART_SEC}}|$(RESTART_SEC)|g" \
	     -e "s|{{GIT_BRANCH}}|$(GIT_BRANCH)|g" \
	     -e "s|{{GIT_REMOTE}}|$(GIT_REMOTE)|g" \
	     -e "s|{{GIT_AMEND}}|$(GIT_AMEND)|g" \
	     -e "s|{{GIT_FORCE_PUSH}}|$(GIT_FORCE_PUSH)|g" \
	     -e "s|{{SIGNALK_URL}}|$(SIGNALK_URL)|g" \
	     -e "s|{{OUTPUT_FILE}}|$(OUTPUT_FILE)|g" \
	     "$(TEMPLATE_FILE)" | sudo tee $(WEBSITE_SERVICE_FILE) > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting website service..."
	@sudo systemctl enable $(WEBSITE_SERVICE_NAME)
	@sudo systemctl start $(WEBSITE_SERVICE_NAME)
	@echo "Website service installed and started successfully!"
	@echo "Check status with: make check-website-service-status"
	@echo "View logs with: make website-logs"

# Show website service logs
website-logs: check-linux
	@echo "Showing logs for $(WEBSITE_SERVICE_NAME) service..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u $(WEBSITE_SERVICE_NAME) -f

# Check website service status
check-website-service-status: check-linux
	@echo "Checking status of $(WEBSITE_SERVICE_NAME) service..."
	@if [ -f "$(WEBSITE_SERVICE_FILE)" ]; then \
		echo "Website service file exists at $(WEBSITE_SERVICE_FILE)"; \
		echo ""; \
		echo "Website Service Status:"; \
		sudo systemctl status $(WEBSITE_SERVICE_NAME) --no-pager -l; \
	else \
		echo "Website service file not found at $(WEBSITE_SERVICE_FILE)"; \
		echo "Website service is not installed. Run 'make install-website-service' to install it."; \
	fi

# Uninstall website systemd service
uninstall-website-service: check-linux
	@echo "Uninstalling $(WEBSITE_SERVICE_NAME) systemd service..."
	@if [ -f "$(WEBSITE_SERVICE_FILE)" ]; then \
		echo "Stopping and disabling website service..."; \
		sudo systemctl stop $(WEBSITE_SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(WEBSITE_SERVICE_NAME) 2>/dev/null || true; \
		echo "Removing website service file..."; \
		sudo rm -f $(WEBSITE_SERVICE_FILE); \
		echo "Reloading systemd..."; \
		sudo systemctl daemon-reload; \
		echo "Website service uninstalled successfully!"; \
	else \
		echo "Website service file not found. Nothing to uninstall."; \
	fi

# Change website service restart cadence (policy/interval) after install
change-server-update-period: check-linux
	@if [ ! -f "$(WEBSITE_SERVICE_FILE)" ]; then \
		echo "Website service file not found at $(WEBSITE_SERVICE_FILE). Install it first with 'make install-website-service'."; \
		exit 1; \
	fi
	@echo "Updating $(WEBSITE_SERVICE_NAME) restart policy to '$(RESTART_POLICY)' and interval to '$(RESTART_SEC)' seconds..."
	@sudo sed -i -E 's/^Restart=.*/Restart=$(RESTART_POLICY)/' $(WEBSITE_SERVICE_FILE)
	@sudo sed -i -E 's/^RestartSec=.*/RestartSec=$(RESTART_SEC)/' $(WEBSITE_SERVICE_FILE)
	@echo "Reloading systemd and restarting website service..."
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(WEBSITE_SERVICE_NAME)
	@echo "New settings:"
	@sudo grep -E '^(Restart|RestartSec)=' $(WEBSITE_SERVICE_FILE) | sed 's/^/  /'

# Change service branch (dev/prod) after install

change-server-branch: check-linux
	@if [ ! -f "$(WEBSITE_SERVICE_FILE)" ]; then \
		echo "Website service file not found at $(WEBSITE_SERVICE_FILE). Install it first with 'make install-website-service'."; \
		exit 1; \
	fi
	@branch="$(BRANCH)"; \
	if [ -z "$$branch" ]; then \
		branch="$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"; \
	fi; \
	echo "Switching $(WEBSITE_SERVICE_NAME) branch to '$$branch'..."; \
	sudo sed -i -E "s/^Environment=GIT_BRANCH=.*/Environment=GIT_BRANCH=$$branch/" $(WEBSITE_SERVICE_FILE)
	@echo "Reloading systemd and restarting website service..."
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(WEBSITE_SERVICE_NAME)
	@echo "New branch configuration:"
	@sudo grep -E '^Environment=GIT_BRANCH=' $(WEBSITE_SERVICE_FILE) | sed 's/^/  /'

# Install sensor service (runs every 1 second)
install-sensor-service: check-linux check-uv check-signalk-token
	@echo "Installing $(SENSOR_SERVICE_NAME) systemd service..."
	@if [ -f "$(SENSOR_SERVICE_FILE)" ]; then \
		echo "Sensor service already exists. Uninstalling first..."; \
		sudo systemctl stop $(SENSOR_SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SENSOR_SERVICE_NAME) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi
	@echo "Rendering sensor service template from $(SENSOR_TEMPLATE_FILE)..."
	@if [ ! -f "$(SENSOR_TEMPLATE_FILE)" ]; then \
		echo "Error: Sensor template file not found at $(SENSOR_TEMPLATE_FILE)"; \
		exit 1; \
	fi
	@sed -e "s|{{DESCRIPTION}}|$(SENSOR_SERVICE_DESCRIPTION)|g" \
	     -e "s|{{USER}}|$(SENSOR_SERVICE_USER)|g" \
	     -e "s|{{WORKING_DIRECTORY}}|$(SENSOR_SERVICE_WORKING_DIR)|g" \
	     -e "s|{{EXEC_START}}|$(SENSOR_SERVICE_EXEC_START)|g" \
	     -e "s|{{RESTART_SEC}}|$(SENSOR_SERVICE_INTERVAL)|g" \
	     -e "s|{{SENSOR_HOST}}|$(SENSOR_HOST)|g" \
	     -e "s|{{SENSOR_PORT}}|$(SENSOR_PORT)|g" \
	     "$(SENSOR_TEMPLATE_FILE)" | sudo tee $(SENSOR_SERVICE_FILE) > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting sensor service..."
	@sudo systemctl enable $(SENSOR_SERVICE_NAME)
	@sudo systemctl start $(SENSOR_SERVICE_NAME)
	@echo "Sensor service installed and started successfully!"
	@echo "Service runs every $(SENSOR_SERVICE_INTERVAL) second(s)"
	@echo "Check status with: make check-sensor-service-status"
	@echo "View logs with: make sensor-logs"

# Check sensor service status
check-sensor-service-status: check-linux
	@echo "Checking status of $(SENSOR_SERVICE_NAME) service..."
	@if [ -f "$(SENSOR_SERVICE_FILE)" ]; then \
		echo "Sensor service file exists at $(SENSOR_SERVICE_FILE)"; \
		echo ""; \
		echo "Sensor Service Status:"; \
		sudo systemctl status $(SENSOR_SERVICE_NAME) --no-pager -l; \
	else \
		echo "Sensor service file not found at $(SENSOR_SERVICE_FILE)"; \
		echo "Sensor service is not installed. Run 'make install-sensor-service' to install it."; \
	fi

# Show sensor service logs
sensor-logs: check-linux
	@echo "Showing logs for $(SENSOR_SERVICE_NAME) service..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u $(SENSOR_SERVICE_NAME) -f

# Uninstall sensor service
uninstall-sensor-service: check-linux
	@echo "Uninstalling $(SENSOR_SERVICE_NAME) systemd service..."
	@if [ -f "$(SENSOR_SERVICE_FILE)" ]; then \
		echo "Stopping and disabling sensor service..."; \
		sudo systemctl stop $(SENSOR_SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SENSOR_SERVICE_NAME) 2>/dev/null || true; \
		echo "Removing sensor service file..."; \
		sudo rm -f $(SENSOR_SERVICE_FILE); \
		echo "Reloading systemd..."; \
		sudo systemctl daemon-reload; \
		echo "Sensor service uninstalled successfully!"; \
	else \
		echo "Sensor service file not found. Nothing to uninstall."; \
	fi

# Run tests
test:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running tests with uv..."; \
		uv run pytest -q; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Install pre-commit hooks
pre-commit-install: check-uv
	@echo "Installing pre-commit hooks..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run pre-commit install; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' first."; \
		exit 1; \
	fi

# Run pre-commit on all files
pre-commit-run: check-uv
	@echo "Running pre-commit on all files..."
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run pre-commit run --all-files; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' first."; \
		exit 1; \
	fi

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
