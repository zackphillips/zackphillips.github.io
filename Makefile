.PHONY: server help install-service logs uninstall-service check-service-status
.PHONY: test check-uv pre-commit-install pre-commit-run config
.PHONY: install-sensors run-sensors check-i2c

# Check if running on Linux
UNAME_S := $(shell uname -s)
SERVICE_NAME := vessel-tracker
SERVICE_FILE := /etc/systemd/system/$(SERVICE_NAME).service

# Optional: server port
SERVER_PORT ?= 8000

# Sensor configuration
SENSOR_HOST ?= 192.168.8.50
SENSOR_PORT ?= 3000
SENSOR_INTERVAL ?= 1.0

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
RESTART_POLICY ?= always
RESTART_SEC ?= 600

# Git/environment parameters for updater
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
	@echo "  make install-service - Install systemd service (Linux only)"
	@echo "  make check-service-status - Check service status (Linux only)"
	@echo "  make logs           - Show service logs (Linux only)"
	@echo "  make uninstall-service - Uninstall systemd service (Linux only)"
	@echo "  make change-server-update-period RESTART_SEC=600 - Change systemd update period in seconds (Linux only)"
	@echo "  make change-server-branch [BRANCH=<name>] - Switch updater branch (defaults to current git branch)"
	@echo "  make test           - Run unit/integration tests (requires git; uses uv if available)"
	@echo "  make check-uv       - Check if uv is installed and install if necessary"
	@echo "  make install-sensors - Install I2C sensor dependencies and enable I2C (Raspberry Pi only)"
	@echo "  make run-sensors    - Run I2C sensors to SignalK publisher"
	@echo "  make test-sensors   - Test SignalK connection without running sensors"
	@echo "  make check-i2c      - Check I2C devices and permissions"
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
install-service: check-linux
	@echo "Installing $(SERVICE_NAME) systemd service..."
	@if [ -f "$(SERVICE_FILE)" ]; then \
		echo "Service already exists. Uninstalling first..."; \
		sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi
	@echo "Rendering service template from $(TEMPLATE_FILE)..."
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
		 "$(TEMPLATE_FILE)" | sudo tee $(SERVICE_FILE) > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting service..."
	@sudo systemctl enable $(SERVICE_NAME)
	@sudo systemctl start $(SERVICE_NAME)
	@echo "Service installed and started successfully!"
	@echo "Check status with: make check-service-status"
	@echo "View logs with: make logs"

# Show service logs
logs: check-linux
	@echo "Showing logs for $(SERVICE_NAME) service..."
	@echo "Press Ctrl+C to exit logs"
	@sudo journalctl -u $(SERVICE_NAME) -f

# Check service status
check-service-status: check-linux
	@echo "Checking status of $(SERVICE_NAME) service..."
	@if [ -f "$(SERVICE_FILE)" ]; then \
		echo "Service file exists at $(SERVICE_FILE)"; \
		echo ""; \
		echo "Service Status:"; \
		sudo systemctl status $(SERVICE_NAME) --no-pager -l; \
	else \
		echo "Service file not found at $(SERVICE_FILE)"; \
		echo "Service is not installed. Run 'make install-service' to install it."; \
	fi

# Uninstall systemd service
uninstall-service: check-linux
	@echo "Uninstalling $(SERVICE_NAME) systemd service..."
	@if [ -f "$(SERVICE_FILE)" ]; then \
		echo "Stopping and disabling service..."; \
		sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true; \
		echo "Removing service file..."; \
		sudo rm -f $(SERVICE_FILE); \
		echo "Reloading systemd..."; \
		sudo systemctl daemon-reload; \
		echo "Service uninstalled successfully!"; \
	else \
		echo "Service file not found. Nothing to uninstall."; \
	fi

# Change service restart cadence (policy/interval) after install
change-server-update-period: check-linux
	@if [ ! -f "$(SERVICE_FILE)" ]; then \
		echo "Service file not found at $(SERVICE_FILE). Install it first with 'make install-service'."; \
		exit 1; \
	fi
	@echo "Updating $(SERVICE_NAME) restart policy to '$(RESTART_POLICY)' and interval to '$(RESTART_SEC)' seconds..."
	@sudo sed -i -E 's/^Restart=.*/Restart=$(RESTART_POLICY)/' $(SERVICE_FILE)
	@sudo sed -i -E 's/^RestartSec=.*/RestartSec=$(RESTART_SEC)/' $(SERVICE_FILE)
	@echo "Reloading systemd and restarting service..."
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(SERVICE_NAME)
	@echo "New settings:"
	@sudo grep -E '^(Restart|RestartSec)=' $(SERVICE_FILE) | sed 's/^/  /'

# Change service branch (dev/prod) after install
change-server-branch: check-linux
	@if [ ! -f "$(SERVICE_FILE)" ]; then \
		echo "Service file not found at $(SERVICE_FILE). Install it first with 'make install-service'."; \
		exit 1; \
	fi
	@branch="$(BRANCH)"; \
	if [ -z "$$branch" ]; then \
		branch="$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"; \
	fi; \
	echo "Switching $(SERVICE_NAME) branch to '$$branch'..."; \
	sudo sed -i -E "s/^Environment=GIT_BRANCH=.*/Environment=GIT_BRANCH=$$branch/" $(SERVICE_FILE)
	@echo "Reloading systemd and restarting service..."
	@sudo systemctl daemon-reload
	@sudo systemctl restart $(SERVICE_NAME)
	@echo "New branch configuration:"
	@sudo grep -E '^Environment=GIT_BRANCH=' $(SERVICE_FILE) | sed 's/^/  /'

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
install-sensors: check-linux check-uv
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
	@chmod +x scripts/sensors_to_signalk.py
	@echo "Installation complete!"
	@echo ""
	@echo "To run the sensor reader:"
	@echo "  make run-sensors"
	@echo ""
	@echo "To run with custom settings:"
	@echo "  make run-sensors SENSOR_HOST=192.168.8.50 SENSOR_PORT=3000 SENSOR_INTERVAL=1.0"
	@echo ""
	@echo "To check I2C devices:"
	@echo "  make check-i2c"

# Test SignalK connection without running sensors
test-sensors: check-uv
	@echo "Testing SignalK connection..."
	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT)"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Testing with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run scripts/sensors_to_signalk.py --host $(SENSOR_HOST) --port $(SENSOR_PORT) --test; \
	else \
		echo "Error: 'uv' is not installed. Run 'make check-uv' to install it."; \
		exit 1; \
	fi

# Run I2C sensors to SignalK publisher
run-sensors: check-uv
	@echo "Starting I2C sensors to SignalK publisher..."
	@echo "Host: $(SENSOR_HOST), Port: $(SENSOR_PORT), Interval: $(SENSOR_INTERVAL)s"
	@if command -v uv >/dev/null 2>&1; then \
		echo "Running with uv: $(UV_BIN)"; \
		"$(UV_BIN)" run scripts/sensors_to_signalk.py --host $(SENSOR_HOST) --port $(SENSOR_PORT) --interval $(SENSOR_INTERVAL); \
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

# Interactive vessel configuration wizard
config:
	@echo "Starting Vessel Configuration Wizard..."
	@python scripts/vessel_config_wizard.py