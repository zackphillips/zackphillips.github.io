.PHONY: server help

# Default target
help:
	@echo "Available commands:"
	@echo "  make server  - Start Python HTTP server on port 8000"
	@echo "  make help    - Show this help message"

# Start Python HTTP server
server:
	@echo "Starting Python HTTP server on port 8000..."
	@echo "Open http://localhost:8000 in your browser"
	@echo "Press Ctrl+C to stop the server"
	python -m http.server 8000 