const vesselUtils = window.vesselUtils;
if (!vesselUtils) {
  throw new Error('vesselUtils must be loaded before app.js');
}
const { haversine, getAnchorDistanceColor, getWindDirection } = vesselUtils;

let map, marker, trackLine, trackMarkers;
let lat, lon; // Global variables for coordinates
let vesselData = null; // Global vessel information
let tideStations = null; // Global tide stations data
const DEFAULT_TIDE_LOCATION = {
  lat: 37.806,
  lon: -122.465,
  label: 'San Francisco Bay',
};

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

async function loadTrack() {
  try {
    const response = await fetch(`data/telemetry/positions_index.json?ts=${Date.now()}`);
    if (!response.ok) {
      throw new Error(`Positions index not found: ${response.status}`);
    }
    const payload = await response.json();
    const positions = Array.isArray(payload) ? payload : payload.positions;
    if (!Array.isArray(positions)) {
      return;
    }
    const latlngs = positions
      .map((point) => {
        const latitude = Number(point.latitude);
        const longitude = Number(point.longitude);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
          return null;
        }
        return [latitude, longitude];
      })
      .filter(Boolean);

    if (!latlngs.length || !map) {
      return;
    }

    if (!trackMarkers) {
      trackMarkers = L.layerGroup().addTo(map);
    } else {
      trackMarkers.clearLayers();
    }

    if (!trackLine) {
      trackLine = L.polyline(latlngs, {
        color: '#3498db',
        weight: 3,
        opacity: 0.8,
      }).addTo(map);
    } else {
      trackLine.setLatLngs(latlngs);
    }

    positions.forEach((point) => {
      const latitude = Number(point.latitude);
      const longitude = Number(point.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        return;
      }
      const timeLabel = point.timestamp ? new Date(point.timestamp).toLocaleString() : 'N/A';
      const speedValue = Number(point.speedOverGround);
      const speedLabel = Number.isFinite(speedValue)
        ? `${(speedValue * 1.94384).toFixed(1)} kts`
        : 'N/A';
      const courseValue = Number(point.courseOverGroundTrue);
      const courseLabel = Number.isFinite(courseValue)
        ? `${(courseValue * 180 / Math.PI).toFixed(0)}°`
        : 'N/A';
      const tooltip = `<strong>Time:</strong> ${timeLabel}<br/><strong>Speed:</strong> ${speedLabel}<br/><strong>Course:</strong> ${courseLabel}`;
      L.circleMarker([latitude, longitude], {
        radius: 3,
        color: '#1f6fb2',
        fillColor: '#3498db',
        fillOpacity: 0.7,
        weight: 1,
      }).bindTooltip(tooltip, { direction: 'top', opacity: 0.9 }).addTo(trackMarkers);
    });
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
            borderColor: '#3498db',
            backgroundColor: 'rgba(52,152,219,0.1)',
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
              backgroundColor: isDark ? 'rgba(52, 152, 219, 0.9)' : 'rgba(0,0,0,0.7)',
              color: isDark ? '#ffffff' : '#fff',
              font: { size: 10 },
              yAdjust: -20,
              position: 'center',
              borderColor: isDark ? 'rgba(52, 152, 219, 1)' : 'rgba(0,0,0,0.8)',
              borderWidth: 1
            }))
          }
        },
        scales: {
          x: {
            grid: {
              color: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'
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
              color: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'
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

  try {
    console.log('Starting to load data...');

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

    if (modifiedDate && !isNaN(modifiedDate.getTime())) {
      const now = new Date();
      const diffHours = (now - modifiedDate) / (1000 * 60 * 60);
      timeElement.textContent = `Last Updated: ${modifiedDate.toLocaleString()}`;
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (diffHours > 3) {
        banner.style.background = isDark ? "#3d1e1e" : "#f8d7da";
        banner.style.color = isDark ? "#f8d7da" : "#721c24";
      } else {
        banner.style.background = isDark ? "#1e3a1e" : '#dff0d8';
        banner.style.color = isDark ? "#d4edda" : '#2c3e50';
      }
    } else {
      timeElement.textContent = "Timestamp not found";
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
      } else {
        map.setView([lat, lon]);
        marker.setLatLng([lat, lon]);
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

    // Update the instrument dashboard with sailing instruments
    const currentTheme = document.documentElement.getAttribute('data-theme');
    document.getElementById('instrument-grid').innerHTML = `
      <div class="info-item" title="Current vessel latitude position"><div class="label">Latitude</div><div class="value">${lat?.toFixed(6) ?? 'N/A'}</div></div>
      <div class="info-item" title="Current vessel longitude position"><div class="label">Longitude</div><div class="value">${lon?.toFixed(6) ?? 'N/A'}</div></div>
      <div class="info-item" title="Speed Over Ground - actual speed relative to the seabed"><div class="label">SOG</div><div class="value">${nav.speedOverGround?.value ? (nav.speedOverGround.value * 1.94384).toFixed(1) + ' kts' : 'N/A'}</div></div>
      <div class="info-item" title="Speed Through Water - speed relative to the water"><div class="label">STW</div><div class="value">${nav.speedThroughWater?.value ? (nav.speedThroughWater.value * 1.94384).toFixed(1) + ' kts' : 'N/A'}</div></div>
      <div class="info-item" title="Trip distance - distance traveled on current trip"><div class="label">Trip</div><div class="value">${nav.trip?.log?.value ? (nav.trip.log.value / 1852).toFixed(1) + ' nm' : 'N/A'}</div></div>
      <div class="info-item" title="Total log distance - cumulative distance traveled"><div class="label">Log</div><div class="value">${nav.log?.value ? (nav.log.value / 1852).toFixed(1) + ' nm' : 'N/A'}</div></div>
      <div class="info-item" title="True wind speed - actual wind speed in the atmosphere"><div class="label">Wind Speed</div><div class="value">${env.wind?.speedTrue?.value ? (env.wind.speedTrue.value * 1.94384).toFixed(1) + ' kts' : 'N/A'}</div></div>
      <div class="info-item" title="True wind direction - actual wind direction relative to true north"><div class="label">Wind Dir</div><div class="value">${env.wind?.angleTrue?.value ? (env.wind.angleTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Apparent wind angle - wind direction relative to vessel heading"><div class="label">Apparent Wind Angle</div><div class="value">${data.environment?.wind?.angleApparent?.value ? (data.environment.wind.angleApparent.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Apparent wind speed - wind speed as felt on the vessel"><div class="label">Apparent Wind Speed</div><div class="value">${data.environment?.wind?.speedApparent?.value ? (data.environment.wind.speedApparent.value * 1.94384).toFixed(1) + ' kts' : 'N/A'}</div></div>
      <div class="info-item" title="Vessel roll angle from BNO055 IMU"><div class="label">Roll</div><div class="value">${data.navigation?.attitude?.value?.roll ? (data.navigation.attitude.value.roll * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Vessel pitch angle from BNO055 IMU"><div class="label">Pitch</div><div class="value">${data.navigation?.attitude?.value?.pitch ? (data.navigation.attitude.value.pitch * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Course Over Ground - true direction the vessel is moving"><div class="label">COG</div><div class="value">${nav.courseOverGroundTrue?.value ? (nav.courseOverGroundTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Magnetic heading from MMC5603 magnetometer"><div class="label">Mag Heading</div><div class="value">${data.navigation?.headingMagnetic?.value ? (data.navigation.headingMagnetic.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Current rudder angle - positive is starboard, negative is port"><div class="label">Rudder Angle</div><div class="value">${data.steering?.rudderAngle?.value ? (data.steering.rudderAngle.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Distance from anchor position - red if outside safe radius"><div class="label">Anchor Distance</div><div class="value" style="color: ${nav.anchor?.currentRadius?.value && nav.anchor?.maxRadius?.value ? getAnchorDistanceColor(nav.anchor.currentRadius.value > nav.anchor.maxRadius.value, currentTheme) : 'var(--text-primary)'}">${nav.anchor?.currentRadius?.value ? (nav.anchor.currentRadius.value * 3.28084).toFixed(1) + ' ft' : 'N/A'}</div></div>
      <div class="info-item" title="Bearing to anchor position from current location"><div class="label">Anchor Bearing</div><div class="value">${nav.anchor?.bearingTrue?.value ? (nav.anchor.bearingTrue.value * 180 / Math.PI).toFixed(0) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="House battery bank voltage"><div class="label">Battery Voltage</div><div class="value">${elec.batteries?.house?.voltage?.value?.toFixed(2) ?? 'N/A'} V</div></div>
      <div class="info-item" title="House battery bank current - positive is charging, negative is discharging"><div class="label">Battery Current</div><div class="value">${elec.batteries?.house?.current?.value?.toFixed(1) ?? 'N/A'} A</div></div>
      <div class="info-item" title="House battery bank power consumption or generation"><div class="label">Battery Power</div><div class="value">${elec.batteries?.house?.power?.value?.toFixed(1) ?? 'N/A'} W</div></div>
      <div class="info-item" title="State of Charge - percentage of battery capacity remaining"><div class="label">SOC</div><div class="value">${elec.batteries?.house?.capacity?.stateOfCharge?.value ? (elec.batteries.house.capacity.stateOfCharge.value * 100).toFixed(0) + '%' : 'N/A'}</div></div>
      <div class="info-item" title="Estimated time remaining until battery depletion"><div class="label">Battery Time Remaining</div><div class="value">${elec.batteries?.house?.capacity?.timeRemaining?.value ? (elec.batteries.house.capacity.timeRemaining.value / 3600).toFixed(1) + ' hrs' : 'N/A'}</div></div>
    `;

    // Update the vessel information with static vessel data
    document.getElementById('vessel-grid').innerHTML = `
      <div class="info-item" title="Overall vessel length from bow to stern"><div class="label">Vessel Length</div><div class="value">${data.design?.length?.value?.overall ? (data.design.length.value.overall * 3.28084).toFixed(1) + ' ft' : 'N/A'}</div></div>
      <div class="info-item" title="Vessel beam - maximum width of the vessel"><div class="label">Vessel Beam</div><div class="value">${data.design?.beam?.value ? (data.design.beam.value * 3.28084).toFixed(1) + ' ft' : 'N/A'}</div></div>
      <div class="info-item" title="Maximum vessel draft - depth below waterline"><div class="label">Vessel Draft</div><div class="value">${data.design?.draft?.value?.maximum ? (data.design.draft.value.maximum * 3.28084).toFixed(1) + ' ft' : 'N/A'}</div></div>
      <div class="info-item" title="Vessel air height - height above waterline"><div class="label">Air Height</div><div class="value">${data.design?.airHeight?.value ? (data.design.airHeight.value * 3.28084).toFixed(1) + ' ft' : 'N/A'}</div></div>
      <div class="info-item" title="Vessel name from SignalK"><div class="label">Vessel Name</div><div class="value">${data.name || 'N/A'}</div></div>
      <div class="info-item" title="Maritime Mobile Service Identity - unique vessel identifier"><div class="label">MMSI</div><div class="value">${data.mmsi || vesselData?.mmsi || 'N/A'}</div></div>
      <div class="info-item" title="VHF radio callsign"><div class="label">Callsign</div><div class="value">${data.communication?.callsignVhf || 'N/A'}</div></div>
      <div class="info-item" title="Hull Number (Assigned by Beneteau)"><div class="label">Hull #</div><div class="value">${vesselData?.hull_number || 'N/A'}</div></div>
      <div class="info-item" title="US Coast Guard vessel registration number"><div class="label">USCG #</div><div class="value">${vesselData?.uscg_number || 'N/A'}</div></div>
    `;

    const isNumericValue = (val) => typeof val === 'number' && Number.isFinite(val);
    const toPercent = (val, digits = 0) =>
      isNumericValue(val) ? `${(val * 100).toFixed(digits)}%` : 'N/A';
    const toGallons = (val) =>
      isNumericValue(val) ? `${(val * 264.172).toFixed(1)} gal` : null;
    const toFahrenheit = (val) =>
      isNumericValue(val) ? `${((val - 273.15) * 9/5 + 32).toFixed(1)}°F` : null;
    const formatTankDisplay = (level, volume, temp) => {
      const parts = [];
      const levelDisplay = toPercent(level);
      if (levelDisplay !== 'N/A') parts.push(levelDisplay);
      const volumeDisplay = toGallons(volume);
      if (volumeDisplay) parts.push(volumeDisplay);
      const tempDisplay = toFahrenheit(temp);
      if (tempDisplay) parts.push(tempDisplay);
      return parts.length ? parts.join(' | ') : 'N/A';
    };
    // Update the environment with environmental data
    document.getElementById('environment-grid').innerHTML = `
      <div class="info-item" title="Water temperature at the surface"><div class="label">Water Temp</div><div class="value">${env.water?.temperature?.value ? ((env.water.temperature.value - 273.15) * 9/5 + 32).toFixed(1) + '°F' : 'N/A'}</div></div>
      <div class="info-item" title="Inside air temperature from BME280 sensor"><div class="label">Inside Temp</div><div class="value">${data.environment?.inside?.temperature?.value ? ((data.environment.inside.temperature.value - 273.15) * 9/5 + 32).toFixed(1) + '°F' : 'N/A'}</div></div>
      <div class="info-item" title="Inside humidity from BME280 sensor"><div class="label">Inside Humidity</div><div class="value">${data.environment?.inside?.humidity?.value ? (data.environment.inside.humidity.value * 100).toFixed(1) + '%' : 'N/A'}</div></div>
      <div class="info-item" title="Inside barometric pressure from BME280 sensor"><div class="label">Barometric Pressure</div><div class="value">${data.environment?.inside?.pressure?.value ? (data.environment.inside.pressure.value * 0.0002953).toFixed(2) + ' inHg' : 'N/A'}</div></div>
      <div class="info-item" title="Indoor air quality - Total Volatile Organic Compounds"><div class="label">TVOC</div><div class="value">${data.environment?.inside?.airQuality?.tvoc?.value ? data.environment.inside.airQuality.tvoc.value.toFixed(0) + ' ppb' : 'N/A'}</div></div>
      <div class="info-item" title="Indoor air quality - Carbon Dioxide equivalent"><div class="label">CO₂</div><div class="value">${data.environment?.inside?.airQuality?.eco2?.value ? data.environment.inside.airQuality.eco2.value.toFixed(0) + ' ppm' : 'N/A'}</div></div>
      <div class="info-item" title="Magnetic variation at current position - difference between true and magnetic north"><div class="label">Magnetic Variation</div><div class="value">${data.navigation?.magneticVariation?.value ? (data.navigation.magneticVariation.value * 180 / Math.PI).toFixed(1) + '°' : 'N/A'}</div></div>
      <div class="info-item" title="Sunrise time today"><div class="label">Sunrise</div><div class="value">${data.environment?.sunlight?.times?.sunrise?.value ? new Date(data.environment.sunlight.times.sunrise.value).toLocaleTimeString() : 'N/A'}</div></div>
      <div class="info-item" title="Sunset time today"><div class="label">Sunset</div><div class="value">${data.environment?.sunlight?.times?.sunset?.value ? new Date(data.environment.sunlight.times.sunset.value).toLocaleTimeString() : 'N/A'}</div></div>
    `;

    const internet = data.internet || {};
    const packetLossValue = internet.packetLoss?.value;
    const packetLossDisplay = isNumericValue(packetLossValue)
      ? `${(packetLossValue <= 1 ? packetLossValue * 100 : packetLossValue).toFixed(1)}%`
      : 'N/A';
    document.getElementById('internet-grid').innerHTML = `
      <div class="info-item" title="Internet service provider"><div class="label">ISP</div><div class="value">${internet.ISP?.value || 'N/A'}</div></div>
      <div class="info-item" title="Download speed"><div class="label">Download</div><div class="value">${isNumericValue(internet.speed?.download?.value) ? internet.speed.download.value.toFixed(1) + ' Mbps' : 'N/A'}</div></div>
      <div class="info-item" title="Upload speed"><div class="label">Upload</div><div class="value">${isNumericValue(internet.speed?.upload?.value) ? internet.speed.upload.value.toFixed(1) + ' Mbps' : 'N/A'}</div></div>
      <div class="info-item" title="Ping latency"><div class="label">Latency</div><div class="value">${isNumericValue(internet.ping?.latency?.value) ? internet.ping.latency.value.toFixed(1) + ' ms' : 'N/A'}</div></div>
      <div class="info-item" title="Ping jitter"><div class="label">Jitter</div><div class="value">${isNumericValue(internet.ping?.jitter?.value) ? internet.ping.jitter.value.toFixed(1) + ' ms' : 'N/A'}</div></div>
      <div class="info-item" title="Packet loss percentage"><div class="label">Packet Loss</div><div class="value">${packetLossDisplay}</div></div>
    `;

    const propulsion = data.propulsion?.port || {};
    const rpmValue = propulsion.revolutions?.value;
    document.getElementById('propulsion-grid').innerHTML = `
      <div class="info-item" title="Engine state"><div class="label">State</div><div class="value">${propulsion.state?.value || 'N/A'}</div></div>
      <div class="info-item" title="Engine revolutions per minute"><div class="label">RPM</div><div class="value">${isNumericValue(rpmValue) ? (rpmValue * 60).toFixed(0) + ' RPM' : 'N/A'}</div></div>
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
      <div class="info-item" title="Main fuel tank level, volume, and temperature (if available)"><div class="label">Fuel (Main)</div><div class="value">${formatTankDisplay(fuelMain.currentLevel?.value, fuelMain.currentVolume?.value, fuelMain.temperature?.value)}</div></div>
      <div class="info-item" title="Reserve fuel tank level, volume, and temperature (if available)"><div class="label">Fuel (Reserve)</div><div class="value">${formatTankDisplay(fuelReserve.currentLevel?.value, fuelReserve.currentVolume?.value, fuelReserve.temperature?.value)}</div></div>
      <div class="info-item" title="Fresh water tank 1 level and volume"><div class="label">Fresh Water 1</div><div class="value">${formatTankDisplay(freshWater0.currentLevel?.value, freshWater0.currentVolume?.value, null)}</div></div>
      <div class="info-item" title="Fresh water tank 2 level and volume"><div class="label">Fresh Water 2</div><div class="value">${formatTankDisplay(freshWater1.currentLevel?.value, freshWater1.currentVolume?.value, null)}</div></div>
      <div class="info-item" title="Propane tank A level and temperature"><div class="label">Propane A</div><div class="value">${formatTankDisplay(propaneA.currentLevel?.value, null, propaneA.temperature?.value)}</div></div>
      <div class="info-item" title="Propane tank B level and temperature"><div class="label">Propane B</div><div class="value">${formatTankDisplay(propaneB.currentLevel?.value, null, propaneB.temperature?.value)}</div></div>
      <div class="info-item" title="Blackwater tank level and temperature"><div class="label">Blackwater</div><div class="value">${formatTankDisplay(blackwaterBow.currentLevel?.value, null, blackwaterBow.temperature?.value)}</div></div>
      <div class="info-item" title="Bilge level"><div class="label">Bilge</div><div class="value">${formatTankDisplay(liveWell0.currentLevel?.value, null, null)}</div></div>
    `;
  } catch (err) {
    console.error("Failed to load data:", err);
    console.error("Error details:", err.message);
    const banner = document.getElementById('updateBanner');
    banner.textContent = `Error loading data: ${err.message}`;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    banner.style.background = isDark ? "#3d1e1e" : "#f8d7da";
    banner.style.color = isDark ? "#f8d7da" : "#721c24";
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
        borderColor: isClosestWindSpeed ? (isDark ? '#ffffff' : '#000000') : `hsla(${hue}, 70%, 50%, 0.50)`, // 50% alpha for non-current lines
        backgroundColor: isClosestWindSpeed ? (isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)') : `hsla(${hue}, 70%, 50%, 0.025)`, // Reduced alpha for background too
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
    borderColor: isDark ? '#ffffff' : '#000000',
    backgroundColor: isDark ? '#ffffff' : '#000000',
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
              color: isDark ? 'rgba(255, 255, 255, 0.4)' : 'rgba(0, 0, 0, 0.1)'
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
        response = await fetch(`https://wttr.in/?format=j1&lat=${lat}&lon=${lon}`);
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
    tideChartInstance.options.scales.x.grid.color = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';
    tideChartInstance.options.scales.y.grid.color = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';
    tideChartInstance.options.scales.x.ticks.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.y.ticks.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.x.title.color = isDark ? '#ffffff' : '#2c3e50';
    tideChartInstance.options.scales.y.title.color = isDark ? '#ffffff' : '#2c3e50';

    // Update annotations if they exist
    if (tideChartInstance.options.plugins.annotation && tideChartInstance.options.plugins.annotation.annotations) {
      tideChartInstance.options.plugins.annotation.annotations.forEach(annotation => {
        if (annotation.type === 'label') {
          annotation.backgroundColor = isDark ? 'rgba(52, 152, 219, 0.9)' : 'rgba(0,0,0,0.7)';
          annotation.color = isDark ? '#ffffff' : '#fff';
          annotation.borderColor = isDark ? 'rgba(52, 152, 219, 1)' : 'rgba(0,0,0,0.8)';
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
  // Load vessel data first
  await loadVesselData();

  // Load tide stations data
  await loadTideStations();

  initDarkMode();
  loadPolarData();
  loadData();

  // Real-time SignalK updates removed; using static data only

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
