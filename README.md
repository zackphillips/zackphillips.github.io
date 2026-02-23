# Vessel Tracker

![Vessel Logo](data/vessel/logo.png)

A comprehensive marine vessel tracking and monitoring dashboard. This web application provides real-time vessel data, tide information, weather forecasts, and polar performance analysis with a modern dark/light mode interface.

## Configuring SSL Access in SignalK
1. `sudo signalk-server-setup`

## Features

### **Real-Time Vessel Monitoring**
- **Position Tracking**: GPS coordinates with location name resolution
- **Navigation Data**: Course over ground, speed over ground, speed through water
- **Environmental Data**: Wind speed/direction, water temperature
- **Electrical Systems**: Battery voltage, current, power, state of charge
- **Anchor Monitoring**: Distance from anchor position with safety radius alerts (visual only)

### **Marine Weather & Tides**
- **Tide Predictions**: NOAA tide data with nearest station detection
- **Wind Forecasts**: Multiple forecast models (wttr.in, ECMWF)
- **Wave Forecasts**: Swell height, period, and direction predictions
- **Location-Based**: All forecasts automatically update based on vessel position

### **Performance Analysis**
- **Polar Performance**: Real-time comparison with vessel polar data
- **VMG Analysis**: Velocity Made Good calculations and optimization
- **Interactive Charts**: Radar-style polar charts with current position overlay
- **Performance Metrics**: Percentage performance vs. theoretical polar speeds

### **Modern Interface**
- **Dark/Light Mode**: Toggle between themes with persistent preference
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Interactive Maps**: Leaflet-based maps with dark/light tile layers
- **Real-Time Updates**: WebSocket connection for live data streaming

## Quick Start

### **Prerequisites**
- Python 3.12 or higher
- Linux system (for system service features)
- SignalK server (optional, for real-time data)

### **Development Setup**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd zackphillips.github.io
   ```

2. **Install development tools** (if not already installed):
   ```bash
   make check-uv
   ```

3. **Install pre-commit hooks**:
   ```bash
   make pre-commit-install
   ```

4. **Start the development server**:
   ```bash
   make server
   ```

5. **Open in browser**:
   Navigate to `http://localhost:8000`

### **System Service Installation (Linux)**

For production deployment, install as a system service:

```bash
# Install as systemd service
make install-service

# Check service status
make check-service-status

# View live logs
make logs

# Uninstall service
make uninstall-service
```

## Data Sources

### **Primary Data Sources**
- **SignalK API**: Real-time vessel data via WebSocket
- **Local JSON**: Fallback to `data/telemetry/signalk_latest.json` file
- **Demo Data**: Static data when no live sources available

### **Weather & Marine Data**
- **NOAA Tides**: Automatic nearest station detection
- **Open-Meteo**: Marine weather forecasts
- **wttr.in**: Alternative weather data
- **ECMWF**: European weather model data

### **External Services**
- **OpenStreetMap**: Map tiles and location resolution
- **Marine Traffic**: Vessel tracking links
- **MyShipTracking**: Alternative tracking service

## Configuration

### **SignalK Connection**
The dashboard automatically tries to connect to SignalK at `https://192.168.8.50:3000`. To change this:

1. Edit the WebSocket URL in the JavaScript
2. Update the REST API endpoint
3. Modify the data parsing logic if needed

### **Polar Data**
Polar performance data is loaded from `data/vessel/polars.csv`. These files may be downloaded from [https://jieter.github.io/orc-data/site/](here). The file should contain:
- Wind speeds in the header row
- True wind angles in the first column
- Boat speeds for each wind speed/angle combination

### **Customization**
- **Colors**: Modify CSS variables in the `:root` and `[data-theme="dark"]` selectors
- **Layout**: Adjust grid layouts and responsive breakpoints
- **Data Fields**: Add or remove instrument readings in the data grid

## Development

### **Project Structure**
```
zackphillips.github.io/
├── index.html                    # Main dashboard file
├── Makefile                      # Build and service management
├── pyproject.toml               # Python project configuration
├── uv.lock                      # Dependency lock file
├── .pre-commit-config.yaml      # Pre-commit hooks configuration
├── README.md                    # This file
├── LICENSE                      # License file
├── assets/                      # Web app assets
│   ├── favicon.ico             # Favicon
│   ├── site.webmanifest        # Web app manifest
│   └── *.png                   # App icons
├── data/
│   ├── vessel/
│   │   ├── info.yaml           # Vessel configuration
│   │   ├── logo.png            # Vessel logo
│   │   └── polars.csv          # Polar performance data
│   ├── telemetry/
│   │   └── signalk_latest.json # Data file that is regularly updated
│   └── tide_stations.json      # NOAA tide station data
├── scripts/
│   ├── calibrate_mmc5603_heading.py  # MMC5603 magnetic heading sensor calibration
│   ├── calibrate_bno055_imu.py       # BNO055 IMU sensor calibration
│   ├── calibrate_sgp30_air_quality.py # SGP30 air quality sensor calibration
│   ├── i2c_sensor_read_and_publish.py  # I2C sensor reader and SignalK publisher
│   ├── signalk_token_management.py    # SignalK token management (create/check)
│   ├── update_signalk_data.py         # SignalK data updater script
│   └── vessel_config_wizard.py       # Configuration wizard
├── services/
│   └── systemd.service.tpl     # Systemd service template
└── tests/
    └── test_update_signalk_data_integration.py # Integration tests
```

### **Available Make Commands**
```bash
make help                 # Show all available commands
make server              # Start development server
make install-service     # Install systemd service (Linux)
make check-service-status # Check service status (Linux)
make logs                # View service logs (Linux)
make uninstall-service   # Remove systemd service (Linux)
make change-server-update-period RESTART_SEC=600 # Change update period
make change-server-branch [BRANCH=<name>] # Switch updater branch
make test                # Run unit/integration tests
make check-uv            # Check if uv is installed and install if necessary
make pre-commit-install  # Install pre-commit hooks
make pre-commit-run      # Run pre-commit on all files
make config              # Interactive vessel configuration wizard

# Sensor and SignalK Commands
make install-sensors     # Install I2C sensor dependencies (Raspberry Pi)
make run-sensors         # Run I2C sensors to SignalK publisher (one-time)
make test-sensors        # Test SignalK connection without running sensors
make check-i2c           # Check I2C devices and permissions
make install-sensor-service # Install recurring sensor service (runs every 1s)
make check-sensor-service-status # Check sensor service status (Linux)
make sensor-logs         # Show sensor service logs (Linux)
make uninstall-sensor-service # Uninstall sensor service (Linux)

# SignalK Token Management
make check-signalk-token # Check if SignalK token exists and is valid
make create-signalk-token # Create a new SignalK access token

# Sensor Calibration
make calibrate-heading # Calibrate MMC5603 magnetic heading sensor offset
make calibrate-imu     # Calibrate BNO055 IMU sensor
make calibrate-air     # Calibrate SGP30 air quality sensor
```

### **Development Tools**
This project uses modern Python development tools:

- **uv**: Fast Python package manager and project management
- **ruff**: Extremely fast Python linter and formatter
- **pre-commit**: Git hooks for code quality
- **pytest**: Testing framework

### **Data Flow**
1. **SignalK WebSocket**: Real-time data streaming
2. **REST API Fallback**: HTTP requests to SignalK server
3. **Local File**: Static JSON data file
4. **Demo Data**: Hardcoded fallback values

## Mobile Support

The dashboard is fully responsive and optimized for mobile devices:
- **Touch-friendly**: Large buttons and touch targets
- **Responsive grids**: Adapts to different screen sizes
- **Mobile charts**: Optimized chart sizes for small screens
- **Efficient loading**: Minimal data transfer for mobile networks

## Security Considerations

### **Network Access**
- **Local Network**: Designed for local network deployment
- **HTTPS**: SignalK connection uses HTTPS
- **No Authentication**: Currently no user authentication (add if needed)

### **Data Privacy**
- **Local Storage**: Theme preference stored locally
- **No External Tracking**: No analytics or tracking scripts
- **Open Source**: All code is visible and auditable

## Troubleshooting

### **Common Issues**

**Service won't start**:
```bash
make check-service-status
make logs
```

**No data showing**:
- Check SignalK server connectivity
- Verify data file exists (see project structure)
- Check browser console for errors

**Charts not updating**:
- Ensure polar data file exists at `data/vessel/polars.csv`
- Check JavaScript console for errors
- Verify data format in CSV file

**Dark mode not working**:
- Clear browser cache
- Check localStorage for theme preference
- Verify CSS variables are loaded

**Development environment issues**:
```bash
# Check if uv is installed
make check-uv

# Install pre-commit hooks
make pre-commit-install

# Install JavaScript test dependencies (once per clone)
make js-install

# Run tests
make test
```

### **Log Locations**
- **Service logs**: `journalctl -u vessel-tracker`
- **Browser logs**: Developer Tools Console
- **System logs**: `/var/log/syslog`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting:
   ```bash
   make test
   make test-js   # optional JS-only loop
   make pre-commit-run
   ```
5. Submit a pull request

## License

This project is open source. Please check the LICENSE file for details.

## About the Vessel

This tracking system is designed for marine vessels and can be configured for any vessel by updating the `data/vessel/info.json` file.

**Vessel Details**:
- **MMSI**: 338543654
- **USCG**: 1024168
- **Hull #**: BEY57004E494
- **Length**: 42.7 feet
- **Beam**: 13.9 feet
- **Draft**: 6.2 feet
