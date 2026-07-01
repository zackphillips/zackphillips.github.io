.PHONY: server help install uninstall test test-py test-js js-install pre-commit-install lint config sync-dev status
.PHONY: install-website-service uninstall-website-service check-service-status-website show-logs-website run-website-update
.PHONY: install-polars-service uninstall-polars-service check-service-status-polars show-logs-polars run-polar-update

.DEFAULT_GOAL := help

UNAME_S := $(shell uname -s)

SERVER_PORT ?= 8000
SIGNALK_HOST ?= 192.168.8.50
SIGNALK_PORT ?= 3000
UV_BIN ?= $(shell command -v uv 2>/dev/null || true)
CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)

# Install a systemd service from a template.
# Args: (1) service name, (2) description, (3) python module, (4) module args, (5) restart sec, (6) template path
define install-service
	@echo "Installing $(1) systemd service..."
	@if [ -f "/etc/systemd/system/$(1).service" ]; then \
		echo "$(1) service already exists. Uninstalling first..."; \
		sudo systemctl stop $(1) 2>/dev/null || true; \
		sudo systemctl disable $(1) 2>/dev/null || true; \
	fi
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Rendering $(1) service template..."
	@sed -e "s|{{DESCRIPTION}}|$(2)|g" \
		-e "s|{{USER}}|$$(whoami)|g" \
		-e "s|{{WORKING_DIRECTORY}}|$(CURDIR)|g" \
		-e "s|{{EXEC_START}}|$(UV_BIN) run python -m $(3) $(4)|g" \
		-e "s|{{RESTART_POLICY}}|always|g" \
		-e "s|{{RESTART_SEC}}|$(5)|g" \
		-e "s|{{GIT_BRANCH}}|$(CURRENT_BRANCH)|g" \
		-e "s|{{GIT_REMOTE}}|origin|g" \
		-e "s|{{SIGNALK_URL}}|http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self|g" \
		-e "s|{{OUTPUT_FILE}}|data/telemetry/signalk_latest.json|g" \
		"$(6)" | sudo tee /etc/systemd/system/$(1).service > /dev/null
	@echo "Reloading systemd..."
	@sudo systemctl daemon-reload
	@echo "Enabling and starting $(1) service..."
	@sudo systemctl enable $(1)
	@sudo systemctl start $(1)
	@echo "$(1) service installed and started successfully!"
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
		echo "$(1) service is not installed. Run 'make install' to install it."; \
	fi
endef

define show-service-logs
	@echo "Showing logs for $(1) service (Ctrl+C to exit)..."
	@sudo journalctl -u $(1) -f
endef

check-linux:
	@if [ "$(UNAME_S)" != "Linux" ]; then \
		echo "Error: This command only works on Linux systems"; \
		echo "Current system: $(UNAME_S)"; \
		exit 1; \
	fi

help:
	@echo "General:"
	@echo "  make install                    - Install all system services (Linux only)"
	@echo "  make uninstall                  - Remove all system services (Linux only)"
	@echo "  make status                     - Report website and polars service statuses"
	@echo "  make config                     - Interactive vessel configuration wizard"
	@echo ""
	@echo "Development:"
	@echo "  make server                     - Start local HTTP server on port $(SERVER_PORT)"
	@echo "  make test                       - Run Python and JavaScript test suites"
	@echo "  make test-py                    - Run Python tests (pytest)"
	@echo "  make test-js                    - Run JavaScript tests (vitest)"
	@echo "  make js-install                 - Install JavaScript dependencies (npm)"
	@echo "  make lint                       - Run ruff linter with auto-fix"
	@echo "  make sync-dev                   - Sync dev Python dependencies"
	@echo "  make pre-commit-install         - Install pre-commit hooks"
	@echo ""
	@echo "Manual execution:"
	@echo "  make run-website-update         - Fetch SignalK data once"
	@echo "  make run-polar-update           - Run one polar accumulation sample"
	@echo ""
	@echo "Service management:"
	@echo "  make install-website-service    - Install website data updater service"
	@echo "  make install-polars-service     - Install polar accumulation service"
	@echo "  make uninstall-website-service  - Uninstall website updater service"
	@echo "  make uninstall-polars-service   - Uninstall polar accumulation service"
	@echo "  make check-service-status-website - Check website service status"
	@echo "  make check-service-status-polars  - Check polar accumulation service status"
	@echo "  make show-logs-website          - Stream website service logs"
	@echo "  make show-logs-polars           - Stream polar accumulation service logs"

server:
	@echo "Open http://localhost:$(SERVER_PORT) in your browser"
	@echo "Press Ctrl+C to stop the server"
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@"$(UV_BIN)" run python -m http.server $(SERVER_PORT)

install: check-linux
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing all vessel tracker services..."
	@$(MAKE) install-website-service
	@echo ""
	@$(MAKE) install-polars-service
	@echo ""
	@echo "All services installed successfully!"

uninstall: check-linux
	@echo "Uninstalling all vessel tracker services..."
	@$(MAKE) uninstall-website-service
	@echo ""
	@$(MAKE) uninstall-polars-service
	@echo ""
	@echo "All services uninstalled successfully!"

install-website-service: check-linux
	$(call install-service,vesselwebsite,Vessel Tracker Data Updater,scripts.update_signalk_data,--interval 300,300,$(CURDIR)/services/systemd.service.tpl)

install-polars-service: check-linux
	$(call install-service,vesselpolars,Vessel Polar Performance Accumulator,scripts.update_polar_data,--interval 10,15,$(CURDIR)/services/polars.service.tpl)

uninstall-website-service: check-linux
	$(call uninstall-service,vesselwebsite)

uninstall-polars-service: check-linux
	$(call uninstall-service,vesselpolars)

check-service-status-website: check-linux
	$(call check-service-status,vesselwebsite)

check-service-status-polars: check-linux
	$(call check-service-status,vesselpolars)

status: check-linux
	@echo "=========================================="
	@echo "Vessel Tracker Status Report"
	@echo "=========================================="
	@echo ""
	@echo "--- Website Service ---"
	@if [ -f "/etc/systemd/system/vesselwebsite.service" ]; then \
		echo "Service: vesselwebsite"; \
		sudo systemctl is-active vesselwebsite >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vesselwebsite >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "--- Polar Accumulation Service ---"
	@if [ -f "/etc/systemd/system/vesselpolars.service" ]; then \
		echo "Service: vesselpolars"; \
		sudo systemctl is-active vesselpolars >/dev/null 2>&1 && echo "Status: ✓ Active" || echo "Status: ✗ Inactive"; \
		sudo systemctl is-enabled vesselpolars >/dev/null 2>&1 && echo "Enabled: ✓ Yes" || echo "Enabled: ✗ No"; \
	else \
		echo "Status: ✗ Not installed"; \
	fi
	@echo ""
	@echo "=========================================="

show-logs-website: check-linux
	$(call show-service-logs,vesselwebsite)

show-logs-polars: check-linux
	$(call show-service-logs,vesselpolars)

run-website-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one website telemetry update..."
	@"$(UV_BIN)" run python -m scripts.update_signalk_data --signalk-url "http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self" --output data/telemetry/signalk_latest.json

run-polar-update:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running one polar accumulation sample..."
	@"$(UV_BIN)" run python -m scripts.update_polar_data --interval 0 --signalk-url "http://$(SIGNALK_HOST):$(SIGNALK_PORT)/signalk/v1/api/vessels/self"

test: test-py test-js

test-py:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running Python tests..."
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

pre-commit-install:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Installing pre-commit hooks..."
	@uvx pre-commit install

lint:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Running ruff linter with auto-fix..."
	@uvx ruff check --fix .

sync-dev:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Syncing dev dependencies..."
	@"$(UV_BIN)" sync --extra dev

config:
	@if [ -z "$(UV_BIN)" ]; then \
		echo "Error: 'uv' is not installed. Please install uv first."; \
		echo "Visit: https://github.com/astral-sh/uv"; \
		exit 1; \
	fi
	@echo "Starting Vessel Configuration Wizard..."
	@"$(UV_BIN)" run python -m scripts.vessel_config_wizard
