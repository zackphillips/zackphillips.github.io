// Shared constants for the vessel tracker frontend.
// Magic numbers extracted here so thresholds are easy to find and tune.

const VESSEL_CONSTANTS = Object.freeze({
  // ── Classification thresholds ────────────────────────────────────────────
  BATTERY_OK_PCT:       75,    // % state-of-charge → ok
  BATTERY_WARN_PCT:     45,    // % → warn (below is alert)
  BATTERY_TIME_OK_H:    6,     // hours remaining → ok
  BATTERY_TIME_WARN_H:  2,     // hours → warn (below is alert)

  ANCHOR_WARN_RATIO:    0.85,  // current/max ratio → ok below, warn above
  ANCHOR_EDGE_RATIO:    1.05,  // → warn below, alert above

  PACKET_LOSS_OK_PCT:   1,     // % packet loss → ok
  PACKET_LOSS_WARN_PCT: 3,     // % → warn (above is alert)

  TANK_OK_RATIO:        0.35,  // fill ratio → ok (above)
  TANK_WARN_RATIO:      0.20,  // → warn (below is alert)
  WASTE_WARN_RATIO:     0.40,  // fill ratio → ok (below)
  WASTE_ALERT_RATIO:    0.70,  // → warn (above is alert)

  // ── Cache TTLs (milliseconds) ────────────────────────────────────────────
  FORECAST_CACHE_TTL_MS: 60 * 60 * 1000,      // 1 hour
  TIDE_CACHE_TTL_MS:     3 * 60 * 60 * 1000,  // 3 hours

  // ── Data display ─────────────────────────────────────────────────────────
  SPARKLINE_POINTS:           60,   // number of history points per sparkline
  DEFAULT_RECENT_TRACK_COUNT:  3,   // coloured track days shown by default

  // ── Fallback privacy zone (South Beach Harbor, SF) ───────────────────────
  // Overridden at runtime by privacy_zones in data/vessel/info.yaml.
  FALLBACK_PRIVACY_ZONE_LAT:    37.7802069,
  FALLBACK_PRIVACY_ZONE_LON:   -122.3858040,
  FALLBACK_PRIVACY_ZONE_RADIUS_M: 200,

  // ── Fallback tide / geocoding location ───────────────────────────────────
  DEFAULT_TIDE_LAT:   37.806,
  DEFAULT_TIDE_LON: -122.465,
  DEFAULT_TIDE_LABEL: 'San Francisco Bay',

  // ── Data URLs ────────────────────────────────────────────────────────────
  SNAPSHOT_INDEX_URL:   'data/telemetry/snapshots_index.json',  // legacy, kept for reference
  TRACKS_INDEX_URL:     'data/telemetry/tracks_index.json',
  POSITIONS_INDEX_URL:  'data/telemetry/positions_index.json',
  INSTRUMENT_LOG_URL:   'data/telemetry/instrument_log.json',
  INSTRUMENT_LOG_ENTRIES: 120,  // must match backend INSTRUMENT_LOG_ENTRIES
});
