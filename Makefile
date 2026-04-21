.PHONY: server help install uninstall test test-py test-js js-install pre-commit-install lint config sync-dev status
.PHONY: install-website-service uninstall-website-service check-service-status-website show-logs-website run-website-update
.PHONY: install-polars-service uninstall-polars-service check-service-status-polars show-logs-polars run-polar-update

# Default target
.DEFAULT_GOAL := help

# System check
UNAME_S := $(shell uname -s)

# Core configuration
SERVER_PORT ?= 8000
SIGNALK_HOST ?= 192.168.8.50
SIGNALK_PORT ?= 3000
UV_BIN ?= $(shell command -v uv 2>/dev/null || true)
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

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
	@sed -e "s|{{DESCRIPTION}}|$(3)|g" \
		-e "s|{{USER}}|$$(whoami)|g" \
		-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
		-e "s|{{EXEC_START}}|$(UV_BIN) run python -m $(4) $(5)|g" \
		-e "s|{{RESTART_POLICY}}|always|g" \
		-e "s|{{RESTART_SEC}}|$(6)|g" \
		-e "s|{{GIT_BRANCH}}|$(CURRENT_BRANCH)|g" \
		-e "s|{{GIT_REMOTE}}|origin|g" \
		-e "s|{{SIGNALK_URL}}|http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self|g" \
		-e "s|{{OUTPUT_FILE}}|data/telemetry/signalk_latest.json|g" \
		"$(CURDIR)/services/systemd.service.tpl" | sudo tee /etc/systemd/system/$(2).service > /dev/null
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
	@echo "Installation and General Usage:"
	@echo "  make install        - Install all services (website, polars)"
	@echo "  make uninstall      - Uninstall all services (Linux only)"
	@echo "  make status         - Reports website and polars service statuses"
	@echo "  make config        - Interactive vessel configuration wizard"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "Development Commands:"
	@echo "  make server         - Start Python HTTP server on port $(SERVER_PORT)"
	@echo "  make test           - Run Python and JavaScript test suites"
	@echo "  make test-js        - Run JavaScript unit tests (vitest)"
	@echo "  make js-install     - Install JavaScript dependencies (npm)"
	@echo "  make pre-commit-install - Install pre-commit hooks (requires uv)"
	@echo "  make lint          - Run ruff linter and auto-fix issues on all Python files"
	@echo "  make run-website-update       - Run one website telemetry update now"
	@echo "  make run-polar-update         - Run one polar accumulation sample now"
	@echo ""
	@echo "Service management:"
	@echo "  make install-website-service    - Install website data updater service"
	@echo "  make install-polars-service     - Install polar accumulation service (10s)"
	@echo "  make uninstall-website-service  - Uninstall website service"
	@echo "  make uninstall-polars-service   - Uninstall polar accumulation service"
	@echo "  make check-service-status-website - Check website service status"
	@echo "  make check-service-status-polars  - Check polar accumulation service status"
	@echo ""
	@echo "Logs:"
	@echo "  make show-logs-website             - Show website service logs"
	@echo "  make show-logs-polars              - Show polar accumulation service logs"

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
install: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing all vessel tracker services..."
	@echo ""
	@echo "This will install:"
	@echo "  - Website data updater service"
	@echo "  - Polar accumulation service"
	@echo ""
	@$(MAKE) install-website-service
	@echo ""
	@$(MAKE) install-polars-service
	@echo ""
	@echo "All services installed successfully!"

# Uninstall all services
uninstall: check-linux
	@echo "Uninstalling all vessel tracker services..."
	@$(MAKE) uninstall-website-service
	@echo ""
	@$(MAKE) uninstall-polars-service
	@echo ""
	@echo "All services uninstalled successfully!"

# Individual service installation
install-website-service: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	$(call install-service,website,vesselwebsite,Vessel Tracker Data Updater,scripts.update_signalk_data,--interval 150,150)

install-polars-service: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing polar accumulation service..."
	@if [ -f "/etc/systemd/system/vesselpolars.service" ]; then \
		echo "vesselpolars service already exists. Uninstalling first..."; \
		sudo systemctl stop vesselpolars 2>/dev/null || true; \
		sudo systemctl disable vesselpolars 2>/dev/null || true; \
	fi
	@sed -e "s|{{DESCRIPTION}}|Vessel Polar Performance Accumulator|g" \
		-e "s|{{USER}}|$$(whoami)|g" \
		-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
		-e "s|{{EXEC_START}}|$(UV_BIN) run python -m scripts.update_polar_data --interval 10|g" \
		-e "s|{{SIGNALK_URL}}|http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self|g" \
		"$(CURDIR)/services/polars.service.tpl" | sudo tee /etc/systemd/system/vesselpolars.service > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting vesselpolars service..."
	@sudo systemctl enable vesselpolars
	@sudo systemctl start vesselpolars
	@echo "vesselpolars service installed and started successfully!"

uninstall-polars-service: check-linux
	$(call uninstall-service,vesselpolars)

check-service-status-polars: check-linux
	$(call check-service-status,vesselpolars,polars)

show-logs-polars: check-linux
	$(call show-service-logs,vesselpolars)

run-polar-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one polar accumulation sample..."
	"$(UV_BIN)" run python -m scripts.update_polar_data --interval 0 --signalk-url "http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self"

# Individual service uninstallation
uninstall-website-service: check-linux
	$(call uninstall-service,vesselwebsite)

# Service status checking
check-service-status-website: check-linux
	$(call check-service-status,vesselwebsite,website)

# Report service statuses
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
	@echo "--- Polar Accumulation Service Status ---"
	@if [ -f "/etc/systemd/system/vesselpolars.service" ]; then \
		echo "Service: vesselpolars"; \
		sudo systemctl is-active vesselpolars >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vesselpolars >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "=========================================="

# Service logs
show-logs-website: check-linux
	$(call show-service-logs,vesselwebsite)

# Run one website telemetry update (single execution)
run-website-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one website telemetry update..."
	@echo "Fetching from SignalK and writing data..."
	"$(UV_BIN)" run python -m scripts.update_signalk_data --signalk-url "http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self" --output data/telemetry/signalk_latest.json

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

# Sync dev dependencies
sync-dev:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Syncing dev dependencies..."
	@"$(UV_BIN)" sync --extra dev

# Interactive vessel configuration wizard
config:
	@echo "Starting Vessel Configuration Wizard..."
	@"$(UV_BIN)" run python -m scripts.vessel_config_wizard
