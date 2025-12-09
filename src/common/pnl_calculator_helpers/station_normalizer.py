"""
Weather station name standardization logic.

Handles conversion of various station name formats to standardized K-prefixed format.
"""

# Constants
_CONST_3 = 3
_CONST_4 = 4


class StationNameNormalizer:
    """Standardizes weather station names to 4-letter K-prefixed format."""

    @staticmethod
    def standardize_station_name(station: str) -> str:
        """
        Standardize weather station names to 4-letter K-prefixed format.

        Args:
            station: Original station name

        Returns:
            Standardized 4-letter K-prefixed station name
        """
        # Handle specific consolidations first
        if station == "DEN":
            return "KDEN"

        # Common station mappings to standardized 4-letter K format
        station_mappings = {
            "AUS": "KAUS",
            "CHI": "KCHI",
            "LAX": "KLAX",
            "MIA": "KMIA",
            "NY": "KNYC",
            "PHIL": "KPHL",
            "LGA": "KLGA",
            "KLGA": "KLGA",  # Already correct but handle KLGA -> KLGA
        }

        # If station is already in correct format (4 letters starting with K), return as-is
        if len(station) == _CONST_4 and station.startswith("K"):
            return station

        # Apply mapping if available
        if station in station_mappings:
            return station_mappings[station]

        # For unknown stations, try to standardize by adding K prefix if needed
        if len(station) == _CONST_3 and not station.startswith("K"):
            return f"K{station}"

        # Return as-is if no standardization rule applies
        return station
