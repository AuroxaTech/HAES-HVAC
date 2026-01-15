"""
Service Area Validation Utility

Validates addresses are within 35-mile radius of downtown Dallas.
"""

import logging
from typing import Any
import math

logger = logging.getLogger(__name__)

# Downtown Dallas coordinates (approximate center)
DALLAS_CENTER_LAT = 32.7767
DALLAS_CENTER_LON = -96.7970

# Service radius in miles
SERVICE_RADIUS_MILES = 35


def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    
    Returns distance in miles.
    """
    # Earth's radius in miles
    R = 3959.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    return distance


def geocode_address(address: str) -> tuple[float, float] | None:
    """
    Geocode an address to get latitude/longitude.
    
    For now, this is a placeholder. In production, you'd use a geocoding service
    like Google Maps API, Mapbox, or similar.
    
    Returns:
        (latitude, longitude) or None if geocoding fails
    """
    # TODO: Implement actual geocoding
    # For now, return None to indicate we can't validate
    # This allows the system to continue without blocking
    logger.warning(f"Geocoding not implemented, cannot validate address: {address}")
    return None


def is_within_service_area(address: str | None, zip_code: str | None = None) -> tuple[bool, str | None]:
    """
    Check if an address is within the 35-mile service radius.
    
    Args:
        address: Full address string
        zip_code: Optional ZIP code for faster lookup
        
    Returns:
        (is_within_area, error_message)
        If geocoding is unavailable, returns (True, None) to allow continuation
    """
    if not address and not zip_code:
        return False, "Address or ZIP code required"
    
    # Try to geocode
    coords = None
    if address:
        coords = geocode_address(address)
    
    # If geocoding not available, allow continuation (don't block)
    if coords is None:
        logger.info("Geocoding unavailable, allowing service request to proceed")
        return True, None
    
    lat, lon = coords
    
    # Calculate distance
    distance = calculate_distance_miles(
        DALLAS_CENTER_LAT, DALLAS_CENTER_LON,
        lat, lon
    )
    
    if distance > SERVICE_RADIUS_MILES:
        return False, f"We service within {SERVICE_RADIUS_MILES} miles of downtown Dallas. Your location is approximately {distance:.1f} miles away."
    
    return True, None
