.PHONY: server help install-service logs uninstall-service check-service-status

# Check if running on Linux
UNAME_S := $(shell uname -s)
SERVICE_NAME := mermug-tracker
SERVICE_FILE := /etc/systemd/system/$(SERVICE_NAME).service

# Default target
help:
	@echo "Available commands:"
	@echo "  make server         - Start Python HTTP server on port 8000"
	@echo "  make install-service - Install systemd service (Linux only)"
	@echo "  make check-service-status - Check service status (Linux only)"
	@echo "  make logs           - Show service logs (Linux only)"
	@echo "  make uninstall-service - Uninstall systemd service (Linux only)"
	@echo "  make help           - Show this help message"

# Check Linux requirement
check-linux:
	@if [ "$(UNAME_S)" != "Linux" ]; then \
		echo "Error: This command only works on Linux systems"; \
		echo "Current system: $(UNAME_S)"; \
		exit 1; \
	fi

# Start Python HTTP server
server:
	@echo "Starting Python HTTP server on port 8000..."
	@echo "Open http://localhost:8000 in your browser"
	@echo "Press Ctrl+C to stop the server"
	python -m http.server 8000

# Install systemd service
install-service: check-linux
	@echo "Installing $(SERVICE_NAME) systemd service..."
	@if [ -f "$(SERVICE_FILE)" ]; then \
		echo "Service already exists. Uninstalling first..."; \
		sudo systemctl stop $(SERVICE_NAME) 2>/dev/null || true; \
		sudo systemctl disable $(SERVICE_NAME) 2>/dev/null || true; \
	fi
	@echo "Creating service file..."
	@sudo tee $(SERVICE_FILE) > /dev/null <<EOF
[Unit]
Description=Mermug Tracker Web Server
After=network.target

[Service]
Type=simple
User=$$(whoami)
WorkingDirectory=$$(pwd)
ExecStart=/usr/bin/python3 -m http.server 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
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