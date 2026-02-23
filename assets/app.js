const vesselUtils = window.vesselUtils;
if (!vesselUtils) {
  throw new Error('vesselUtils must be loaded before app.js');
}
const { haversine, getAnchorDistanceColor, getWindDirection } = vesselUtils;

Chart.defaults.font.family = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.font.size = 12;

let map, marker, trackLine, trackMarkers;
let anchorLayer = null;   // Leaflet circle for anchor swing radius
let trackLegend = null;   // Leaflet control for day-colour legend
let lat, lon; // Global variables for coordinates
let vesselData = null; // Global vessel information
let tideStations = null; // Global tide stations data
const DEFAULT_TIDE_LOCATION = {
  lat: 37.806,
  lon: -122.465,
  label: 'San Francisco Bay',
};

const PANEL_SKELETONS = {
  'navigation-grid': 6,
  'wind-grid': 4,
  'power-grid': 4,
  'vessel-grid': 4,
  'environment-grid': 6,
  'internet-grid': 4,
  'propulsion-grid': 2,
  'tanks-grid': 6,
};


function classifyBatteryStatus(percent) {
  if (!Number.isFinite(percent)) return null;
  if (percent >= 75) return { level: 'ok', label: 'Charged' };
  if (percent >= 45) return { level: 'warn', label: 'Low' };
  return { level: 'alert', label: 'Critical' };
}

function classifyBatteryTime(hours) {
  if (!Number.isFinite(hours)) return null;
  if (hours >= 6) return { level: 'ok', label: 'Plenty' };
  if (hours >= 2) return { level: 'warn', label: 'Soon' };
  return { level: 'alert', label: 'Short' };
}

function classifyAnchorStatus(current, max) {
  if (!Number.isFinite(current) || !Number.isFinite(max) || max <= 0) return null;
  if (current <= max * 0.85) return { level: 'ok', label: 'Safe' };
  if (current <= max * 1.05) return { level: 'warn', label: 'Edge' };
  return { level: 'alert', label: 'Drifting' };
}

function classifyPacketLoss(loss) {
  if (!Number.isFinite(loss)) return null;
  const percentage = loss <= 1 ? loss * 100 : loss;
  if (percentage < 1) return { level: 'ok', label: 'Clean' };
  if (percentage < 3) return { level: 'warn', label: 'Lossy' };
  return { level: 'alert', label: 'Dropping' };
}

function classifyTankLevel(level) {
  if (!Number.isFinite(level)) return null;
  if (level >= 0.35) return { level: 'ok', label: 'Healthy' };
  if (level >= 0.2) return { level: 'warn', label: 'Low' };
  return { level: 'alert', label: 'Refill' };
}

function classifyWasteTank(level) {
  if (!Number.isFinite(level)) return null;
  if (level <= 0.4) return { level: 'ok', label: 'Clear' };
  if (level <= 0.7) return { level: 'warn', label: 'Rising' };
  return { level: 'alert', label: 'Full' };
}

// Classify a value using SignalK meta.zones if available, otherwise return null.
// SignalK zone states: nominal/normal → ok, warn/caution → warn, alert/alarm/emergency → alert.
function classifyByZones(value, zones) {
  if (!Array.isArray(zones) || !Number.isFinite(value)) return null;
  for (const zone of zones) {
    const above = zone.lower == null || value >= zone.lower;
    const below = zone.upper == null || value <= zone.upper;
    if (above && below) {
      const s = zone.state;
      if (s === 'nominal' || s === 'normal') return { level: 'ok' };
      if (s === 'warn'    || s === 'caution') return { level: 'warn' };
      if (s === 'alert'   || s === 'alarm' || s === 'emergency') return { level: 'alert' };
    }
  }
  return null;
}

// Render a value div whose text is colored by status level (ok/warn/alert).
function colorValue(display, status) {
  if (display === 'N/A') return `<div class="value"><span class="value-na">N/A</span></div>`;
  const cls = status?.level ? ` value-${status.level}` : '';
  return `<div class="value${cls}">${display}</div>`;
}

function renderAlertSummary() {
  const el = document.getElementById('alert-summary');
  if (!el) return;
  const items = [];
  document.querySelectorAll('.info-item').forEach(item => {
    const valueEl = item.querySelector('.value-alert, .value-warn');
    if (!valueEl) return;
    const labelEl = item.querySelector('.label');
    if (!labelEl) return;
    const level = valueEl.classList.contains('value-alert') ? 'alert' : 'warn';
    items.push({ label: labelEl.textContent.trim(), value: valueEl.textContent.trim(), level });
  });
  items.sort((a, b) => (a.level === 'alert' ? -1 : 1));
  if (!items.length) { el.style.display = 'none'; return; }
  el.style.display = '';
  el.innerHTML = `
    <div class="panel-title">System Alerts</div>
    <div class="alert-chips">
      ${items.map(i => `
        <div class="alert-chip alert-chip--${i.level}">
          <span class="alert-chip__label">${i.label}</span>
          <span class="alert-chip__value">${i.value}</span>
        </div>`).join('')}
    </div>`;
}

function renderSkeletonGrid(containerId, count = 6) {
  const container = document.getElementById(containerId);
  if (!container) return;
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="info-item skeleton-card">
        <div class="skeleton-bar skeleton-label"></div>
        <div class="skeleton-bar skeleton-value"></div>
      </div>`;
  }
  container.innerHTML = html;
}

function renderForecastSkeleton(containerId, count = 4) {
  const container = document.getElementById(containerId);
  if (!container) return;
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="skeleton-card" style="height: 110px;">
        <div class="skeleton-bar skeleton-label" style="width: 50%;"></div>
        <div class="skeleton-bar skeleton-value" style="margin-top: 12px;"></div>
        <div class="skeleton-bar skeleton-label" style="width: 70%; margin-top: 12px;"></div>
      </div>`;
  }
  container.innerHTML = html;
}

function primeSkeletons() {
  Object.entries(PANEL_SKELETONS).forEach(([id, count]) => renderSkeletonGrid(id, count));
  renderForecastSkeleton('wind-forecast-grid');
  renderForecastSkeleton('wave-forecast-grid');
}

function renderEmptyState(containerId, title, subtitle = '') {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = `
    <div class="empty-state">
      <strong>${title}</strong>
      <span>${subtitle}</span>
    </div>`;
}

async function updateMapLocation(lat, lon) {
  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&zoom=10&addressdetails=1`);
    const data = await response.json();

    let locationName = "Unknown Location";

    if (data.display_name) {
      // Parse the display name to get a more concise location
      const parts = data.display_name.split(', ');
      if (parts.length >= 2) {
        // Try to get city and state/country
        const city = parts[0];
        const state = parts[1];
        locationName = `${city}, ${state}`;
      } else {
        locationName = data.display_name;
      }
    }

    document.getElementById('mapTitle').textContent = locationName;
  } catch (error) {
    console.error('Error fetching location:', error);
    document.getElementById('mapTitle').textContent = 'Location unavailable';
  }
}

// 24 distinct colors for per-day track segments (cycles if more than 24 days).
const DAY_TRACK_COLORS = [
  '#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#1abc9c', '#3498db',
  '#9b59b6', '#e91e63', '#ff5722', '#8bc34a', '#00bcd4', '#673ab7',
  '#ff9800', '#4caf50', '#03a9f4', '#9c27b0', '#f44336', '#cddc39',
  '#009688', '#2196f3', '#ff4081', '#76ff03', '#40c4ff', '#ea80fc',
];

/**
 * Normalise a positions_index entry to {latitude, longitude, timestamp,
 * speedOverGround, courseOverGroundTrue}, handling both:
 *   - Legacy format: flat keys (latitude, longitude, speedOverGround, …)
 *   - New SignalK format: values array [{path, value}, …]
 */
function parsePositionPoint(point) {
  if (!point || typeof point !== 'object') return null;

  if (Array.isArray(point.values)) {
    // New SignalK-style format
    const find = (path) => point.values.find((v) => v.path === path)?.value;
    const pos = find('navigation.position');
    const sog = find('navigation.speedOverGround');
    const cog = find('navigation.courseOverGroundTrue');
    return {
      latitude: Number(pos?.latitude),
      longitude: Number(pos?.longitude),
      timestamp: point.timestamp ?? null,
      speedOverGround: sog != null ? Number(sog) : NaN,
      courseOverGroundTrue: cog != null ? Number(cog) : NaN,
    };
  }

  // Legacy flat format
  return {
    latitude: Number(point.latitude),
    longitude: Number(point.longitude),
    timestamp: point.timestamp ?? null,
    speedOverGround: point.speedOverGround != null ? Number(point.speedOverGround) : NaN,
    courseOverGroundTrue: point.courseOverGroundTrue != null ? Number(point.courseOverGroundTrue) : NaN,
  };
}

async function loadTrack() {
  try {
    const response = await fetch(`data/telemetry/positions_index.json?ts=${Date.now()}`);
    if (!response.ok) {
      throw new Error(`Positions index not found: ${response.status}`);
    }
    const payload = await response.json();
    const rawPositions = Array.isArray(payload) ? payload : payload.positions;
    if (!Array.isArray(rawPositions) || !map) return;

    // Filter to the most recent 24 days.
    const cutoff = new Date();
    cutoff.setUTCDate(cutoff.getUTCDate() - 24);

    const positions = rawPositions
      .map(parsePositionPoint)
      .filter((p) => p
        && Number.isFinite(p.latitude)
        && Number.isFinite(p.longitude)
        && (!p.timestamp || new Date(p.timestamp) >= cutoff));

    if (!positions.length) return;

    // Group by LOCAL calendar day (YYYY-MM-DD) so one day's track is one color.
    const byDay = new Map();
    for (const p of positions) {
      let dayKey = 'unknown';
      if (p.timestamp) {
        const dt = new Date(p.timestamp);
        dayKey = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
      }
      if (!byDay.has(dayKey)) byDay.set(dayKey, []);
      byDay.get(dayKey).push(p);
    }

    // Clear previous track layers.
    if (!trackMarkers) {
      trackMarkers = L.layerGroup().addTo(map);
    } else {
      trackMarkers.clearLayers();
    }
    if (trackLine) {
      const lines = Array.isArray(trackLine) ? trackLine : [trackLine];
      lines.forEach((l) => map.removeLayer(l));
      trackLine = null;
    }

    // Draw one polyline + markers per day, cycling through 24 colours.
    const days = [...byDay.keys()].sort();
    const lines = [];
    days.forEach((day, idx) => {
      const color = DAY_TRACK_COLORS[idx % DAY_TRACK_COLORS.length];
      const pts = byDay.get(day);
      const latlngs = pts.map((p) => [p.latitude, p.longitude]);
      lines.push(L.polyline(latlngs, { color, weight: 3, opacity: 0.8 }).addTo(map));

      pts.forEach((point) => {
        const timeLabel = point.timestamp ? new Date(point.timestamp).toLocaleString() : 'N/A';
        const speedLabel = Number.isFinite(point.speedOverGround)
          ? `${(point.speedOverGround * 1.94384).toFixed(1)} kts` : 'N/A';
        const courseLabel = Number.isFinite(point.courseOverGroundTrue)
          ? `${(point.courseOverGroundTrue * 180 / Math.PI).toFixed(0)}°` : 'N/A';
        const tooltipHtml = `<strong>Time:</strong> ${timeLabel}<br/><strong>Speed:</strong> ${speedLabel}<br/><strong>Course:</strong> ${courseLabel}`;
        L.circleMarker([point.latitude, point.longitude], {
          radius: 3,
          color,
          fillColor: color,
          fillOpacity: 0.7,
          weight: 1,
        }).bindTooltip(tooltipHtml, { direction: 'top', opacity: 0.9 }).addTo(trackMarkers);
      });
    });

    trackLine = lines;

    // Build / rebuild the day-colour legend.
    if (trackLegend) { trackLegend.remove(); trackLegend = null; }
    if (days.length && map) {
      trackLegend = L.control({ position: 'bottomright' });
      trackLegend.onAdd = () => {
        const div = L.DomUtil.create('div', 'track-legend');
        div.innerHTML = days.map((day, idx) => {
          const color = DAY_TRACK_COLORS[idx % DAY_TRACK_COLORS.length];
          const label = new Date(`${day}T12:00:00`).toLocaleDateString([], { month: 'short', day: 'numeric' });
          return `<div class="track-legend-item">
            <span class="track-legend-swatch" style="background:${color}"></span>
            <span>${label}</span>
          </div>`;
        }).join('');
        return div;
      };
      trackLegend.addTo(map);
    }
  } catch (error) {
    console.warn('Unable to load track data:', error);
  }
}

// Get all tide stations from loaded JSON data
function getAllStations() {
  if (!tideStations) return [];

  // New format: tideStations.stations is a flat array
  return tideStations.stations || [];
}

let tideChartInstance = null;
let polarChartInstance = null;
let polarData = null;
let currentEnv = null; // Global environment data
let currentNav = null; // Global navigation data
let isDrawingPolarChart = false; // Flag to prevent multiple simultaneous chart draws
let lastPolarChartUpdate = 0; // Timestamp of last chart update
const SNAPSHOT_INDEX_URL = 'data/telemetry/snapshots_index.json';
const SPARKLINE_POINTS = 60;
let seriesByPath = null;
let seriesPromise = null;
let refreshSparklines = null; // set once initInlineSparklines is ready

// ── Unit-toggle configuration ──────────────────────────────────────────────
// Each group lists unit options in cycle order. Clicking/tapping any info-item
// with a matching data-unit-group cycles to the next unit in the list.
const UNIT_GROUPS = {
  speed: [
    { unit: 'kts',  transform: v => v * 1.94384,  digits: 1 },
    { unit: 'mph',  transform: v => v * 2.23694,   digits: 1 },
    { unit: 'km/h', transform: v => v * 3.6,       digits: 1 },
  ],
  temperature: [
    { unit: '°F', transform: v => (v - 273.15) * 9 / 5 + 32, digits: 1 },
    { unit: '°C', transform: v => v - 273.15,                 digits: 1 },
  ],
  pressure: [
    { unit: 'mbar', transform: v => v / 100,       digits: 1 },
    { unit: 'inHg', transform: v => v * 0.0002953, digits: 2 },
  ],
  distance: [
    { unit: 'nm', transform: v => v / 1852,    digits: 1 },
    { unit: 'km', transform: v => v / 1000,    digits: 2 },
    { unit: 'mi', transform: v => v / 1609.34, digits: 1 },
  ],
  length: [
    { unit: 'ft', transform: v => v * 3.28084, digits: 1 },
    { unit: 'm',  transform: v => v,            digits: 1 },
  ],
};

// Maps SignalK paths to a UNIT_GROUPS key for sparkline display config.
const PATH_TO_UNIT_GROUP = {
  'navigation.speedOverGround':      'speed',
  'navigation.speedThroughWater':    'speed',
  'environment.wind.speedTrue':      'speed',
  'environment.wind.speedApparent':  'speed',
  'navigation.trip.log':             'distance',
  'navigation.log':                  'distance',
  'environment.water.temperature':   'temperature',
  'environment.inside.temperature':  'temperature',
  'environment.inside.pressure':     'pressure',
  'navigation.anchor.currentRadius': 'length',
};

// Persisted unit preferences: { groupName: cycleIndex }
const UNIT_PREFS_KEY = 'unitPrefs_v2'; // bump when UNIT_GROUPS defaults change
const unitPrefs = (() => {
  try { return JSON.parse(localStorage.getItem(UNIT_PREFS_KEY) || '{}'); }
  catch { return {}; }
})();

const getUnitCfg = (group) =>
  UNIT_GROUPS[group][(unitPrefs[group] || 0) % UNIT_GROUPS[group].length];

// Format a raw SI value using the active unit preference for a group.
const fmtUnit = (group, rawSI) => {
  if (rawSI == null || !Number.isFinite(rawSI)) return 'N/A';
  const { transform, unit, digits } = getUnitCfg(group);
  return `${transform(rawSI).toFixed(digits)}\u00a0${unit}`;
};

const hasValidCoordinates = (latitude, longitude) =>
  Number.isFinite(latitude) && Number.isFinite(longitude);

function resolveTidePosition(currentLat, currentLon) {
  if (hasValidCoordinates(currentLat, currentLon)) {
    return {
      lat: currentLat,
      lon: currentLon,
      usingFallback: false,
      label: 'current position',
    };
  }

  const fallbackFromVessel = vesselData?.default_location;
  if (
    fallbackFromVessel &&
    hasValidCoordinates(fallbackFromVessel.lat, fallbackFromVessel.lon)
  ) {
    return {
      lat: fallbackFromVessel.lat,
      lon: fallbackFromVessel.lon,
      usingFallback: true,
      label: fallbackFromVessel.label || 'default vessel location',
    };
  }

  return {
    ...DEFAULT_TIDE_LOCATION,
    usingFallback: true,
    label: DEFAULT_TIDE_LOCATION.label,
  };
}

// Load vessel information from YAML file
async function loadVesselData() {
  try {
    const response = await fetch('data/vessel/info.yaml');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const yamlText = await response.text();
    
    // Parse YAML using js-yaml library
    if (typeof jsyaml === 'undefined') {
      throw new Error('js-yaml library not loaded');
    }
    vesselData = jsyaml.load(yamlText);
    
    // Add default_location if not present
    if (!vesselData.default_location) {
      vesselData.default_location = {
        lat: 37.806,
        lon: -122.465,
        label: 'San Francisco Bay'
      };
    }
    
    console.log('Vessel data loaded:', vesselData);
    updateVesselLinks();
  } catch (error) {
    console.error('Error loading vessel data:', error);
    // Set default values if loading fails
    vesselData = {
      name: "S.V.Mermug",
      mmsi: "338543654",
      uscg_number: "1024168",
      hull_number: "BEY57004E494",
      default_location: {
        lat: 37.806,
        lon: -122.465,
        label: 'San Francisco Bay'
      }
    };
    updateVesselLinks();
  }
}

// Load tide stations information from JSON file
async function loadTideStations() {
  try {
    const response = await fetch('data/tide_stations.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    tideStations = await response.json();
    console.log('Tide stations data loaded:', tideStations);
  } catch (error) {
    console.error('Error loading tide stations data:', error);
    // Set default values if loading fails
    tideStations = {
      stations: [
        { id: "9414290", name: "San Francisco", lat: 37.806, lon: -122.465 }
      ]
    };
  }
}

// Update vessel links with data from JSON
function updateVesselLinks() {
  if (!vesselData) return;

  // Update page title and dynamic references
  if (vesselData.name) {
    const pageTitle = document.getElementById('page-title');
    if (pageTitle) {
      pageTitle.textContent = `${vesselData.name} Tracker`;
    }

    // Update document title
    document.title = `${vesselData.name} Tracker`;

    // Update logo alt text
    const logoImg = document.querySelector('img[src="data/vessel/logo.png"]');
    if (logoImg) {
      logoImg.alt = `${vesselData.name} Logo`;
    }

    // Update WiFi note
    const wifiNote = document.querySelector('.wifi-note');
    if (wifiNote) {
      wifiNote.textContent = `*Only works on ${vesselData.name} WiFi`;
    }
  }

  // Construct SignalK URLs from base configuration
  const signalk = vesselData.signalk;
  if (signalk?.host && signalk?.port && signalk?.protocol) {
    const baseUrl = `${signalk.protocol}://${signalk.host}:${signalk.port}`;
    const wsUrl = `wss://${signalk.host}:${signalk.port}`;

    // Store constructed URLs for use in other functions
    vesselData.signalk.base_url = baseUrl;
    vesselData.signalk.admin_url = `${baseUrl}/admin/#/webapps`;
    vesselData.signalk.freeboard_url = `${baseUrl}/@signalk/freeboard-sk`;
    vesselData.signalk.api_url = `${baseUrl}/signalk/v1/api/vessels/self`;
    vesselData.signalk.websocket_url = `${wsUrl}/signalk/v1/stream`;
  }

  // Construct external tracking links using MMSI
  if (vesselData.mmsi) {
    vesselData.links = {
      marinetraffic: `https://www.marinetraffic.com/en/ais/details/ships/mmsi:${vesselData.mmsi}`,
      myshiptracking: `https://www.myshiptracking.com/vessels/mmsi-${vesselData.mmsi}`
    };
  }

  // Update SignalK links
  const signalkAdminLink = document.getElementById('signalk-admin-link');
  const signalkFreeboardLink = document.getElementById('signalk-freeboard-link');
  const signalkAnchorAlarmLink = document.getElementById('signalk-anchor-alarm-link');
  const marinetrafficLink = document.getElementById('marinetraffic-link');
  const myshiptrackingLink = document.getElementById('myshiptracking-link');

  if (signalkAdminLink && vesselData.signalk?.admin_url) {
    signalkAdminLink.href = vesselData.signalk.admin_url;
  }
  if (signalkFreeboardLink && vesselData.signalk?.freeboard_url) {
    signalkFreeboardLink.href = vesselData.signalk.freeboard_url;
  }
  if (signalkAnchorAlarmLink && vesselData.signalk?.host) {
    // SignalK anchor alarm is typically available at the SignalK server root with anchor alarm plugin
    signalkAnchorAlarmLink.href = `http://${vesselData.signalk.host}:${vesselData.signalk.port || 3000}/`;
  }
  if (marinetrafficLink && vesselData.links?.marinetraffic) {
    marinetrafficLink.href = vesselData.links.marinetraffic;
  }
  if (myshiptrackingLink && vesselData.links?.myshiptracking) {
    myshiptrackingLink.href = vesselData.links.myshiptracking;
  }
}
let themeChangeTimeout = null; // Timeout for theme change debouncing
let isThemeChanging = false; // Flag to prevent multiple theme changes

// Find nearest NOAA tide station from lat/lon
// Uses local lookup table (fast and reliable)
// Prioritizes known-working stations for certain areas
async function findNearestNOAAStation(lat, lon) {
  const stations = getAllStations();
  if (!stations || stations.length === 0) {
    throw new Error('No tide stations available in lookup table');
  }
  
  // For San Francisco Bay area, prefer San Francisco station (9414290) which reliably supports predictions
  // South Beach Harbor and most SF locations should use SF station
  const isSFBayArea = lat >= 37.7 && lat <= 37.9 && lon >= -122.5 && lon <= -122.3;
  if (isSFBayArea) {
    const sfStation = stations.find(s => s.id === '9414290');
    if (sfStation) {
      console.debug('SF Bay area detected, preferring San Francisco station');
      return sfStation;
    }
  }
  
  // For other areas, find nearest station using haversine distance
  const nearest = stations.reduce((a, b) =>
    haversine(lat, lon, a.lat, a.lon) < haversine(lat, lon, b.lat, b.lon) ? a : b
  );
  
  return nearest;
}

async function drawTideGraph(lat, lon, tidePositionMeta = {}) {
  const {
    usingFallback = false,
    label: fallbackLabel = 'default location',
  } = tidePositionMeta;
  
  // Find nearest station using NOAA Metadata API
  let nearest;
  try {
    nearest = await findNearestNOAAStation(lat, lon);
  } catch (error) {
    console.error('Error finding nearest station:', error);
    const tideHeader = document.getElementById("tideHeader");
    if (tideHeader) tideHeader.textContent = "Tides unavailable (error finding station)";
    return;
  }

  // Calculate distance in nautical miles
  const distKm = haversine(lat, lon, nearest.lat, nearest.lon);
  const distNm = (distKm / 1.852).toFixed(1);

  // Update title element above the chart
  const locationDescriptor = usingFallback ? fallbackLabel : 'current position';
  const fallbackSuffix = usingFallback ? ' — waiting for live GPS data' : '';
  document.getElementById("tideHeader").textContent =
    `Tides near ${nearest.name} (Station #${nearest.id} - ${distNm} NM from ${locationDescriptor})${fallbackSuffix}`;


  const now = new Date();
  // NOAA predictions are future-only, so start from current time
  const startTime = new Date(now.getTime());
  const endTime = new Date(now.getTime() + 30 * 60 * 60 * 1000); // 30 hours forward


  // NOAA expects YYYYMMDD for begin_date/end_date
  function fmtYYYYMMDD(d) {
    const y = d.getUTCFullYear();
    const m = String(d.getUTCMonth() + 1).padStart(2, '0');
    const da = String(d.getUTCDate()).padStart(2, '0');
    return `${y}${m}${da}`;
  }
  const begin = fmtYYYYMMDD(startTime);
  const end = fmtYYYYMMDD(endTime);

  // Build NOAA API URL according to official documentation
  // https://api.tidesandcurrents.noaa.gov/api/prod/
  const buildUrl = (stationId) => {
    const params = new URLSearchParams({
      product: 'predictions',
      application: 'vessel-tracker',
      begin_date: begin,
      end_date: end,
      datum: 'MLLW',
      station: stationId,
      time_zone: 'gmt',
      units: 'english',
      interval: 'h',
      format: 'json'
    });
    return `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?${params.toString()}`;
  };
  
  let targetStation = nearest;
  let url = buildUrl(targetStation.id);
  const fallbackStation = { id: '9414290', name: 'San Francisco', lat: 37.806, lon: -122.465 };
  let attemptedFallback = false;

  try {
    console.debug('Tide fetch: attempting station', {
      id: targetStation.id,
      name: targetStation.name,
      lat: targetStation.lat,
      lon: targetStation.lon,
      url,
      begin_date: begin,
      end_date: end
    });
    
    let res;
    let json;
    
    // Try primary station
    try {
      res = await fetch(url);
      if (res.ok) {
        json = await res.json();
        // Check for NOAA API error in response (they sometimes return 200 with error object)
        if (json.error) {
          throw new Error(json.error.message || JSON.stringify(json.error));
        }
      } else {
        // Try to get error details from response body
        let errorDetails = res.statusText;
        try {
          const errorBody = await res.text();
          if (errorBody) {
            try {
              const errorJson = JSON.parse(errorBody);
              errorDetails = errorJson.error?.message || errorJson.message || errorBody;
            } catch {
              errorDetails = errorBody;
            }
          }
        } catch {
          // Ignore errors parsing error response
        }
        throw new Error(`HTTP ${res.status}: ${errorDetails}`);
      }
    } catch (error) {
      // If primary station fails, try fallback (San Francisco is known to work)
      if (!attemptedFallback && targetStation.id !== fallbackStation.id) {
        console.warn('Primary station failed, retrying with fallback 9414290 (San Francisco)', error);
        attemptedFallback = true;
        targetStation = fallbackStation;
        url = buildUrl(fallbackStation.id);
        console.debug('Tide fetch: attempting fallback station', {
          id: targetStation.id,
          name: targetStation.name,
          url
        });
        
        try {
          res = await fetch(url);
          if (res.ok) {
            json = await res.json();
            // Check for NOAA API error in response
            if (json.error) {
              throw new Error(json.error.message || JSON.stringify(json.error));
            }
          } else {
            // Try to get error details from response body
            let errorDetails = res.statusText;
            try {
              const errorBody = await res.text();
              if (errorBody) {
                try {
                  const errorJson = JSON.parse(errorBody);
                  errorDetails = errorJson.error?.message || errorJson.message || errorBody;
                } catch {
                  errorDetails = errorBody;
                }
              }
            } catch {
              // Ignore errors parsing error response
            }
            throw new Error(`NOAA API ${res.status}: ${errorDetails}`);
          }
        } catch (retryError) {
          throw new Error(`Failed to fetch tide data: ${retryError.message || 'Network error'}`);
        }
      } else {
        // Already tried fallback or it was the fallback, re-throw
        throw error;
      }
    }
    const rawData = Array.isArray(json?.predictions) ? json.predictions : [];
    if (rawData.length === 0) {
      console.warn('No tide predictions returned from NOAA for station', {
        id: targetStation.id,
        name: targetStation.name,
        lat: targetStation.lat,
        lon: targetStation.lon,
        url
      });
      const tideHeader = document.getElementById("tideHeader");
      if (tideHeader) tideHeader.textContent = `Tides in ${targetStation.name} (no predictions available)`;
      return;
    }

    const data = rawData
      .map(d => ({ t: new Date(d.t), v: parseFloat(d.v) }))
      .filter(d => d.t >= startTime && d.t <= endTime);


    const labels = data.map(d =>
    new Date(d.t.getTime() - d.t.getTimezoneOffset() * 60000)
      .toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
  );
    const heights = data.map(d => d.v);

    const peaks = [];
    for (let i = 1; i < heights.length - 1; i++) {
      if ((heights[i] > heights[i - 1] && heights[i] > heights[i + 1]) ||
          (heights[i] < heights[i - 1] && heights[i] < heights[i + 1])) {
        peaks.push({ i, value: heights[i], time: labels[i] });
      }
    }

    // Find the current tide height (closest time to now)
    const nowUTC = new Date(Date.now() + new Date().getTimezoneOffset() * 60000);

    let currentIndex = 0;
    let minDiff = Infinity;
    data.forEach((d, i) => {
      const diff = Math.abs(d.t - nowUTC);
      if (diff < minDiff) {
        minDiff = diff;
        currentIndex = i;
      }
    });

    const canvas = document.getElementById('tideChart');
    canvas.height = 250;
    const ctx = canvas.getContext('2d');

    if (tideChartInstance) {
      tideChartInstance.destroy();
    }

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    tideChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: `Tide Height (${targetStation.name})`,
            data: heights,
            borderColor: isDark ? '#60a5fa' : '#2563eb',
            backgroundColor: isDark ? 'rgba(96,165,250,0.12)' : 'rgba(37,99,235,0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
          },
          {
            label: 'Now',
            data: heights.map((v, i) => (i === currentIndex ? v : null)),
            borderColor: 'transparent',
            backgroundColor: '#e74c3c',
            pointRadius: 5,
            pointHoverRadius: 6,
            type: 'line',
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              title: ctx => `Time: ${ctx[0].label}`,
              label: ctx => `Height: ${ctx.raw} ft`
            }
          },
          legend: { display: false },
          annotation: {
            annotations: peaks.map(p => ({
              type: 'label',
              xValue: labels[p.i],
              yValue: p.value,
              content: `${p.value.toFixed(1)} ft @ ${p.time}`,
              backgroundColor: isDark ? 'rgba(96,165,250,0.9)' : 'rgba(37,99,235,0.85)',
              color: '#ffffff',
              yAdjust: -20,
              position: 'center',
              borderColor: isDark ? '#60a5fa' : '#2563eb',
              borderWidth: 1
            }))
          }
        },
        scales: {
          x: {
            grid: {
              color: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.08)'
            },
            ticks: {
              color: isDark ? '#ffffff' : '#2c3e50'
            },
            title: {
              display: true,
              text: `Tides as of ${now.getMonth() + 1}/${now.getDate()}/${now.getFullYear()}`,
              color: isDark ? '#ffffff' : '#2c3e50'
            }
          },
          y: {
            grid: {
              color: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.08)'
            },
            ticks: {
              color: isDark ? '#ffffff' : '#2c3e50'
            },
            title: {
              display: true,
              text: "Tide Height (ft)",
              color: isDark ? '#ffffff' : '#2c3e50'
            },
            min: Math.min(...heights) - 1,
            max: Math.max(...heights) + 1
          }
        }
      },
      plugins: [Chart.registry.getPlugin('annotation')]
    });
  } catch (err) {
    console.error("Tide data fetch error:", err);
  }
}

async function loadData() {

  function findLatestTimestamp(obj) {
    let latest = null;

    function search(o) {
      if (o && typeof o === "object") {
        for (const key in o) {
          if (key === "timestamp" && typeof o[key] === "string") {
            const t = new Date(o[key]);
            if (!isNaN(t.getTime()) && (!latest || t > latest)) {
              latest = t;
            }
          } else if (typeof o[key] === "object") {
            search(o[key]);
          }
        }
      }
    }

    search(obj);
    return latest;
  }
  const formatTimestamp = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleString();
  };

  const withUpdated = (description, node) => {
    const formatted = formatTimestamp(node?.timestamp);
    return formatted ? `${description}\nLast updated: ${formatted}` : description;
  };

  const withUpdatedNodes = (description, ...nodes) => {
    for (const node of nodes) {
      const formatted = formatTimestamp(node?.timestamp);
      if (formatted) {
        return `${description}\nLast updated: ${formatted}`;
      }
    }
    return description;
  };

  const toSnapshotFilename = (timestamp) => {
    if (!timestamp) return null;
    const normalized = timestamp.replace('Z', '+00:00');
    const datePart = normalized.split('+')[0];
    if (!datePart) return null;
    return `${datePart.replace(/:/g, '-')}Z.json`;
  };

  const buildSeriesFromSnapshots = (snapshots) => {
    const map = new Map();
    for (const snapshot of snapshots) {
      if (!snapshot || typeof snapshot !== 'object') continue;

      // Support both formats:
      //   New: SignalK delta  → { context, updates: [{ timestamp, values: [{path, value}] }] }
      //   Legacy:             → { timestamp, numericValues: { path: value } }
      const update = snapshot.updates?.[0];
      const timestamp = update?.timestamp || snapshot.timestamp || snapshot.time || null;
      const date = timestamp ? new Date(timestamp) : null;
      if (!date || Number.isNaN(date.getTime())) continue;

      if (Array.isArray(update?.values)) {
        // New SignalK format
        for (const { path, value } of update.values) {
          if (typeof value === 'number' && Number.isFinite(value)) {
            const list = map.get(path) || [];
            list.push({ t: date, v: value });
            map.set(path, list);
          }
        }
      } else {
        // Legacy numericValues format
        const values = snapshot.numericValues;
        if (!values || typeof values !== 'object') continue;
        Object.entries(values).forEach(([path, value]) => {
          if (typeof value !== 'number' || !Number.isFinite(value)) return;
          const list = map.get(path) || [];
          list.push({ t: date, v: value });
          map.set(path, list);
        });
      }
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.t - b.t);
    }
    return map;
  };

  const loadSeries = async () => {
    if (seriesByPath) return seriesByPath;
    if (seriesPromise) return seriesPromise;
    seriesPromise = fetch(`${SNAPSHOT_INDEX_URL}?ts=${Date.now()}`)
      .then((res) => (res.ok ? res.json() : null))
      .then(async (payload) => {
        const positions = Array.isArray(payload) ? payload : payload?.positions;
        if (!Array.isArray(positions) || !positions.length) {
          seriesByPath = new Map();
          return seriesByPath;
        }
        const recent = positions.slice(-SPARKLINE_POINTS);
        const files = recent
          .map((entry) => entry?.file || toSnapshotFilename(entry?.timestamp))
          .filter(Boolean);
        const snapshots = await Promise.all(
          files.map((file) =>
            fetch(`data/telemetry/${file}?ts=${Date.now()}`)
              .then((res) => (res.ok ? res.json() : null))
              .catch(() => null)
          )
        );
        seriesByPath = buildSeriesFromSnapshots(snapshots);
        return seriesByPath;
      })
      .catch(() => {
        seriesByPath = new Map();
        return seriesByPath;
      });
    return seriesPromise;
  };

  // Unit conversion config keyed by SignalK path.
  // transform: converts raw SI value to display value; unit: label shown next to min/max.
  const PATH_DISPLAY_CONFIG = {
    'navigation.speedOverGround':                        { transform: v => v * 1.94384,                    unit: 'kts'   },
    'navigation.speedThroughWater':                      { transform: v => v * 1.94384,                    unit: 'kts'   },
    'navigation.trip.log':                               { transform: v => v / 1852,                       unit: 'nm'    },
    'navigation.log':                                    { transform: v => v / 1852,                       unit: 'nm'    },
    'navigation.attitude.roll':                          { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'navigation.attitude.pitch':                         { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'navigation.courseOverGroundTrue':                   { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'navigation.headingMagnetic':                        { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'navigation.magneticVariation':                      { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'navigation.anchor.currentRadius':                   { transform: v => v * 3.28084,                    unit: 'ft'    },
    'navigation.anchor.bearingTrue':                     { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'steering.rudderAngle':                              { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'environment.wind.speedTrue':                        { transform: v => v * 1.94384,                    unit: 'kts'   },
    'environment.wind.angleTrue':                        { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'environment.wind.angleApparent':                    { transform: v => v * 180 / Math.PI,              unit: '°'     },
    'environment.wind.speedApparent':                    { transform: v => v * 1.94384,                    unit: 'kts'   },
    'electrical.batteries.house.voltage':                { transform: v => v,                              unit: 'V'     },
    'electrical.batteries.house.current':                { transform: v => v,                              unit: 'A'     },
    'electrical.batteries.house.power':                  { transform: v => v,                              unit: 'W'     },
    'electrical.batteries.house.capacity.stateOfCharge': { transform: v => v * 100,                        unit: '%'     },
    'electrical.batteries.house.capacity.timeRemaining': { transform: v => v / 3600,                       unit: 'hrs'   },
    'environment.water.temperature':                     { transform: v => (v - 273.15) * 9/5 + 32,       unit: '°F'    },
    'environment.inside.temperature':                    { transform: v => (v - 273.15) * 9/5 + 32,       unit: '°F'    },
    'environment.inside.humidity':                       { transform: v => v * 100,                        unit: '%'     },
    'environment.inside.pressure':                       { transform: v => v / 100,                        unit: 'mbar'  },
    'environment.inside.airQuality.tvoc':                { transform: v => v,                              unit: 'ppb'   },
    'environment.inside.airQuality.eco2':                { transform: v => v,                              unit: 'ppm'   },
    'internet.speed.download':                           { transform: v => v,                              unit: 'Mbps'  },
    'internet.speed.upload':                             { transform: v => v,                              unit: 'Mbps'  },
    'internet.ping.latency':                             { transform: v => v,                              unit: 'ms'    },
    'internet.ping.jitter':                              { transform: v => v,                              unit: 'ms'    },
    'internet.packetLoss':                               { transform: v => v <= 1 ? v * 100 : v,          unit: '%'     },
    'propulsion.port.revolutions':                       { transform: v => v * 60,                         unit: 'RPM'   },
    'tanks.fuel.0.currentLevel':                         { transform: v => v * 100,                        unit: '%'     },
    'tanks.fuel.reserve.currentLevel':                   { transform: v => v * 100,                        unit: '%'     },
    'tanks.freshWater.0.currentLevel':                   { transform: v => v * 100,                        unit: '%'     },
    'tanks.freshWater.1.currentLevel':                   { transform: v => v * 100,                        unit: '%'     },
    'tanks.propane.a.currentLevel':                      { transform: v => v * 100,                        unit: '%'     },
    'tanks.propane.b.currentLevel':                      { transform: v => v * 100,                        unit: '%'     },
    'tanks.blackwater.bow.currentLevel':                 { transform: v => v * 100,                        unit: '%'     },
    'tanks.liveWell.0.currentLevel':                     { transform: v => v * 100,                        unit: '%'     },
  };

  const renderSparkline = (canvas, points, displayConfig = {}, colors = {}) => {
    const { transform = v => v, unit = '' } = displayConfig;
    const {
      line: lineColor     = 'rgba(255, 255, 255, 0.85)',
      axis: axisColor     = 'rgba(255, 255, 255, 0.25)',
      label: labelColor   = 'rgba(255, 255, 255, 0.6)',
      noData: noDataColor = 'rgba(255, 255, 255, 0.5)',
    } = colors;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!points || points.length < 2) {
      ctx.fillStyle = noDataColor;
      ctx.font = '10px system-ui,-apple-system,sans-serif';
      ctx.fillText('No data', 6, canvas.height / 2 + 4);
      return;
    }
    const formatValue = (value) => {
      if (!Number.isFinite(value)) return '';
      const abs = Math.abs(value);
      if (abs >= 1000) return `${(value / 1000).toFixed(1)}k`;
      if (abs >= 100 || abs === 0) return value.toFixed(0);
      if (abs >= 10) return value.toFixed(1);
      return value.toFixed(2);
    };
    const formatTime = (date) =>
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });

    const rawValues = points.map((p) => p.v);
    const displayValues = rawValues.map(transform);
    const min = Math.min(...displayValues);
    const max = Math.max(...displayValues);
    const rawMin = Math.min(...rawValues);
    const rawMax = Math.max(...rawValues);
    const rawRange = rawMax - rawMin || 1;

    const padding = { top: 8, right: 8, bottom: 20, left: 34 };
    const w = canvas.width - padding.left - padding.right;
    const h = canvas.height - padding.top - padding.bottom;
    const axisX = canvas.height - padding.bottom;
    const axisY = padding.left;

    // Axes
    ctx.strokeStyle = axisColor;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(axisY, padding.top);
    ctx.lineTo(axisY, axisX);
    ctx.lineTo(canvas.width - padding.right, axisX);
    ctx.stroke();

    // Y-axis labels (right-aligned into left padding, no unit to save space)
    ctx.fillStyle = labelColor;
    ctx.font = '9px system-ui,-apple-system,sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText(`${formatValue(max)}${unit}`, axisY - 2, padding.top);
    ctx.textBaseline = 'bottom';
    ctx.fillText(`${formatValue(min)}${unit}`, axisY - 2, axisX);

    // X-axis time ticks (4 labels: start, ⅓, ⅔, end)
    const tFirst = points[0].t.getTime();
    const tLast  = points[points.length - 1].t.getTime();
    const numTicks = 3;
    ctx.font = '9px system-ui,-apple-system,sans-serif';
    ctx.textBaseline = 'top';
    for (let i = 0; i <= numTicks; i++) {
      const ratio = i / numTicks;
      const x = padding.left + ratio * w;
      const tickDate = new Date(tFirst + ratio * (tLast - tFirst));
      ctx.textAlign = i === 0 ? 'left' : i === numTicks ? 'right' : 'center';
      ctx.fillText(formatTime(tickDate), x, axisX + 3);
      // tick mark
      ctx.strokeStyle = axisColor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, axisX);
      ctx.lineTo(x, axisX + 3);
      ctx.stroke();
    }

    // Data line
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    points.forEach((point, index) => {
      const x = padding.left + (index / (points.length - 1)) * w;
      const y = padding.top + (1 - (point.v - rawMin) / rawRange) * h;
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };

  /**
   * Render small inline sparkline charts directly inside each .info-item card.
   * Safe to call multiple times — re-renders existing canvases in place.
   * Also exposed as module-level refreshSparklines for the theme toggle.
   */
  const SPARKLINE_HEIGHT = 80;

  const initInlineSparklines = async () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const colors = {
      line:   isDark ? 'rgba(96, 165, 250, 0.95)'  : 'rgba(37, 99, 235, 0.85)',
      axis:   isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.12)',
      label:  isDark ? 'rgba(255, 255, 255, 0.45)' : 'rgba(0, 0, 0, 0.4)',
      noData: isDark ? 'rgba(255, 255, 255, 0.25)' : 'rgba(0, 0, 0, 0.2)',
    };

    const seriesMap = await loadSeries();
    if (!seriesMap || !seriesMap.size) return;

    // Render a canvas per info-item.
    document.querySelectorAll('.info-item[data-path]').forEach((item) => {
      const path = item.dataset.path;
      const list = seriesMap.get(path);
      if (!list || !list.length) return;

      let canvas = item.querySelector('.sparkline-inline');
      if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.className = 'sparkline-inline';
        canvas.height = SPARKLINE_HEIGHT;
        canvas.style.display = 'none'; // hidden by default
        item.appendChild(canvas);
      }
      canvas.width = item.clientWidth || 120;
      canvas.height = SPARKLINE_HEIGHT;

      const points = list.slice(-SPARKLINE_POINTS);
      const grp = PATH_TO_UNIT_GROUP[path];
      const displayCfg = grp
        ? { transform: getUnitCfg(grp).transform, unit: getUnitCfg(grp).unit }
        : (PATH_DISPLAY_CONFIG[path] || {});
      renderSparkline(canvas, points, displayCfg, colors);
    });

    // Add a toggle button to each panel that has at least one sparkline canvas.
    document.querySelectorAll('.info-panel').forEach((panel) => {
      const sparklines = panel.querySelectorAll('.sparkline-inline');
      if (!sparklines.length) return;

      // Don't add a second button on re-render.
      if (panel.querySelector('.sparkline-toggle-btn')) return;

      // The header is always the first direct child div of the panel.
      const header = panel.querySelector(':scope > div:first-child');
      if (!header) return;

      const btn = document.createElement('button');
      btn.className = 'sparkline-toggle-btn';
      btn.textContent = '📈 History';
      btn.dataset.open = 'false';

      // Make the header a flex row so the button sits on the right.
      header.style.display = 'flex';
      header.style.justifyContent = 'space-between';
      header.style.alignItems = 'center';
      header.appendChild(btn);

      btn.addEventListener('click', () => {
        const opening = btn.dataset.open === 'false';
        panel.querySelectorAll('.sparkline-inline').forEach((c) => {
          c.style.display = opening ? 'block' : 'none';
        });
        btn.dataset.open = opening ? 'true' : 'false';
        btn.textContent = opening ? '📉 Hide History' : '📈 History';
      });
    });
  };

  // Expose so theme toggle can re-render sparklines with updated colors.
  refreshSparklines = initInlineSparklines;

  try {
    console.log('Starting to load data...');
    initInlineSparklines(); // kick off async — renders once series data loads

    // Load data from local file
    let res;
    let data;
    let dataSource = 'static';

    try {
      // Local file only
      console.log('Attempting to fetch signalk_latest.json...');
      res = await fetch('data/telemetry/signalk_latest.json');
      console.log('Local file fetch response:', res.status, res.statusText);
      if (res.ok) {
        data = await res.json();
        dataSource = 'static';
        console.log('Local JSON file data loaded successfully');
      } else {
        throw new Error(`Local file not available: ${res.status} ${res.statusText}`);
      }
    } catch (fileError) {
      console.log('Local file fetch error:', fileError);
      console.log('Local file unavailable, creating dummy data...');

      // Create dummy data as fallback
      console.log('Creating dummy data as fallback...');
      data = {
        navigation: {
          position: { value: { latitude: 37.806, longitude: -122.465 } },
          courseOverGroundTrue: { value: 0 },
          speedOverGround: { value: 0 },
          speedThroughWater: { value: 0 }
        },
        environment: {
          wind: {
            speedTrue: { value: 10 },
            angleTrue: { value: 0 }
          },
          water: { temperature: { value: 288.15 } }
        },
        electrical: {
          batteries: {
            house: {
              voltage: { value: 12.5 },
              current: { value: 0 },
              power: { value: 0 },
              capacity: {
                stateOfCharge: { value: 0.8 },
                timeRemaining: { value: 36000 }
              }
            }
          }
        }
      };
      dataSource = 'dummy';
      console.log('Dummy data created successfully');
    }

    console.log('Fetch response status:', res.status);
    const nav = data.navigation || {};
    const elec = data.electrical || {};
    const env = data.environment || {};
    const entertainment = data.entertainment || {};
    const internet = data.internet || {};

    const signalkName = data.name;
    const signalkMmsi = data.mmsi;
    if (signalkName || signalkMmsi) {
      vesselData = vesselData || {};
      if (signalkName) vesselData.name = signalkName;
      if (signalkMmsi) vesselData.mmsi = signalkMmsi;
      updateVesselLinks();
    }

    // Store globally for polar performance calculations
    currentNav = nav;
    currentEnv = env;

    // Update banner with data source and timestamp
    const statusElement = document.getElementById('dataStatus');
    const timeElement = document.getElementById('updateTime');
    const banner = document.getElementById('updateBanner');

    // Set data source status
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (dataSource === 'static') {
      statusElement.textContent = 'Static Data';
      statusElement.style.color = isDark ? '#d4edda' : '#2c3e50';
    } else if (dataSource === 'dummy') {
      statusElement.textContent = '⚠️ Demo Data';
      statusElement.style.color = '#f39c12';
    }

    // Try specific field first, fall back to recursive scan
    let timestampStr = data.navigation?.position?.timestamp;
    let modifiedDate = timestampStr ? new Date(timestampStr) : findLatestTimestamp(data);

    const formatAge = (ms) => {
      const s = Math.floor(ms / 1000);
      if (s < 60)  return 'just now';
      const m = Math.floor(s / 60);
      if (m < 60)  return `${m} min ago`;
      const h = Math.floor(m / 60);
      if (h < 24)  return `${h} hr${h === 1 ? '' : 's'} ago`;
      const d = Math.floor(h / 24);
      return `${d} day${d === 1 ? '' : 's'} ago`;
    };

    if (modifiedDate && !isNaN(modifiedDate.getTime())) {
      const now = new Date();
      const diffMs    = now - modifiedDate;
      const diffHours = diffMs / (1000 * 60 * 60);
      const ageDot    = diffHours < 1 ? '🟢' : diffHours < 6 ? '🟡' : diffHours < 24 ? '🟠' : '🔴';
      const ageLabel  = formatAge(diffMs);
      timeElement.textContent = `${ageDot} ${ageLabel} · ${modifiedDate.toLocaleString()}`;
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (diffHours > 3) {
        banner.style.background = isDark ? "#3d1e1e" : "#f8d7da";
        banner.style.color = isDark ? "#f8d7da" : "#721c24";
      } else {
        banner.style.background = isDark ? "#1e3a1e" : '#dff0d8';
        banner.style.color = isDark ? "#d4edda" : '#2c3e50';
      }
    } else {
      timeElement.textContent = '🔴 Timestamp not found';
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      banner.style.background = isDark ? "#3d1e1e" : "#f8d7da";
      banner.style.color = isDark ? "#f8d7da" : "#721c24";
    }

    lat = nav.position?.value?.latitude;
    lon = nav.position?.value?.longitude;
    const hasGpsFix = hasValidCoordinates(lat, lon);

    if (hasGpsFix) {
      if (!map) {
        map = L.map('map').setView([lat, lon], 13);
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const tileLayer = isDark
          ? L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
              attribution: '© OpenStreetMap contributors © CARTO'
            })
          : L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
              attribution: '© OpenStreetMap contributors'
          });
        tileLayer.addTo(map);
        marker = L.marker([lat, lon]).addTo(map);

        // Privacy exclusion zone indicator — mirrors PRIVACY_EXCLUSION_ZONES in Python.
        // Positions inside this ring are redacted from all stored data.
        L.circle([37.7802069, -122.3858040], {
          radius: 200,
          color: '#e74c3c',
          fillColor: '#e74c3c',
          fillOpacity: 0.05,
          opacity: 0.5,
          weight: 1.5,
          dashArray: '5 5',
          interactive: false,
        }).bindTooltip('📍 Privacy zone — position not recorded inside this area', {
          sticky: true, opacity: 0.85,
        }).addTo(map);
      } else {
        map.setView([lat, lon]);
        marker.setLatLng([lat, lon]);
      }

      // Anchor swing-radius circle.
      const anchorPos = nav.anchor?.position?.value;
      const anchorRadius = nav.anchor?.maxRadius?.value;
      if (anchorPos?.latitude && anchorPos?.longitude && anchorRadius > 0) {
        const anchorLatLng = [anchorPos.latitude, anchorPos.longitude];
        if (anchorLayer) {
          anchorLayer.setLatLng(anchorLatLng).setRadius(anchorRadius);
        } else {
          anchorLayer = L.circle(anchorLatLng, {
            radius: anchorRadius,
            color: '#f39c12',
            fillColor: '#f39c12',
            fillOpacity: 0.08,
            opacity: 0.7,
            weight: 2,
            dashArray: '6 4',
          }).bindTooltip(`⚓ Anchor radius: ${(anchorRadius * 3.28084).toFixed(0)} ft`, {
            sticky: true, opacity: 0.85,
          }).addTo(map);
        }
      } else if (anchorLayer) {
        anchorLayer.remove();
        anchorLayer = null;
      }

      // Load wind forecast asynchronously without blocking main data load
      loadWindForecast().catch(err => console.error('Wind forecast error:', err));
      // Load wave forecast asynchronously without blocking main data load
      loadWaveForecast().catch(err => console.error('Wave forecast error:', err));
      // Update map location title
      updateMapLocation(lat, lon).catch(err => console.error('Location fetch error:', err));
      // Load track for last 24 hours
      loadTrack().catch(err => console.error('Track load error:', err));
      // Update polar performance
      updatePolarPerformance();
    } else {
      document.getElementById('mapTitle').textContent = 'Waiting for GPS position...';
    }

    const tidePosition = resolveTidePosition(lat, lon);
    drawTideGraph(tidePosition.lat, tidePosition.lon, tidePosition);

    // Update the Now Playing section
    updateNowPlaying(entertainment);

    // Update navigation data
    const currentTheme = document.documentElement.getAttribute('data-theme');

    const anchorRawSI = nav.anchor?.currentRadius?.value ?? null;
    const anchorStatus = classifyAnchorStatus(anchorRawSI, nav.anchor?.maxRadius?.value);
    const anchorValueHtml = colorValue(fmtUnit('length', anchorRawSI), anchorStatus);

    const socRaw = elec.batteries?.house?.capacity?.stateOfCharge?.value;
    const socZones = elec.batteries?.house?.capacity?.stateOfCharge?.meta?.zones;
    const socPercent = socRaw != null ? socRaw * 100 : null;
    const socDisplay = socPercent != null ? `${socPercent.toFixed(0)}%` : 'N/A';
    const socValueHtml = colorValue(socDisplay, classifyByZones(socRaw, socZones) || classifyBatteryStatus(socPercent));

    const timeRemainingRaw = elec.batteries?.house?.capacity?.timeRemaining?.value;
    const timeRemainingZones = elec.batteries?.house?.capacity?.timeRemaining?.meta?.zones;
    const timeRemainingHours = timeRemainingRaw != null ? timeRemainingRaw / 3600 : null;
    const timeRemainingDisplay = timeRemainingHours != null ? `${timeRemainingHours.toFixed(1)} hrs` : 'N/A';
    const timeRemainingHtml = colorValue(timeRemainingDisplay, classifyByZones(timeRemainingRaw, timeRemainingZones) || classifyBatteryTime(timeRemainingHours));

    const packetLossValueRaw = internet.packetLoss?.value;
    const packetLossZones = internet.packetLoss?.meta?.zones;
    const packetLossPercent = packetLossValueRaw != null ? (packetLossValueRaw <= 1 ? packetLossValueRaw * 100 : packetLossValueRaw) : null;
    const packetLossDisplay = packetLossPercent != null ? `${packetLossPercent.toFixed(1)}%` : 'N/A';
    const packetLossHtml = colorValue(packetLossDisplay, classifyByZones(packetLossValueRaw, packetLossZones) || classifyPacketLoss(packetLossValueRaw));

    const tankValueWithBadge = (level, valueDisplay, waste = false, zones = null) =>
      colorValue(valueDisplay, classifyByZones(level, zones) || (waste ? classifyWasteTank(level) : classifyTankLevel(level)));

    document.getElementById('navigation-grid').innerHTML = `
      <div class="info-item" title="${withUpdated('Current vessel latitude position', nav.position)}"><div class="label">Latitude</div><div class="value">${lat?.toFixed(6) ?? 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('Current vessel longitude position', nav.position)}"><div class="label">Longitude</div><div class="value">${lon?.toFixed(6) ?? 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.speedOverGround" data-label="SOG" data-unit-group="speed" data-raw="${nav.speedOverGround?.value ?? ''}" title="${withUpdated('Speed Over Ground - actual speed relative to the seabed', nav.speedOverGround)}"><div class="label">SOG</div><div class="value">${fmtUnit('speed', nav.speedOverGround?.value)}</div></div>
      <div class="info-item" data-path="navigation.speedThroughWater" data-label="STW" data-unit-group="speed" data-raw="${nav.speedThroughWater?.value ?? ''}" title="${withUpdated('Speed Through Water - speed relative to the water', nav.speedThroughWater)}"><div class="label">STW</div><div class="value">${fmtUnit('speed', nav.speedThroughWater?.value)}</div></div>
      <div class="info-item" data-path="navigation.trip.log" data-label="Trip" data-unit-group="distance" data-raw="${nav.trip?.log?.value ?? ''}" title="${withUpdated('Trip distance - distance traveled on current trip', nav.trip?.log)}"><div class="label">Trip</div><div class="value">${fmtUnit('distance', nav.trip?.log?.value)}</div></div>
      <div class="info-item" data-path="navigation.log" data-label="Log" data-unit-group="distance" data-raw="${nav.log?.value ?? ''}" title="${withUpdated('Total log distance - cumulative distance traveled', nav.log)}"><div class="label">Log</div><div class="value">${fmtUnit('distance', nav.log?.value)}</div></div>
      <div class="info-item" data-path="navigation.attitude.roll" data-label="Roll" title="${withUpdated('Vessel roll angle from BNO055 IMU', data.navigation?.attitude)}"><div class="label">Roll</div><div class="value">${data.navigation?.attitude?.value?.roll ? (data.navigation.attitude.value.roll * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.attitude.pitch" data-label="Pitch" title="${withUpdated('Vessel pitch angle from BNO055 IMU', data.navigation?.attitude)}"><div class="label">Pitch</div><div class="value">${data.navigation?.attitude?.value?.pitch ? (data.navigation.attitude.value.pitch * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.courseOverGroundTrue" data-label="COG" title="${withUpdated('Course Over Ground - true direction the vessel is moving', nav.courseOverGroundTrue)}"><div class="label">COG</div><div class="value">${nav.courseOverGroundTrue?.value ? (nav.courseOverGroundTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.headingMagnetic" data-label="Mag Heading" title="${withUpdated('Magnetic heading from MMC5603 magnetometer', data.navigation?.headingMagnetic)}"><div class="label">Mag Heading</div><div class="value">${data.navigation?.headingMagnetic?.value ? (data.navigation.headingMagnetic.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="steering.rudderAngle" data-label="Rudder Angle" title="${withUpdated('Current rudder angle - positive is starboard, negative is port', data.steering?.rudderAngle)}"><div class="label">Rudder Angle</div><div class="value">${data.steering?.rudderAngle?.value ? (data.steering.rudderAngle.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.anchor.currentRadius" data-label="Anchor Distance" data-unit-group="length" data-raw="${nav.anchor?.currentRadius?.value ?? ''}" title="${withUpdated('Distance from anchor position - red if outside safe radius', nav.anchor?.currentRadius)}"><div class="label">Anchor Distance</div>${anchorValueHtml}</div>
      <div class="info-item" data-path="navigation.anchor.bearingTrue" data-label="Anchor Bearing" title="${withUpdated('Bearing to anchor position from current location', nav.anchor?.bearingTrue)}"><div class="label">Anchor Bearing</div><div class="value">${nav.anchor?.bearingTrue?.value ? (nav.anchor.bearingTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
    `;

    // Update wind data
    document.getElementById('wind-grid').innerHTML = `
      <div class="info-item" data-path="environment.wind.speedTrue" data-label="Wind Speed" data-unit-group="speed" data-raw="${env.wind?.speedTrue?.value ?? ''}" title="${withUpdated('True wind speed - actual wind speed in the atmosphere', env.wind?.speedTrue)}"><div class="label">True Wind Speed</div><div class="value">${fmtUnit('speed', env.wind?.speedTrue?.value)}</div></div>
      <div class="info-item" data-path="environment.wind.angleTrue" data-label="Wind Dir" title="${withUpdated('True wind direction - actual wind direction relative to true north', env.wind?.angleTrue)}"><div class="label">True Wind Dir</div><div class="value">${env.wind?.angleTrue?.value ? (env.wind.angleTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="environment.wind.angleApparent" data-label="Apparent Wind Angle" title="${withUpdated('Apparent wind angle - wind direction relative to vessel heading', data.environment?.wind?.angleApparent)}"><div class="label">Apparent Angle</div><div class="value">${data.environment?.wind?.angleApparent?.value ? (data.environment.wind.angleApparent.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" data-path="environment.wind.speedApparent" data-label="Apparent Wind Speed" data-unit-group="speed" data-raw="${data.environment?.wind?.speedApparent?.value ?? ''}" title="${withUpdated('Apparent wind speed - wind speed as felt on the vessel', data.environment?.wind?.speedApparent)}"><div class="label">Apparent Speed</div><div class="value">${fmtUnit('speed', data.environment?.wind?.speedApparent?.value)}</div></div>
    `;

    // Update power data
    document.getElementById('power-grid').innerHTML = `
      <div class="info-item" data-path="electrical.batteries.house.voltage" data-label="Battery Voltage" title="${withUpdated('House battery bank voltage', elec.batteries?.house?.voltage)}"><div class="label">Battery Voltage</div><div class="value">${elec.batteries?.house?.voltage?.value?.toFixed(2) ?? 'N/A'} V</div></div>
      <div class="info-item" data-path="electrical.batteries.house.current" data-label="Battery Current" title="${withUpdated('House battery bank current - positive is charging, negative is discharging', elec.batteries?.house?.current)}"><div class="label">Battery Current</div><div class="value">${elec.batteries?.house?.current?.value?.toFixed(1) ?? 'N/A'} A</div></div>
      <div class="info-item" data-path="electrical.batteries.house.power" data-label="Battery Power" title="${withUpdated('House battery bank power consumption or generation', elec.batteries?.house?.power)}"><div class="label">Battery Power</div><div class="value">${elec.batteries?.house?.power?.value?.toFixed(1) ?? 'N/A'} W</div></div>
      <div class="info-item" data-path="electrical.batteries.house.capacity.stateOfCharge" data-label="SOC" title="${withUpdated('State of Charge - percentage of battery capacity remaining', elec.batteries?.house?.capacity?.stateOfCharge)}"><div class="label">SOC</div>${socValueHtml}</div>
      <div class="info-item" data-path="electrical.batteries.house.capacity.timeRemaining" data-label="Battery Time Remaining" title="${withUpdated('Estimated time remaining until battery depletion', elec.batteries?.house?.capacity?.timeRemaining)}"><div class="label">Battery Time Remaining</div>${timeRemainingHtml}</div>
    `;

    // Update the vessel information with static vessel data
    document.getElementById('vessel-grid').innerHTML = `
      <div class="info-item" data-unit-group="length" data-raw="${data.design?.length?.value?.overall ?? ''}" title="${withUpdated('Overall vessel length from bow to stern', data.design?.length)}"><div class="label">Vessel Length</div><div class="value">${fmtUnit('length', data.design?.length?.value?.overall)}</div></div>
      <div class="info-item" data-unit-group="length" data-raw="${data.design?.beam?.value ?? ''}" title="${withUpdated('Vessel beam - maximum width of the vessel', data.design?.beam)}"><div class="label">Vessel Beam</div><div class="value">${fmtUnit('length', data.design?.beam?.value)}</div></div>
      <div class="info-item" data-unit-group="length" data-raw="${data.design?.draft?.value?.maximum ?? ''}" title="${withUpdated('Maximum vessel draft - depth below waterline', data.design?.draft)}"><div class="label">Vessel Draft</div><div class="value">${fmtUnit('length', data.design?.draft?.value?.maximum)}</div></div>
      <div class="info-item" data-unit-group="length" data-raw="${data.design?.airHeight?.value ?? ''}" title="${withUpdated('Vessel air height - height above waterline', data.design?.airHeight)}"><div class="label">Air Height</div><div class="value">${fmtUnit('length', data.design?.airHeight?.value)}</div></div>
      <div class="info-item" title="${withUpdated('Vessel name from SignalK', data)}"><div class="label">Vessel Name</div><div class="value value-text">${data.name || 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('Maritime Mobile Service Identity - unique vessel identifier', data)}"><div class="label">MMSI</div><div class="value value-text">${data.mmsi || vesselData?.mmsi || 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('VHF radio callsign', data.communication)}"><div class="label">Callsign</div><div class="value value-text">${data.communication?.callsignVhf || 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('Hull Number (Assigned by Beneteau)', vesselData)}"><div class="label">Hull #</div><div class="value value-text">${vesselData?.hull_number || 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('US Coast Guard vessel registration number', vesselData)}"><div class="label">USCG #</div><div class="value value-text">${vesselData?.uscg_number || 'N/A'}</div></div>
    `;

    const isNumericValue = (val) => typeof val === 'number' && Number.isFinite(val);
    const toPercent = (val, digits = 0) =>
      isNumericValue(val) ? `${(val * 100).toFixed(digits)}%` : 'N/A';
    const toGallons = (val) =>
      isNumericValue(val) ? `${(val * 264.172).toFixed(1)} gal` : null;
    const formatTankDisplay = (level, volume) => {
      const parts = [];
      const levelDisplay = toPercent(level);
      if (levelDisplay !== 'N/A') parts.push(levelDisplay);
      const volumeDisplay = toGallons(volume);
      if (volumeDisplay) parts.push(volumeDisplay);
      return parts.length ? parts.join(' | ') : 'N/A';
    };
    // Update the environment with environmental data
    document.getElementById('environment-grid').innerHTML = `
      <div class="info-item" data-path="environment.water.temperature" data-label="Water Temp" data-unit-group="temperature" data-raw="${env.water?.temperature?.value ?? ''}" title="${withUpdated('Water temperature at the surface', env.water?.temperature)}"><div class="label">Water Temp</div><div class="value">${fmtUnit('temperature', env.water?.temperature?.value)}</div></div>
      <div class="info-item" data-path="environment.inside.temperature" data-label="Inside Temp" data-unit-group="temperature" data-raw="${data.environment?.inside?.temperature?.value ?? ''}" title="${withUpdated('Inside air temperature from BME280 sensor', data.environment?.inside?.temperature)}"><div class="label">Inside Temp</div><div class="value">${fmtUnit('temperature', data.environment?.inside?.temperature?.value)}</div></div>
      <div class="info-item" data-path="environment.inside.humidity" data-label="Inside Humidity" title="${withUpdated('Inside humidity from BME280 sensor', data.environment?.inside?.humidity)}"><div class="label">Inside Humidity</div><div class="value">${data.environment?.inside?.humidity?.value ? (data.environment.inside.humidity.value * 100).toFixed(1) + '%' : 'N/A'}</div></div>
      <div class="info-item" data-path="environment.inside.pressure" data-label="Barometric Pressure" data-unit-group="pressure" data-raw="${data.environment?.inside?.pressure?.value ?? ''}" title="${withUpdated('Inside barometric pressure from BME280 sensor', data.environment?.inside?.pressure)}"><div class="label">Barometric Pressure</div><div class="value">${fmtUnit('pressure', data.environment?.inside?.pressure?.value)}</div></div>
      <div class="info-item" data-path="environment.inside.airQuality.tvoc" data-label="TVOC" title="${withUpdated('Indoor air quality - Total Volatile Organic Compounds', data.environment?.inside?.airQuality?.tvoc)}"><div class="label">TVOC</div><div class="value">${data.environment?.inside?.airQuality?.tvoc?.value ? data.environment.inside.airQuality.tvoc.value.toFixed(0) + ' ppb' : 'N/A'}</div></div>
      <div class="info-item" data-path="environment.inside.airQuality.eco2" data-label="CO₂" title="${withUpdated('Indoor air quality - Carbon Dioxide equivalent', data.environment?.inside?.airQuality?.eco2)}"><div class="label">CO₂</div><div class="value">${data.environment?.inside?.airQuality?.eco2?.value ? data.environment.inside.airQuality.eco2.value.toFixed(0) + ' ppm' : 'N/A'}</div></div>
      <div class="info-item" data-path="navigation.magneticVariation" data-label="Magnetic Variation" title="${withUpdated('Magnetic variation at current position - difference between true and magnetic north', data.navigation?.magneticVariation)}"><div class="label">Magnetic Variation</div><div class="value">${data.navigation?.magneticVariation?.value ? (data.navigation.magneticVariation.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('Sunrise time today', data.environment?.sunlight?.times?.sunrise)}"><div class="label">Sunrise</div><div class="value">${data.environment?.sunlight?.times?.sunrise?.value ? new Date(data.environment.sunlight.times.sunrise.value).toLocaleTimeString() : 'N/A'}</div></div>
      <div class="info-item" title="${withUpdated('Sunset time today', data.environment?.sunlight?.times?.sunset)}"><div class="label">Sunset</div><div class="value">${data.environment?.sunlight?.times?.sunset?.value ? new Date(data.environment.sunlight.times.sunset.value).toLocaleTimeString() : 'N/A'}</div></div>
    `;

    document.getElementById('internet-grid').innerHTML = `
      <div class="info-item" title="${withUpdated('Internet service provider', internet.ISP)}"><div class="label">ISP</div><div class="value value-text">${internet.ISP?.value || 'N/A'}</div></div>
      <div class="info-item" data-path="internet.speed.download" data-label="Download" title="${withUpdated('Download speed', internet.speed?.download)}"><div class="label">Download</div><div class="value">${isNumericValue(internet.speed?.download?.value) ? internet.speed.download.value.toFixed(1) + ' Mbps' : 'N/A'}</div></div>
      <div class="info-item" data-path="internet.speed.upload" data-label="Upload" title="${withUpdated('Upload speed', internet.speed?.upload)}"><div class="label">Upload</div><div class="value">${isNumericValue(internet.speed?.upload?.value) ? internet.speed.upload.value.toFixed(1) + ' Mbps' : 'N/A'}</div></div>
      <div class="info-item" data-path="internet.ping.latency" data-label="Latency" title="${withUpdated('Ping latency', internet.ping?.latency)}"><div class="label">Latency</div><div class="value">${isNumericValue(internet.ping?.latency?.value) ? internet.ping.latency.value.toFixed(1) + ' ms' : 'N/A'}</div></div>
      <div class="info-item" data-path="internet.ping.jitter" data-label="Jitter" title="${withUpdated('Ping jitter', internet.ping?.jitter)}"><div class="label">Jitter</div><div class="value">${isNumericValue(internet.ping?.jitter?.value) ? internet.ping.jitter.value.toFixed(1) + ' ms' : 'N/A'}</div></div>
      <div class="info-item" data-path="internet.packetLoss" data-label="Packet Loss" title="${withUpdated('Packet loss percentage', internet.packetLoss)}"><div class="label">Packet Loss</div>${packetLossHtml}</div>
    `;

    const propulsion = data.propulsion?.port || {};
    const rpmValue = propulsion.revolutions?.value;
    document.getElementById('propulsion-grid').innerHTML = `
      <div class="info-item" title="${withUpdated('Engine state', propulsion.state)}"><div class="label">State</div><div class="value value-text">${propulsion.state?.value || 'N/A'}</div></div>
      <div class="info-item" data-path="propulsion.port.revolutions" data-label="RPM" title="${withUpdated('Engine revolutions per minute', propulsion.revolutions)}"><div class="label">RPM</div><div class="value">${isNumericValue(rpmValue) ? (rpmValue * 60).toFixed(0) + ' RPM' : 'N/A'}</div></div>
    `;

    const tanks = data.tanks || {};
    const fuelMain = tanks.fuel?.['0'] || {};
    const fuelReserve = tanks.fuel?.reserve || {};
    const freshWater0 = tanks.freshWater?.['0'] || {};
    const freshWater1 = tanks.freshWater?.['1'] || {};
    const propaneA = tanks.propane?.a || {};
    const propaneB = tanks.propane?.b || {};
    const blackwaterBow = tanks.blackwater?.bow || {};
    const liveWell0 = tanks.liveWell?.['0'] || {};
    document.getElementById('tanks-grid').innerHTML = `
      <div class="info-item" data-path="tanks.fuel.0.currentLevel" data-label="Fuel (Main)" title="${withUpdatedNodes('Main fuel tank level, volume, and temperature (if available)', fuelMain.currentLevel, fuelMain.currentVolume, fuelMain.temperature)}"><div class="label">Fuel (Main)</div>${tankValueWithBadge(fuelMain.currentLevel?.value, formatTankDisplay(fuelMain.currentLevel?.value, fuelMain.currentVolume?.value), false, fuelMain.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.fuel.reserve.currentLevel" data-label="Fuel (Reserve)" title="${withUpdatedNodes('Reserve fuel tank level, volume, and temperature (if available)', fuelReserve.currentLevel, fuelReserve.currentVolume, fuelReserve.temperature)}"><div class="label">Fuel (Reserve)</div>${tankValueWithBadge(fuelReserve.currentLevel?.value, formatTankDisplay(fuelReserve.currentLevel?.value, fuelReserve.currentVolume?.value), false, fuelReserve.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.freshWater.0.currentLevel" data-label="Fresh Water 1" title="${withUpdatedNodes('Fresh water tank 1 level and volume', freshWater0.currentLevel, freshWater0.currentVolume)}"><div class="label">Fresh Water 1</div>${tankValueWithBadge(freshWater0.currentLevel?.value, formatTankDisplay(freshWater0.currentLevel?.value, freshWater0.currentVolume?.value), false, freshWater0.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.freshWater.1.currentLevel" data-label="Fresh Water 2" title="${withUpdatedNodes('Fresh water tank 2 level and volume', freshWater1.currentLevel, freshWater1.currentVolume)}"><div class="label">Fresh Water 2</div>${tankValueWithBadge(freshWater1.currentLevel?.value, formatTankDisplay(freshWater1.currentLevel?.value, freshWater1.currentVolume?.value), false, freshWater1.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.propane.a.currentLevel" data-label="Propane A" title="${withUpdatedNodes('Propane tank A level and temperature', propaneA.currentLevel, propaneA.temperature)}"><div class="label">Propane A</div>${tankValueWithBadge(propaneA.currentLevel?.value, formatTankDisplay(propaneA.currentLevel?.value, null), false, propaneA.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.propane.b.currentLevel" data-label="Propane B" title="${withUpdatedNodes('Propane tank B level and temperature', propaneB.currentLevel, propaneB.temperature)}"><div class="label">Propane B</div>${tankValueWithBadge(propaneB.currentLevel?.value, formatTankDisplay(propaneB.currentLevel?.value, null), false, propaneB.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.blackwater.bow.currentLevel" data-label="Blackwater" title="${withUpdatedNodes('Blackwater tank level and temperature', blackwaterBow.currentLevel, blackwaterBow.temperature)}"><div class="label">Blackwater</div>${tankValueWithBadge(blackwaterBow.currentLevel?.value, formatTankDisplay(blackwaterBow.currentLevel?.value, null), true, blackwaterBow.currentLevel?.meta?.zones)}</div>
      <div class="info-item" data-path="tanks.liveWell.0.currentLevel" data-label="Bilge" title="${withUpdated('Bilge level', liveWell0.currentLevel)}"><div class="label">Bilge</div>${tankValueWithBadge(liveWell0.currentLevel?.value, formatTankDisplay(liveWell0.currentLevel?.value, null), true, liveWell0.currentLevel?.meta?.zones)}</div>
    `;

    // Render alert summary and inline sparklines now that all info-item cards are in the DOM.
    renderAlertSummary();
    initInlineSparklines();
  } catch (err) {
    console.error("Failed to load data:", err);
    console.error("Error details:", err.message);
    const banner = document.getElementById('updateBanner');
    banner.textContent = `Error loading data: ${err.message}`;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    banner.style.background = isDark ? "#3d1e1e" : "#f8d7da";
    banner.style.color = isDark ? "#f8d7da" : "#721c24";

    Object.keys(PANEL_SKELETONS).forEach((id) =>
      renderEmptyState(id, 'Data unavailable', 'SignalK feed not reachable.'));
    renderEmptyState('wind-forecast-grid', 'Forecast unavailable', 'Check network or GPS data.');
    renderEmptyState('wave-forecast-grid', 'Wave data unavailable', 'Retry when online.');
  }
}

async function loadPolarData() {
  try {
    const response = await fetch('data/vessel/polars.csv');

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const csvText = await response.text();

    // Parse CSV data
    const lines = csvText.split('\n');
    const headers = lines[0].split(';');
    const windSpeeds = headers.slice(1).map(Number); // [4, 6, 8, 10, 12, 14, 16, 20, 24]

    polarData = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(';');
      const twa = parseFloat(values[0]); // True Wind Angle
      if (!isNaN(twa)) {
        const speeds = values.slice(1).map(v => parseFloat(v) || 0);
        polarData.push({ twa, speeds });
      }
    }
  } catch (error) {
    console.error('Error loading polar data:', error);
    document.getElementById('polar-performance').innerHTML = `
      <div style="color: #e74c3c;">Error loading polar data: ${error.message}</div>
    `;
  }
}

function getPolarSpeed(twa, tws) {
  if (!polarData) return 0;

  // Find closest wind speed
  const windSpeeds = [4, 6, 8, 10, 12, 14, 16, 20, 24];
  let speedIndex = 0;

  // Find the closest wind speed index
  for (let i = 0; i < windSpeeds.length; i++) {
    if (tws <= windSpeeds[i]) {
      speedIndex = i;
      break;
    }
  }

  // If wind speed is higher than all available speeds, use the last one
  if (speedIndex === 0 && tws > windSpeeds[0]) {
    speedIndex = windSpeeds.length - 1;
  }

  // Find closest TWA, but avoid 0° if possible since it has zero speed
  let closestAngle = polarData[0];
  let minDiff = Math.abs(twa - polarData[0].twa);

  for (const angle of polarData) {
    const diff = Math.abs(twa - angle.twa);
    if (diff < minDiff) {
      // Prefer non-zero speeds when possible
      if (angle.twa === 0 && twa > 10) {
        // Skip 0° angle if we're not very close to it
        continue;
      }
      minDiff = diff;
      closestAngle = angle;
    }
  }

  return closestAngle.speeds[speedIndex] || 0;
}

function calculateVMG(bearingToDest, bsp) {
  // VMG = Boat Speed * cos(angle between boat heading and destination bearing)
  // This calculates how fast you're progressing toward your destination
  const angleRad = (bearingToDest * Math.PI) / 180;
  return bsp * Math.cos(angleRad);
}

function updateNowPlaying(entertainment) {
  const trackNameEl = document.getElementById('track-name');
  const artistAlbumEl = document.getElementById('artist-album');
  const playbackSourceEl = document.getElementById('playback-source');
  const trackNumberEl = document.getElementById('track-number');

  // Check if we have entertainment data from Fusion stereo
  const fusion = entertainment?.device?.fusion1;
  if (!fusion || !fusion.track) {
    trackNameEl.textContent = 'No track playing';
    artistAlbumEl.textContent = 'No artist information';
    playbackSourceEl.textContent = 'No source';
    trackNumberEl.textContent = 'Track -- of --';
    return;
  }

  const track = fusion.track;
  const trackName = track.name?.value || 'Unknown Track';
  const artistName = track.artistName?.value || 'Unknown Artist';
  const albumName = track.albumName?.value || '';
  const trackNumber = track.number?.value || 0;
  const totalTracks = track.totalTracks?.value || 0;

  // Get the current playback source
  let sourceName = 'Unknown Source';
  if (fusion.output?.zone1?.source?.value) {
    const sourcePath = fusion.output.zone1.source.value;
    // Extract source name from path like "entertainment.device.fusion1.avsource.source6"
    const sourceMatch = sourcePath.match(/\.source(\d+)$/);
    if (sourceMatch) {
      const sourceNum = sourceMatch[1];
      const source = fusion.avsource?.[`source${sourceNum}`];
      if (source?.name?.value) {
        sourceName = source.name.value;
      }
    }
  }

  // Update the display
  trackNameEl.textContent = trackName;
  artistAlbumEl.textContent = albumName ? `${artistName} - ${albumName}` : artistName;
  playbackSourceEl.textContent = sourceName;
  trackNumberEl.textContent = `Track ${trackNumber} of ${totalTracks}`;
}

function updatePolarPerformance() {
  if (!polarData) {
    return;
  }

  // Check for different wind angle data sources
  let windAngle = null;
  if (currentEnv?.wind?.angleTrue?.value) {
    windAngle = currentEnv.wind.angleTrue.value;
  } else if (currentEnv?.wind?.angleTrueWater?.value) {
    windAngle = currentEnv.wind.angleTrueWater.value;
  } else if (currentEnv?.wind?.angleApparent?.value) {
    windAngle = currentEnv.wind.angleApparent.value;
  }

  // Check for different boat speed data sources
  let boatSpeed = null;
  if (currentNav?.speedThroughWater?.value) {
    boatSpeed = currentNav.speedThroughWater.value;
  } else if (currentNav?.speedOverGround?.value) {
    boatSpeed = currentNav.speedOverGround.value;
  }

  // Check for wind speed data
  let windSpeed = null;
  if (currentEnv?.wind?.speedTrue?.value) {
    windSpeed = currentEnv.wind.speedTrue.value;
  }

  // Use default values if data is missing
  const twa = windAngle ? windAngle * 180 / Math.PI : 90; // Default to 90 degrees (middle of chart)
  const bsp = boatSpeed ? boatSpeed * 1.94384 : 0; // Default to 0 knots (center of bullseye)
  const tws = windSpeed ? windSpeed * 1.94384 : 10; // Default to 10 knots

  const polarSpeed = getPolarSpeed(twa, tws);
  const performancePercent = polarSpeed > 0 ? (bsp / polarSpeed * 100).toFixed(1) : 0;

  // Get bearing to destination for VMG calculation
  let bearingToDest = null;
  if (currentNav?.courseRhumbline?.bearingToDestinationTrue?.value) {
    bearingToDest = currentNav.courseRhumbline.bearingToDestinationTrue.value * 180 / Math.PI;
  }

  // Calculate VMG relative to destination (not wind)
  const vmg = bearingToDest ? calculateVMG(bearingToDest, bsp) : 0;
  const polarVMG = bearingToDest ? calculateVMG(bearingToDest, polarSpeed) : 0;

  // Update performance display with data availability indicators
  const windAngleDisplay = windAngle ? `${twa.toFixed(1)}°` : 'N/A (using 90°)';
  const boatSpeedDisplay = boatSpeed ? `${bsp.toFixed(1)} kts` : 'N/A (using 0 kts)';
  const windSpeedDisplay = windSpeed ? `${tws.toFixed(1)} kts` : 'N/A (using 10 kts)';

  document.getElementById('polar-performance').innerHTML = `
    <div><strong>True Wind Angle:</strong> ${windAngleDisplay}</div>
    <div><strong>Boat Speed:</strong> ${boatSpeedDisplay}</div>
    <div><strong>Polar Speed:</strong> ${polarSpeed.toFixed(1)} kts</div>
    <div><strong>Performance:</strong> <span style="color: ${performancePercent >= 95 ? '#27ae60' : performancePercent >= 85 ? '#f39c12' : '#e74c3c'}">${performancePercent}%</span></div>
  `;

  // Update VMG display
  if (bearingToDest) {
    document.getElementById('vmg-analysis').innerHTML = `
      <div><strong>Current VMG:</strong> ${vmg.toFixed(1)} kts</div>
      <div><strong>Polar VMG:</strong> ${polarVMG.toFixed(1)} kts</div>
      <div><strong>VMG %:</strong> <span style="color: ${vmg >= polarVMG * 0.95 ? '#27ae60' : vmg >= polarVMG * 0.85 ? '#f39c12' : '#e74c3c'}">${polarVMG > 0 ? (vmg / polarVMG * 100).toFixed(1) : 0}%</span></div>
    `;
  } else {
    document.getElementById('vmg-analysis').innerHTML = `
      <div><strong>Current VMG:</strong> <span style="color: #7f8c8d;">No destination set</span></div>
      <div><strong>Polar VMG:</strong> <span style="color: #7f8c8d;">No destination set</span></div>
      <div><strong>VMG %:</strong> <span style="color: #7f8c8d;">No destination set</span></div>
    `;
  }

  // Always draw polar chart, even with default values
  drawPolarChart(twa, bsp, tws);
}

function drawPolarChart(currentTWA, currentSpeed, currentTWS) {
  const now = Date.now();
  if (isDrawingPolarChart) {
    return;
  }


  if (!polarData) return;

  // Get theme information early for use throughout the function
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  isDrawingPolarChart = true;
  lastPolarChartUpdate = now;

  const canvas = document.getElementById('polarChart');
  const ctx = canvas.getContext('2d');

  // Ensure previous chart is properly destroyed
  if (polarChartInstance) {
    polarChartInstance.destroy();
    polarChartInstance = null;
  }



  // Clear the canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Determine which side to show based on boat course
  let focusSide = 'starboard'; // default
  if (currentNav?.courseOverGroundTrue?.value) {
    const boatCourse = currentNav.courseOverGroundTrue.value * 180 / Math.PI;
    const windDirection = currentEnv?.wind?.angleTrueWater?.value * 180 / Math.PI;

    // Calculate relative angle to determine tack
    let relativeAngle = boatCourse - windDirection;
    if (relativeAngle > 180) relativeAngle -= 360;
    if (relativeAngle < -180) relativeAngle += 360;

    // Positive = starboard tack, negative = port tack
    focusSide = relativeAngle > 0 ? 'starboard' : 'port';
  }

  // Create full 360° angle array
  const fullAngles = [];
  const fullLabels = [];

  // Add angles from 0° to 180° (port side)
  for (let i = 0; i <= 180; i += 15) {
    fullAngles.push(i);
    fullLabels.push(`${i}°`);
  }

  // Add angles from 195° to 345° (starboard side)
  for (let i = 195; i <= 345; i += 15) {
    fullAngles.push(i);
    fullLabels.push(`${i}°`);
  }

  // Create datasets for each wind speed
  const polarDatasets = [];
  const windSpeeds = [4, 6, 8, 10, 12, 14, 16, 20, 24];

  // Find the closest wind speed to current wind speed
  let closestWindSpeedIndex = 0;
  let minWindSpeedDiff = Math.abs(currentTWS - windSpeeds[0]);
  for (let i = 1; i < windSpeeds.length; i++) {
    const diff = Math.abs(currentTWS - windSpeeds[i]);
    if (diff < minWindSpeedDiff) {
      minWindSpeedDiff = diff;
      closestWindSpeedIndex = i;
    }
  }

  windSpeeds.forEach((tws, index) => {
    const speeds = fullAngles.map(angle => {
      // For angles > 180°, use the mirror angle (360° - angle)
      const lookupAngle = angle > 180 ? 360 - angle : angle;

      // Find closest angle in polar data
      let closestAngle = polarData[0];
      let minDiff = Math.abs(lookupAngle - polarData[0].twa);

      for (const point of polarData) {
        const diff = Math.abs(lookupAngle - point.twa);
        if (diff < minDiff) {
          minDiff = diff;
          closestAngle = point;
        }
      }

      return closestAngle.speeds[index] || 0;
    });

    const validSpeeds = speeds.filter(speed => speed > 0);
    if (validSpeeds.length > 0) {
      // Reverse the color order: red for max wind, blue for min wind
      const reversedIndex = windSpeeds.length - 1 - index;
      const hue = reversedIndex * 30; // 0 = red, 30 = orange, 60 = yellow, 120 = green, 180 = cyan, 240 = blue

      // Highlight the closest wind speed line
      const isClosestWindSpeed = index === closestWindSpeedIndex;

      polarDatasets.push({
        label: `${tws} kts${isClosestWindSpeed ? ' (Current)' : ''}`,
        data: speeds,
        borderColor: isClosestWindSpeed ? (isDark ? '#60a5fa' : '#2563eb') : `hsla(${hue}, 70%, 50%, 0.50)`, // 50% alpha for non-current lines
        backgroundColor: isClosestWindSpeed ? (isDark ? 'rgba(96,165,250,0.2)' : 'rgba(37,99,235,0.2)') : `hsla(${hue}, 70%, 50%, 0.025)`, // Reduced alpha for background too
        borderWidth: isClosestWindSpeed ? 4 : 2, // Thicker line for current wind speed
        fill: false,
        tension: 0.4,
        order: isClosestWindSpeed ? 0 : 1 // Current wind speed drawn last (on top)
      });
    }
  });

  // Add current position as a single point
  // Normalize TWA to 0-360 range
  let normalizedTWA = currentTWA;
  while (normalizedTWA < 0) normalizedTWA += 360;
  while (normalizedTWA >= 360) normalizedTWA -= 360;

  // Find the closest angle in our chart's angle array
  const closestAngleIndex = fullAngles.reduce((closest, angle, index) => {
    return Math.abs(angle - normalizedTWA) < Math.abs(fullAngles[closest] - normalizedTWA) ? index : closest;
  }, 0);

  // Create a dataset with just the single point
  const currentData = new Array(fullAngles.length).fill(null);
  currentData[closestAngleIndex] = currentSpeed;



  // Add current position last so it appears on top
  polarDatasets.push({
    label: 'Current',
    data: currentData,
    borderColor: isDark ? '#60a5fa' : '#2563eb',
    backgroundColor: isDark ? '#60a5fa' : '#2563eb',
    borderWidth: 0, // No line
    pointRadius: 12,
    pointHoverRadius: 16,
    fill: false,
    tension: 0,
    showLine: false, // Don't draw lines between points
    order: -1 // Lower order values are drawn last (on top)
  });

  // Note: Chart.js radar charts don't support true straight radial lines
  // The TWA line would need to be implemented as a custom canvas overlay
  // For now, the current position marker and highlighted wind speed line provide good reference

  let startAngle = 0;
  let endAngle = 180;

  polarChartInstance = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: fullLabels,
      datasets: polarDatasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 0 // Disable all animations
      },
      plugins: {
        tooltip: {
          enabled: false
        },
        legend: {
          position: 'top',
          labels: {
            usePointStyle: true,
            color: isDark ? '#ffffff' : '#2c3e50'
          }
        }
      },
      scales: {
        r: {
            beginAtZero: true,
            grid: {
              color: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
              stepSize: 2,
              color: isDark ? '#ffffff' : '#2c3e50',
              backdropColor: 'transparent',
              font: {
                size: 11,
                weight: 'bold'
              }
            },
            pointLabels: {
              color: isDark ? '#ffffff' : '#2c3e50',
              font: {
                size: 14,
                weight: 'bold'
              },
              callback: function(value, index) {
                return value;
              }
            },
            title: {
              display: true,
              text: 'Boat Speed (kts)',
              color: isDark ? '#ffffff' : '#2c3e50'
            },
            startAngle: startAngle,
            min: 0,
            backgroundColor: 'transparent'
          }
        }
    }
  });

  isDrawingPolarChart = false;


}



async function loadWaveForecast() {
  try {
    if (!hasValidCoordinates(lat, lon)) {
      document.getElementById('wave-forecast-grid').innerHTML = `
        <div class="wave-forecast-item">
          <div class="wave-time">Waiting</div>
          <div class="wave-height">For GPS</div>
          <div class="wave-period">Position</div>
          <div class="wave-direction">--</div>
        </div>
      `;
      return;
    }

    const response = await fetch(`https://marine-api.open-meteo.com/v1/marine?latitude=${lat}&longitude=${lon}&hourly=wave_height,wave_period,wave_direction&timezone=auto`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    let forecastHTML = '';
    const waveForecastGrid = document.getElementById('wave-forecast-grid');

    // Find current time index in the data
    const now = new Date();
    let currentIndex = 0;
    let minDiff = Infinity;

    data.hourly.time.forEach((timeStr, index) => {
      const forecastTime = new Date(timeStr);
      const diff = Math.abs(forecastTime - now);
      if (diff < minDiff) {
        minDiff = diff;
        currentIndex = index;
      }
    });



    // Get next 4 time periods starting from current time
    const timeIntervals = [0, 3, 6, 9];
    const timeLabels = ['Now', '+3hr', '+6hr', '+9hr'];

    timeIntervals.forEach((hourOffset, index) => {
      const dataIndex = currentIndex + hourOffset;
      const waveHeight = data.hourly.wave_height[dataIndex];
      const wavePeriod = data.hourly.wave_period[dataIndex];
      const waveDirection = data.hourly.wave_direction[dataIndex];

      if (waveHeight !== null && wavePeriod !== null && waveDirection !== null) {
        const waveHeightFt = waveHeight * 3.28084;

        // Determine color based on wave height
        let backgroundColor;
        if (waveHeightFt < 2) {
          backgroundColor = 'linear-gradient(135deg, #27ae60 0%, #2ecc71 100%)'; // Green
        } else if (waveHeightFt >= 2 && waveHeightFt < 5) {
          backgroundColor = 'linear-gradient(135deg, #3498db 0%, #5dade2 100%)'; // Blue
        } else if (waveHeightFt >= 5 && waveHeightFt < 7) {
          backgroundColor = 'linear-gradient(135deg, #f39c12 0%, #f7dc6f 100%)'; // Orange
        } else if (waveHeightFt >= 7 && waveHeightFt < 10) {
          backgroundColor = 'linear-gradient(135deg, #e74c3c 0%, #ec7063 100%)'; // Red
        } else {
          backgroundColor = 'linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%)'; // Purple
        }

        // Convert direction to cardinal directions
        const direction = waveDirection;
        let directionText;
        if (direction >= 337.5 || direction < 22.5) directionText = 'N';
        else if (direction >= 22.5 && direction < 67.5) directionText = 'NE';
        else if (direction >= 67.5 && direction < 112.5) directionText = 'E';
        else if (direction >= 112.5 && direction < 157.5) directionText = 'SE';
        else if (direction >= 157.5 && direction < 202.5) directionText = 'S';
        else if (direction >= 202.5 && direction < 247.5) directionText = 'SW';
        else if (direction >= 247.5 && direction < 292.5) directionText = 'W';
        else if (direction >= 292.5 && direction < 337.5) directionText = 'NW';
        else directionText = 'N';

        const time = new Date(data.hourly.time[dataIndex]);
        const timeStr = time.toLocaleTimeString('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        });

        forecastHTML += `
          <div class="wave-forecast-item" style="background: ${backgroundColor};">
            <div class="wave-time">${timeLabels[index]} (${timeStr})</div>
            <div class="wave-height">${waveHeightFt.toFixed(1)}ft @ ${wavePeriod.toFixed(1)}s</div>
            <div class="wave-direction">${directionText} (${waveDirection.toFixed(0)}°)</div>
          </div>
        `;
      }
    });

    if (forecastHTML === '') {
      forecastHTML = `
        <div class="wave-forecast-item">
          <div class="wave-time">No Data</div>
          <div class="wave-height">Available</div>
          <div class="wave-period">--</div>
          <div class="wave-direction">--</div>
        </div>
      `;
    }

    waveForecastGrid.innerHTML = forecastHTML;
  } catch (error) {
    console.error('Wave forecast error:', error);
    document.getElementById('wave-forecast-grid').innerHTML = `
      <div class="wave-forecast-item">
        <div class="wave-time">Error</div>
        <div class="wave-height">Loading</div>
        <div class="wave-period">Failed</div>
        <div class="wave-direction">--</div>
      </div>
    `;
  }
}

async function loadWindForecast() {
  try {
    if (!hasValidCoordinates(lat, lon)) {
      document.getElementById('wind-forecast-grid').innerHTML = `
        <div class="wind-forecast-item">
          <div class="wind-time">Waiting</div>
          <div class="wind-speed">For GPS</div>
          <div class="wind-direction">Position</div>
        </div>
      `;
      return;
    }

    const selectedModel = document.getElementById('forecast-model').value;
    let response;

    // Select API based on chosen model
    switch(selectedModel) {
      case 'ecmwf':
        // ECMWF via OpenMeteo (free tier, global)
        response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=wind_speed_10m,wind_direction_10m&timezone=auto`);
        break;
      default:
        // Default to wttr.in (global)
        response = await fetch(`https://wttr.in/${lat},${lon}?format=j1`);
        break;
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    let forecastHTML = '';
    const windForecastGrid = document.getElementById('wind-forecast-grid');

    // Parse data based on selected model
    if (selectedModel === 'wttr' && data && data.weather && data.weather[0] && data.weather[0].hourly) {
      // wttr.in format
      const timeIntervals = [0, 3, 6, 9]; // Start with 0 for "Now"
      const usedIndices = new Set();

      timeIntervals.forEach(hours => {
        const targetTime = new Date();
        targetTime.setHours(targetTime.getHours() + hours);

        let closestForecast = null;
        let closestIndex = -1;
        let minDiff = Infinity;

        data.weather[0].hourly.forEach((forecast, index) => {
          if (usedIndices.has(index)) return;

          const forecastTime = new Date(forecast.time);
          const diff = Math.abs(forecastTime - targetTime);
          if (diff < minDiff) {
            minDiff = diff;
            closestForecast = forecast;
            closestIndex = index;
          }
        });

        if (closestForecast && closestForecast.windspeedKmph) {
          usedIndices.add(closestIndex);
          const windSpeedKmph = parseInt(closestForecast.windspeedKmph);
          const windSpeedKts = (windSpeedKmph * 0.539957).toFixed(1);
          const windDeg = parseInt(closestForecast.winddirDegree);
          const windDirection = getWindDirection(windDeg);

          const targetTime = new Date();
          targetTime.setHours(targetTime.getHours() + hours);
          const timeStr = targetTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          const speedKts = parseFloat(windSpeedKts);
          let windColor = '';
          if (speedKts < 10) {
            windColor = 'background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);';
          } else if (speedKts >= 10 && speedKts < 15) {
            windColor = 'background: linear-gradient(135deg, #00b894 0%, #00a085 100%);';
          } else if (speedKts >= 15 && speedKts < 20) {
            windColor = 'background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);';
          } else if (speedKts >= 20 && speedKts < 25) {
            windColor = 'background: linear-gradient(135deg, #e17055 0%, #d63031 100%);';
          } else {
            windColor = 'background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);';
          }

          // Create time label - "Now" for current conditions, "+Xh" for future
          const timeLabel = hours === 0 ? 'Now' : `+${hours}h`;

          forecastHTML += `
            <div class="wind-forecast-item" style="${windColor}">
              <div class="wind-time">${timeLabel} (${timeStr})</div>
              <div class="wind-speed">${windSpeedKts} kts</div>
              <div class="wind-direction">${windDirection} (${windDeg}°)</div>
            </div>
          `;
        }
      });
    } else if (selectedModel === 'ecmwf' && data && data.hourly) {
      // ECMWF format
      const timeIntervals = [0, 3, 6, 9]; // Start with 0 for "Now"
      const usedIndices = new Set();

      timeIntervals.forEach(hours => {
        const targetTime = new Date();
        targetTime.setHours(targetTime.getHours() + hours);

        let closestIndex = -1;
        let minDiff = Infinity;

        data.hourly.time.forEach((timeStr, index) => {
          if (usedIndices.has(index)) return;

          const forecastTime = new Date(timeStr);
          const diff = Math.abs(forecastTime - targetTime);
          if (diff < minDiff) {
            minDiff = diff;
            closestIndex = index;
          }
        });

        if (closestIndex >= 0) {
          usedIndices.add(closestIndex);
          const windSpeedMs = data.hourly.wind_speed_10m[closestIndex];
          const windSpeedKts = (windSpeedMs * 1.94384).toFixed(1); // m/s to knots
          const windDeg = data.hourly.wind_direction_10m[closestIndex];
          const windDirection = getWindDirection(windDeg);

          const targetTime = new Date();
          targetTime.setHours(targetTime.getHours() + hours);
          const timeStr = targetTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          const speedKts = parseFloat(windSpeedKts);
          let windColor = '';
          if (speedKts < 10) {
            windColor = 'background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);';
          } else if (speedKts >= 10 && speedKts < 15) {
            windColor = 'background: linear-gradient(135deg, #00b894 0%, #00a085 100%);';
          } else if (speedKts >= 15 && speedKts < 20) {
            windColor = 'background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);';
          } else if (speedKts >= 20 && speedKts < 25) {
            windColor = 'background: linear-gradient(135deg, #e17055 0%, #d63031 100%);';
          } else {
            windColor = 'background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);';
          }

          // Create time label - "Now" for current conditions, "+Xh" for future
          const timeLabel = hours === 0 ? 'Now' : `+${hours}h`;

          forecastHTML += `
            <div class="wind-forecast-item" style="${windColor}">
              <div class="wind-time">${timeLabel} (${timeStr})</div>
              <div class="wind-speed">${windSpeedKts} kts</div>
              <div class="wind-direction">${windDirection} (${windDeg}°)</div>
            </div>
          `;
        }
      });

    } else {
      // Fallback for other models or errors
      forecastHTML = `
        <div class="wind-forecast-item">
          <div class="wind-time">Model</div>
          <div class="wind-speed">Not</div>
          <div class="wind-direction">Available</div>
        </div>
      `;
    }

    if (forecastHTML) {
      windForecastGrid.innerHTML = forecastHTML;
    } else {
      throw new Error('No forecast data available for this location');
    }
  } catch (error) {
    console.error('Wind forecast fetch error:', error);
    document.getElementById('wind-forecast-grid').innerHTML = `
      <div class="wind-forecast-item" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
        <div class="wind-time">Error</div>
        <div class="wind-speed">${error.message}</div>
        <div class="wind-direction">Try another model</div>
      </div>
    `;
  }
}

// Dark mode functionality
function initDarkMode() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  const html = document.documentElement;

  // Check for saved theme preference or default to light mode
  const savedTheme = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-theme', savedTheme);
  updateDarkModeButton(savedTheme);

  darkModeToggle.addEventListener('click', () => {
      // Prevent multiple clicks while theme is changing
      if (isThemeChanging) {
        console.log('Theme change already in progress, ignoring click');
        return;
      }

      isThemeChanging = true;
      const currentTheme = html.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

      // Update button immediately to show it's been clicked
      updateDarkModeButton(newTheme);

      // Debounce chart updates to prevent rapid toggling issues
      if (themeChangeTimeout) {
        clearTimeout(themeChangeTimeout);
      }
      themeChangeTimeout = setTimeout(() => {
        // Apply theme change after delay
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // Update charts
        updateChartsForTheme(newTheme);

        // Re-render inline sparklines with updated theme colors
        refreshSparklines?.();

        // Re-enable theme changes after chart update completes
        setTimeout(() => {
          isThemeChanging = false;
        }, 200); // Reduced delay to ensure chart is fully rendered
      }, 150); // Reduced delay to 150ms
    });
}

function updateDarkModeButton(theme) {
  const button = document.getElementById('darkModeToggle');
  if (theme === 'dark') {
    button.textContent = '☀️ Light Mode';
    button.style.background = '#f39c12';
  } else {
    button.textContent = '🌙 Dark Mode';
    button.style.background = '#2c3e50';
  }
}

function updateChartsForTheme(theme) {
  // Update tide chart
  if (tideChartInstance) {
    const isDark = theme === 'dark';
    tideChartInstance.options.scales.x.grid.color = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.08)';
    tideChartInstance.options.scales.y.grid.color = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.08)';
    tideChartInstance.options.scales.x.ticks.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.y.ticks.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.x.title.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.y.title.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.data.datasets[0].borderColor = isDark ? '#60a5fa' : '#2563eb';
    tideChartInstance.data.datasets[0].backgroundColor = isDark ? 'rgba(96,165,250,0.12)' : 'rgba(37,99,235,0.1)';

    // Update annotations if they exist
    if (tideChartInstance.options.plugins.annotation && tideChartInstance.options.plugins.annotation.annotations) {
      tideChartInstance.options.plugins.annotation.annotations.forEach(annotation => {
        if (annotation.type === 'label') {
          annotation.backgroundColor = isDark ? 'rgba(96,165,250,0.9)' : 'rgba(37,99,235,0.85)';
          annotation.color = '#ffffff';
          annotation.borderColor = isDark ? '#60a5fa' : '#2563eb';
        }
      });
    }

    tideChartInstance.update();
  }

  // Update polar chart - force complete redraw for point labels
  if (polarData && !isDrawingPolarChart) {
    // Destroy existing chart if it exists
    if (polarChartInstance) {
      polarChartInstance.destroy();
      polarChartInstance = null;
    }

    // Use the same logic as updatePolarPerformance for consistency
    let windAngle = null;
    if (currentEnv?.wind?.angleTrue?.value) {
      windAngle = currentEnv.wind.angleTrue.value;
    } else if (currentEnv?.wind?.angleTrueWater?.value) {
      windAngle = currentEnv.wind.angleTrueWater.value;
    } else if (currentEnv?.wind?.angleApparent?.value) {
      windAngle = currentEnv.wind.angleApparent.value;
    }

    let boatSpeed = null;
    if (currentNav?.speedThroughWater?.value) {
      boatSpeed = currentNav.speedThroughWater.value;
    } else if (currentNav?.speedOverGround?.value) {
      boatSpeed = currentNav.speedOverGround.value;
    }

    let windSpeed = null;
    if (currentEnv?.wind?.speedTrue?.value) {
      windSpeed = currentEnv.wind.speedTrue.value;
    }

    // Use default values if data is missing (same as updatePolarPerformance)
    const twa = windAngle ? windAngle * 180 / Math.PI : 90;
    const bsp = boatSpeed ? boatSpeed * 1.94384 : 0;
    const tws = windSpeed ? windSpeed * 1.94384 : 10;

    // Always draw the chart to ensure it appears
    drawPolarChart(twa, bsp, tws);

  }

  // Update banner colors
  const banner = document.getElementById('updateBanner');
  const statusElement = document.getElementById('dataStatus');
  const timeElement = document.getElementById('updateTime');
  const isDark = theme === 'dark';

  // Update status text colors and banner background
  if (statusElement.textContent.includes('Static Data')) {
    statusElement.style.color = isDark ? '#d4edda' : '#2c3e50';
    banner.style.background = isDark ? '#1e3a1e' : '#dff0d8';
    banner.style.color = isDark ? '#d4edda' : '#2c3e50';
  } else if (statusElement.textContent.includes('API Data') || statusElement.textContent.includes('Streaming')) {
    statusElement.style.color = '#3498db';
    banner.style.background = isDark ? '#1e3a1e' : '#dff0d8';
    banner.style.color = isDark ? '#d4edda' : '#2c3e50';
  } else if (statusElement.textContent.includes('Error') || statusElement.textContent.includes('Demo')) {
    statusElement.style.color = '#f39c12';
    banner.style.background = isDark ? '#3d1e1e' : '#f8d7da';
    banner.style.color = isDark ? '#f8d7da' : '#721c24';
  } else {
    banner.style.background = isDark ? '#1e3a1e' : '#dff0d8';
    banner.style.color = isDark ? '#d4edda' : '#2c3e50';
  }

  // Update map tile layer
  if (map) {
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) {
        map.removeLayer(layer);
      }
    });

    const newTileLayer = isDark
      ? L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '© OpenStreetMap contributors © CARTO'
        })
      : L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '© OpenStreetMap contributors'
        });
    newTileLayer.addTo(map);

    // Re-add marker if it exists
    if (marker) {
      marker.addTo(map);
    }
  }

  // Update anchor distance colors in the data grid
  const anchorDistanceElement = document.querySelector('.info-item .value[style*="color"]');
  if (anchorDistanceElement && anchorDistanceElement.textContent.includes('ft')) {
    const theme = document.documentElement.getAttribute('data-theme');
    // Find the anchor distance element and update its color
    const anchorItems = document.querySelectorAll('.info-item');
    anchorItems.forEach(item => {
      const label = item.querySelector('.label');
      const value = item.querySelector('.value');
      if (label && label.textContent === 'Anchor Distance' && value) {
        const currentColor = value.style.color;
        // Check if it's currently red or green and update accordingly
        if (currentColor.includes('#e74c3c') || currentColor.includes('#ff6b6b')) {
          // Currently red (outside safe radius)
          value.style.color = getAnchorDistanceColor(true, theme);
        } else if (currentColor.includes('#27ae60') || currentColor.includes('#51cf66')) {
          // Currently green (inside safe radius)
          value.style.color = getAnchorDistanceColor(false, theme);
        }
      }
    });
  }
}

    document.addEventListener("DOMContentLoaded", async function() {
  primeSkeletons();
  // Load vessel data first
  await loadVesselData();

  // Load tide stations data
  await loadTideStations();

  initDarkMode();
  loadPolarData();
  loadData();

  // Real-time SignalK updates removed; using static data only

  // Unit toggle: click/tap any info-item with data-unit-group to cycle its units.
  document.addEventListener('click', (e) => {
    const item = e.target.closest('.info-item[data-unit-group]');
    if (!item) return;
    const group = item.dataset.unitGroup;
    if (!UNIT_GROUPS[group]) return;
    unitPrefs[group] = ((unitPrefs[group] || 0) + 1) % UNIT_GROUPS[group].length;
    try { localStorage.setItem(UNIT_PREFS_KEY, JSON.stringify(unitPrefs)); } catch {}
    // Re-render every box in this group from its stored raw SI value.
    document.querySelectorAll(`.info-item[data-unit-group="${group}"]`).forEach(el => {
      const raw = parseFloat(el.dataset.raw);
      const valueEl = el.querySelector('.value');
      if (!valueEl) return;
      const formatted = fmtUnit(group, Number.isFinite(raw) ? raw : null);
      // Preserve colour spans produced by colorValue(); only update the text.
      const inner = valueEl.querySelector('span') || valueEl;
      inner.textContent = formatted;
    });
    if (refreshSparklines) refreshSparklines();
  });

  // Add event listener for forecast model dropdown
  document.getElementById('forecast-model').addEventListener('change', function() {
    if (lat && lon) {
      loadWindForecast();
    }
  });

  // Update wind forecast every hour
  setInterval(() => {
    if (lat && lon) {
      loadWindForecast();
    }
  }, 60 * 60 * 1000);

  // Update wave forecast every hour
  setInterval(() => {
    if (lat && lon) {
      loadWaveForecast();
    }
  }, 60 * 60 * 1000);
});
