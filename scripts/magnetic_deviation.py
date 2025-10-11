#!/usr/bin/env python3
"""
Magnetic Deviation Calculation Module

This module provides functions to calculate magnetic declination (variation)
based on latitude, longitude, and date using the NOAA World Magnetic Model.
"""

import json
import logging
import math
from datetime import UTC, datetime

import requests

logger = logging.getLogger(__name__)

# Try to import geomag library for magnetic declination calculation
try:
    import geomag
    GEOMAG_AVAILABLE = True
except ImportError:
    GEOMAG_AVAILABLE = False

# NOAA Magnetic Declination API endpoint (backup method)
NOAA_MAGNETIC_API_URL = "https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"

def calculate_magnetic_declination(
    latitude: float,
    longitude: float,
    date: datetime | None = None,
    elevation: float = 0.0
) -> float | None:
    """
    Calculate magnetic declination (variation) for given coordinates.

    Args:
        latitude: Latitude in decimal degrees (positive for North, negative for South)
        longitude: Longitude in decimal degrees (positive for East, negative for West)
        date: Date for calculation (defaults to current date)
        elevation: Elevation in meters above sea level (defaults to 0)

    Returns:
        Magnetic declination in radians (positive for East, negative for West)
        Returns None if calculation fails
    """
    if date is None:
        date = datetime.now(UTC)

    # Try geomag library first (more reliable)
    if GEOMAG_AVAILABLE:
        try:
            logger.debug(f"Calculating magnetic declination using geomag for lat={latitude}, lon={longitude}, date={date}")

            # Convert elevation from meters to kilometers
            elevation_km = elevation / 1000.0

            # Calculate declination using geomag
            # Convert datetime to date for geomag compatibility
            date_for_geomag = date.date()
            declination_deg = geomag.declination(latitude, longitude, h=elevation_km, time=date_for_geomag)

            # Convert degrees to radians
            declination_rad = math.radians(declination_deg)

            logger.info(f"Magnetic declination (geomag): {declination_deg:.2f}° ({declination_rad:.4f} rad)")
            return declination_rad

        except Exception as e:
            logger.warning(f"Geomag calculation failed: {e}, trying NOAA API")

    # Fallback to NOAA API
    try:
        # Prepare API request parameters
        params = {
            'lat1': latitude,
            'lon1': longitude,
            'model': 'WMM',
            'startYear': date.year,
            'startMonth': date.month,
            'startDay': date.day,
            'endYear': date.year,
            'endMonth': date.month,
            'endDay': date.day,
            'resultFormat': 'json'
        }

        # Add elevation if provided
        if elevation > 0:
            params['height'] = elevation

        logger.debug(f"Requesting magnetic declination from NOAA API for lat={latitude}, lon={longitude}, date={date}")

        # Make API request
        response = requests.get(NOAA_MAGNETIC_API_URL, params=params, timeout=10)
        response.raise_for_status()

        # Parse response
        data = response.json()

        if 'result' in data and len(data['result']) > 0:
            result = data['result'][0]
            declination_deg = result.get('declination', 0.0)

            # Convert degrees to radians
            declination_rad = math.radians(declination_deg)

            logger.info(f"Magnetic declination (NOAA API): {declination_deg:.2f}° ({declination_rad:.4f} rad)")
            return declination_rad
        else:
            logger.error("No declination data in NOAA API response")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"NOAA API request failed: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Error parsing NOAA API response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error calculating magnetic declination: {e}")
        return None


def get_position_from_signalk(signalk_host: str, signalk_port: int) -> tuple[float, float] | None:
    """
    Get current vessel position from SignalK server.

    Args:
        signalk_host: SignalK server hostname or IP
        signalk_port: SignalK server port

    Returns:
        Tuple of (latitude, longitude) in decimal degrees, or None if unavailable
    """
    try:
        # Construct SignalK API URL
        api_url = f"http://{signalk_host}:{signalk_port}/signalk/v1/api/vessels/self/navigation/position"

        logger.debug(f"Requesting position from SignalK: {api_url}")

        # Make API request
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()

        # Parse response
        data = response.json()

        if 'value' in data:
            position = data['value']
            latitude = position.get('latitude')
            longitude = position.get('longitude')

            if latitude is not None and longitude is not None:
                logger.info(f"Retrieved position: lat={latitude:.6f}, lon={longitude:.6f}")
                return (latitude, longitude)
            else:
                logger.warning("Position data missing latitude or longitude")
                return None
        else:
            logger.warning("No position value in SignalK response")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get position from SignalK: {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing SignalK position response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting position: {e}")
        return None


def calculate_magnetic_declination_from_signalk(
    signalk_host: str,
    signalk_port: int,
    date: datetime | None = None,
    elevation: float = 0.0
) -> float | None:
    """
    Calculate magnetic declination using current vessel position from SignalK.

    Args:
        signalk_host: SignalK server hostname or IP
        signalk_port: SignalK server port
        date: Date for calculation (defaults to current date)
        elevation: Elevation in meters above sea level (defaults to 0)

    Returns:
        Magnetic declination in radians, or None if calculation fails
    """
    # Get current position
    position = get_position_from_signalk(signalk_host, signalk_port)

    if position is None:
        logger.warning("Could not get vessel position from SignalK")
        return None

    latitude, longitude = position

    # Calculate magnetic declination
    return calculate_magnetic_declination(latitude, longitude, date, elevation)


def load_cached_declination(cache_file: str = "data/magnetic_declination_cache.json") -> float | None:
    """
    Load cached magnetic declination value.

    Args:
        cache_file: Path to cache file

    Returns:
        Cached declination in radians, or None if not available
    """
    try:
        with open(cache_file) as f:
            cache_data = json.load(f)

        # Check if cache is still valid (less than 24 hours old)
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        age_hours = (datetime.now(UTC) - cache_time).total_seconds() / 3600

        if age_hours < 24:
            logger.info(f"Using cached magnetic declination: {math.degrees(cache_data['declination']):.2f}°")
            return cache_data['declination']
        else:
            logger.info(f"Cache expired ({age_hours:.1f} hours old)")
            return None

    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.debug(f"No valid cache available: {e}")
        return None


def save_cached_declination(
    declination: float,
    cache_file: str = "data/magnetic_declination_cache.json"
) -> bool:
    """
    Save magnetic declination to cache file.

    Args:
        declination: Declination value in radians
        cache_file: Path to cache file

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        import os
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        cache_data = {
            'declination': declination,
            'timestamp': datetime.now(UTC).isoformat(),
            'declination_degrees': math.degrees(declination)
        }

        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

        logger.info(f"Cached magnetic declination: {math.degrees(declination):.2f}°")
        return True

    except Exception as e:
        logger.error(f"Failed to save declination cache: {e}")
        return False


def get_magnetic_declination_with_cache(
    signalk_host: str,
    signalk_port: int,
    cache_file: str = "data/magnetic_declination_cache.json",
    force_refresh: bool = False
) -> float | None:
    """
    Get magnetic declination with caching to avoid frequent API calls.

    Args:
        signalk_host: SignalK server hostname or IP
        signalk_port: SignalK server port
        cache_file: Path to cache file
        force_refresh: Force refresh even if cache is valid

    Returns:
        Magnetic declination in radians, or None if calculation fails
    """
    # Try to load from cache first (unless forcing refresh)
    if not force_refresh:
        cached_declination = load_cached_declination(cache_file)
        if cached_declination is not None:
            return cached_declination

    # Calculate new declination
    declination = calculate_magnetic_declination_from_signalk(signalk_host, signalk_port)

    if declination is not None:
        # Save to cache
        save_cached_declination(declination, cache_file)

    return declination


if __name__ == "__main__":
    # Test the module
    import argparse

    parser = argparse.ArgumentParser(description="Test magnetic declination calculation")
    parser.add_argument("--lat", type=float, help="Latitude in decimal degrees")
    parser.add_argument("--lon", type=float, help="Longitude in decimal degrees")
    parser.add_argument("--signalk-host", help="SignalK server host")
    parser.add_argument("--signalk-port", type=int, default=3000, help="SignalK server port")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.lat is not None and args.lon is not None:
        # Test with provided coordinates
        declination = calculate_magnetic_declination(args.lat, args.lon)
        if declination is not None:
            print(f"Magnetic declination: {math.degrees(declination):.2f}° ({declination:.4f} rad)")
        else:
            print("Failed to calculate magnetic declination")
    elif args.signalk_host:
        # Test with SignalK position
        declination = get_magnetic_declination_with_cache(args.signalk_host, args.signalk_port)
        if declination is not None:
            print(f"Magnetic declination: {math.degrees(declination):.2f}° ({declination:.4f} rad)")
        else:
            print("Failed to calculate magnetic declination")
    else:
        print("Please provide either --lat/--lon coordinates or --signalk-host")
