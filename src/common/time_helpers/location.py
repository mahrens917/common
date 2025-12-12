"""Location-based time utilities."""

import logging

logger = logging.getLogger(__name__)

# Geographic coordinate bounds
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

# Timezone heuristic longitude ranges
PACIFIC_HONOLULU_MIN_LON = -180
PACIFIC_HONOLULU_MAX_LON = -120
ASIA_TOKYO_MIN_LON = 120
ASIA_TOKYO_MAX_LON = 180
EUROPE_LONDON_MIN_LON = -15
EUROPE_LONDON_MAX_LON = 40


def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Get timezone name from geographic coordinates.

    Args:
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)

    Returns:
        Timezone name string (e.g., "America/New_York")

    Raises:
        ValueError: If coordinates are out of valid range
    """
    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
        raise ValueError(f"Latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}, got {latitude}")
    if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ValueError(f"Longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}, got {longitude}")

    try:
        from timezonefinder import TimezoneFinder

        tf = TimezoneFinder()
        timezone_name = tf.timezone_at(lat=latitude, lng=longitude)

        if timezone_name is None:
            logger.warning(
                "No timezone found for coordinates (%.4f, %.4f), defaulting to UTC",
                latitude,
                longitude,
            )
            return "UTC"
    except ImportError:  # policy_guard: allow-silent-handler
        logger.warning("timezonefinder not available, using simple heuristic")
        return _get_timezone_heuristic(latitude, longitude)
    else:
        return timezone_name


def _get_timezone_heuristic(latitude: float, longitude: float) -> str:
    """
    Simple heuristic timezone lookup based on longitude.

    This is a fallback when timezonefinder is not available.
    It's not accurate but provides reasonable defaults for common cases.

    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees

    Returns:
        Timezone name
    """
    # Define timezone regions as (lon_min, lon_max, lat_min, lat_max, timezone_name)
    regions = [
        (-79, -67, 38, 45, "America/New_York"),
        (-125, -114, 32, 42, "America/Los_Angeles"),
        (-106, -93, 25, 37, "America/Chicago"),
        (-112, -102, 31, 45, "America/Denver"),
    ]

    # Check specific regional boundaries
    for lon_min, lon_max, lat_min, lat_max, tz_name in regions:
        if lon_min <= longitude <= lon_max and lat_min <= latitude <= lat_max:
            return tz_name

    # Check broad longitude-based zones
    if PACIFIC_HONOLULU_MIN_LON <= longitude < PACIFIC_HONOLULU_MAX_LON:
        return "Pacific/Honolulu"
    if ASIA_TOKYO_MIN_LON <= longitude <= ASIA_TOKYO_MAX_LON:
        return "Asia/Tokyo"
    if EUROPE_LONDON_MIN_LON <= longitude <= EUROPE_LONDON_MAX_LON:
        return "Europe/London"

    return "UTC"
