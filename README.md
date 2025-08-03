# Mermug Tracker

![Mermug Logo](mermug.png)

A comprehensive marine vessel tracking and monitoring dashboard for the S.V. Mermug. This web application provides real-time vessel data, tide information, weather forecasts, and polar performance analysis with a modern dark/light mode interface.

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
- Python 3.6 or higher
- Linux system (for system service features)
- SignalK server (optional, for real-time data)

### **Basic Setup**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd zackphillips.github.io
   ```

2. **Start the development server**:
   ```bash
   make server
   ```

3. **Open in browser**:
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
- **Local JSON**: Fallback to `signalk_latest.json` file
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
Polar performance data is loaded from `resources/polars/polars.csv`. The file should contain:
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
├── index.html              # Main dashboard file
├── Makefile                # Build and service management
├── README.md              # This file
├── mermug.png             # Vessel logo
├── signalk_latest.json    # Data file that is regularly updated
└── resources/
    └── polars/
        ├── polars.csv     # Polar performance data for our boat
        └── polars_readme.md # Source for our polar data
```

### **Available Make Commands**
```bash
make help                 # Show all available commands
make server              # Start development server
make install-service     # Install systemd service (Linux)
make check-service-status # Check service status (Linux)
make logs                # View service logs (Linux)
make uninstall-service   # Remove systemd service (Linux)
```

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
- Verify `signalk_latest.json` exists
- Check browser console for errors

**Charts not updating**:
- Ensure polar data file exists
- Check JavaScript console for errors
- Verify data format in CSV file

**Dark mode not working**:
- Clear browser cache
- Check localStorage for theme preference
- Verify CSS variables are loaded

### **Log Locations**
- **Service logs**: `journalctl -u mermug-tracker`
- **Browser logs**: Developer Tools Console
- **System logs**: `/var/log/syslog`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please check the license file for details.

## About S.V. Mermug

The S.V. Mermug is a 1994 Beneteau First 42s7 sailing vessel based in San Francisco, CA. It is owned by Zack Phillips, Chris Lalau-Kerely, and Brandon Wood

**Vessel Details**:
- **MMSI**: 338543654
- **USCG**: 1024168
- **Hull #**: BEY57004E494
- **Length**: 42.7 feet
- **Beam**: 13.9 feet
- **Draft**: 6.2 feet
